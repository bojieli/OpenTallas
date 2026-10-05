# Local RTX PRO 6000 measured break-even runs

This directory preserves governed measurements of the shared local
`NVIDIA RTX PRO 6000 Blackwell Workstation Edition` service comparator.
Neither run supports whole-GPU energy attribution because unrelated compute
processes remained active.

| Run | Role | Notes |
| --- | --- | --- |
| [`20260828T113804Z`](20260828T113804Z/) | archived original | Initial measured service run retained for provenance. |
| [`20260828T114437Z`](20260828T114437Z/) | current governed source | Runtime/version-locked replacement used to generate [`../measured_break_even`](../measured_break_even/). It records vLLM `0.19.0`, NVIDIA driver `595.71.05`, endpoint identity/version stability, and before/after shared-process inventories. |

The endpoint API reports the governed model root but does not attest a model
revision. Checkpoint accounting is tied instead to the sole local snapshot
selected by that cache's `main` ref; this is strong linkage, not runtime
revision attestation.
