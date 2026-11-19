# FABLE-FIX-S81-COLH9R1 handoff (Fable; owns S81 col_h9_r1, 60 types, end to end)
Work dir: epyc2 /srv/opentallas-scratch3/claude/fable-fix-s81-colh9r1 (L). Tools L/tools (rundump.sh = ODB location dump, runsta.sh = read-only TT STA, grp.py).

## 2026-11-18 23:2x finding (V = measured by me, 2 kits, D8e, TT, placement RC after tap_balance + TT repair, 4_cts.odb)
- pv36da905c: ws -277.82, 643 ends: t3_payload/i 536 (worst -277.82), t3/xai 86 (-55.45), t3/cci 1 (-34.24), bn6/e_r 20 (-13.48).
- pv4bd36c74: ws -280.20, 608 ends: t3_payload/i 536 (-280.20), t3/cci 4 (-35.48), t3/xai 47 (-26.81), bn6/e_r 20 (-13.57), t3/xbi 1 (-5.23).
- NOT a clock problem. t3_payload ck arrives at 151 ps on purpose: the core has 262 ps of internal clock (core_latency.txt, TT)
  and the kit pads ck with 3 BUFx4 to land at 151; 151 + 262 = 413 against 434-452 at the relay flops. Lib setup on i[] is -93 ps.
  A 300 ps lead would break hold on every t3_payload input (lib hold +105 FF). No lead row. Tap assignment is right.
- It IS distance, and the cause is the plan: internal_stations[4] (bus frame_int_i1, 1167 b, S face x 6..260) sites its 5 lane-pad
  stages toward the 1-bit reset capture u_bn5.rs: (527,0) (920,0) (1235.5,77.8) (1235.5,449.3) (1235.5,842.4).
  1,100 of the 1,167 bits end in t3_payload.i (536 b, pins x 573..654 y 43) and t3 (564 b, pins x 704..782 y 43), 300-500 um from
  the face pins. They tour 2,135 um and come back over ONE relay: OT_RELAY_POLY WARN lpl_6_r 1346 um, lpl_7_r 1304, lpl_8_r 1359,
  lpl_9_r 1458 (hops 652-729 um). The last leg crosses the c5/c7 ROM columns, so repair cannot buffer it (718 ps wire, slew 2244 ps).
  The other 67 bits: 1100..1165 -> lpl_16_r -> rt_15a_1 -> n15.a; 1166 -> d1_6_Y -> frame_int_o0 station bit, and the reset tree.

## Rows H9R1-I1-TRUNK-1 (0 cycles, no RTL), L/mk_rows_h9r1.py BASE OUT_PLAN OUT_ROWS (asserts the 60 types are uniform)
- internal_stations.4.regs_um = (216,25.92) (302.4,25.92) (388.8,25.92) (475.2,25.92) (540,25.92); to_um (613.4,43.2). 86 um hops.
- relay_sites: bits 1100..1166 x 5 stages (335 flop keys u_lpad_frame_int_i1.r[j][b] / .q[b]) keep the OLD sites.
- u_lpl_6..9_r.u_y_q follow by relay_mid (midpoint of q and the core pins); no explicit site.
- On D8e applied df7446e48ba9: plan L/plan_d8e_h9r1_v1.json b6a116853371, rows L/rows_h9r1_i1trunk_v1.json 795d7be5c3d5.

## State
- Gate L/gate_v1 (G0 + strict bind + LATCHECK, about 45 min) and control G0 L/gate_ctl started 23:16. Logs L/gate_v1.out, L/gate_ctl.out.
- Next: private kit of pv36da905c from gate_v1/out (kits.sh recipe of s81-geom-opus-bank), place -> CTS -> GRT, read
  4_cts_post_hook.rpt and 5_global_route.tt.rpt, then HANDOFF to S81-DIE-R3 for D8h.
- Same misdirected-trunk pattern exists in the plan for col_h10_r1 (frame_int_i1 -> bn6.rs), col_h10_r2 (frame_int_i0 -> bn11.rs),
  col_h9_r2 (frame_int_i0 -> bn10.rs). Not mine; told S81-GEOM-OPUS.
