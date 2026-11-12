# INTENT: col_h9_r1 family, form R2-APRON port (VISLAYOUT2-S81, 2026-11-11)

Types: col_h9_r1__t1__{cl49d7a23e (54 inst), clf32cde8d (6)} = 60 instances.
Outline 1442.88 x 1226.88 um, unchanged. Positions only: no cycle, port, RTL, outline or core-shape change.

## Before
- Real GRT fails at about 100-138k overflow, mostly M6 H (calib). Round 1 called this ARCH (frame_int_i1 pin cycle).
- route_supply edge_outline p99 is 1.02 (max 1.19, 36 hot bins, mstreet H M2 at (297, 92)). RUDY ovfH is 8.19M, the worst of the
  R families.
- The floorplan is the col_h9_r2 floorplan at the SAME y. The names are:

  | col_h9_r1 | role |
  |---|---|
  | e5 / e6 | ROM row 1 |
  | e7 / e9 | ROM row 2 |
  | e8 | bf group |
  | c5 / c6, c7 / c9, c8 | c rows |
  | s5 / s6 / s7 / s9 / s8 | sequencers |
  | bs5 / bs6 / bs7 / bs9, bn5 / bn6 / bn7 / bn9 | banks |
  | t3 / t4 / t5 | stages |

  It also has extras: n12/n13 between ROM row 1 and band 2, rg0 on the S band, an E node column n14-n21, and n22/n19 in the
  N band. The S window is frame_int_i1 (x 6-260) and the S output is frame_int_o1. The N side carries frame_int_i0 / frame_int_o0.
- It has the same defect as col_h9_r2:
  - bs6 (the 2 x 549-b bank of e6) sits 200 um E of its junction.
  - The t3 and t4 payloads sit in the E corner.
  - The frame_int_i1 bits run E under the c5 row.
  - There is no channel under the ROM S faces.

## Hand arrangement (seed_h9r1.py)
- The same moves as col_h9_r2 R2-APRON:
  - row 1, band 2, n12 and n13 move +77.76;
  - row 2, band 3, the bf group and n17 move +120.96;
  - bs5 goes to (380.16, 120.96) and bs6 to (838.08, 120.96);
  - bn5 goes to (198.72, 440.64) and bn6 to (777.6, 440.64);
  - t3 goes to (60.48, 43.2) and t3p to (181.44, 43.2), over the S window;
  - t4p goes to (501.12, 552.96);
  - the c5 row sits at x 285-669 with s5 at (440.64, 43.2);
  - the c6 row and s6 move +34.56.
- Extras:
  - rg0 goes into the c5|c6 gap (673.92, 77.76);
  - n22 moves out of the bf group's path to the free NE strip (1218.24, 1097.28).
- Station 4 (frame_int_i1 -> bn5.rs relay) already needs more registers in the base plan (same need_more_idx [4] on a no-move
  run). It keeps its base registers, and core_place_vl2 --allow-need-more 4 applies on that basis. The other 4 stations are
  re-sited.
- Added taps: kit split re-checked with taptune. No tap moved; max added radius 176.7 um.

## Scores (ready7 -> form)
- route_supply edge_outline p99 1.02 -> 0.74 (max 1.19 -> 0.92, hot bins 36 -> 0).
- RUDY ovfH 8.19M -> 0.89M; cut V 0.66 -> 0.40.
- explorer bit-mm 9721 -> 10678 (+9.8%). This is the cost: the window -> row-2 / bf links get longer by the apron shift.
  The G0C internal-bundle advisories that grow are window -> ROM relay fans, which the bind relays cover.
- G0 on ready7 + R2 + h10 + h9_r1: 77 -> 77 errors, 0 new. col_h9_r1 warnings 361 -> 281.
