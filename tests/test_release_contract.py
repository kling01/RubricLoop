"""Public-release contracts exercised offline through the real evaluation engine."""

import asyncio
import json

import httpx
import pytest

from agenteval.adapters import normalize_traces
from agenteval.api import evaluate


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    async def refuse_request(*args, **kwargs):
        raise AssertionError("Release tests must not make network requests.")

    monkeypatch.setattr(httpx.AsyncClient, "send", refuse_request)


def dialogue(trace_id, output="A useful result."):
    return {
        "id": trace_id,
        "messages": [
            {"role": "user", "content": "Perform the task."},
            {"role": "assistant", "content": output},
        ],
    }


def run(traces, **kwargs):
    return asyncio.run(evaluate(traces, **kwargs))


def test_atomic_rule_outcomes_keep_na_and_errors_separate():
    traces = [
        dialogue("shared-prefix-A/full-session-id"),
        dialogue("shared-prefix-B/full-session-id"),
    ]
    rules = """
rules:
  - id: always_pass
    name: always_pass
    check: "False"
  - id: always_fail
    name: always_fail
    check: "True"
  - id: inactive_tool
    name: inactive_tool
    scope: "tool:absent_tool"
    check: "True"
  - id: invalid_expression
    name: invalid_expression
    check: "1 / 0"
"""
    result = run(traces, rules_yaml=rules)
    assert len(result["checks"]) == 8
    assert {row["trace_id"] for row in result["checks"]} == {
        trace["id"] for trace in traces
    }
    assert result["summary"] == {
        "pass": 2,
        "fail": 2,
        "not_applicable": 2,
        "error": 2,
        "checks": 8,
        "traces": 2,
    }


def test_duplicate_trace_ids_are_rejected():
    with pytest.raises(ValueError):
        normalize_traces([dialogue("duplicate"), dialogue("duplicate")])


def test_multimodal_payload_is_not_silently_converted_to_text():
    trace = dialogue("multimodal")
    trace["messages"][0]["content"] = [{"type": "image_url", "url": "example"}]
    with pytest.raises(ValueError):
        normalize_traces([trace])


EVALUATOR = """
evaluators:
  - name: task_quality
    iterate_over: trace
    output_contract: tristate_v1
    prompt: "{{Agent_output}}"
"""


def test_llm_evaluation_requires_explicit_model_configuration():
    with pytest.raises(ValueError):
        run([dialogue("needs-model")], evaluators_yaml=EVALUATOR)


def test_mocked_llm_outcomes_and_errors_preserve_full_ids(monkeypatch):
    from agenteval.engine.llm import eval as engine_eval

    private_marker = "private-gateway-and-credential-marker"
    requested = []

    async def provider(prompt, client):
        requested.append(prompt)
        if "CASE_ERROR" in prompt:
            raise RuntimeError(private_marker)
        for marker, outcome in (("CASE_PASS", 1), ("CASE_NA", 0), ("CASE_FAIL", -1)):
            if marker in prompt:
                return json.dumps({"output": outcome, "reason": marker})
        raise AssertionError("The intended trace output was absent from the prompt.")

    monkeypatch.setattr(engine_eval, "call_llm", provider)
    traces = [
        dialogue(f"shared-prefix-{kind}/full-session-id", f"CASE_{kind}")
        for kind in ("PASS", "NA", "FAIL", "ERROR")
    ]
    result = run(
        traces,
        evaluators_yaml=EVALUATOR,
        model_options={
            "base_url": "https://provider.example/v1",
            "api_key": "test-only-key",
            "model": "test-only-model",
        },
    )
    assert len(requested) == 4
    assert {row["trace_id"] for row in result["checks"]} == {
        trace["id"] for trace in traces
    }
    assert result["summary"] == {
        "pass": 1,
        "fail": 1,
        "not_applicable": 1,
        "error": 1,
        "checks": 4,
        "traces": 4,
    }
    serialized = json.dumps(result)
    assert private_marker not in serialized
    assert "test-only-key" not in serialized


def test_report_escapes_untrusted_trace_and_judge_text():
    from agenteval.render import render_html

    payload = '<img src=x onerror="alert(1)">'
    result = run(
        [dialogue("untrusted-" + payload, payload)],
        rules_yaml='rules:\n  - name: local_check\n    check: "False"\n',
    )
    result["checks"][0]["reason"] = payload
    html = render_html(result)
    assert payload not in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "<script" not in html.lower()


def test_offline_demo_preserves_existing_output(tmp_path, monkeypatch):
    from agenteval.cli import main

    monkeypatch.setenv("AGENTEVAL_BASE_URL", "https://must-not-be-called.example/v1")
    monkeypatch.setenv("AGENTEVAL_API_KEY", "must-not-be-in-demo")
    monkeypatch.setenv("AGENTEVAL_MODEL", "must-not-be-called")
    out = tmp_path / "demo"
    assert main(["demo", "--out", str(out)]) == 0
    original = (out / "results.json").read_bytes()
    result = json.loads(original)
    assert result["demo"] is True
    assert result["mode"] == "rules_only"
    assert result["summary"]["error"] == 0
    assert result["model_config"] == {}
    assert "No model was called." in (out / "report.html").read_text()
    assert b"must-not-be-in-demo" not in original
    assert main(["demo", "--out", str(out)]) == 1
    assert (out / "results.json").read_bytes() == original


def test_hybrid_judge_receives_real_rule_context(monkeypatch):
    from agenteval.engine.llm import eval as engine_eval

    received = []

    async def provider(prompt, client):
        received.append(prompt)
        return json.dumps({"output": -1, "reason": "Observed the deterministic failure."})

    monkeypatch.setattr(engine_eval, "call_llm", provider)
    result = run(
        [dialogue("hybrid-context")],
        rules_yaml='rules:\n  - id: deterministic-failure\n    name: deterministic-failure\n    check: "True"\n',
        evaluators_yaml=EVALUATOR.replace(
            'prompt: "{{Agent_output}}"',
            'prompt: "Answer: {{Agent_output}}; Rule results: {{issues}}; Details: {{issue_detail}}"',
        ),
        model_options={
            "base_url": "https://provider.example/v1",
            "model": "test-only-model",
        },
    )
    assert len(received) == 1
    assert "deterministic-failure" in received[0]
    assert "{{issues}}" not in received[0]
    assert "{{issue_detail}}" not in received[0]
    assert result["summary"]["fail"] == 2
    assert result["summary"]["error"] == 0
