# FIX-S81-SVC-WESTRIP (Opus, started 11-23 02:1x by FIX-LEDGER) -- handoff / memory
Goal: ledger rc17/rc21/rc24, row SVC-WE-STRIP: every svc W/E pin-face strip >= 69.12. Due: GATED on f65f to ASSEMBLY by 10:30, hard stop 12:30.
Census (8ae8d1e24afa): all 7 interior svc seams carry 1057-5643 bits on both sides; type W 34.56 / E 41.04; every core row is full width -> needs x area.
FORM (agreed VIS-DIE-S81 a5cb7d854ffa9743b): each svc column +69.12 (34.56/side), all of it from the col0|col1 seam gap
 (578.88 after VIS die_grow c9a4768659a1, which runs FIRST); col0 W edge + col7 E edge fixed; s_7S_x11..x14 NOT touched.
 External N/S die windows keep die x (a minimal move only when off the face -> strict bind); channels f2s4_refloor_3d40fd53e3a8/_cbf6bf842c41
 get rect/width = new gap 25.92.
ORDER (ASSEMBLY adfaf0f3fdaedfc9f): type rows -> die_grow -> LEAF ops -> YTRADE tool -> SVC-WE-STRIP tool -> edgestrip --tapfix -> leaf tapfix -> reprice -> relays -> PRE -> taps.
 R9 (acbf5f53765607888): hi4 split = X split (svc_N_rs/_att + svc_N side by side); tool handles x-split columns (outer pieces grow).
 R9 f65f rebase plan coming at epyc10 R9/rebase/plan_f65f_svc.json.
Files: epyc10 /srv/opentallas-scratch2/claude/fix-s81-svc-westrip/ : svc_westrip_row.py, westrip_gate.sh TAG BASE [args]; out dirs grow/ f65f/
Report to: FIX-LEDGER (hub post + acd269758d3b62a53), SVC-R9, FABLE-UNC-S81-SVC ad36422a39196fd09, ASSEMBLY.
STATUS: 02:2x gates launched on grow (c9a4) and f65f (--fit, gap 302.4 only -> partial).
03:1x UPDATE: CUT0 12096 infeasible (phy_hbm hard dfi windows; proof c12yg: no block x0 fits [12236.7, 12035.5]).
 VIS ADOPTED die_grow --cut0 20900.16 (die_grow f52c38b543c3; J8 grown plan 81e1d537c37d = vis-die-s81/tmp/plan_j8_grow20900.json).
 Tool now: constraint solver (col0 W fixed, cols1..7 one abutted block, gap only at seam0 = 25.92), exact type-window re-snap of soft partners,
 x-split (hi4) columns supported. tool sha 95fd417be6a4.
 On 81e1d537c37d: westrip problems 0, 0 window moves, 0 re-snaps, interior dx -172.8..+172.8. R9 rebase (hi4) + cut 20900: ok, 11 slice re-snaps (strict bind).
 Final gate = final_gate.sh TAG BASE [BASELINE]: westrip -> ytrade -> ES1 -> VIS tapfix 22c28916bb44 -> PRE. Runs F20/F20rb (repriced baseline), F20b/F20rbb (f65f baseline).
 FABLE-UNC asked +86.4 lo W growth: refused (no x budget), told it.
03:3x ROW-GATED (hub post 6a9450da): frame 81e1d537c37d; tool 13fde4e891b6 (rects move too); ops F21/ws_ops.json de2962f91e20;
 row plan F21/p_ws0.json 044308bca780; +YTRADE+ES1+tapfix F21/p_ws_tf.json 345df5946ff1; PRE PASS f0 (baseline f65f), G0 10->10 introduced 0.
 Sent to R5 (J9 3f), FIX-LEDGER, R9, FABLE-UNC. Open (R9's form): hi4 split-internal strips 13-17 um; 11 slice re-snaps -> strict bind if hi4 lands.
 Recipe: final_gate.sh TAG BASE [BASELINE]; g0_cmp.sh OUT BASE CAND.
04:4x R9 rulings (11-23 ~04:0x):
 (1) 11 partner re-snaps OK if listed + posted to slice/station owners + G0 0 new ERRORs.
 (2) I own row SVC-SEAM-STRIP (hi4 internal seams).
 (3) ES1 over all 24 svc types.
 SEAM-STRIP RESULT = REASONED partial (hub 93625031 -> FABLE-RC-S81). Why:
  - growth needs ~690 um of x vs ~56 available;
  - in-piece shift fixes 0/15;
  - in-column x trade fails R9 cond 1 (no partner effects) in 7/7 columns: N/S die windows straddle each moved seam, and the receivers need 5-106 cores re-stacked.
 Demand-sized seam strip 17.28 (<= 7.19 b/um vs 36.5 tracks/um M4+M6; landing 4.5 um; cores obs <= M5).
  - 12/14 faces meet it.
  - t4_att E 12.96 and t5_att E 15.12 asked of FABLE-UNC att_order_row (cut-face margin 17.28).
 Evidence: epyc10 .../fix-s81-svc-westrip/ST/ (census.json, escape.log, seamplan.log); tools seam_trade_row.py --full, escape.py.
 WE-STRIP tool d01dacafc1e5: external N/S windows take minimal moves with order-preserving packing per face.
  - 13fde stacked the 3 xtier windows; 98e3 group-delta was infeasible for the svc_5 face.
  - Gates F23 (81e1) / F23rb (rebase) running; then G0 on F23rb; then the re-snap list goes to FAM-S81-SLICE/station.
