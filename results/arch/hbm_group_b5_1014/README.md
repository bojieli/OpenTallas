# SU.VOP end-to-end sweep (group B5, 2026-10-14)

`suvop_e2e_sweep.py` (run from the repo root) re-schedules the exact r25gq S2 programs (tools/throughput/accepted_cost.py
`hbm_schedule`, the ledger's own model) with every SU.VOP record at `ratio x price`, everything else at price.
`suvop_e2e_sweep.json`: per workload the base cycles, the SU.VOP record count and the tok/s loss % per ratio.

| ratio | DS AR loss % | Qwen AR loss % |
|---:|---:|---:|
| 1.10 | 1.75 | 0.42 |
| 1.183 (Qwen monolithic measured) | 3.22 | 0.76 |
| 1.333 (24 of 32 sectors / engine edge) | 5.84 | 1.38 |
| 2.0 | 16.37 | 4.04 |
| 2.651 (DS native 59a measured) | 24.98 | 6.49 |
| 4.0 | 38.46 | 11.21 |
| 5.33 (6 of 32 sectors, pure bandwidth) | 47.75 | 15.41 |
