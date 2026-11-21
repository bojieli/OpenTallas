# HANDOFF FLOW-NOADV-R4 (11-20 evening)
Clone: intel2 /srv/opentallas-scratch2/claude/flow-noadv-r2 (branch flow-noadv-r2). Push log push-r4.log there.
1 PLACE-SETUP-STOP: code is in rt/current on intel1/intel2/epyc2/7/8/9/10 (epyc4 host key changed, unreadable; epyc5/6 not resolvable). rt synced ~20:00. ZERO rows yet in autopilot/log.txt: only kits generated after the sync carry it. Still open: first 3 rows (WNS, worst path, hop_um), hours saved over 6 h (~2.85 h per stopped kit).
2 PLACE-REGION: no S81 serdes kit log with OT_PLACE_REGION_* found yet; DPL-0033 not yet confirmed gone. S81-DIE-R5 watcher may retire only after that confirmation.
3 REPEAT-STOP: total-attempt cap TOTAL_CAP=6 per item@event (BLOCKED-CAP, PLAN note to owner; released by new event / unblock line, not by input change); rows already past 6 (attempt number as hint) stop at their next failure. Ledger key is now die|item@event (legacy die|item stops still hold). INFRA tool_mix error identical on 2 attempts stops (TOOL_MIX_IDENT_N), kept through the INFRA release.
4 Cancel final: place_cancelled() reads signals.log (ot-run --cancel naming the place kit) -> row CANCELLED/QUEUE-CANCELLED, no retry; place_retry_sh no longer reruns a client that exited 143/130/129.
5 test_class_stop order dependence: launch() refuses when scheduler_current() is false (kit_wave.py/autopilot.py on disk differ from the imported code, e.g. an edit/merge mid gate run). test_kit_wave_grt_arm.py now pins scheduler_current in setUpModule.

## State 21:25 PST (supersedes the "first run" numbers above)
- Tool committed in the lane clone: W/src 9fbc898cd1 tools/die_plan/link_sites.py (not pushed: needs a unit test first). W/link_sites.py is the same file.
- Rows now lie on each row's OWN planned polyline (window far end / from_um -> regs -> to_um), re-spaced; count = census need.
  Class rule: every bc_i<NN> row gets --min-stations 4 (one count on the crossing class; FABLE-PD-QC-1840 said 1 -> 4).
- Representative cbn_q00__cl622f65d2 (W/rep3/plan_*.json, rep_*.json, target 292): na_i00 4->6, nb_i00 7->9, y_o00 2->4, bc_i00 1->4,
  bc_i10 1->4; 136 legs, all <= 300 except t11.n_y -> y_o11 face register (353 by pin centre + half span; direct pin -> face, no row,
  not a census row; optional +1 station row for R7). Census (rt a4fc295c2a05 plan_geom_census.py --types 'cb*'): 0 HOP rows on the
  representative (was 5); W/rep3/census.
- W/run_all.sh OUTDIR [args] chains link_sites.py over every type with staged RTL (W/v1rtl; 6 of 17 staged at 21:20, W/kitrtl_all.sh
  still running, about 5 min per type). Run: bash run_all.sh a2 --target 292 --min-stations bc_i00=4 --min-stations bc_i10=4
  --min-stations bc_i20=4 --min-stations bc_i30=4 ; then the census on a2/plan_all.json must show 0 HOP rows on cb*.
- Proof GEN p1: W/proof.sh TYPE TAG PLAN (current runtime, private launch tree W/proof/p1; the lane-pad depth of the staged bound RTL
  is set from the plan rows = PRIVATE proof input, not a bind). Launched 21:2x via ot-run --priority proof, waiting for memory on
  epyc9; log W/proof_p1.log. Then: OT_LANE=FABLE-FIX-QC-CB ot-run --mem 64 --threads 16 --hosts epyc9 --dir W/proof/p1 --
  bash W/proof/p1/gen/run_kit.sh W/proof/p1/gen/cbn_q00__cl622f65d2 route 64 16 ; read 3_detailed_place.rpt / 4_cts_final.rpt:
  class A endpoints (u_d*_sg* -> u_pc_nk) must be gone, place WNS >= -42 (the -296 u_lk_nk latch class L clears at CTS).
- Cycles for R7 per changed row = station delta on every lane ending on that bus of the type (V/r6_bus_stations.py rule) + R8 re-derive.
