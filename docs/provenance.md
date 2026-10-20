# Engine provenance

AgentEval packages the generic evaluation engine maintained by the same author
in [Human Value Allocation](https://github.com/kling01/human-value-allocation),
under its MIT license. The source snapshot is commit
`0bbbd074c5c4eada8f4530ddde060ee3b5b6c1be`, directory
`src/human_value/_engine`.

The code is namespaced as `agenteval.engine`. The public API, input adapter, CLI,
standalone report and authored examples are separate components in this release.
The public result layer preserves full trace IDs, requires explicit model
configuration and output contracts, and distinguishes errors and non-applicability
from successful evaluations. Raw provider exception messages are not exported.

`engine-manifest.json` records source and release SHA-256 hashes for each copied
engine file. This new repository contains a clean source snapshot, not the history,
credentials or business datasets of earlier development workspaces.

The example traces were written to exercise the interface. They are not customer
conversations, benchmark samples or model-quality measurements.
