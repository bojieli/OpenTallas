# FABLE-FIX-QC-SLE-R2 handoff (Fable, started 2026-11-20 23:5x PST; succeeds FABLE-FIX-QC-SLE). Family: QC sle_ctl, sle_sc, slw_sc + sle_su_c, slw_su_c* (taken from FAM-QC-HCST)

Work dir epyc9 W=/srv/opentallas-scratch2/claude/fable-fix-qc-sle/r2 (lane clone ../clone). Read this, then W/rep_r2b.json.

## Cause of the sle_ctl flat GRT overflow (bound RTL, W/base/rtl/sle_ctl__cla4f6f12f_bound.sv)
The 879 pins facing each other across the 8.64-um tap/ctl slit do not connect to each other:
- tap.hr_q (453, tap E face) <- x_fw_p2_i from the type E face: its lane pads led to (969,457), so the hop crossed u_ctl.
- u_ctl W outputs own_ch/cc_o/ag_own -> x_fw_o on the type W face: stations on the u_ctl W edge, routes over the tap.
- b_hw_hc1_o / hc2_o (tap S pins -> N face), b_tw_data_st_a_o (b_tw_data_i lane pad -> W face; its leaf (660,200) was stale: the source is
  the lane pad, not u_ctl), x_st_b_o, x_su_c_p1_o, ft cws1 / cws2: stations on, and routes over, u_tap / u_ctl.
- Every hard core AND every clock-landing macro blocks M1-M5 (LEF OBS); only M6-M8 pass over them.
V1 census (station_core.py): 21 rows with findings on sle_ctl; hc1 2,714 sites in macros / 1,574 routes over the tap, st_a_o 1,478, hc2 644.

## Fix (private plan delta W/sle_delta.py; V1 base p_h.json; W/rep_r2{a,b}.json)
1. u_tap origin 164.16 -> 56.16 (west 108 um, not the briefed 129.6: 750 b_tw_data_st_a_o pins sit behind the tap on the W face and need
   the 52-um W strip) and u_ctl 475.2 -> 514.08 (east 38.88; bounded by the u_lpad_x_su_l0_i relay sites). Channel 155.5 um. Moves only.
2. Per-bit FIRM sites for every chain that crossed a core, written as plan relay_sites (u_ist_<bus>_<k>.q[b] / .eq; the kit's existing
   rs_place_all form, no generator change): b_hw_hc0/1/2/3_o, b_tw_data_st_a_o, x_fw_o, x_st_b_o, x_su_c_p1_o. Each bit runs on its own
   polyline (launch row 10 um under the tap S pins, two-knee through the channel, over the N edge of tap / ctl), stations at equal
   arclength, a site that falls in a landing macro slides along its route (core-slide), >= 30 um off the tap / ctl pin rows.
3. x_fw_p2_i lane pad stages per bit (u_lpad_x_fw_p2_i.r[0][b] / .q[b]): hr_q bits under u_ctl and up the channel, u_rp bits NE of u_ctl;
   u_bin_x_fw_p2_i sites x 1022 -> 960. b_tw_data_i, x_st_b_i, x_hc0..3_i pad sites and the 444 u_lpad_x_su_l0_i sites follow the cores.
4. ft cws1 landed stations at x 436 (channel centre), cws2 east of u_ctl ((940,876) (945,586) (941,300) (662,289)).
5. 30 plan points the moved cores cover (collector relays, landing start stages, 3 reset consumer sites) pushed 6 um out of the box.
Evaluator after the delta: 0 station sites in a macro, 0 routes over u_tap / u_ctl (residual: short M6-M8 passes over landing macros to
the pins behind them, as in V1).
Variants: A (p_r2a.json 3739aac316be) zero added cycles, hc1 343 um / hc3 365 um worst hop;
          B (p_r2b.json 7327a8c33ef3) hc1 4->5 and hc3 3->4 stations, all hops <= 296 um, 24 lanes fixed_cycles +1 (+ latency.lanes).
