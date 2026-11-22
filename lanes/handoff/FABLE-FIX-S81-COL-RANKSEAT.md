# FABLE-FIX-S81-COL-RANKSEAT handoff (started 11-22 02:34 PST; Fable fix lane, brief lanes/FABLE-CLOSURE-0235.md section 3)
Goal: close S81 col (214 types). Deliver rank-level seat in tools (main, tests), GRT 50 iterations via plan key, private kits to sign-off for
col_h9_r0_p3 / col_h9_r0_p6 / col_h10_r0_p4 (do NOT rebuild col_h10_r1 or col_h9_r0_p2). Pairs: OPUS-FIX-S81-COLROM-R6, FAM-S81-COL-H9R0-R4 (files the
combined J8 col set by 14:00), FAM-S81-COL-H10-R4, S81-J6-ASSEMBLY-R5 (J8 cut 16:00). Tools floor >= 6d2e187f0d.

## Dirs
- intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-col-rankseat (bindJ7.sh/.log/.pid, tmp/)
- epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-col-rankseat/clone (lane clone, cone tools + physical/common_flow), tmp/push1.log
- epyc7 bind OUT /srv/opentallas-scratch2/claude/FABLE-FIX-S81-COL-RANKSEAT/ot-build/s81/src_s81_pin_3c913dbdfb23_d8j7_1117_work/b_24a9496dfcdb

## Findings (measured 02:4x)
- The wide ranks ARE seated FIRM, but as one packed block round a point (ff_put_near spiral on the 2.16 x 0.27 um station grid), not unseated:
  p3 u_lpad_xo_i0.q 1,104 flops in x 1414.8-1436.4, y 639-668.5 (30-um gap between u_cf and the E edge) = hot bins (1350-1400, 650);
  h10_r0_p4 u_lpad_x_i0.r[0] (69 x 15 um) beside u_ist_frame_int_o0_0 (86 x 13) = hot bin (1350, 850); p6 hot bins (800-900, 1150) are the N channel
  under u_ist_frame_int_o0_2 (repair buffer nets), a channel-capacity case: 394 overflow at 10 iterations -> needs iterations, not seats.
- col_h10_r1: lpad_frame_int_i1 ranks sit at the RLYBR trunk sites (272/406/536/670,0 + 682,82), 110 x 7 um blocks in the 52-um S strip; the 5 keyed bits
  per rank are the MINORITY bits (819, 1155-1158) on the old north route. Seating all bits at those keys (COLROM kits P / P2) moves 1,259 bits away from
  their sink centroid (718, 214): expect setup loss; told COLROM-R6.
- Existing OUT-bus forms: kit_istations.ordered_station_row (N/S face buses, +-90 um row). Packed lane pads (u_lpad_*) had no line form.
- H9R0-R4 p3 / p6 kits and H10-R4 lever-1 kit continue past GRT-0116 through GRT-RESID (<= 500 overflow, -allow_congestion).

## Tool (lane clone commit 3c337c5511, pushing)
- rs_rank_line (kit_istations.RANK_TCL): all bits of a rank FIRM on a line in bit order.
- plan partition_types[].relay_rank_sites {rank: {line_um: [[x0,y0],[x1,y1]], order}} explicit rows.
- plan budgets.rank_line_types {type regex: {min_bits 512, span_um 180, min_um 40}}: auto lines for packed lane-pad ranks (across travel; 45 deg at a turn;
  clear of cores / landing bands). plan budgets.grt_cong_iters / grt_cong_iters_types {regex: n}; env OT_GRT_CONG_ITERS still wins; default 10.
- tests tools/die_plan/test_rank_seat.py.

## In flight
- J7 plan strict rebind on rt 79f34e2ad42e (>= floor), epyc7, driver intel2 pid in bindJ7.pid, log bindJ7.log (started 02:38, ~2.5 h).
## Next
1. push lands -> note rt sha. 2. private plan = J7 plan + budgets.rank_line_types for the 3 sub-forms + grt_cong_iters_types {"^col_": 50}.
3. after bind: kit_wave.py private-spec s81 ITEM --plan PRIV --tree sealed J7 --bind-out OUT --host epyc7 --rt <sha> (one rep per sub-form:
   col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898, col_h9_r0_p6__t1__pv0012ba28, col_h10_r0_p4__t1__pvcc166a6d), run-item, ot-wait --kit --stage grt.
4. GRT read (final 5_1_grt.odb) -> J8 rows to FAM-S81-COL-H9R0-R4 + S81-J6-ASSEMBLY-R5 by 14:00; sibling fan-out kits to sign-off.

## UPDATE 05:2x 11-22
- Tool PUSHED main d219668949 (rt >= 73fdcdf7365e has it). Bind-stamp generators untouched.
- J7 rebind BUILT 05:21 on rt 79f34e2ad42e: epyc7 /srv/opentallas-scratch2/claude/FABLE-FIX-S81-COL-RANKSEAT/ot-build/s81/src_s81_pin_3c913dbdfb23_d8j7_1117_work/b_24a9496dfcdb
  (pre/elab/bind/latcheck BUILT; bpc bound_param_check rc=1, 35 errors BOUND-PARAM-PARTIAL, node still BUILT; toolskew check ok vs rt 73fdcdf7365e).
- Private plan planR1 (intel2 + epyc7 fable-fix-s81-col-rankseat/planR1/plan_h2_2249.json sha 737bebdb9331, delta.json) = J7 plan +
  budgets.rank_line_types {^col_h9_r0_p3__, ^col_h9_r0_p6__, ^col_h10_r0_p4__: {}} + budgets.grt_cong_iters_types {"^col_": 50}.
- Kits LAUNCHED 05:25 (epyc7, wave env, no --ab, src_manifest on, goal auto, rt 73fdcdf7365e); run-item pids intel2 runitem_{p3,p6,h10p4}.pid/.log:
  specs ~/coord/autopilot/private_specs/FABLE-FIX-S81-COL-RANKSEAT/s81_col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898_1122052247,
  s81_col_h9_r0_p6__t1__pv0012ba28_1122052340, s81_col_h10_r0_p4__t1__pvcc166a6d_1122052426
  work epyc7 .../kit-wave/s81/18a2688b741/private/FABLE-FIX-S81-COL-RANKSEAT/<item>_<stamp>
- Check at gen: kit log "RANK-SEAT n packed pad ranks on lines", istations.tcl rs_rank_line calls, config.mk -congestion_iterations 50;
  at place: "OT_RELAY_RANK ... bits FIRM on the line". GRT verdict from final 5_1_grt.odb only.

## COORD 05:4x
- Kits must reach sign-off via goal route. Mine were spec'd --goal auto (resolves to the runner default; COORD: auto can stop at geom). Left running.
  IF a run-item ends after geom without CTS: continue by hand: ot-run --hosts epyc7 run_kit.sh <K> route 48 8 (as H10-R4 A2), ot-wait --kit K --stage grt.
  New specs: always --goal route.
- Rank-seat form posted to FAM-S81-COL-H10-R4 (L1e/L1f/L1g variants of col_h10_r0_p4) + FAM-S81-COL-H9R0-R4 for the 14:00 J8 row set.
