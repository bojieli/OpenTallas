# OPUS-FIX-S81-COL-RANKSEAT-R2 handoff (Opus successor of FABLE-FIX-S81-COL-RANKSEAT, started 11-22 22:3x PST)
Goal: S81 col family row (all col_h*, 216 types) -> J9 (cut 11-23 12:00, to S81-J6-ASSEMBLY-R5, manifest lanes/handoff/S81-J9-MANIFEST-1123.txt).
Predecessor handoff lanes/handoff/FABLE-FIX-S81-COL-RANKSEAT.md is the design history (do not message it; Fable 429 to 11-29).
Pairs: OPUS-FIX-S81-COLROM-R6 (agent ae0436ab6d9c2030f; ROM-half stations, S1/S0 on stnEH epyc9), FAM-S81-COL-H9R0-R4, FAM-S81-COL-H10-R4.
Lane dir intel2 /srv/opentallas-scratch2/claude/opus-fix-s81-col-rankseat-r2 (apply_r2.py, diffplan.py, j9/, tmp/).

## COORD RULING 22:4x: J9 takes planR2; planR3 (priced lockup +1) goes to J10
- apply_r2.py BASE OUT: lockup:true on relay_depth sink rows {13 ROM-input ports} of ROM halves *u_e<k>_u_[we] (104/type),
  clock.tap_grt_pre true on every col_h* type, budgets.rank_line_types {^col_: {}}. Self-check on J7 = planR2 byte-identical (0fced563a60d).
  J8 already has relay_mid_re + col GRT iterations, so they are NOT added on J8 (only with --j7-extras).
- Driver intel2 j9/j9r2.sh (pid j9/j9r2.pid, log j9/j9r2.log): waits for J8 tree kw45/src_s81_pin_3c913dbdfb23_d8j8_1117_work
  (.src-manifest.sha256 + plan) on epyc9/8/2/7 (not epyc10), ot-tree-fork -> j9/treeJ8R2 on that host, apply_r2 via ot-run, then
  ot_build_hub --goal bind (PRE + elab + strict bind + LATCHECK) --src-manifest off, rt = rt/current at start (c4c1e9e0c1dc).
  On green: hand plan sha + bind dir + delta (apply_r2.py) to S81-J6-ASSEMBLY-R5 for J9.

## Running (adopted 22:4x)
- planR2 bind PASSED 21:08 epyc7 .../FABLE-FIX-S81-COL-RANKSEAT/ot-build/s81/src_s81_pin_3c913dbdfb23_d8j7_1117_work/b_ab86b11e195d.
- 3 reps --goal route, planR2, run-item drivers intel2 fable-fix-s81-col-rankseat/runitem_{r2p3,r2h10p4,r2h9r1}.pid/.log (alive);
  work epyc7 kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/private/FABLE-FIX-S81-COL-RANKSEAT/<item>_11222107xx..
  p3 + h10p4 solid views (wave env at spec), h9r1 porous.
- p6 rank-line kit (planR1): run-item runitem_p6.pid; container on epyc10 dpkit-col_h9_r0_p6__t1__pv0012ba28-117687, GRT passed,
  detailed route iteration 15 ~1900 DRC violations falling (11301 -> 1991 by it 14).

## Done by R2
- 22:4x kit_wave item_env "col_h*" = {OT_KEEP_WIRES: ot_dp_dly:r, OT_POROUS_VIEWS: all} (hub 1ef45bfe005). Items 5 + 6 (porous ruling:
  easiest for closure; solid +900 GRT overflow per H10-R4; porous already on h9_r1/h9_r2/p5/p6).

## Open
- probe-through kit (--ab OT_PROBE_THROUGH=1) on planR2: col_h9_r2 type.
- stnEH fold for col_h10_r1 (COLROM-R6 plan epyc9 opus-fix-s81-colrom-r6/srcJ8G/physical/die_plan/s81/plan_h2_2249_stnEH.json,
  rows .../tmp/j8_stn_rows.json) -> J10 (planR3) unless S1/S0 sign and it is cheap.
- planR3 / J10: IFN(1) plan-kit regen, latency.internal_pipe_ack, frame_schedule_asb --schedule-relay-depth, X-age re-qual,
  go-pin + bank_free/sh_free loop check.

