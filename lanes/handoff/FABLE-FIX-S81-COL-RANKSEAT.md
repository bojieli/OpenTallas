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

## RESUMED 17:4x 11-22 (after weekly limit 11:1x-17:2x)
- p3 (unit oth-ubuntu-20617-1795361471, died 16:42 rc 6) and h10_r0_p4 (oth-ubuntu-817309-1795360527, died 11:56 rc 6): GRT OVERFLOW 0/0/0
  (p3 at extra iteration 24, was 1784; h10_r0_p4 at 17, was 2475), all rank lines placed 1104/1104. Death = FAIL_POSTCTS SETUP_TRIAGE:
  TT setup_est -160.16 (p3) / -170.72 (h10p4) < -150. Not congestion. Final 5_1_grt.odb kept in both kits (epyc7).
- Worst setup class (4_cts_post_hook.rpt + 5_global_route.rpt, both kits AND H10-R4 baseline _1121190309): xd ROM stage station
  u_y_xd_*_u_e_xs_q*/go_tag .q -> u_e*_u_w ROM pin (-85/-93 at CTS post-hook), then port->u_bin hold; hold repair then drags setup
  (OT_HOLD_SETUP_GUARD stop -78 / -113). Same class H10-R4 L1e/f/g (-165..-174) and H9R0 kit C on seat-fix rebind (-158.79) while the
  same p3 type on the J7 bind + E RELAY_MID_RE row is -22.3 (H9R0-R4 17:30). => floor tools RELAY-INST seat the xd xs_q stations at
  plan sites (= COLROM kit D, -81); my kits lack the E row (wave env only).
- p6 ALIVE: run-item intel2 runitem_p6.pid, container dpkit-col_h9_r0_p6__t1__pv0012ba28-3655650 on epyc7 in 5_1_grt (2 h CPU at 17:36).
- H9R0-R4 has p3/p6/p2 on J7 bind in detailed route (GRT gate passed): do NOT rebuild those forms.
- NEXT: (1) p6 GRT verdict. (2) one p3 + one h10_r0_p4 kit on planR2 = planR1 + budgets.relay_mid_re_types {"^col_": <E regex>} (plan key,
  no env), goal route, on bind b_24a9496dfcdb; if TT >= -42 at GRT -> fan out siblings. (3) tell ASSEMBLY: J8 col needs the E row as plan key.

## COORD RULING 18:0x (Fable review, hub 503187672f): THIS LANE INTEGRATES ONE COL FAMILY ROW (all col_*, ~214 types) for J9
Row = budgets.relay_mid_re (E regex; already J8 plan key via ASSEMBLY) + clock.tap_grt_pre=true on every col type + grt_cong_iters_types
{^col_: 50} + COLROM kit-H 1,212 south seats (planH, col_h10_r1) + rank lines (rank_line_types ^col_) ; NO STAGGER, NO keep-rq.
Residual -90..-207 (xs_q station -> ROM u_w pin; x2_4_0 -> t4_payload): registered ROM-input stage at the pin, +1 cycle, family-wide.
Proof: 3 sealed --goal route reps (one h9_r0, one h10_r0, one h9_r1), then hand row to S81-J6-ASSEMBLY-R5 for J9.
COL-R5, H9R0-R4, H10-R4, COLROM-R6 feed levers here; they start no new variant kits outside this row.
Inputs: COLROM stnE/stnEH plans epyc9 opus-fix-s81-colrom-r6/srcJ8G/physical/die_plan/s81/plan_h2_2249_stnEH.json (gate bindEH, intel2
opus-fix-s81-colrom-r6/bindEH.log); relay_depth rows = existing +1-cycle stage mechanism (schema relay_depth {inst, D, side}).
Base for the row: the J8 plan of ASSEMBLY (s81-j6-r5/tmp/j8cut/RESUME.md) once sealed, else J7 + stnEH.

## 18:3x ROM-INPUT STAGE design state
- Worst path p3: xs_q station launch clk 477 -> ROM u_w falling capture, core early tap clock 272, lib setup 347: budget launch-edge->pin 142 ps
  (clk->Q+INV = 92). A +1 stage on the soft tap gains nothing; stage flop must be clocked from the ROM core early tap (clk_c<k>) -> ~+220.
- COLROM-R6 (agent ae0436ab6d9c2030f) confirmed: NO existing plan key does that (core_tap_rows raises on non hard_cores inst; tap_balance.tcl
  tb_direct_core / tb_passthru gate on isBlock; core_pin_lead_ps is hard-core only). It warned FF hold stage->ROM -175 (I expect half-cycle
  path = safe; MEASURE). COLROM sends S1/S0 GRT on stnEH + stnEH plan/bind when bindEH passes.
