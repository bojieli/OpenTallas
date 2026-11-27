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

## 2026-11-26 private f628 collector feedthrough cohort

- The five sibling types are coll_ftm, coll_ftc, coll_ftn, coll_ft__cl78c7b300 and coll_ft__cla4a25d77. Their f628 source passed native parallel strict bind, all 1,922 latency checks, PRE, G0, independent source visual review and stock per-kit fast preflight. The original long-egress class was repaired across all 60 terminal ranks. Actual FTm and FTn output pins reach their registers within 26 µm. Preserve these ranks in the next pass.
- Canonical private controllers are under ~/coord/autopilot/private_specs/QC-ALLFIX/collft_cohort_f628_1126_rebalance on Intel2. Exact placed geometry and independent actual review hold the route. E7 handles FTm, FTn and cl78. Intel1 handles FTc and clA4. W means /srv/opentallas-scratch2/claude/QC-ALLFIX/coll_ftm_geometry_codex_1126/cohort on these hosts. Rehome work using an identical published C9 lower plus the sealed f628 data delta and existing native bind. This moved the sub-1 GB carrier to Intel1 in 1m33 and E7 in 2m37, with the same source and PVR form, without repeating the die bind. Move unadmitted requests only.
- Native binding takes collector attachments from the asbuilt clock-landing sidecar. The plan already named correct local taps while its old sidecar produced remote attachments on FTm, FTn and cl78. The native sidecar replacement and exact old/new ancestry are on E8 at W/monitor_sidecar_followup. Local source legs go 1533→0, 609→61 and 641→62 µm, with the same raw and return-cycle depth in each branch. This covers the FTm two-way monitor and FTn/cl78 ring collector class. The diagnostic FTn/cl78 midpoint group placements are superseded. After normal retap, sync and check the emitted sidecar and final native groups together. A visually plausible plan alone cannot catch this mismatch.
- Source-only grouped ops are staged on E8 at W/physical_followup/known_rows.ops.json. This incorporates FTm 20 shallow receive bands, its unchanged-source raw reset seat and TSTART origin, FTn/FTc/coll_n paired widened payload openings, one b914 destination adjustment, clA4 same-depth FLTK/FLTV writer midpoint, and all 12 inherited FTc long clock-export source picks. The f628 exact-clA4 actual confirmed the 421 µm writer head. FTm retained-graph input p90/max projection is 28.73/132.47 µm pending fresh placement review. The FTn new receiver and b914 projected 30/172 µm, with the entire stock latency table unchanged. FTc E/W/S and exact placed failure follow-up may add rows to this foundation.
- FTc stage 3_4 took 9m00.79 on Intel1. The physical repair_design call took 59s, then intermediate reporting dominated the remainder before ODB writing. For the next eligible scoped place-only specs use the already supported `--ab OT_SKIP_PRECTS_METRICS=1 --why 'skip intermediate stage 2/3 summaries and retain explicit gates'`. Stock installer and regression coverage preserve explicit gates and the final placement review. Audit other lanes before broader adoption.
- Stock fill and empty-area holds remain. Dedicated separator morphology accounts for low global occupancy. The owner method question is under OWNER? in CODEX-LOG. No GRT or route began. Complete the source package, then use stock scoped bind and fresh source visual plus exact automatic and independent physical reviews. Stage count or clock-window decisions that need native timing remain explicit.

