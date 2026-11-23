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
