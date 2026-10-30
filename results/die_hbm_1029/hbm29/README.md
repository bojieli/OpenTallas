# DIE-HBM-29 (2026-10-29) — HBM plan event on d28c

Plan dirs (intel1 /srv/opentallas-scratch2/claude/die-hbm-29/plan/, self-contained: cores/ + fr28 pin table are hard-linked copies, no symlinks):

| plan | delta | die_plan sha | G0 | G0C | strict bind UNPLANNED |
|---|---|---|---|---|---|
| d28c (base, fixed cores) | — | 57e3ad3cb729 | PASS | 8 err | 85 pairs / 65,930 b |
| d29a | HBM-055 scorer slot rotation b101/b102/b103 + glue (hbm055_event.py) | 17fa9069a351 | PASS | 8 (same set) | 81 / 62,658 |
| d29b | + xq_pegress folded into hub soft logic (xq_fold.py) | 95e7e13aa89e | PASS | 8 (same set) | 81 / 62,658 |
| d29c | + idx_query 5 SRAM static sites (idxq_static.py) + glue step 2 map (hbm055_glue2.py) | 95e7e13aa89e (core_macros a54015351781) | PASS | 8 (same set) | 81 / 62,052 |
| d29d | + pgp relay lanes su01->su00 1650 b, su21->su20 3x240 b (lane_add.py, pgp_rows_d.json) | 1aefc6184b2a | PASS | 8 (same set) | 81 / 57,312 |

All bind runs: tied/undriven/multiply-bound 0/0/0, unmapped 0 (CHECKED). G0C 8 = the d28c set (hub u_vmb_* core_faces), 0 new (CHECKED).

- HBM-055 residual b101<->b103 after glue step 2: 6 b + 102 b per half (row-1 meta md.q 24 b, row regs 71685/71686/71687/71692/71712/71740/71745/71750 still in b103). Next: move those 8 regs to b101 (one map step).
- pgp relay: hub->su00 2,846 -> 1,198 b, hub->su20 2,846 -> 2,126 b UNPLANNED. lane_add finds no free edge window for > 1,650 b (su01|su00) or > 720 b (su21|su20). Relay path latency hub->su01 L0 14 + 2 = 16 cyc vs direct L36 14 (+2 cyc, UNCHECKED in the token model); su20 path L2 6 + 2 = 8 vs L38 9.
- idx_query static sites: W column x 15.12 (gcode[0..2]), 2nd column x 79.488 (scmem, gcode[3]); channels 12.96 (x) / 12.954 (y) >= 10.8; clock island clear; render idxq_static.png viewed. Pin faces unchanged (fr28 table) -> HBM-CORES-KITS-25 re-kit of ot_hbm_idx_query_static on these sites.
- xq_pegress: hub glue run estimate <= ~178k cells (< 400k; arithmetic, synthesis UNCHECKED).
- Token (claude/die-hbm-29t-1029@3f87ca65769): L6 +1, L181 +3, scorer +30 -> 1808.0 tok/s (-0.245%), bound 1799.8 (-0.698%); no OWNER item.
- opstore_a (claude/die-hbm-29o-1029@064a34ec3fb): V1 q_b113 repack recommended over the 2-core split; not built.
- GRT0 not run: bind not 0.
