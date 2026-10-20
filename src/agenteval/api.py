"""Stable public layer over the extracted evaluation engine.

Rule expressions are trusted Python, not a sandbox. Detailed engine compatibility
scores are deliberately not used as quality metrics in this interface.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import yaml

from .adapters import normalize_traces
from .engine.core.pipeline import PipelineConfig, run_combined
from .engine.core.evaluator_spec import normalize_config, OUTPUT_CONTRACTS
from .engine.core.rules import load_rules_from_dict
from .engine.llm.runtime import public_model_config


def _rules(text):
    if not text.strip():
        return []
    cfg = yaml.safe_load(text)
    if not isinstance(cfg, dict):
        raise ValueError("Rules YAML must be an object.")
    rules, _ = load_rules_from_dict(cfg)
    active = [r for r in rules if r.enabled]
    ids = [r.id for r in active]
    if len(ids) != len(set(ids)):
        raise ValueError("Rule IDs must be unique.")
    for rule in active:
        try:
            compile(rule.check_expr, "<rule>", "eval")
        except (SyntaxError, TypeError) as exc:
            raise ValueError(f"Invalid Python expression in rule {rule.id}.") from exc
    return active


def _evaluators(text):
    if not text.strip():
        return []
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        raise ValueError("Evaluator YAML must be an object.")
    cfg = normalize_config(doc)
    entries = cfg.get("evaluators", [])
    if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
        raise ValueError("evaluators must be a list of objects.")
    evs = [e for e in entries if e.get("enabled", True)]
    names = [e.get("name") for e in evs]
    if any(not isinstance(n, str) or not n for n in names) or len(names) != len(set(names)):
        raise ValueError("Evaluator names must be non-empty and unique.")
    for ev in evs:
        if ev.get("iterate_over", "trace") != "trace":
            raise ValueError("This release supports iterate_over=trace only.")
        if ev.get("enable_fewshot"):
            raise ValueError("External few-shot retrieval is not included in this release.")
        if ev.get("prompt"):
            if ev.get("output_contract") not in OUTPUT_CONTRACTS:
                raise ValueError("LLM evaluators must declare tristate_v1, binary_score_v1 or binary_passed_v1.")
        elif not ev.get("inline_rules"):
            raise ValueError("Each evaluator needs a prompt or inline_rules.")
        if ev.get("inline_rules"):
            _rules(yaml.safe_dump(ev["inline_rules"]))
    return evs


def _atomic(trace_id, rule_id, outcome, reason, kind="code"):
    return {"trace_id": trace_id, "evaluator": rule_id, "outcome": outcome,
            "status": {1: "pass", 0: "not_applicable", -1: "fail", None: "error"}[outcome],
            "reason": reason, "kind": kind}


async def evaluate(traces, *, rules_yaml="", evaluators_yaml="", model_options=None,
                   concurrency=4, n_runs=1):
    """Evaluate text traces; no network calls are made without LLM evaluators.

    Returns JSON-serializable traces, atomic checks, counts and config hashes.
    Error checks have null outcomes; N/A and errors never count as passes.
    """
    traces = normalize_traces(traces)
    rules, evaluators = _rules(rules_yaml), _evaluators(evaluators_yaml)
    if not rules and not evaluators:
        raise ValueError("Provide at least one enabled rule or evaluator.")
    if not isinstance(concurrency, int) or not 1 <= concurrency <= 20:
        raise ValueError("concurrency must be between 1 and 20.")
    if not isinstance(n_runs, int) or not 1 <= n_runs <= 20:
        raise ValueError("n_runs must be between 1 and 20.")
    opts = dict(model_options or {})
    uses_model = any(e.get("prompt") for e in evaluators)
    if uses_model and (not opts.get("base_url") or not opts.get("model")):
        raise ValueError("LLM evaluation needs AGENTEVAL_BASE_URL and AGENTEVAL_MODEL (or model_options).")
    result = await run_combined(traces, PipelineConfig(
        rules_yaml=rules_yaml, llm_yaml=evaluators_yaml, enable_llm=uses_model,
        llm_options=opts if uses_model else {}, concurrency=concurrency, n_runs=n_runs,
        source_name="User-supplied traces"))
    checks = []
    by_id = {r.get("full_trace_id", r["trace_id"]): r for r in result.rule_results}
    llm_rows = {(r.get("full_trace_id", r["trace_id"]), r["evaluator"]): r for r in result.llm_results}
    for trace in traces:
        tid = trace["id"]
        for rule in rules:
            row = by_id.get(tid, {})
            outcome = row.get("rule_outcomes", {}).get(rule.id)
            if outcome is None:
                reason = "Rule execution error or missing result; inspect the trusted expression and trace schema."
            elif outcome == 0:
                reason = f"Scope {rule.scope} was not activated."
            else:
                reason = f"{rule.description or rule.name} | check evaluated to {outcome == -1}: {rule.check_expr}"
            checks.append(_atomic(tid, rule.id, outcome, reason))
        for ev in evaluators:
            row = llm_rows.get((tid, ev["name"]), {})
            # Inline rules are separate checks, even when also passed to a judge.
            if ev.get("inline_rules"):
                for rule in _rules(yaml.safe_dump(ev["inline_rules"])):
                    outcomes = row.get("rule_outcomes") or {
                        x["id"]: x.get("outcome") for x in (row.get("rule_check") or {}).get("all_rules", [])}
                    outcome = outcomes.get(rule.id)
                    checks.append(_atomic(tid, ev["name"] + "/" + rule.id, outcome,
                        "Inline rule: " + (rule.description or rule.check_expr) if outcome is not None
                        else "Inline rule execution error or missing result."))
            if not ev.get("prompt"):
                continue
            status = row.get("execution_status", "technical_error")
            if status != "ok":
                outcome, reason = None, f"Evaluation incomplete ({status}). Check model configuration, response contract and required evidence."
            else:
                outcome = row.get("outcome")
                if outcome is None:
                    outcome = 1 if row.get("passed") else -1
                reason = "\n".join(s.get("reason", "") for s in row.get("steps", []))
            item = _atomic(tid, ev["name"], outcome, reason, "llm")
            item.update(evaluator_version=row.get("evaluator_version"), evaluator_hash=row.get("evaluator_hash"))
            if row.get("stability"):
                item["repetitions"] = {k: row["stability"][k] for k in
                    ("valid_runs", "technical_errors", "agreement_rate") if k in row["stability"]}
            checks.append(item)
    counts = Counter(c["status"] for c in checks)
    summary = {k: counts[k] for k in ("pass", "fail", "not_applicable", "error")}
    summary.update(traces=len(traces), checks=len(checks))
    public = public_model_config(opts) if uses_model else {}
    public.pop("base_url", None)  # Shareable reports never embed endpoint details.
    return {"schema_version": "agenteval/report/v1", "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": "model_and_rules" if uses_model else "rules_only",
            "summary": summary, "checks": checks, "traces": traces, "model_config": public,
            "run_config": {"concurrency": concurrency, "n_runs": n_runs},
            "config_hash": hashlib.sha256(json.dumps([rules_yaml, evaluators_yaml]).encode()).hexdigest()}
