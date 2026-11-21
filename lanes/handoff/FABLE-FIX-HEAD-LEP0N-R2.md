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

## UPDATE 11-21 ~07:25 PST (supersedes the kit list above)
- col_we FAILED the band dry pass at 3_3 (59 min in): 3 native stage bands do not fit (mlwd_h2, mlwd_h3, rop_half1). Cause: LEP-BANDFIX-1 moves only
  rects < 50 % free and accepts 60 %-free sites, so ~70 of 141 stage bands of the column plan still straddle SRAM columns.
- LEP-BANDFIX-2 (F/bandfix2.py; F/col_bf2/{plan_reset.json,bandfix2.json,bandfix2.log}): undo BANDFIX-1, every band < 98 % macro-free to the nearest
  macro-free site -> 74 of 141 bands move, median 75 um, max 528 um, 7 over 150 um. That scrambles the stage data flow. COLUMN FORM PARKED: not
  launched. It needs the bands re-derived with their banks (plan work), only worth it if the shelf GRT still shows the east band congested.
- SHELF = main path. shelf_we oth-ubuntu-1587841-1795268678 PASSED the dry pass (78,023 FIRM cells), in global place (movable util 2.0 %:
  routability-driven GPL off, timing-driven kept). It has NO OT_TAP_GRT_PRE (as the wave): use it for the early placed TT / GRT congestion read.
- shelf_tg = sign-off candidate proof: same plan + gen env OT_GEN_TAP_GRT_PRE=1 (config OT_TAP_GRT_PRE=1 + OT_PINREG_PAD=1; COORD / FABLE-PD-HEAD-0700).
  Pipe oth-ubuntu-3859648-1795273702 (hub shelf_tg_pipe.otrun.log); on WE_PIPE_PASS launch its kit as in "In flight" (F/shelf_tg/gen/...).
- BEFORE GRT on either kit (FABLE-PD-HEAD-0700 lever 6, estimator only): on the post-CTS DB list every *_tb* pad-chain net and tap pin pair against
  reserved_sites.tcl M1-M7 strips (chain cells on both sides of a strip that holds the tap pin; guide length > 10x pin HPWL at GRT). Read GRT/CTS
  numbers from the final stage DB only, never 5_global_route.rpt / 4_cts_final.rpt.
- HEAD event rows carried here (assembled on HEAD-START-R16's base sha; strict bind + LATCHECK + G0):
  hd_lep0N: shelf macro form + LEP-BANDFIX-1 3 rects (plan_reset 394f7f1a6760), clock.tap_grt_pre true, late-meta RTL (R4-3). Column rows R4-2 (tap moves) dropped unless column returns.
  hd_serdes (from OPUS-FIX-HEAD-SERDES-R4, stood down): clock.tap_grt_pre true; tap groups u_enc:clk_t20, u_ptx:clk_t14; OT_S81_KP4_SYN_SCOPY define + OT_KEEP_WIRES ot_s81_kp4_dsyn:S_u once sdr2d proves.
  START hops hd_st_k5 1,676 um / hd_st_m 1,261 um: proposed to HEAD-START-R16 as owner (posted 07:1x; inputs opus-fix-head-lep0n-r3/startfix); no reply yet. If it declines, they are relay rows here.

## R2 TAKEOVER 11-21 08:1x PST (lane FABLE-FIX-HEAD-LEP0N-R2, successor Fable; supersedes the lists above where they differ)
- Units: shelf_we oth-ubuntu-1587841-1795268678 (CTS since 07:45), shelf_tg oth-ubuntu-21834-1795274496 (global place since 07:45). ot-run clients on intel2.
  Waiter form (from any host): ssh intel2 'ot-wait --kit F/NAME/gen/gen/hd_lep0N --host epyc10 --stage cts|grt|route|finish --also UNIT --timeout 28000'.
- strip_check: F/tmp/sc_test/run_sc.sh DIR [ODB] (docker openroad -python, via ot-run --mem 12 --threads 2; DIR needs strip_check.py + reserved_sites.tcl + the odb).
  TESTED on hd_serdes sdr2d 4_cts.odb: flags exactly the measured crossing nets (clk_t4 n0,n1,n2,n4,n5; clk_t5 n1,n2). Detour estimate is 30-50 um
  short of the GRT guide. Rely on cell-to-cell pair flags; PIN->d0 and bare both_sides flags are advisory.
  For a kit: copy 4_cts.odb is NOT needed; mount the kit dir read-only is not supported by run_sc.sh (it writes strip_check.json into DIR) -> copy
  strip_check.py is already in F; use a tmp DIR with hardlink/copy of the odb + reserved_sites.tcl.
- HEAD EVENT e1 (assembled, gates GREEN, NOT applied): F/event1/{compose_ev.py,run_ev.sh}, out F/event1/e1 (prep, bind, receipt, g0).
  Plan 79ac2973400d on HEAD-START-R16 p6 58f896b3fcbe / sidecar facc71b93198. Rows: hd_lep0N type (shelf + BANDFIX-1 + tap_grt_pre), hd_serdes
  tap_grt_pre + tap_group (u_enc:clk_t20, u_ptx:clk_t14). Held out: late-meta RTL R4-3, hd_serdes SCOPY define/KEEP_WIRES, column rows.
  Apply waits on R16 transport bench on p6 + the hd_lep0N proof. START hops k5/m: none on the applied plan (R16 07:49), no rows.
  Re-base: edit the three sha guards in run_ev.sh, run with a new TAG (ot-run --priority plan --plan-job bind --mem 32 --threads 8 --hosts epyc10 --dir F).
- Sign-off provenance: the proof kits are private (src_manifest off); the signed build must come from the HEAD event manifest tree.
