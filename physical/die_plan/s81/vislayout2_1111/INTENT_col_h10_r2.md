# INTENT: col_h10_r2 family, form R2-APRON port (VISLAYOUT2-S81, 2026-11-11)

Types: col_h10_r2__t1__{cl1f5d6c2a (6 inst), cl99efd374 (4), cl8b686b3e (1), clac068e56 (1)} = 12 instances.
Outline 1442.88 x 1226.88 um, unchanged. Positions only: no cycle, port, RTL, outline or core-shape change.

## Before
- Real GRT fails at 83-120k overflow, mostly M6 / M7 (cl8b686b3e: 119,291 at kw26 a18, 82,809 at s81-colh-10).
  GRT-CALIB-1 lists col_h10_r2 x3 as model misses at p99 0.82-0.97: the congestion sits over single macros.
- The floorplan is the col_h9_r2 floorplan shifted about 147 um N, with names +1 (e11/e12 row 1, e13/e14 row 2, e15 bf group,
  c11..c15, s11..s15, bs11..14, bn11..14, t7..t9, n25..n30). It has the same defect:
  - bs12 (the 2 x 549-b bank of the e12 pair) and the t8 payload sit in the E corner.
  - The t7 payload sits on the S edge at x 890, so the window bits run E for 560 um under the c11/c12 row.
  - There are only 40 um (row 1) and 58 um (row 2) between each c row and the ROM S faces (xs_q pins), so the bank fans
    climb over the ROMs on M6.

## Dataflow and pairs
These are the same as col_h9_r2 (see INTENT_col_h9_r2.md):
- S window frame_int_i0 -> t7/t7p -> t8/t8p -> t9/t9p -> e15.
- bs1x broadcasts to both ROM halves of its pair.
- bn1x drives the N pins.
- s1x sequences the c1x ROMs.

## Hand arrangement (seed_h10r2.py)
Every band goes to the R2-APRON y of col_h9_r2:
- the c11/c12 row to y 25.92;
- ROM row 1 to 207.36;
- band 2 (c13/c14, s13/s14, bs13/bs14, t8, bn13) by -69.12, to y 475.2;
- ROM row 2 to 639.36;
- band 3 and the bf group by -25.92.

This gives 118 / 101 um aprons under the ROM rows and frees 26 um at the top.

Specific moves:
- bs11 to (380.16, 120.96) and bs12 to (846.72, 120.96), each under its junction.
- bn11 to (222.48, 440.64) and bn12 to (790.56, 440.64), above ROM row 1.
- t7 to (60.48, 43.2) and t7p to (181.44, 43.2), over the window.
- t8p to (501.12, 552.96).
- c11 row E of the window (x 285-669) with s11 mid-row (440.64, 43.2); c12 row and s12 +34.56 in x.
- n25 to (1123.2, 43.2) and n27 to (1166.4, 172.8).
- Added taps: clk_t24 (275.06, 198.72) and clk_t25 (120.96, 552.96) [clk_t25/t26 on cl8b686b3e]. Max added radius is 196 um.
- core_place re-sited the internal station (frame_int_i0 relay) and it is carried in the delta.

## Scores (ready7 -> form)
- bit-mm 13328 -> 12306 (-7.7%). clac068e56 2494 -> 1922 (-22.9%; it has a smaller conn set).
- RUDY ovfH 4.27M -> 1.26M (V 0.24M -> 0.45M).
- route_supply edge_outline p99 0.90 -> 0.84 (max 0.96, 0 hot bins).
- G0 (main 0f8cdf0fa6) on ready7 + R2 + h10: 77 -> 77 errors, 0 new. col_h10_r2 warnings 789 -> 463.

## Known advisories
These G0C internal-bundle lines are new: window -> rs/rst_n relay receivers, and t7.c1 -> s12.st at 838 um (475 um in base).
The t7.c1 -> s12.st growth is the one path to watch in the build's sign-off STA (the same pattern is t6.c1 -> s11.st on col_h9_r2).
