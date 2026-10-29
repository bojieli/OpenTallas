# DIE-QC-23 (QC die owner, successor of DIE-QC-22) -- 2026-10-28 PDT

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc23-1028 (plan/, trial15, c15_{TT,FF}, g15, hb_est23.json).
Branch claude/die-qc23-1028 (on claude/die-qc22-1028@191f31deec). Worktree intel2 wt/die-qc22-1028 now on this branch.

## 1. a0k6s collect (AP 7d28e91ad84d, intel2 ~/coord/autopilot/jobs/7d28e91ad84d)
See section 5 (status at park).

## 2a. ESTIMATE: kit hold buffers for clock.tap_window 180 + clock.seam_hold {sender 25, seam 180} (scripts/hb_est23.py, hb_est23.json)
Analytic BOUND from the plan only (no partition netlists exist: QC partition kits were never built). Kit-frame hold need
per register pair: cross-tap intra d_min >= W + t_hold + U_h; seam input d_min >= (seam - sender) + t_hold + U_h
(in_min -155); output >= sender + U_h/2 after vclk. k = ceil(deficit / HB4 FF early 44.6 ps) per bit (HB4xp67,
0.1021 um2, the die_sta_related HB4 model). Assumptions: t_hold 10, U_h 25 (no split credit), clk->q FF 18, face wire 2,
ft hop wire 25 ps -> k: input 5, ft/internal station hop 4, hard-core data pin 5, output 1 (legacy plan W 0 / in_min -40: 2/0/1/0).
Classes counted per partition: input-port bits 1.28 M, output 1.28 M, ft station hops 1.39 M, internal stations 0.61 M,
hard-core data pins 2.15 M. Glue-to-glue internal paths NOT counted (no netlist).
- Result (UNCHECKED, bound): 26.4 M HB4 die-wide (+21.7 M vs the legacy contract), 2.70 mm2. Worst partition
  sl_E0_sc / sl_E2_sc / sl_E4_sc 1.53 % of the partition outline (12,570 um2 in 0.82 mm2); median 0.29 %.
  **0 of 377 partitions > 5 %** -> COORD rule satisfied, plan event built without an ASK.
- Risk (reported, not a gate): 73 partitions get > 100 k HB4 (max c_W5_bf_01 140 k) -> counts against the 400 k
  cells/run cap of their partition kits; TT cost 83 ps per HB4 (5 per zero-logic input bit = 415 ps) is safe on
  face/station pairs but must be checked on hard-core pin paths with logic at kit time.

## 2b. STRUCTURAL long-snake fix: opt-in die_trial --region-dme-snake-cap UM (tools/die_plan/die_trial.py)
- Measured first (scripts/snake_len23.py on trial14 routed TT, stage-cal model; snake_len14.json): 1787 snake legs,
  179 longer than 1.2 mm. The calibrated model is NOT biased on long legs (> 1.6 mm: median routed/model 0.999,
  median error -0.4 ps; the DIE-QC-22 '1.37x' compared against the uncalibrated leg_ps). What grows with length is the
  routed residual: sd 9.6 ps (< 400 um) -> 11.6 (1.2-1.6 mm) -> 19.0 ps (> 1.6 mm); the 9 identical 1800-um replicas route
  -15..+41 ps off the model (c_W2_bn_01 node 15664 = +40.8, the outlier). These snakes sit on glue-to-glue UNSHARED
  paths because the merge-mode build snakes every low glue subtree that the spatial cut puts beside an early core sink.
- Fix (merge point moves up, applied to every early-merge region): per partition the glue taps are built into one DME
  tree first and each early core sink is then joined at the glue root (join(): descends only where the depths meet), so
  the elongation, if any, lands once on the shared glue root leg. Stats report snake_max_leg_um / snake_legs_over_cap.
  Default off = byte-identical trees. Fixture (4x8 glue grid + 2 interior early cores 300/250 ps): stock 3 snakes /
  1469 um snake wire -> capped 0 snakes, early delivered 299.9 / 250.2, glue spread 0.1 ps.
- Tests: test_die_trial_region_dme_snake_cap.py (3) ; all die_trial tests 96/96 PASS (CHECKED).