- I OPEN the flow change (in lane clone epyc8 fable-fix-s81-col-rankseat/clone, rebase on origin/main first):
  new key clock.stage_core_tap [{inst (rel u_y_xd_<sink>_<port>_k* stage or regex), tap (core tap name)}]:
  simplest form = pre-CTS Tcl hook that moves the CLK pins of the matching stage flops onto the net of the named core clock pin (port clk_c<k>),
  so STA prices them with the core tap source latency and tap_balance drives them with the core; touch gen_phys.core_tap_rows (accept),
  tap_balance.tcl (tb_direct_core/tb_passthru isBlock gates, tb_sinks), core_tap_ff_sdc, relay_depth sink rows D1 for the stage itself. Tests.
- Then: row plan (J8 base or J7+stnEH) -> ONE strict bind -> 3 sealed --goal route reps (h9_r0, h10_r0, h9_r1).

## 19:0x ROM-INPUT STAGE = EXISTING KEYS (supersedes the stage_core_tap flow-change idea of 18:3x; NOT opened)
- ROM RTL rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv line 111: boundary register on NEGEDGE clk (xs_*_n); lib: 13 input ports
  (cfg_v go xs_v cfg_a cfg_d go_tag xs_b xs_e0 xs_e1 xs_p xs_pos xs_q0 xs_q1) setup_falling -273 / hold_falling 295. So station(posedge, clock 477)
  -> ROM negedge reg (core tap 205 early) is a half-cycle path with 142 ps budget.
- Fix by existing plan key: relay_depth SINK row {inst: <ROM core>, port, side sink, D 1, lockup true} = posedge stage + negative-level
  lockup latch (ot_dp_lk) at the pin: latch opens at soft fall edge 893, ROM captures next fall edge (required 1452): est +490 setup,
  FF hold est +180. Declared cycles (+1 stage, +1 from the latch crossing the ROM negedge). No clock-tree change.
- planR2 (intel2 + epyc7 fable-fix-s81-col-rankseat/planR2/plan_h2_2249.json sha f37d8afdb43c, delta.json; script scratch mkplan2.py):
  J7 plan + on ALL 216 col types: clock.tap_grt_pre true; budgets.rank_line_types {^col_}, grt_cong_iters_types {^col_: 50},
  relay_mid_re_types {each col base name: E regex}; relay_depth sink+lockup rows on every ot_v41_rom_elem_q_*_gb_h[ew] core x 13 ports.
  NOT yet in it: kit-H 1,212 south seats (col_h10_r1 only; take from COLROM stnEH), stnE station rows.
- private-spec on old bind refused (KIT_TOPOLOGY_BIND_STALE) -> strict bind of planR2 RUNNING: intel2 bindR2.sh/.log/.pid, epyc7 unit
  oth-ubuntu-1293818-1795399798, OUT .../FABLE-FIX-S81-COL-RANKSEAT/ot-build/s81/src_s81_pin_3c913dbdfb23_d8j7_1117_work/b_ddbcd2eeb544 (rt 79f34e2ad42e).
  RISK: bind may refuse sink rows on ports that already have a source-level relay_depth stage ("also has a source-level pipe") -> then
  fall back to lockup on the existing source rows (needs bind.py relay_depth_lockup for source rows) .
- After bind: 3 reps --goal route --rt 73fdcdf7365e (or current if toolskew ok) on epyc7: col_h9_r0_p3__t1__cl8ce97bcb__pv1489a898,
  col_h10_r0_p4__t1__pvcc166a6d, col_h9_r1__t1__cl49d7a23e__pv0a45e191 (spec2.sh in scratch: spec.sh with planR2 + --goal route + new --bind-out).

## 19:3x planR2 v2 (sha 0fced563a60d) + bind relaunch
- bindR2 try1 (oth-ubuntu-1293818) died at pre: SCHEMA-UNKNOWN-KEY rank_line_types / grt_cong_iters_types on rt 79f34e2ad42e (predates my push)
  -> relaunched on rt 73fdcdf7365e (intel2 bindR2.log/.pid; try1 log bindR2.try1.log).
- J7 ALREADY has the posedge ROM-input stage: 104 relay_depth sink rows per col type ("FAM-S81-COL lever 1", 8 ROM halves x 13 ports, D 1) =
  the u_y_xd_<rom>_<port>_* stations that fail -85..-207. So planR2 v2 adds NO rows: it sets lockup: true on those 104 existing rows per type
  (22,464 rows, all 216 col types, full coverage checked) -> bind emits ot_dp_lk after each stage (bind.py emit_lp, relay_depth_lockup).
  COLROM-R6 warned: sink row + source-level pipe on same bit is refused (bind.py ~4936), stationed port with core_input_lockup refused (~4868);
  not expected here since rows already bind in J7, only the lockup flag is new.
- Cycle note: latch across the ROM negedge = +1 cycle at the ROM (declared? lockup is documented 0 cycles; LATCHECK / token lane must price it).