## 22:5x PST COORD: watch slw_su_c__cl92142dac
- Wave row = HELD by FAM-QC-SLWSLE-R1 (hold_items, eta 11-23 12:00 V4: GRT hotspot (500,400)/(600,200) + setup -278..-504; needs cap2b rows). No live attempt on any of 6 hosts (ps 22:5x). -> include it in the V5c kits (probe-through + sealed route).
- Gap: v5c = L0 + re-seat + taps, NO cap2b (cap2b is in l1a). If l1a binds clean, compose v5e = l1a + su re-seat + taps (+ clk_t181) so cl92142dac gets cap2b + taps together.

## 23:0x PST COORD: cancelled slw_su_c__cl19bb38ef GRT proof (epyc10 sonnet-fix-qc-vmrproof2/gen), reason design
- 75 h, 2nd GRT round (1st took 153927 s, ended congested), overflow ~1525 flat; goal grt (cannot sign); pre-V5/V3 plan.
- Old rt/7ceb ot-run client (intel2 pid 1022671) was not matched by --cancel -> TERM by exact pid + ot-run --cancel-dir --reason design; remote run.sh/run_kit.sh TERM by exact pid + docker stop dpkit-slw_su_c__cl19bb38ef-1614513. Kit dir kept (VIS-QC dumps read its 3_place.odb).
- What supersedes it is the V4 cap2b in l1a, not V5: cl19bb38ef is not a V5 re-seat or tap type. TODO: sealed --goal route kit for cl19bb38ef on l1a_bound (or on the V4 wave) once l1a binds clean.

## 23:0x PST l1a DONE = NOT clean (3 errs: LANE_ASBUILT arm_wo_arm_ei / arv_wo_arv_ei 12 vs 8, unpriced kit stations; static G0 0). l1r = the same + fixed_cycles 4->8 on those lanes -> the V4 hand-over candidate. cap2b-dependent kits (cl19bb38ef, cl92142dac v5e) move to l1r_bound. Waiter bgc4q40uc (seen l1a).

## 23:2x PST OWNER LOOK-BEFORE-LAUNCH (scratchpad visual_brief2.txt; VIS-QC a2e32d9bfa40faa1f; lanes/VIS-COVERAGE.tsv NOT yet created at 23:3x)
- V5 kit order changed: on clean v5b/v5c launch ONLY the OT_PROBE_THROUGH=1 probe kits now (slw_su_l1__clcc9d0155, sle_fw_v2__cl6740750e, slw_su_c__cl92142dac). Render + read the placed/GRT result, post it to VIS-QC; the sealed --goal route kits start only once the family row is PROBE-PASS (or NONE-NEEDED).
- cl19bb38ef on l1r_bound: probe first, too.
- V4 hand-over to R13 carries the note: first V4 attempts start only for families at PROBE-PASS/NONE-NEEDED; R13 holds the rest with kit_wave_edit, reason "LOOK-BEFORE-LAUNCH <family>". Running kits keep running.

## 23:4x PST VIS-QC (a2e32d9bfa40faa1f) family gate
- May start after V4 apply: sle_hc1 x2, native59, tt_ctlm, sle_st_b_v2. NOT passed: st_a, su_c, su_l1, fe/fw, coll_core (DRAFT rows in lanes/VIS-COVERAGE.tsv) -> include in the V4 hand-over to R13 (LOOK-BEFORE-LAUNCH holds).
- Probes wanted (send placed + GRT render paths to VIS-QC; it answers in 30 min, then I may set PROBE-PASS): su_c cl19bb38ef on l1r; st_a cl9f076a5c + clf4365a62 (on l1r, coordinate SLWSLE); fe clf110fab2 + su_l1 clcc9d0155 on v5b/v5c (plus sle_fw_v2 cl6740750e, slw_su_c cl92142dac).
- VISQC-SU-1 (if the clcc9d0155 probe shows a hotspot west of cl_x_su_c_i): landing macros flush to the E edge, pads + first station as a band along the lane4 E face, density taps there. v5b keeps the landing-slit blob (455-510,170-320) and adds x_su_c_i columns to the same 190 um E channel.

