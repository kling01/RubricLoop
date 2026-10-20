# RubricLoop roadmap

RubricLoop is the evaluation layer of a broader data-quality workflow: turn traces into explicit assessments, expose the evidence for review, and make later revisions measurable.

The table below shows available capabilities and planned extensions.

| Area | Status | Scope |
| --- | --- | --- |
| Trace input | Available | Simple message histories and cleaned trace trees. |
| Code rules | Available | YAML-defined checks, applicability scopes, and explicit per-rule outcomes. |
| Model and hybrid evaluation | Available in the engine and CLI | Configurable judges through a compatible endpoint, optionally using code-rule results. |
| Review artifacts | Available | Standalone HTML and JSON output. |
| Structured evaluator criteria | Available in the engine | Identified clauses, versions, output contracts, and constrained clause patching. |
| Human feedback workflow | Planned | Record a disputed decision, the relevant evidence, and the intended correction. |
| Evaluator revision and regression | Planned | Propose a change, rerun a retained evaluation set, and review regressions before accepting a revision. |
| Policy-to-rubric generation | Research direction | Derive candidate criteria from source documents and verify their applicability. |
| Data-production integration | Planned | Connect reviewed assessments to pre-annotation and dataset-quality workflows. |
| Training integrations | Future direction | Export or connect supervision for data selection and training systems. |
| Multimodal inputs and interactive environments | Future direction | Extend evidence beyond the current text-trace interface. |
| Human intervention-value prediction | Separate research direction | Study when human input improves subsequent joint work, with appropriate validation. |

## Next useful milestone

The immediate extension is a small, inspectable evaluator-improvement loop:

1. A reviewer identifies a disagreement and supplies a correction.
2. The system records the trace, criterion version, judgment, and feedback.
3. A revision changes identified rubric clauses.
4. The candidate is compared with the previous version on held-out cases.
5. A reviewer inspects improvements and regressions before accepting it.

Build on the versioned-clause API to add feedback capture, candidate generation, and regression acceptance.

## Evaluation plan

Useful progress measures include agreement with reviewed labels, errors by criterion, regression rates after revision, and the time and model cost required to obtain accepted results. Those measurements should identify the evaluation set, model configuration, and evaluator version.

## Relationship to Human Value Allocation

[Human Value Allocation](https://github.com/kling01/human-value-allocation) is an independent tool and research project for analyzing visible human contributions. Its related [paper](https://arxiv.org/abs/2610.26365) informs the longer-term work on human participation.

RubricLoop evaluates agent behavior against criteria. Using that component in a system that predicts when human intervention is worthwhile is a future integration and research task.