p_r2c / p_r2d = A / B with cleaner nominal leaf_um on x_su_l0_i and x_hc2/3_i (census 0 rows); use the script, not these files, for V2.

## Private bind (needed: GEN refuses the V1 bound RTL, the reset identity changes when cores move)
W/bind_r2.sh TAG PLAN = QC-PLAN-R6 bind_v1.sh recipe of b_n4 (side_e.json, R8 r8_v1a.json, rt 65f3f85d7c5f, PCS pcs_e.json, NO schema preview).
bind_a2 / bind_b2 (logs W/bind_{a2,b2}.log, rc files). bind_a / bind_b = refused runs (schema preview arg), delete with ot-delete.

## Proof kits
W/kit_r2.sh TAG BIND_TAG (kit-rtl from the bind launch, kit_topology + gen.py phys on rt current), W/chain_r2.sh TAG BIND_TAG [GOAL]
(GEN then the kit's run_kit.sh, 64 GB / 16 thr). Launch: OT_LANE=FABLE-FIX-QC-SLE-R2 ot-run --mem 64 --threads 16 --priority plan
--hosts epyc9 --dir W -- bash W/chain_r2.sh k_a a2 route. Read GRT in W/k_a/gen/sle_ctl__cla4f6f12f/run/logs/asap7/*/base/5_1_grt.log
and reports/.../congestion*.rpt (20,000-marker cap per report); CTS verdicts post-hook only.

## Checks on main (4fbf6ee84e)
tools/die_plan/station_core.py (+ test): every station row on the kit site model vs every hard macro; place_precheck.py class STATIONCORE;
check.py G0 WARN station_core. Advisory. `python3 -I tools/die_plan/station_core.py PLAN [TYPE_RE]`. In-bus rows report both the per-bit
model and the packed lane-pad (regs_um) model, because the plan cannot tell which the bound RTL carries.

## Family census (V1 p_h.json, station_core.py)
sle_su_c, slw_su_c__cl19bb38ef, slw_su_c__cl92142dac: x_su_l0_o / x_su_l0_p1_o / x_su_l1_p1_o / x_ctl_o / x_sc_o / x_su_l0_i / x_ctl_p1_i /
x_ctl_p2_i rows put 60-1,866 sites each in u_suvm_u_vm8q_* / u_red_u_core; cws1 / cws2 ft hops over the vm8q cores. Same class as sle_ctl,
not started. slw_st_a_v2__cl9f076a5c (FAM-QC-HCST): x_st_b_o 460 sites in u_r2, rs_s0/rs_s1 one regs_um site in u_r1.
sle_sc / slw_sc: no finding in this class.

## STATE AT STAND-DOWN (2026-11-21 ~00:50 PST, context limit). READ THIS FIRST. Successor: FABLE-FIX-QC-SLE-R3
Nothing has been built yet: NO GRT number, NO timing, NO sign-off, NO export exists for the fix. The evaluator numbers above are static.
Running (all mine; clients on rtx-pro = localhost):
- bind_a2: ot-run client PID 3807179, unit oth-ubuntu-3565225-1795250184 (epyc9), plan p_r2a.json (variant A, zero cycles).
- bind_b2: ot-run client PID 3807180, unit oth-ubuntu-3565268-1795250184 (epyc9), plan p_r2b.json (variant B, hc1/hc3 +1).
  Started 00:36 PST; V1 b_n4 took ~25 min. rc in W/bind_{a2,b2}.rc, log W/bind_{a2,b2}.log (+ bind_X2/bind.log, bind_report.json).
  Pass = rc 0 = "R4 candidate bind errors 0" + LANE_ASBUILT verdict PASS. Variant B may fail FIXEDCYC / R8_STALE (24 lanes +1 with the
  V1 R8 table r8_v1a.json): then derive a new table (land_r8_derive.py, QC-PLAN-R8.md "R8_STALE only (expected)") and rebind with
  R8T=<table> bash W/bind_r2.sh b3 W/p_r2b.json. Variant A has no latency change and should bind in one pass.
- Launchers rtx-pro ~/fable-fix-qc-sle-r2/launch_kit.sh, PIDs 3921391 (k_a after bind_a2) and 3921392 (k_b after bind_b2): each waits for
  its bind client, posts STATE or FAIL, and on rc 0 execs
  ot-run --mem 64 --threads 16 --priority plan --hosts epyc9 --dir W -- bash W/chain_r2.sh k_X X2 route
  (client log rtx-pro ~/fable-fix-qc-sle-r2/kit_k_X.client.log, launcher log launch_k_X.log; the ot-run unit name is in the client log).
  UNTESTED: kit_r2.sh / chain_r2.sh have never run. Expected first failures are in GEN (W/k_X.gen.out, W/k_X/gen.log): the earlier GEN on
  the V1 bound RTL stopped at "physical collector_tree differs from captured bound reset identity"; the private bind should remove that.
  If GEN refuses a moved plan point (reset consumer site, collector relay, landing start stage: 30 moved, list in rep_r2a.json
  moved_points), fix sle_delta.py, rerun (see header), rebind, relaunch. Kit dirs W/k_a, W/k_b must not exist before a relaunch (ot-delete).
Baselines (same type, old geometry):
- N46C attempt, epyc10 .../ot-jobs/sle_ctl__cla4f6f12f-route-civil-redfish-276253-1795122318: GRT overflow 40.2k (it 10) -> 39.0k (it 20), flat.
- V1 wave kit epyc7 .../kit-wave/qwen_compute/s29q103S4Q9N46R6V1/items/sle_ctl__cla4f6f12f/attempt_4: placed, WAIT-VISUAL, same class
  expected (auto_geom FAIL r2r 1125 um, 2,542 captures > 405). Not mine; do not cancel (old-plan kits keep running).
Pass criteria for the proof: 5_1_grt.log overflow 0 (kit runs with OT_GRT_ALLOW_CONGESTION=1, so read the number, the kit will not stop);
then DRC 0 route, TT setup >= -42 ps, FF hold >= 0, LEC; export (AGIdock + rtx-pro, standard export). If GRT is still > ~2k after 2
rounds: read congestion-*.rpt by 20-um bin first. My ranked suspects: (1) channel cut x 358.6-514.1 at y ~400 (hc1 + hc2 + cws1 ~ 68 % of
derated V tracks) -> move hc2 east of u_ctl with +1 station; (2) W strip x 4-56 behind the tap; (3) under-ctl row y 250-337.
Variant A hops of 343 / 365 um are over the 300-um cap: if A closes GRT but misses setup on hc1 / hc3, B is the answer.
NOT DONE: (a) rows to QC-PLAN-R8 for V2: do NOT hand p_r2*.json (V1 base). Give them W/sle_delta.py (copy: lanes/handoff/
FABLE-FIX-QC-SLE-R2-delta.py) to run on the V2 plan AFTER a proof passes: usage
N_HC1=5 N_HC3=4 python3 -I sle_delta.py PLAN_IN ../ev_cache.pkl PLAN_OUT ROWS_OUT REPORT <plan_of_record dir with cores/ pins files>;
V2 moved cl_cws1_i / cl_cws2_i +116.64 um in y, so the hard-coded cws1 / cws2 ft regs_um in the script must be recomputed from the V2
landing position (equal arclength from the macro to the out pins; x 436 for cws1, east of u_ctl for cws2) and ev_cache.pkl (V1 type
pins) re-made if V2 pins differ. A reset-identity change means V2 needs its strict bind after these rows. (b) sle_su_c / slw_su_c*:
same class, census above, no design yet. (c) no kit_istations hook for the census (place_precheck + G0 only). (d) bind_a / bind_b dirs
(refused runs) and k1 (refused GEN) in W are dead: ot-delete.
Deviations from the COORD brief, on evidence: tap west 108 not 129.6; u_ctl also moves east 38.88; leaf re-sites and "two-knee /
core-slide form" are done as explicit per-bit relay_sites rather than a new generator form; station counts +1 on hc1 / hc3 only in B.