## 23:5x PST after 23:3x outage: all units alive (epyc8 l1r + l0su bind.py ~3h20; epyc10 v5b + v5c bind.py ~1h05); waiter bgc4q40uc alive (seen l1a). No change, no RESUMED post needed.
- Speed rule (hub f95aac4): probes never wait for review; I may self-review: render + READ my probe, set PROBE-PASS in VIS-COVERAGE.tsv with render path + 1-line verdict; 30-min SLA; holds release on PROBE-PASS/NONE-NEEDED.

## 00:2x PST 11-23
- SLWSLE l0su (= V3 cr + su_c cap2b) bound CLEAN 00:21: strict 0, LATCHECK 1921/1921 (epyc8 FAM-QC-SLWSLE-R1/v4r/l0su_bound). SLWSLE owns its hand-over.
- LAUNCHED slw_su_c__cl19bb38ef sealed --goal route on l0su_bound (rt 0890cc9405b7, host epyc8): spec intel2 ~/coord/autopilot/private_specs/OPUS-FIX-QC-V4-R2/qwen_compute_slw_su_c__cl19bb38ef_1123002439, run-item pid 3797619 on intel2 (systemd unit runitem-slw_su_c__cl19bb38ef), log hub-coord/autopilot/private_specs/OPUS-FIX-QC-V4-R2/cl19_runitem.log, work epyc8 .../s29q103S4Q9N46R6V3/private/OPUS-FIX-QC-V4-R2/slw_su_c__cl19bb38ef_1123002417. Render at place + GRT, READ, post to VIS-QC (self PROBE-PASS after 30 min).
- PROBE-THROUGH GAP: OT_PROBE_THROUGH needs rt >= 934ebc63141a (22:20), whose reset generators (kit_relay_depth/reset_anchor/reset_leg_plan/reset_tree) differ from the bind rt 0890/c9b8 (sig a22a11397762), so private-spec refuses --rt on every V4/V5 bind. Ruling: sealed --goal route kits double as the probes (read place + GRT renders en route). Unused probe spec _1123002309 left (never run).
- Waiter bfjstrraz (seen l0su,l1a) for l1r / v5b / v5c.

## 01:5x PST 11-23: OWNER rule 6079af4 -> V4 = ONE comprehensive QC event, all V5 folds in; 06:00 cut CANCELLED, new cut 14:00 only when every QC item in lanes/DIE-FIX-LEDGER.tsv is GATED/REASONED. Tell COORD by 12:00 on misses. Compose with QC-PLAN-R13; gate once; whole-die render; FABLE-RC-QC re-review before cut.
- l1r CLEAN 01:42: strict 0, LATCHECK 1921/1921, post-bind G0 0 (epyc8 l1r_bound; plan post-lat 1b0ccabeeac1). = V4 base.
- cl19bb38ef kit (l0su) FAILED prov_views INFRA-VIEW-MISSING: qfd_dv_s8x_btab view (qct13/views) gone on all hosts; same as sle_su_c hold (SLWSLE eta 03:00). Relaunch once the view is restored.
- PROBE-PASS redefined (fe8a2a5): whole-type hotspot census + total overflow <10% of baseline + row for every path class worse than -42 / hold <0.
- COMPOSE c1 (epyc8, chain_r2.sh = chain.sh with OT_LANE=OPUS-FIX-QC-V4-R2): l1r + v5c (merge3 vs l0, 348 leaves, 0 conflicts: su re-seat 8 types + sink-bin taps 4 types) + clk_t181. Pre c9cf5aaa75b3, TAPNAME 0/0, addtap illegal 0. Log c1.log, R8IN = l1r_bound/r8_final.json. Waiter r2_wait seen l0su,l1a,l1r (now also watches c1/c2/c3).
- FIX-LEDGER (acd269758d3b62a53): 12 QC items: OPEN rc96 st_a b_tw intra_stations (SLWSLE), rc97 btab SRAM->g_read (HCST-R3: STA-1b zero-cycle re-seat vs btab_s4r +1; pick by 08:00), rc104 su_l1 E-channel ft re-site (SLWSLE ~03:00); ROW-DRAFT SEAT-1a/1b/1c, CB Row A, cap2b/SU-2, COLL spread, DIE-SEAT-1. Rows due 13:00. Plan: c2 = c1 + every row JSON that lands by ~08:00 (bind ~4-5 h on epyc8), c3 = late rows by ~09:30.

