# FABLE-FIX-HEAD-LEP0N (Fable, 11-21 05:3x PST): hd_lep0N owner + HEAD plan-event rows (successor of OPUS-FIX-HEAD-LEP0N-R4)

Predecessors: lanes/handoff/OPUS-FIX-HEAD-LEP0N-R4.md (forms, band fix, held HEAD rows), -R3 (congestion measurement), -R2, FABLE-FIX-HEAD-LEP0N.md (11-20).
Lane dir: epyc10 F=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-env. Hub logs: intel2 ~/fable-fix-head-lep0n/. OT_LANE=FABLE-FIX-HEAD-LEP0N.

## Env diff (3+ failure rule), measured 05:3x
Reference = the r16 WAVE kit of the same type (epyc10 kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r16/items/hd_lep0N/gen/hd_lep0N)
and kit_wave.json dies.s81_head die_gen_env + item_env.hd_lep0N.
- R4's private kits shelf_bf / col_bf (gen script Codex lep_shelf_remapped_gen_v2.sh) used a hand env subset. Their config.mk lacks
  OT_PGCAP=1 (+ pg_pair_cap.tcl hook in grt_pre.tcl), OT_PLACE_MAX_FANOUT=64, OT_CLAND_STRIP_DENS=1, OT_PG_CELL_KEEPOUT=0; no flow_tag;
  gen had no OT_IO_HOLD=sender_min, OT_SIGNED_VIEW_SHA, OT_GPL_SPARSE_UTIL=0.10, OT_RFLOW=0, and an extra --cland-pinslot all.
  Without PGCAP their GRT overflow is not comparable with r11b (which had it).
- No S81 global-place exit on any r16 kit (prefix bug fixed in tools 745c8f11); s81_head is not in RFLOW_DIES.
- Fix: F/lep_gen_waveenv.sh (exact wave env, wave gen args) + F/run_we.sh NAME SRCPLAN (gen -> preflight -> strict bind/LATCHECK -> G0; writes flow_tag).

## In flight
- col_we pipe oth-ubuntu-1162507-1795267891, shelf_we pipe oth-ubuntu-1162486-1795267891 (epyc10; hub {col_we,shelf_we}_pipe.otrun.log).
  On WE_PIPE_PASS: launch kit  ot-run --mem 48 --threads 12 --hosts epyc10 --dir F/NAME/gen -- bash F/NAME/gen/gen/run_kit.sh F/NAME/gen/gen/hd_lep0N route 48 12
  then cancel the matching old kit (ot-run --cancel exact unit; R4 found --cancel may reach only the client: check the container).
- Old-env kits still running (R4 units): shelf_bf oth-ubuntu-531201-1795266567, col_bf oth-ubuntu-520697-1795266534
  (kits epyc10 opus-fix-head-lep0n-r3/{shelf_bf,col_bf}/gen/gen/hd_lep0N; log is run_route.log, NOT run_place.log as R4 wrote).
- First read on any kit: grep "OT_CLAND dry pass\|BAND FAIL\|OT_CLAND placed" run_route.log; then GRT east band (x 800-1600, y 550-700)
  vs r11b (opus-fix-head-lep0n-r3/cancelled_ref/r11b/reports congestion-*.rpt).

## Held HEAD rows (next batched HEAD event ~11-22 01:xx): see R4 handoff list (R4-1 macro form, R4-2 tap moves, R4-3 late-meta RTL, START reach, SERDES-R4).
- COORD 05:3x (low priority, after lep0N): r16 has no START stage provider (start_stages.json/.sv), so TOKEN-1121's HEAD transport check cannot run.
  When the HEAD event applies and the die clock runs (die_trial ctree.v/.tcl + die_sta_related tap_arrivals): head_start_sources.py /
  start_stage_emit.py emit, then bench_fixed.py gen ... --top completed/s81_head_top.sv --extra completed/start_stages.sv. Details in TOKEN-1121 posts.
- Sign-off provenance: a private proof that signs must be rebuilt from a src_manifest tree (the HEAD event carries the rows).
- hd_serdes, host_e, host_n: deferred re-signs, running jobs finish, no new builds.

## UPDATE 11-21 ~07:00 PST (supersedes "In flight" above)
- Wave-env pipes PASSED (preflight 0, strict bind, cohort 26/26, LATCHECK 329/329, G0 0); config.mk == r16 wave kit except the plan-derived SDC sha.
- RUNNING (epyc10, GOAL=route, waiter armed on band checkpoint / job end):
  col_we   oth-ubuntu-1587844-1795268678, kit F/col_we/gen/gen/hd_lep0N, prepared plan bb5a400f362f (input plan_reset 8ef51cce2f23), hub col_we_kit.otrun.log
  shelf_we oth-ubuntu-1587841-1795268678, kit F/shelf_we/gen/gen/hd_lep0N, prepared plan 9f2a56b66b34 (input 394f7f1a6760), hub shelf_we_kit.otrun.log
  Waiter re-arm per NAME: until hub NAME_kit.otrun.log has "ot-run: RAN|NOT RUN|interrupted" or kit run_route.log has
  "OT_CLAND dry pass|BAND FAIL|OT_CLAND placed .* FIRM in nonoverlapping|FAIL_PREFLOOR|[ERROR"; sleep 300.
- CANCELLED by this lane (superseded, old env, ~35 min in): col_bf 520697, shelf_bf 531201 (ot-run --cancel by exact --dir; containers gone). COORD told.
- HEAD-START-R16 (COORD 06:5x): r16 K straps are bound to the NF15b START tree (1488 stages) while providers + clock e5c13 use l48 (1251):
  transport bench fails 211/329. That lane re-plans START on e5c13, re-binds K, emits the provider. It coordinates the HEAD plan change with
  this lane; plan shas above were posted to it. Its rows + the lep0N rows go in the same HEAD event (lep0N rows re-bound on its base);
  regenerate the lep0N proof on its base if it touches hd_lep0N START/K pins or relay sites. This also covers the earlier COORD START-provider item.
