DIE-HEAD-34 Thu Oct 29 19:36:09 PDT 2026: hd_tile density r200 (COORD 18:4x-b (A)) fails closed - root cause + local fix estimate (CHECKED, tool run on main e4b3808d5 taps.py).
Input: Codex density plan (localhost /srv/opentallas-scratch/claude/wt/codex-head-1847/results/codex_head_dense_1847/source_plan.json, sink bins
hd_tile_sink_bins.json from V1r 3_place: 25769 local sinks, fclk_in_i 2306 excluded), copied to intel2 die-head-34/tile (bins path patched).
Cause: macro eA1 (elemA, origin 371.52,8.64, 319.68 sq; actual LEF-snapped box+8.64 halo = x 362.916..699.876, y 0.036..336.996) leaves NO legal tap
site in its S street (8.676 um) or E street (17.244 < 2 x 8.64 by 0.036 um).  11 V1r flops sit there = the reset/START raw pad relays
u_rrl_19/20/23/24/25 + u_srl_19/20/23/24/25 (+u_rrl_23 export) at (652.2,4.3) and (695.5,99.3), i.e. next to the rst/run pad pins.
Nearest legal tap: x<=358 column or y>=337 row -> 235-378 um > 200.  Only these 3 bins (11 sinks) are uncoverable (tile_tap_dead_zone.out).
Fix estimate: shift u_eA1 by one macro lattice step -4.32 um in x (371.52 -> 367.2): E street 21.56 um -> legal tap column x 695.556..699.84;
density_taps PASS: 38 taps, max load 1252/1500, max radius 191.2 um.  eA0-eA1 channel 34.56 -> 30.24 (mid tap column 12.98 um still legal).
No pin, RTL, cycle or die-level change (macro is internal to hd_tile).  Needs: kit regen + PLACE + AUTO-GEOM (GRT >=50 it) + die clock rerun.