## 02:0x PST compose state (epyc8 fable-fix-qc-v4; rows in plans/v4c/rows/, row.base.json = base type blocks)
- c1 (l1r + v5c + clk_t181) chain running (c1.log).
- c2 = c1 + VISQC-CB-1 (18 types: 17 cb + coll_core in_last/in_valid bands; merge3 2027 leaves, 0 conflicts) + VISQC-CB-STREET (cbn_q00 cl622f65d2, 749 leaves, 0 conflicts) + VISQC-STA-2 (11 st_a wholesale; vs c1 differs only in the 4 btab origins per type). Pre 44559a47df43, chain c2 running (c2.log). VIS-QC gates the same rows on its own binds (rt f01b, has probe-through) and posts results to me.
- READY for c3: rows/coll13_edits.json = COLL-R3 pkg13 targeted leaves: g_pf_0/1/2 x 492.48->544.32 (rc107), bands shr_p_rx_i -> [17.28,25.92,43.2,218.88] + monitor_0 [43.2,158.76,90.72,167.4] (rc109/SEAT-1b). NOT taken from pkg13: tap_reset_split (LEC open), xev seats, XEPRE defines, clk_t126 removal.
- STILL NEEDED for c3 (08:00): SEAT-1c pin-reg taps (TAP-GRID-R5, generate on c2 plan), rc96 b_tw intra_stations (SLWSLE; asbuilt option, not plan), rc97 g_read (HCST-R3 by 07:00), rc103 su_l1 tap affinity (SLWSLE after SEAT-1c rule), rc104 su_l1 ft re-site + VISQC-SU-1 (SLWSLE ~03:00), rc105 VISQC-SU-2 (+150 um middle row, VIS-QC form), cb rc99 Row A latch_except + HB4 rev5 (CB-R4: check whether already live in V3), rc101 CB-R4 landing bands.

## 02:2x PST
- c2 FAILED TAPNAME (10 st_a from STA-2 + cbf_q00 cl1b5a6458 from CB-1: moved btab/cores changed the density base count, so added_taps names are off). c2b = c2 + addtap --fix (table rename only) + fwdretap (OLD = c1; forwarded clock sources re-pointed by site; frozen reset consumers untouched) -> pre 4ee5a470fef2, then TAPNAME + chain c2b (c2b.log). Tell VIS-QC: their cb1d/sta2 binds will hit the same TAPNAME rename.
- ot-delete of l1b/l2b/l1a/l0x/l0y/l2 _bound running on epyc8 (disk 89 -> 135 GB free and rising).
- VISQC-FEFW-1 (sle_fw spine stacking, from OWN-QC-1123): ruled V4; asked FIX-LEDGER to add the row and VIS-QC for row JSON by 07:30.
- 02:4x: c2b TAPNAME 0/0, chain in bind. STAGED for c3: rows/fefw1.json (VISQC-FEFW-1, base c2b 4ee5a470fef2 -> ec5259b742df, 6 fe/fw types, internal_stations leg_order channel; VIS-QC gating it on epyc8 VIS-QC/fefw1g). VIS-QC also builds rc105 VISQC-SU-2 (unless SLWSLE has it) + slw_fe_v2 clf110fab2 leaf-spread by 07:30.

