# QC-ALLFIX-COLL handoff (FAMILY helper of QC-ALLFIX; updated 11-23 17:50 PST)

Integrator: QC-ALLFIX (agent a19642e09aa8ab59f). Base compose A f418c1b290f3 = epyc8 /srv/opentallas-scratch2/claude/QC-ALLFIX/cA/rows/plan_b25_tapoff.json.
Work dirs: E10 /srv/opentallas-scratch/claude/QC-ALLFIX-COLL (CTS probes), epyc8 /srv/opentallas-scratch2/claude/QC-ALLFIX-COLL (clone, rows).

1. coll_core 80 CLK-open (functional stop): ROOT CAUSE = native CTS keeps one sink per location of a clock net; tap_reset_split
   seated copies at sink centroids / launch copies at their stage bbox, which gave 81 same-tap same-(x,y) pairs, and 80 opens.
   FIX = tools row main 32027184aff (commit 79e81c90823): tap_reset_split.tcl uniq_seats + test. Proof E10 ctsopen_fix_1730
   (CTS-only, pkg15 3_place e0a45c22c7b3): 205 copies, 0 open. Diag: ctsopen_diag_1640 (before/after.tsv). ROW-REBASED sent 17:39.
   Open: u_rrl_26 AND D-net to 23 copies is -521 pre-repair at CTS (SKIP_CTS_REPAIR_TIMING=1); the GRT probe decides; fallback clock.tap_reset_split_max_taps.
2. rc107/rc109: coll types are byte-identical C4 -> compose A (pkg15 carried). Probe after an rt with 32027184aff.
3. SLE CTL B_TW bank spread: ALREADY in C4/b25 (4 per-bit banks x158-504, 9 stages kept; QC-V4 ctl_1123/station_row.json, btw_station_and_clock_model.png). Needs only the sle_ctl__cla4f6f12f place/GRT probe.
4. SLE CTL clock entry: sle_ctl edge taps = landing contract in C4 already (455.136/1159.008 ...). NEW peer finding: 14 hc1/hc2 types' fclk_in_b_hw_i
   tap 140.192 != contract 206.624 (hc1) / 251.936 (hc2), which abut sle_ctl fclk_out_b_hw_hc*_o; preflight clock_pin_geometry would FAIL.
   Row: epyc8 QC-ALLFIX-COLL/rows/ctlclk_row.py (123a8da159af), row_ctlclk.json (7eba760c7fbd), plan f418c1b290f3 -> b96b49014c35. PRE (epyc7 t7 fork, rt 70b6): row adds 0 findings; base and row both carry the inherited ROWS-NO-PROOF (9 sc types). ROW-REBASED 18:17.

## 18:50 PST compose C
- CBN-RSF-SEAT ROW-REBASED: rsfseat_row.py 59991d13f2c3, B1 99ab093a8b8f -> e0d2191f6daf, PRE = base (1 inherited ROWS FAIL), over-core sites 162 -> 156.
- TTCTLM ROW-DROP for the placement route: cone place CTS -218.57/-133.58 (E9 QC-ALLFIX-COLL/ttc_cone_cts_1840); the fix is a depth cap or register stage in the CODEX-TOKEN Native32 constructor, plus LEC.
- coll_core GRT probe: waiting for an rt containing 32027184aff. Then run intel2 /srv/opentallas-scratch2/claude/QC-ALLFIX-probe.sh copy with --rt swapped on compose A; report CLK-open plus CTS/GRT setup.

## 18:51 TTC-STAGE (COORD 19:02) -> ROW-DROP
- Depth census: CTS-read cpub39_1 has 1047 flops >=18 levels; B1 F5 source has 3304 >=18 (max 38/71). Worst endpoints are internal hold-enable flops; 1208-flop strongly connected loops exist. Needs a constructor depth cap/retime by CODEX-TOKEN plus token bench and sequential LEC. Scripts: E9 QC-ALLFIX-COLL/depth.py, scc.py. Hub bef6a0da.

## 19:35 PST
- coll_core moved to QC-OPEN-COLL (COORD 19:30); handover posted; waiter stopped.
- Only job now: 13-probe census watch (4 IN-SET + 9 RELAUNCH, A on epyc8). Watcher intel2 /srv/opentallas-scratch2/claude/QC-ALLFIX-COLL/watch13.py, census epyc8 /srv/opentallas-scratch2/claude/QC-ALLFIX-COLL/census.sh. Post one full-cause line per type at GRT, or a hold reason if it fails.

## 2026-11-24 03:4x PST
- sle_ctl A probe + cbf_q00 C1 probe: GRT DESIGN-FAIL (FLEET-WATCH cancel 03:17), hold reasons hub 74a445d8.
- Watching cbn_q00, glue, native59, slw_hc1, sle_hc2 (epyc7 R6V4, still in GRT) via watch13.py - <items>; census: CB=<R6V4 base> census2.sh on epyc7.
