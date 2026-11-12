# VL2QC-SC intent sheet: sl_sc family re-floor (QC s25 e4820bd9d97c), 2026-11-12

Types (9): sle_sc_v1__cl115da35f, sle_sc_v1__cl7479a5ec, sle_sc_v2, sle_sc_v3, slw_sc_v1__cl63e5a7a2,
slw_sc_v1__cl64543eaf__cl4590432d, slw_sc_v1__cl64543eaf__cl5e017c6f, slw_sc_v2, slw_sc_v3.
Slot 613.44 x 1339.2 (die slice tiling, fixed). One leaf core u_core (qfd_dv_s5_sc2_leaf 244.56 x 514.08) at
(345.6, 648.0) R0: unchanged (core-shape freeze; a W move was measured in round 2 and does not help).

## Defect seen (round 2 + this round)
route_supply (s25 tools, --grt-halving edge_outline) p99 1.135-1.53, all M3 V, worst in the W ring column (sle,
5.4,642.6), the open glue (sle_sc_v2 340,848) or the E face (slw, 610,740).
Ablation (ROUTE_SUPPLY_SKIP): skip=ft -> 0.72-0.80; skip=ring -> 1.26 worst; skip=glue/station/core: no change.
So the shortage is ft wiring, not the rings and not the core.  The plan's ft station chains zig-zag in y
(sle x_fw_fe_p2: W y842 -> 536 -> 613 -> 865; x_stm_fe 1005 -> 847 -> 985 -> 1018; x_fe_fw_p1 658 -> 492 -> 519),
so ~9.5k E<->W bits make two long V jogs each through the open glue and across the W landing-ring column, although
every E<->W window pair is already aligned (in-pin y ~= out-window y).  x_su_l1_ctl and x_fw_ctl_p1 climb the 23-um
E gap / the core's W edge, piling V wires on one column.

## Form (positions only; stations count, windows, pins, rings, core unchanged)
1. Every ft slot re-sited with tools/die_plan/ft_corridor.py: straight bundles, E<->W ones over the leaf core on the
   free M6/M7, register columns in the glue (bit order kept, hop <= 394.9 um), same registered depth.
2. E<->W Z slots (window offsets 3-70 um) jog OVER the core (x 467.64): the short V jog legs ride M7 over the core
   instead of crossing the four W-glue N->S bundles.
3. x_ctl_su_c_p2 (N->S, windows straddle the core's W edge) runs in a corridor band x 284-343 W of the core, so its
   register rows are not projected onto the core edge (was a 511-b pile at x 340).
4. x_fw_ctl_p1 (W->N, 536 b; its L corner column x 479 would cross the 514-um core > reach) takes a 4-corner path:
   W pin row -> column X (W glue) -> row YTOP above the core -> out-window column -> N face; the bundle keeps its
   window spread through the turns (offsets rotated) instead of collapsing onto one column.
Ring part: LAND-RING-2 strip density (OT_CLAND_STRIP_DENS=1.0, 506b5064f28d overlay) in the builds = combined form.

5. (step 2, make_sc3.py) the five *_sc_v1 types take the sibling v2/v3 landing arrangement for two NW rings:
   x_stm_fe_p1_i moves to the W face at its in-pins (hop 233 -> 114 um) and cws2_i into the NW corner column under its
   N window; flops/widths/rings unchanged (rect_um only).  Removes the NW-corner H M2 pile (1.05-1.10 at x 210, y 1215).

Generator args (final): make_sc2.py --x 237.6 --ytop 1175.04 --ewjog 467.64 --band x_ctl_su_c_p2=284.0,343.0
  --nsjog x_ctl_su_c=604.8 --nsjog x_ctl_su_c_p1=561.6  (plan_sc_m 52b915469a77), then make_sc3.py -> plan_sc_p
  657aad6bfc23.  Base planq25/plan_qc99_s25.json e4820bd9d97c.  Only ft_slots + 10 band rects differ.

## Scores (route_supply s25 tools, --grt-halving edge_outline; G0 gates25 style)
| type | s25 p99 (worst) | plan_sc_p p99 (worst) |
|---|---|---|
| sle_sc_v1__cl115da35f / cl7479a5ec | 1.53 ring V M3 | 0.964 ring H M2 |
| sle_sc_v2 | 1.325 open V M3 | 0.904 ring V M3 |
| sle_sc_v3 | 1.337 ring V M3 | 0.879 ring V M3 |
| slw_sc_v1 x3 | 1.142-1.144 face V M3 | 0.974 ring H M2 |
| slw_sc_v2 | 1.135 face | 0.883 ring V M3 |
| slw_sc_v3 | 1.135 face | 0.882 ring V M3 |
G0: s25 265 errors / 305 warnings -> plan_sc_p 265 / 305 (g0diff: no new errors); schema + sl checks rc=0.
Variants b..o scored on the way (rs/plan_sc_*.log): b straight corridors 1.14-1.22 (open column x 340 =
x_ctl_su_c_p2 pile + W-glue Z jogs); g jogs over core + p2 band 1.06-1.09; h x_fw_ctl_p1 spread 0.88-1.15 (NW corner
H M2); m nsjogs + ytop 1175 1.045-1.094 (NW corner ring H M2, cws2/x_stm_fe_p1 bands) -> p.