## 03:1x PST
- c3 (EARLY gate of staged rows) = c2b + VISQC-FEFW-1 (6 types) + COLL-R3 pkg13 leaves + FIX-SYNC r1/r2 (cbn_q11 cl5cc92dfe tap 89->90; cbx_q10 x3 y_o21 regs) + reprice (0 lanes) -> pre 3b5d2af7f2b0, TAPNAME 0/0, chain c3 running (c3.log). Script c3.sh TAG composes c2b + every rows/*.json with base_sha 4ee5a470fef2 (wholesale types) + coll13 edits + r1/r2.
- c4 = FINAL at 08:00: bash c3.sh c4 after renaming staged rows: rows/su2.json.staged -> su2.json (VISQC-SU-2: sle_su_c + slw_su_c x2, middle row +151.2 um, street y276-549) + SLWSLE/HCST/TAP-GRID rows (must be base c2b; else merge3).
- 13 gate findings (FIX-SYNC pgp on l1r): 7 SCHEMA-UNKNOWN-KEY = old c9b8 schema in l1r_bound/tree vs live V3 keys -> REASONED infra (rerun pgp on a current-rt tree). 6 coll_core FIXEDCYC (fault_io_fault, crec_tx_s0/1/2, fltc, fltvc): reprice touched 0; read c3/pgp.log; if present, fix the latency table rows or reason (LATCHECK 1921/1921 as-bound passes).
- slw_fe_v2 clf110fab2: no leaf-spread (VIS-QC reason: 25 chains end at one u_core leaf; needs core partition per bus = next event; GRT ovf 7/1; spine taps covered by c2b sink-bin taps) -> REASONED, to FABLE-RC-QC.
- DPL-0033 (ledger x5, 4 st_a kits): fixed on main f60d28bf6dc; V4 st_a kits must run flow from rt/current (flow scripts refresh from rt/current per stage) and record 0 DPL-0033.
- rc97: FABLE-RC-QC NOT accepted (-49 ps); FIX-LEDGER asked COORD to rule; STA-1b measure ~08:00 (HCST-R3) is the only V4 close.
- ot-delete done for l1a/l1b/l2b/l0x (l0y/l2 pending); epyc8 471 GB free.
- 03:3x x7 (slw_fe_v2 clf110fab2, FABLE-RC-QC rejected 745b777): posted MEASURED reason: V3 wave kit epyc10 R6V3 items/slw_fe_v2__clf110fab2 place TT setup wns 0.00, worst +6.17 ps; no 900 um wire in current form (only in leaf-spread alternative). Kit finished place 19:32 PST 11-22 and NO later stage is running (no container) -> check why/CTS later; re-read CTS/GRT final-stage setup if it runs. rc101 = already in c2b (CB-1 + STREET). rc104 owed by SLWSLE for c4.
- 03:4x x7 ADDENDUM 778bbd1: clf110fab2 leaf legs stationed by FEFW-1 in c3 (27 stations, 25 leaf legs, max hop 276 um). Gate = c3 bind + sealed route kit TT. Waiting on FABLE-RC-QC accept.
- 03:5x SU-1 row staged rows/su1.json.staged (base c2b; slw_su_l1 cla2a78701+clcc9d0155); gate su1g running at VIS-QC; c4 drops it if gate fails. VIS-QC: no further su_l1 chain row; sle_su_l1 cl5ea486db stays as in c2b; REASON for FABLE-RC-QC = E channel ft-width-bound (cws0 516b/rsf/x_st_a_fe in 190-um gap), growth sized by SLWSLE cl5ea486db GRT probe. Needs FABLE-RC-QC accept before cut.
- 04:0x LAND-CAP: c3 0 hits (STA-2 re-seats btab y>=864); v5c hits are input-only. DRIFT: rt 0890/c9b8 lacks f60d28 -> new W2/launch on rt 0d6ca1628921, chain_r3.sh, c4.sh (= c3.sh on W2 + rt 0d6c + LAND-CAP gate). Pilot c3n (plan 0add75b7851a) binding epyc8 (c3n.out). c4 at 08:00 = bash c4.sh c4 after renaming su1/su2 .staged. Kits --rt current. Posted adb9dce.
- 04:2x x12 stale tap_offset: tapoff_rows.py + census wired into c4.sh (last compose step, gate 0 missing). Trial on c3n: 1724->0. Owner me.
- 04:3x v5b (2e8cdbf9915e) + v5c bound clean on epyc10: strict 0, LATCHECK 1921/1921 (component plans, folded into c-series; old rt c9b8). Waiter re-armed for c1/c2b/c3/c3n/c4.
- 04:4x x12 all-mode: QC non-density = 2 explicit + 1 grid + 3 none; tapoff_x.py fallback in c4.sh (+34 nearest-tap rows on cbn_q00 cl622f65d2 / coll_ft cla4a25d77, 0 left). Swap in FABLE-UNC-KV all-mode tool if it lands by 07:30.
- 04:5x c2b bind REFUSED (TREE-FORK disk, superseded by c3); c1 bind cancelled exact PIDs (superseded). ot-delete c1/c2b/l0b_bound (del_0450.out). c3 (old rt) + c3n (new rt) binding. OWNERS: 3 st_a CLAND rows + 9 stale QC rows owned by me -> covered by V4 rows, relaunch from c4 bound (6aba137). VIS-QC may fork c3n_bound for st_a probe after LATCHECK.
- 05:0x rc96 STA-BTW-0 (FIX-QC-STA-BTW, 7d6aa569146e) wired in c4.sh as key-merge after compose (C4_NO_BTW=1 to skip); trial on c3n plan_m: 319 sites/11 types OK. FIX-QC-STA-BTW launches its 3 st_a probes from c4_bound.
- 05:2x c3n bind 12 errors (10 LATCH_EXCEPT_MODULE cbn/cbx + cl622f65d2 EMIT clk_t113 + RESET_ANCHOR) = CB-1 class; asked VIS-QC fix row by 07:30; fallback revert cl622f65d2 to l1r + drop unmatched by_type keys.
- 10:5x RESUMED after 06:4x-10:40 limit. QC-V4 lane (lanes/handoff/QC-V4.md) now owns V4 compose; Codex C4 81fd3e6370c0 strict bind live epyc8 c4_1123_0924_bound unit979014 (rt c84f72ee2c9e has f60d28). ADOPTED; my c4.sh RETIRED (do not run). Verified C4: cl622f65d2 == l1r, core_input_lockup == c3n (no key drop), BTW0 on 12 types; bind is PARALLEL emit. My check when bind lands: bind_core_input_pipe.json >= 2352 + 0 LATCH_EXCEPT, else rebind with OT_BIND_EMIT_J=1. Posted 89a4370.
- 11:0x COORD: serial hedge LAUNCHED epyc8 c4h_bound (unit oth-ubuntu-3427622-1795460070, hedge.sh, c4h.out): fork of 0924 tree, plan 81fd3e6370c0, rt c84f72ee2c9e, seeded asbuilt, OT_BIND_EMIT_J=1. If parallel unit979014 passes (pipe>=2352, 0 LATCH) -> cancel hedge (ot-run --cancel own unit); else V4 gate = hedge ~13:30. Class bug posted to FLOW-OPS-R3 (bc8394e).
- 11:2x DISK: ot-delete l1r_bound/tree done (+56 GB, 66->122); c3n_bound/tree, c4_1123_0819_bound/tree, rows/rebase_p7c5rt/no_freg_su_seats in progress (del_1115.out). KEEP W/tree (W3 src), W2, keep/ copies, l0b (protected). Hedge bind CONFIRMED OT_BIND_EMIT_J=1 in bind.py, started 11:18 PST. Posted 3cba329.
- 15:4x RESUMED. Hedge c4h FINISHED: strict 0, LAT 1921/1921, pipe 2352, 0 LATCH; parallel C4 pipe byte-identical -> C4 81fd3e6370c0 confirmed both modes; nothing to cancel. Class bug narrowed to diagnostics cascade (FLOW-OPS-R3). Disk epyc8 585 GB; deleting c4_1123_0819_bound/tree + c4h_bound/tree (del_1545.out; reports in keep/). rebase_p7c5rt done. Posted e62a8a6.
- 16:0x OWN 9 QC cb types (cbf_q00_s2, cbf_q01, cbf_q01_s2, cbn_q01 x3, cbf_q00 cl870de686, cbn_q11 x2): ride C4 unchanged (not in e28b row; same in successor b25b1cf7c404). Renders review_cb_1700 PASS. 9 probe-through GRT kits launched epyc8 (probes/*.out, specs in private_specs/OPUS-FIX-QC-V4-R2). Next: census at GRT -> PROBE-PASS -> sealed route kits. Disk epyc8 610 GB; all my deletes done.
- 18:4x RESUMED after 17:14 weekly limit. RHI-RST row for cbf_q00 cl1b5a6458 on compose A: 4f883c119199 PRE PASS 0 -> QC-ALLFIX (ROW-REBASED sent). 9 cb probes: 8 CTS, 1 GRT; census ~20-21:30.
- 11-24 11:01 PST: 9 C4 cb probes all GRT FAIL (overflow 1.5k..2.18M; cbn_q01 x3 ~100k, cbn_q11 cl49ae4555 2.18M, cbf_q01 x2 ~1.5-1.9k, cl5cc92dfe 6.3k). cb types now owned by QC-CB-SPREAD-R2 (C1j plan). HANDOVER posted 41d1d2d. No more cb kits from this lane. Open from me: nothing live except possibly cldd6ea846 chain (handed over).
