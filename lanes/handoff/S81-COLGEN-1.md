# S81-COLGEN-1 handoff (2026-11-14/15)

Lane: S81 column generator mechanisms C2 (reset/flush driver replication) and C4 (lane-pad station routing), FABLE-TYPES-S81-COL.

## Code (merged / approved)
- main 471e3ce14da: tools/die_plan/reset_replicate.py, lane_pad_route.py, colgen_smoke.py, bind.py hook (emit_type), schema key partition_types[T].reset_replicate (+ die_plan.schema.json), tests (test_reset_replicate.py, test_lane_pad_route.py).
- claude/s81-colgen-1b @733ef61a993 (approved, goes into B6f): reset_replicate fans assign loads out per region (no shared "rest" copy).
- No force-push; later rebases go to a new branch name.

## C2 reset_replicate
Plan key partition_types[T].reset_replicate = [{driver | driver_re, region_re?, grid_um?, optional?}]. Last stage of the named 1-bit ot_dp_dly becomes n-1 common stages + one kept ot_dp_rrelay per region (keep_hierarchy, no opt_merge). Latency equal (n). Region = grid cell of the sink hard core (grid_um) else regex group of the sink instance name; assign-defined wires carrying the driver (e10/e11/e12/e14 element-pair buses) are cloned per region through the assign chain; dead assigns dropped; only loads outside any instance keep a "rest" copy. W must be 1.
Smoke (col_h9_r2 pvb2cd22a7 bound sv, kit epyc10 s81-col-inherit/h9r2_clb8d_pvb2cd22a7): 68 copies, 4 assign buses split, 112 loads, 7 stages kept, 0 loads on old wire, no shared rest; yosys elab ok (ot_dp_rrelay 39 -> 107); iverilog cycle equivalence tests.
Use: B6c4_cg.json has it on 60 col_h9_r2 types (driver_re u_d\d+_6_Y, grid_um 300, optional) -> B6c4_cg is the B6d base (sha1 a9b3e628e0f6, s81-b3-clk/ev/B6c4_cg.json). The B6cg bind in flight carries the earlier 61-copy version; B6f gets 733ef61a993.
Not proven: CTS proof (rst_n_pin >= -42 ps) on col_h9_r2 needs a bind + kit CTS.

## C4 lane_pad_route
lane_pad_route.py PLAN TYPE_OR_RE (--re) --bus NAME | --all [--limit 400]: wall = bf_col3/bf16_half cores grown 50 um (and to the die edge where the gap < 100 um); shortest Manhattan route on the Hanan grid avoiding walls (strip travel penalised); stages at equal arclength, slid off cores and wall zones; stage count grows only if a hop > 400 um (cycles_added reported, latency row is DIE's). --apply writes regs_um; --all only touches entries with a stage in a wall zone or a hop > 405 (G0 reach).
col_h10_r1 (12 types, frame_int_i1): 5 -> 5 stages, regs [[518.586,0],[641.308,66.47],[690.398,300.572],[973.59,300.572],[1274.782,300.572]], route 1699 um, max hop 393 -> 377 um, 3 strip stages -> 0 in wall zone. col_h9_r2 frame_int_i0 needed no change. r0 families: route not found for some (min channel 100), skipped, not in scope. Rows: s81-colgen-1/ev/lane_pad_delta.json.
Stage 0 stays in the open strip gap at x 518 (west wall blocks any earlier exit north); the first hop still runs 377 um along the strip under the west wall.

## Proof runs (numbers pending, see STATE lines)
- G0 of B6c4_cg vs 274 control: epyc7 s81-colgen-1/g0run (rc file when done); compare via the s92g0e.sh diff recipe (control cg/prebind_ctl/g0/g0_report.json).
- Strict bind + LATCHECK B6cg: epyc7 s81-b3-clk/log/B6cg.log, run/b/B6cg.
- C4 proof GRT (place->GRT, M7, resumed from floorplan): kit col_h10_r1__t1__cl95b37463__pv799da6f8: NEW pads on epyc7 s81-colgen-1-c4/<kit>, CONTROL (old sites, same config) on epyc2 s81-colgen-1-c4/ctl/<kit>; logs intel2 ~/s92/colgen_c4_new7.log / colgen_c4_ctl2.log. Baseline M8: 44,569 overflow (M6 40,502), 2,509 gcells at x 680-900 y 0-120. Pass = those gcells at 0 on M7 and not worse than control elsewhere (the new route crosses the 56 um p6 channel: check x 500-700 y 0-310). The epyc10 copies of these runs were cancelled (load 228).

## Open
- READY owed to COORD when G0 shows 0 new vs 274 and bind RC 0.
- C2 CTS proof; C4 GRT numbers.
- Scratchpad clone deleted; a sparse clone r3 may remain in the localhost scratchpad (delete).
