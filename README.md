<p align="center">
  <img src="docs/assets/hero.svg" width="100%" alt="AgentEval — Trace → Executable rubric → Evidence & review" />
</p>

<p align="center">
  <a href="https://kling01.github.io/agenteval/demo.html">Live demo</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="docs/usage.md">Usage</a> ·
  <a href="docs/roadmap.md">Roadmap</a> ·
  <a href="https://github.com/kling01/human-value-allocation">Human Value Allocation</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB" alt="Python 3.10+" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-5B5BD6" alt="MIT License" /></a>
  <img src="https://img.shields.io/badge/Status-Early%20release-64748B" alt="Early release" />
</p>

**AgentEval turns agent traces into inspectable evaluation results.** Define executable rubrics, combine code rules with model judges, and review each decision alongside its trace in a standalone HTML report.

The starting point is a practical data-quality workflow: **which behavior needs attention, which criterion caught it, and what should a person review?** AgentEval provides the evaluation layer for that workflow.

## What you can run today

| Capability | What it gives you |
| --- | --- |
| **Trace evaluation** | Evaluate simple message histories or cleaned trace trees. |
| **Executable rubrics** | Express deterministic checks in YAML, with trace and tool scopes. |
| **Model judges** | Run configurable evaluators through an OpenAI-compatible chat endpoint. |
| **Hybrid evaluation** | Use code-rule results as context for model judgments. |
| **Versioned criteria** | Define identified rubric clauses and evaluator versions with the engine's structured specification. |
| **Reviewable results** | Inspect traces, rule outcomes, and model judgments in HTML; use JSON for downstream analysis. |

The offline demo uses three small, hand-authored traces and executes real code rules. It is an installation and workflow example; it does not measure judge accuracy or performance on a benchmark.

<p align="center">
  <img src="docs/assets/demo.png" width="100%" alt="Actual AgentEval offline report: three authored traces, nine checks, six passes, two failures, and one non-applicable result." />
</p>

*Actual output from `agenteval demo`: 3 traces, 9 checks, 6 pass, 2 fail, and 1 not applicable. [View the saved HTML source](https://kling01.github.io/agenteval/demo.html), or run the command below to open a local report.*

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/kling01/agenteval.git
cd agenteval
python -m venv .venv
source .venv/bin/activate
pip install -e .

agenteval demo --out runs/demo
```

Open `runs/demo/report.html` in your browser. The same run writes `runs/demo/results.json`.

### Evaluate your own traces

```bash
agenteval run examples/traces.json \
  --rules examples/rules.yaml \
  --out runs/rules
```

Start with a JSON array of conversations:

```json
[
  {
    "id": "example-001",
    "messages": [
      {"role": "user", "content": "What is 17 + 25?"},
      {"role": "assistant", "content": "42"}
    ]
  }
]
```

Use code rules for checks you can state precisely. Add a model judge for criteria that require semantic judgment:

```bash
export AGENTEVAL_BASE_URL="https://your-provider.example/v1"
export AGENTEVAL_MODEL="your-model"
export AGENTEVAL_API_KEY="your-api-key"

agenteval run examples/traces.json \
  --rules examples/rules.yaml \
  --evaluators examples/judge.yaml \
  --concurrency 4 \
  --n-runs 1 \
  --out runs/judged
```

The configured provider receives the trace content selected by your evaluator prompts. This command uses that provider's API and may incur charges. The offline demo needs no provider or API key.

See [Usage](docs/usage.md) for input formats, rule semantics, model configuration, and result interpretation.

## How it works

```text
Trace / message history
          │
          ▼
Normalize and extract features
          │
          ├── Code rules ───────────────┐
          │                            │
          └── Model / hybrid judges ───┤
                                       ▼
                              HTML + JSON results
                                       │
                                       ▼
                              Evidence and review
```

Each criterion retains its own outcome:

| Value | Meaning |
| --- | --- |
| `1` | Pass |
| `0` | Not applicable |
| `-1` | Fail |
| `null` | Evaluation error; inspect the reason and configuration |

**A code rule's `check` describes a violation:** `True` produces a fail. Rules are trusted Python expressions, executed locally; they are not sandboxed. Review rule files before running them.

The report counts passes, failures, non-applicable results, and errors separately. A model's judgment remains an assessment to validate against human-reviewed examples.

## Release scope

This release packages the evaluation engine, a CLI, authored examples, and standalone reports. The engine includes structured, versioned rubric clauses; the public CLI focuses on trace-level runs.

The next steps are evaluator feedback and revision, regression checks, and integrations into data-production workflows. Policy-to-rubric generation, automatic repair loops, model training, and intervention-value prediction are tracked in the [roadmap](docs/roadmap.md).

## Related research and tooling

[**Human Value Allocation**](https://github.com/kling01/human-value-allocation) is a separate project for inspecting visible human contributions in human–agent conversations.

Its related paper, [*From Tasks to Turns: Measuring Human Labor Contributions in Human–Agent Joint Production*](https://arxiv.org/abs/2610.26365), motivates research on human participation. AgentEval is the generic evaluation component; this repository does not claim to reproduce that paper's experiments.

## Contributing

Concrete evaluation cases are especially useful: a minimal trace, an intended criterion, the observed result, and the expected result. Remove private data and credentials before sharing a reproduction in [Issues](https://github.com/kling01/agenteval/issues).

See [Usage](docs/usage.md) for the runnable interface and [Roadmap](docs/roadmap.md) for the current boundary and development direction.

## License

[MIT](LICENSE).
