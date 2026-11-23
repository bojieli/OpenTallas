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
