# Using RubricLoop

RubricLoop evaluates traces using locally executed code rules and optionally a configured model judge. Begin with the offline demo, then substitute your own traces and criteria.

## 1. Install and run the demo

From the repository root, with Python 3.10 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
rubricloop demo --out runs/demo
```

On Windows, activate the environment with `.venv\Scripts\activate`.

The demo uses three hand-authored conversations. It executes code checks without network access to a model provider. Open `runs/demo/report.html` in a browser and inspect `runs/demo/results.json` for machine-readable results.

Choose a new `--out` directory for each run. The CLI refuses to overwrite an existing output directory, preserving earlier results for comparison.

### Migration from AgentEval

Version `0.1.0a2` adopts the RubricLoop project name. Use the `rubricloop` command and the `RUBRICLOOP_BASE_URL`, `RUBRICLOOP_MODEL`, and `RUBRICLOOP_API_KEY` environment variables for new setups.

The `agenteval` command and the corresponding `AGENTEVAL_BASE_URL`, `AGENTEVAL_MODEL`, and `AGENTEVAL_API_KEY` variables remain supported for compatibility. Python imports and the source namespace remain `agenteval`, including `from agenteval import evaluate`.

When both environment-variable families are set, `RUBRICLOOP_*` takes precedence. If you installed the previous `agenteval-traces` distribution, remove it before installing the updated checkout; both distributions use the same Python namespace:

```bash
python -m pip uninstall agenteval-traces
python -m pip install -e .
```

The repository is now [kling01/RubricLoop](https://github.com/kling01/RubricLoop), and the online report is at [kling01.github.io/RubricLoop/demo.html](https://kling01.github.io/RubricLoop/demo.html). Existing checkouts can update their remote:

```bash
git remote set-url origin https://github.com/kling01/RubricLoop.git
```

## 2. Supply traces

The simplest input is a JSON array. Each trace has an identifier and a message list:

```json
[
  {
    "id": "sum-001",
    "messages": [
      {"role": "system", "content": "Answer concisely."},
      {"role": "user", "content": "What is 17 + 25?"},
      {"role": "assistant", "content": "42"}
    ]
  }
]
```

Supported message roles are `user`, `assistant`, `system`, and `tool`; message content is text. Use stable, unique trace IDs so that results remain easy to compare across runs.

The engine also accepts cleaned trace trees. This format preserves nested execution structure for the engine's trace navigation and scoped checks. A flat conversation alone does not create missing tool-call or nested-agent evidence: use a cleaned tree when your criterion depends on those structures.

For a first integration, adapt one representative trace and inspect the report before submitting a large batch.

## 3. Define code rules

Rules are YAML entries with a `check` expression. **The expression describes a failure condition.**

```yaml
pass_threshold: 60
rules:
  - id: final-answer-present
    name: Final answer is present
    description: The trace should end with a usable assistant response.
    scope: trace
    check: "not has_final_output"
    weight: 50
    severity: error
    enabled: true
```

When `not has_final_output` is `True`, the rule produces `-1` (fail). When it is `False`, the rule produces `1` (pass).

Run a rule file:

```bash
rubricloop run examples/traces.json \
  --rules examples/rules.yaml \
  --out runs/rules
```

Useful generic feature names include `has_final_output`, `final_content`, `n_dispatch`, `agent_names`, `n_env_fail`, `n_real_fail`, `n_empty_return`, and `n_success_return`. Their values depend on the evidence in the trace. See the definitions in [`features.py`](../src/agenteval/engine/core/features.py) and [`feature_registry.py`](../src/agenteval/engine/core/feature_registry.py) when writing structural checks.

`scope: trace` applies to the whole trace. A scope such as `tool:search` activates only when the matching tool is present; an inactive rule returns `0` (not applicable).

**Trust boundary:** `check` is a Python expression evaluated locally. The feature namespace limits ordinary use, but it is not a security sandbox. Run only rule files you have reviewed and trust.

### Counts and errors

The public report counts `pass`, `fail`, `not_applicable`, and `error` separately. It retains a result for each criterion, so an inactive rule or an execution error is never counted as a pass.

The inherited engine also has weighted-score fields for compatibility with evaluator prompts. Those fields use rule weights and `pass_threshold`; the public report does not use them as a headline quality score.

## 4. Add model judgment

Configure an OpenAI-compatible chat endpoint:

```bash
export RUBRICLOOP_BASE_URL="https://your-provider.example/v1"
export RUBRICLOOP_MODEL="your-model"
export RUBRICLOOP_API_KEY="your-api-key"
```

Replace the example values with your provider's settings. Keep credentials out of committed files.

Start from [`examples/judge.yaml`](../examples/judge.yaml):

```bash
rubricloop run examples/traces.json \
  --evaluators examples/judge.yaml \
  --concurrency 4 \
  --n-runs 1 \
  --out runs/judged
