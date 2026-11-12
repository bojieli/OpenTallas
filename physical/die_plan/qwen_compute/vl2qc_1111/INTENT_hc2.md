# INTENT sl_hc2 x6 (VISLAYOUT2-QC, 2026-11-11, AMENDMENT 4 structural fix)

## Dataflow
- S face b_hw_i (1573 b, window x 4-276) → landing ring u_cland_b_hw_i → glue → hc3 crossings.
  - The ring has 8000 padded storage flops (6400 forwarded-write, 1600 local-read).
  - The hc3 crossings are x_hc3_ctl_i (8 b) and x_hc3_i (1 b), at the SE.
- cw_s2 (S, 516 b) ↔ cw_n2 (N, 516 b) is a straight pass-through lane, x 277-366 → x 47-140. No macros are in its way.
- The type has 0 hard cores and 349k cells (measured synth), so it is dense glue (dens_A 0.42 cells/um²).

## Timing / route-critical
- The ring write side: 1573 bits enter at the S face and fan into a 5-deep storage ring.

## Defect
- The band reserve is 272 x 45 um. This equals the ring's area_reserve (12,137 um²), so the ring sits at 100% occupancy right at the face.
- Real GRT shows 4.5-5.5k overflow on M3/M5/M7 V rows at y 17-27 inside the band, plus H pin escape at x 50 / x 250 (calib.tsv, VIS-TRIAGE-QC).
- With halving OFF the same positions pass GRT with 0 overflow (slw_hc2__cla3497502__cl16607c7a arm a2). So the shortage is local pin density in a full band, made worse by the edge model. It is not a die-level track shortage.

## Structural fix (delta_hc2_e.json, plan_vl2_qc_e)
- b_hw_i band rect y1 goes from 62.64 to 103.68 on the same x span (17.28-289.25). Band area doubles, so the ring spreads at about 50% occupancy and its per-gcell pin and V-row demand about halves.
- Collector relays and the reader-start stage already sit at y 62-103, inside the new band. They are std cells and stay valid.
- The cw lane channel x 277-366 stays free.
- No cycle change and no window change: the window partner is die-level.

## Fallback (parallel only)
- The edge_outline GRT mode (AMENDMENT 2) is the parallel fallback.

## Scores
| check | value |
|---|---|
| route_supply edge_outline p99, s22 | 0.744 |
| route_supply edge_outline p99, after | 0.756 |
| G0 diff | in the CLEANSLATE2-QC row |

The ring model already spreads the ring by flop count, so it does not see the band depth. The build is the test.
