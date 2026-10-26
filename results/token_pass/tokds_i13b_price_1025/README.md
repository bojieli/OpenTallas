# TOK-DS: I13 rewrite reprice, 554 cyc/job (2026-10-25)

Tool: tools/s81_dv/tokfunc/compose_tok_ds.py (unchanged, same method as 1a602bbe9), base = main 6a6fc12dd
(adopt178 + faultfeed plan 6c5365e4a + head per-die delta 1691e7939). epyc1 ot-run unit oth-ubuntu-3189938-1792933981, run.sh.
Three cases: base (no component), i13_554 (comp/), i13_612 (comp612/, control: reproduces 1a602bbe9 exactly).
Files compose_1u.json / calendar_mu.json are the i13_554 run.

| case | AR DAG T | AR map tok/s | AR50 agg | MTP T_step (pipeline) | MTP tok/s | MTP6 agg | stretch |
|---|---:|---:|---:|---:|---:|---:|---:|
| main base (attn.gather old 607.5) | 1,387,238.6 | 784.9 | 39,244 | 1,815,229.6 | 2,749.4 | 16,496 | 2,517.4 |
| I13 612 (1a602bbe9, control) | 1,387,274.6 | 784.9 | 39,243 | 1,815,440.6 | 2,749.1 | 16,494 | 2,517.2 |
| **I13 554 (rewrite)** | **1,386,810.6** | **785.1** | **39,255** | **1,814,686.6** | **2,750.2** | **16,501** | **2,518.1** |

- Delta 554 vs 612: AR -464 cyc (+0.03 %, 784.9 -> 785.1), MTP -754 cyc/step (+0.04 %, 2,749.1 -> 2,750.2).
  Delta 554 vs main base: AR -428 cyc, MTP -543 cyc/step. Calendars AR50/MTP6 0 collisions (checker null = PASS as before).
- I13 (comp/i13_gather.json): command->done 554 cyc/job with native ASAP7 SRAM models (cam/skip/twosrc 554, dense 550; R3
  random-init flops 552); miss/duplicate/wrongtag/wrongq/order/idorder/same-bank mutants CAUGHT; two-job overlap 174/174
  beats 0 mismatch. RTL claude/s81-i13r-1025@36364ebdb (e3feef588). Slot unchanged: logic of DAG op attn.gather (AR 8x).
- **PENDING**: 554 is pending S81 source/synth adoption of the rewrite (S81 lane owns it: no synth fit, no P&R, not in the
  S81 release netlist). Until adopted, the price of record stays 612 (1a602bbe9). No change > 5 %, no ledger row.