## 2c. Plan event + trial15 + gate (scripts/plan_event23.py, kit23.sh, chain23.sh, gate23.sh)
- plan/ev_qc23.json (sha 6410861441e5) = die-qc20 ev_a0meas (ccadb0371233) + clock.tap_window 180 + clock.seam_hold
  {25, 180}; gen_phys reads W 180, in_min -155, out_min -25 (CHECKED). cores/ census/ symlinked (views match).
- trial15 = trial14 args (stage-cal, inv2, early 1.0/0.87, snake + merge-only c_* lists) + --region-dme-snake-cap 1200.

## 4. OWNER QC PG option (c) (19:58): input to QC-PG-5 + the next plan event
- ev_qc23 does NOT carry the PG delta yet (QC-PG-5 posts bump map + M8/M9 straps). The QC plan owner applies that delta
  at the next plan event, with the window/seam keys of ev_qc23 kept.
- M8/M9 clock budget the straps must leave (scripts/m89_est23.py on trial15 routed clock GRT guides, 2W2S = 5 tracks,
  pitch 0.08 um): inside the c_* (A0 array) partitions, 620 mm2: clock wire M8 2003 mm / M9 2229 mm = average track use
  0.13 % / 0.14 % (UNCHECKED; local peaks on the feed/region trunks are higher, so straps keep the clock guide corridors
  as obstructions like mk_clkfirst13). Long-hop die signals use leftover M8/M9 (12.1c) and are not in this number.

## 5. trial16 (2b gated form, 5597e5365) = trial15 byte-identical -> snake cap REJECTED (CHECKED on routed GRT)
- The gated form (rebuild only partitions whose stock tree has a snake leg > 1200 um, keep only if shorter) rebuilt the
  same 192 partitions as the all-partition form: tree.json nodes/taps, ctree.v, clkonly.v and routed arr_TT/FF are
  md5-identical to trial15 (val16 == val15). So every regressed region (c_*_tf_00 19.5 -> 136 ps TT routed glue spread)
  had a stock snake leg > 1.2 mm, and moving the merge point up re-embeds its glue tree worse.
- Routed c_* glue spread trial14 -> trial15/16: TT p90 76.7 -> 88.7, regions > 92 ps 10 -> 14; FF p90 74.7 -> 80.0,
  > 92 ps 2 -> 10 (wins: c_W2_bn_01 130.9 -> 34.4, c_E0_tf_11 106.9 -> 28.4). Measured worse -> rejected, not tuned
  (rule). --region-dme-snake-cap stays an opt-in tool flag on this branch only (default byte-identical, 97/97 tests); no
  ROOT-MERGE requested. Main path keeps the trial14 stock tree.
- QC-MESH-EST-1 triggers (COORD 10-28): (b) hold-buffer area max 1.53 % of a partition (sl_E*_sc) < 5 %; (c) tap
  arrival movement, routed GRT TT, 7889 core/glue taps trial14 -> trial15/16: max |d| 270.8 ps (t_c_W4_tf_00__clk_t24),
  p99 199.5, 3319 taps > 30 ps; region-relative (median per region removed) max 96.3 ps, 866 > 30 -> trigger (c) FIRES
  (FF max 237.7 / rel 86.7). trial16 vs trial15 = 0 ps. (a) intra-region hold with OCV after the cap: gate g15 (same
  inputs as trial16; g16 stopped as duplicate) - see section 6.

## 6. PG delta applied (COORD 20:4x, QC-PG-5 1cee05eb9d approved)
- plan/ev_qc23pg.json sha ad01d656b2b5 = ev_qc23 6410861441e5 + a0_bump_field.py (DIL 155): 768 A0 outlines -> 2 rects,
  626.02 mm2 75-um field, M9 width 0.48 -> 0.672; die.pg == qc_pg_delta.json "die.pg" exactly (CHECKED); window 180 /
  seam_hold 25,180 kept. Built on claude/die-qc23-pg-1028 (= this branch + merge of claude/qc-pg-5-1028; 109/109 die_trial +
  test_pg_bump_fields PASS locally). QC-PG-5 re-ran trial15 clock GRT with M9 0.672: 0 overflow, arrivals identical
  (their number, UNCHECKED here). Next QC trial uses ev_qc23pg.

