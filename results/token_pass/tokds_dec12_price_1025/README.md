# S81 decision-17 plan reprice, 2026-10-25

Plan source codex/s81-dec12-1025@81f23d224: 176/176 G0C, lane-side leaf placement and frame corridors. Token components are the existing tokds_comp_1024 records. This is analytical composition and static-calendar checking, not a new RTL token pass.

| metric | result |
|---|---:|
| Single-user AR, 241-stage map | 1,524,133.6 cycles / 787.3 tok/s |
| Single-user MTP, pipeline law of record | 1,809,990.6 cycles/step / 2,757.4 tok/s |
| MTP old stretch sensitivity | 1,977,020.8 cycles/step / 2,524.4 tok/s |
| AR50 aggregate | 39,367 tok/s |
| MTP6 aggregate | 16,544 tok/s |
| AR DAG diagnostic | 1,382,494.6 cycles / 868.0 tok/s |
| MTP DAG diagnostic | 1,788,913.8 cycles/step / 2,789.8 tok/s |

The previous pipeline record was2,763.0 tok/s (AR789.1), so this plan is -0.20% MTP/-0.23% AR, not a change of speed regime. The current plan has -173 summed lane cycles across112 changed lanes versus its immediate DEC12 base; that sum alone is not a token critical-path delta.

Found an implementation lag behind owner decision15: the pipeline mode still took max(stretch,pipeline). The code now uses the checker-qualified pipeline directly and keeps stretch as an explicit sensitivity. Comparing2,757 to the old2,528 stretch row would confuse a law change with a physical improvement.

Calendar PASS: AR50 and MTP6,0 collisions, same-user checks enabled. Injected-shift controls fault660/2,748 collisions; N+1 controls fault1 each (AR51/MTP7). Current-RTL shares of the DAG are29.28% AR/25.74% MTP; the remainder is older measured, priced, or modeled PHY work. Full G5 remains open.

Opt-in quant-release prototype costs are not folded into this record: it is not yet adopted or qualified across all norm modes. Subsequent IDXNET/PORTFIX and exact channel-site changes will need a successor price table.
