# FABLE-FIX-KV-HUB handoff (Fable; KV hub/hroot/sys family; successor of FAM-KV-HUB-R2). CURRENT 2026-11-21 06:1x PST
Family: kv3_hroot (representative), kv3_hub_{C,Ei,Eo,Wi,Wo}, kv3_sys_c, kv3_sys_SD_v1. Rows go to KV-PLAN-R5 (D27d/D28).
Work dir: epyc8 /srv/opentallas-scratch2/claude/fable-fix-kv-hub (tree_b, launch_b, ana/, scripts). Client logs: intel2 ~/tmp/fablefixkvhub/.
Predecessor dir (read-only, its bind A still writes there): epyc8 fam-kv-hub-r2.

## Diagnosis (measured on D25d attempt_5, epyc2 kw43-wave-1109/.../KV-D25d/items/kv3_hroot/attempt_5/gen/kv3_hroot)
- Clock at CTS is fine, read post-hook only: OT_TAP_INSERTION 41 taps, mean insertion 238..268 ps, clk_t9 280 ps / skew 47.7;
  OT_CTS_POST_TIMING setup -39.71, TT +2.11 after the TT repair. So the -532 ps skew is not a pre-hook artifact: it appears at GRT.
- Cause of the GRT clock skew: OT_TAP_SPAN at CTS says 10 of 41 taps have a sink box over 300 um (clk_t9 447, clk_t10 454, clk_t17 423).
  Their tree branches route 217-432 um, and the GRT long-branch pass of clk_leaf_repeat.tcl (routed > 120 um, slew > 150 ps) puts a
  midpoint repeater on the long branch only, up to 4 passes: 39 repeaters, 7 in series in front of clkbuf_leaf_52_clk_t9, nothing on
  the sibling branches and no re-balance. FF report: fan_c[143] clock arrives 615 ps (launch flop 215 ps), leaf net slew 325 ps.
- The -753.66 is the TT number at GRT RC (tt_setup_measure_grt.log); 5_global_route.rpt is the FF corner.
- Variant A (R2 rows, plan 3f4e0024a8d1) does not fix the clock: nearest-tap replay of its planned sites gives 9 taps over 300 um
  (clk_t25 497 um with 1,214 sinks). Script ana check: /tmp/fkh_tapspan.py on epyc8 (copy in rtx-pro scratchpad fkh/tapspan.py).
- GRT max-wire repair also stalled (OT_GRT_REPAIR_NO_PROGRESS, second attempt ran with it skipped), so long data wires stayed unbuffered.

## Variant B (mine) = plan 3f4e0024a8d1 + rows_b.py -> plan 9ec33fa3c347 (after gen.py latency --inplace)
- b1 kvpc: dsel -> bin -> r_c -> r -> 2 new FIRM stations -> bout_o_emb, new internal_stations row bus:o_kvs_hroot_Q_o_emb,
  stations (1400,760) (1660,760); max hop 390 -> 273 um, 0 bits over 300; +2 cycles.
- b2 slg: o_ctl row 1 -> 2 stations (1400,700) (1660,700); max hop 321 -> 271 um; +1 cycle. reprice: 8 lanes, +12 lane-cycles.
- b3 clock: tap density on the planned register positions (ana/planned_regs_b.json): clock.added_taps +11 (41 -> 52 taps),
  0 taps over 300 um, max load 760; clock.tap_span_um 300; clock.tap_grt_pre true (GRT-RC tap + subtree balance before FF GRT).
- R2 rows h1 (kvs fan / esh re-spacing), h3 (sender_ps_types.kv3_hroot -50) are kept; h2 is replaced by b2.
- Scripts: rows_b.py, prep_b.sh (restores plan A from ana/plan_a_3f4e.json first), setup_tree_b.sh. Report ana/rows_b_report.json.

## Live units (mine; ot-run on epyc8, intel2 client pids)
- G0 B: client 2595639 -> g0gate_b/gate.out.   strict bind + LATCHECK B: client 2595642 -> bindgate_b/gate.out (about 2 h).
- Inherited bind A: client 1581881 -> fam-kv-hub-r2/bindgate_a2/gate.out (G0 A PASS 0 errors). Its result only tells whether h1-h3 bind clean.
- Re-arm: timeout 14400 ssh -o ControlPath=none intel2 'export OT_LANE=FABLE-FIX-KV-HUB; ot-wait <pid> --poll 120'

## Next
1. Bind B green (RC_BIND 0, BIND_ERRORS 0, RC_LATCHECK 0, ALL_DONE): ot-run --hosts epyc8 --mem 24 --dir W -- bash W/gen_b.sh b1.
   gen_b.sh carries the wave env (COORD ruling 05:33): flow_tag + die_gen_env + item_env[kv3_hroot] + type_args from
   intel2 ~/coord/autopilot/kit_wave.json. The inherited gen_hroot.sh did NOT (no type_args --gpl-plain/--slew-margin/--cap-margin/
   --max-wire-um 120, no OT_FLOW_TAG, OT_MAX_BUFFER_PERCENT, OT_GRT_POST_MAX_S, OT_HOLD_STOP_PS, OT_GRT_ALLOW_CONGESTION,
   OT_CLAND_STRIP_DENS, OT_CBC_REACH_UM; extra OT_PLACE_MAX_TRANSITION): do not use it.
   Diff proof/b1/gen/kv3_hroot/config.mk against the D25d attempt_5 config.mk before launch; expected differences only:
   OT_TAP_GRT_PRE / OT_PINREG_PAD, tap ports, paths.
2. run_kit.sh GOAL=route through ot-run on epyc7/8/10 with a waiter. Read: OT_TAP_SPAN (0 over 300 expected), 4_2_tapbal_grt.log,
   "OT_CLK_LEAF_REPEAT grt" count (expect near 0), tt_setup_measure_grt.log, congestion-N.rpt.
3. If bind B fails on the new clk_t41..t51 ports or on the +3 cycles: the die clock mesh / lane latency rows are the place to look
   (G0 gate first, 2 min). Fallback without new ports: move relay banks into existing tap boxes.
4. Flow item not done: clk_leaf_repeat.tcl GRT pass should re-balance (or repeat the sibling branches) after inserting repeaters;
   today it creates skew by design on any tap with a branch over 120 um. Affects every die. Post to the flow lane with the hroot evidence.
5. Proof passes -> rows_b.py + R2 rows to KV-PLAN-R5 for D28 (sign-off build must come from a src_manifest tree). Then siblings:
   run the same tap-span replay on hub_Ei/Eo/Wo/Wi/C and sys_c (hub_Ei: 26 of 81 taps over 300 um, max 491).
6. hub_Ei -433 is port_in (seam class): no builds on it. hgi faces: OPUS-FIX-KV-HGI-R3 owns; R2's in-core relay-site finding is in
   fam-kv-hub-r2/ana/station_core_hg.txt.