## 7. Gate g15 (= trial16 inputs; ev_qc23 W180, real views where signed, OCV table + shared droop) - CHECKED (gate run)
- Intra kit-contract hold at W180: plain -4.28 ps (9 pairs); WITH clock OCV -46.24 ps (279 pairs, worst
  c_W0/W5/E4_tf_00 t8->t24) -> mesh trigger (a) FIRES. trial14 at W180 (DIE-QC-22 what-if): -45.8 OCV (62 pairs, 42 in
  c_W2_bn_01): the cap moved the failure from c_W2_bn_01 to the *_tf_00 regions, it did not remove it.
- Seam kit-contract W180: +81.68 plain / +54.32 OCV PASS. CA 2537 crossings TT/FF PASS (worst lo 104.1 / hi 142.8 TT).
  Gate verdict FAIL closed (768 A0 taps without a signed view; TT intra setup 58.98, FF intra hold -527 in view mode).
- CA depth (TOK-QC-1 / 12.16b(iii)): 2525 crossings DEPTH 4, 12 DEPTH 8. All D4 crossings rely on the MESO-COUNT-1 D4 RTL
  proof (results/meso_count_1027/README.md: lag sweep K {-2,1,2,5} x DEPTH 4, clean [0.502, 3.501] T, 0 silent-wrong of
  14995); D8 on the D8 sweep line. None is without a proof, so none moved; the 12.16b(iii) text lists only 8/16 -> ASK.

## 8. Root cause of the 270.8-ps routed tap move trial14 -> trial15 (COORD 20:5x). Scripts tapmove23/slide23/legres23.
- Above the region roots nothing moved: the feed node driving each region root has 0.0 ps arrival change on 204 regions;
  region roots move <= 44.8 ps. The move is inside the rebuilt region trees.
- Fixed calibrated model (val14 coef) on both trees: within-region predicted move <= 26.0 ps (0 taps > 30); routed
  within-region move up to 96.3 ps (875 taps > 30). Absolute move: predicted up to 109.5 ps (rebuilt regions are deeper by
  design), routed up to 270.8.
- Cap-specific defect (the *_tf_00 regression): the re-embedded glue tree runs 504-um legs across A0 core rows and site
  legalisation slides 28 repeaters 146.8 um off the planned leg (trial14: 0 cells > 50 um, max 7 um) in 14 regions -> a
  392-um cell hop, leg residual +73 ps (trial14 worst leg +43). The model is blind to the slide (it assumes the planned
  route). Reason enough to keep the cap rejected; a guard "repeater off-leg > 50 um -> fail kit" would catch it.
- Not cap-specific (both trees): per-leg routed residual is small (short sd 5.6, long sd 10-12, snake sd 9-11 ps, |res|
  <= 43 ps), but it accumulates over ~8 legs per path: per-tap region-relative residual max 95.8 ps (trial14) / 98.0
  (trial16), p99 45 / 53 ps. So the stock tree is reproducible to its model only to ~+-50 ps p99 per tap; this is the
  routed spread the W180 window and the mesh estimate (Rr 30-60) already carry. It is a property of the deep (~8-stage)
  region trees, not an instability that flips between runs (same tree routes md5-identical: trial15 == trial16).

## 9. a0k6s AP 7d28e91ad84d: NOT SIGNED (FF hold) -> hold census (CHECKED, scripts/a0k6s_census.tcl on the routed odb)
- Sign-off: TT setup +29.65, FF hold -15.32 (kit std overlay in_min 0 / out_min -25; raw SDC -35.98), DRC 0, ant 0.
- 290 failing endpoints: input side 216 (ports b[]/a[] -> u_w.q regs, worst -8.36, med -3.27, TNS -688), internal
  reg->reg 74 (g_add[*] adder regs, worst -15.32 on a 51-ps T0/T1 branch skew of the kit CTS, med -4.14, TNS -358),
  output side 0. Not routed LEC / export_view (not signed off).