```

Use `--rules` and `--evaluators` together when the evaluator should consume rule results:

```bash
rubricloop run examples/traces.json \
  --rules examples/rules.yaml \
  --evaluators examples/hybrid.yaml \
  --concurrency 4 \
  --n-runs 1 \
  --out runs/hybrid
```

`examples/hybrid.yaml` explicitly includes `{{issues}}` and `{{issue_detail}}` in its prompt. Merely supplying both files does not automatically add those fields to a judge prompt.

`--concurrency` controls parallel model work. `--n-runs` controls repeated judgments; increasing it increases model use. Begin with one run on a small, human-reviewed sample.

Evaluator templates can select conversation content and, when available, reference answers, metadata, and rule results. The endpoint receives the material included by those templates. Review the selected fields before using private traces.

Provider compatibility can vary, including structured-output behavior. An execution error should remain distinguishable from a failed criterion.

## 5. Read the output

Every run writes:

| File | Use |
| --- | --- |
| `report.html` | Open locally to inspect traces and evaluation details. |
| `results.json` | Read structured results in scripts or downstream workflows. |

Use the individual criterion result to distinguish:

| Outcome | Interpretation |
| --- | --- |
| `1` | The criterion passed. |
| `0` | The criterion did not apply. |
| `-1` | The criterion failed. |
| `null` | Evaluation failed to produce a valid outcome. Inspect the reason and configuration. |

The public `checks` array normalizes results to the outcome convention above. Raw engine fields and binary model contracts have their own conventions; read the evaluator definition if you work directly with the underlying engine.

A useful review starts with failed criteria and execution errors, then samples passed and non-applicable cases. The model's explanation is a judgment to inspect; it is not independently verified evidence.

The CLI exits with `0` after a completed run without execution errors, `2` when the report contains evaluation errors, and `1` for input or configuration failures. A successfully evaluated failing criterion is a result, so it does not by itself produce a nonzero exit status.

## 6. Version criteria

The engine includes a structured evaluator specification with evaluator IDs, versions, clause IDs, evidence fields, and output contracts. See [`evaluator_spec.py`](../src/agenteval/engine/core/evaluator_spec.py) for validation and compilation.

This structure makes criteria explicit and supports controlled clause edits. The public CLI currently focuses on trace-level evaluation. Automatic proposal of repairs, regression acceptance, and deployment of revised evaluators are future workflow components.

## Offline demo

The offline demo walks through installation, trace normalization, code-rule execution, and report generation using the shipped examples.

For your domain, keep a separate human-reviewed evaluation set and inspect error types before expanding the workload.

## Python API

```python
import asyncio
import json
from pathlib import Path
from agenteval import evaluate

result = asyncio.run(evaluate(
    json.loads(Path("examples/traces.json").read_text()),
    rules_yaml=Path("examples/rules.yaml").read_text(),
))
print(result["summary"])
```

Use `evaluators_yaml` and `model_options={"base_url": ..., "model": ..., "api_key": ...}` for model judges. The API does not read environment variables.

The engine serializes long trace fields with length limits (for example, message text in `{{messages}}` is capped at 4,000 characters per message). Inspect the prompt formatter before evaluating long-context criteria; this release is not a lossless long-context judge.
