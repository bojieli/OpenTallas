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

## 22:5x
- FINDING: gen_phys._relay_mid_re: env OT_RELAY_MID_RE WINS over plan budgets.relay_mid_re_types. Wave item_env sets the old
  all-u_y_ regex on every col type -> the 3 planR2 reps (wave env) do NOT apply the E regex; they prove lockup only.
  J8 apply unsets col OT_RELAY_MID_RE (ASSEMBLY j8_apply.sh) -> J9 form = E regex from plan.
- PROBE launched (J9 form): col_h9_r2__t1__clce45cab5__pv06a1adf6, planR2 bind b_ab86b11e195d, --ab OT_PROBE_THROUGH=1 --ab OT_RELAY_MID_RE=
  (unset), porous + keep_wires from col_h*; spec ~/coord/autopilot/private_specs/OPUS-FIX-S81-COL-RANKSEAT-R2/s81_col_h9_r2__t1__clce45cab5__pv06a1adf6_1122225205,
  run-item intel2 opus-fix-s81-col-rankseat-r2/runitem_probe_h9r2.{pid,log}. (first try _1122224838 stopped by me at kit_rtl to add the unset.)
- r2h10p4 waits on epyc7 load admission (load 124/96) at gen_lint; p3 in place.
- Read-only subagent checks go-pin / bank_free-sh_free loop + schedule pricing (for planR3/J10).
- Waiter: local background poll of intel2 opus-fix-s81-col-rankseat-r2/snap.sh.

## 23:1x item 3 read (read-only subagent; for planR3 / J10)
- Uniform +1: all 13 ports are the element only non-clock inputs (_gb.sv:175-178); go_pin is post g_ifn/g_go_boundary -> timeline shift.
- ef = {bank_free, sh_free} gates only cfg load (ot_s81_cfg7_seq.sv:215-216 ld_ok, level-wait pend). GO GUARD GG=13 vs stale window
  10 -> 11 with +1 (still covered); without RDX guard window 9->10 under phase spacing P>=125. No wait constant change; update the
  "window 10" basis at cfg7_seq.sv:199 + xs_field_calendar.py:103. e_st (fault,busy) = status OR, not credit.
- Pricing: frame_schedule_asb.py relay_depth_extra (:344) reads only int(D) -> must add lockup_cycles (bind_verify.py:41 counts latch 0);
  re-qualify X age: check_native_go_split.py --dd incl old age+1 (defaults 0 2 16 17 26 27, :106); xs_field_calendar.colrom_record span_tail.
- RISK: ot_dp_lk transparent-low (gen_rtl.py:98) vs IFN=1 negedge sampling -> latency +1 only if the latch->ROM hold check is met
  (else +2 / race). The FF hold >= 0 gate on the reps decides it: READ hold on u_lk_xd_* -> u_e*_u_[we] pins at GRT/route.
