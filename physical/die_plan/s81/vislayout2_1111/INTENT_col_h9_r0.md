# INTENT: col_h9_r0 family, form R0-LIFT (VISLAYOUT2-S81, 2026-11-11)

Types (11): col_h9_r0_p1__t1, p2__t1__{cl0045af7b, cl9f71e63d}, p3__t1__{cl0cd90c0e, cl31d0dc4b, cl8ce97bcb},
p4__t1__{cl8ef405e8, clcb2fbfe8}, p5__t1, p6__t1. All share one floorplan (84 hard cores). Six variants have e1/e3 up to
+16 um E; the form is written relative where it touches them.
Outline 1442.88 x 1226.88 um, unchanged. Positions only: no cycle, port, RTL, outline, orient or core-shape change.

## Dataflow (what talks to what)

| Link | Bits (real) | Ends |
|---|---|---|
| xo_i0 / x_i0 type port -> u_cf xl0-3 | 1104 | E face (y 740-980 on p1-p3, 981-1221 on p4-p6) -> cf S face; 1 FIRM station each lane, landed ring u_cland_xo_i0 (5760 flops) |
| u_cf x2 broadcast -> 8 e ROM S faces | 605 | cf N face -> e0..e3 S faces (y 216 / 604.8) |
| bs* o_x -> e ROM xs_q | 2 x 512 per ROM row | bank N face -> ROM S face (facing faces, 34.56 um clearance) |
| t2 / t2p -> frame_int_o0 | 549 + 536 | stage below the top bf row -> N face x 6-260 |
| t2 / t2p <-> u_e4 | 1320 S face, 545 N face | u_e4 = bf_front_roots in the top bf row |
| cf.rd -> ret_o0 | 70 | cf S face E end -> E face y 6-115, 1 FIRM station (length-capped) |
| cf.rs -> frame_int_o0 | 1 | cf N face E end -> N face x 133, 4 relay regs (length-capped) |

## Defects seen (before)
- Real GRT (kit-wave attempt 20, p5): GRT-0116, max 118 %, 161k gcells > 90 %. The HOT marks are at (572-624, 1151-1180).
  That is the N strip right above u_e4, where t2/t2p's 1630 bits cross the top bf row through the 25 um
  e4w.u_c | u_e4 gap and turn W to the frame_int_o0 window. A second orange band sits under the e2/e3 S faces.
- route_supply (edge_outline, augmented conns) worst: street H 1.18-1.68 at (729-740, 599.4). That is the thin street
  between the bs2/bs3 banks and the e2/e3 S faces. Below the banks, the c2/c3 rows leave only a 23 um gap (mstreet H
  1.40). cf sits 17 um above n4/rg2/t0p, so the street under cf is at 1.35.
- A model bug hid this. route_supply's landing-ring growth floor-divided float um (1393.2 // 10.8 == 128.0), so the
  xo_i0 ring never grew W. It ran down the E outline as a 50 um column, and "ring V M3 1.70-1.82 at x 1420" was
  reported in every variant. That is fixed on this branch (commit 3d0030cdc5); the numbers below use the fixed tool.
- The base stations already miss their registers: no-move run need_more_idx [1, 2, 3, 4, 7] on p4-p6, [3, 4] on
  p1-p3.

## Hand arrangement (seed_r0.py v4f, cf R0)
1. u_cf goes one row up, 604.8 -> 665.28, with orient kept. That opens a 78 um street under cf. The xl / rd / rs
   stations re-site with no extra register; all stations fit, including the 5 that missed in the base. MX (xl facing
   the port) was tried: it costs station 7 a register (+1 cycle), so it is rejected.
2. The n-node tree (n5-n11, rg1) leaves the region above cf and the NE pocket. n9/n10/n11/rg1 go to the free band
   between the e3 top and the bf row (y 838); n5-n8 go to the lower E strip. The NE pocket is then free for the
   xo_i0 / ft0_i landing rings and the lane climb.
3. The port-side column of the top bf row (e4w.u_c | u_e4, 25 um) is where the t2/t2p -> frame_int_o0 bits cross
   (the real-GRT HOT); it gets wider.
   - p4-p6: u_e4 and the e4e group (u_c, u_ha, u_hb) move +43.2 E, so the column goes 25 -> 68 um.
   - p1-p3: these carry the ft0 E->W pass-through, whose fixed stage-1 station sites sit in a column at x 1142.64,
     just E of e4e.u_ha. Only u_e4 moves (+25.92), so the columns go 25 -> 51 and 56 -> 30 um. (G0 caught the
     ft0 x u_ha intersection on the first try.)
4. The c2/c3 rows and s2/s3 move -34.56 (on the 8.64 lattice) into the 46 um gap above the e0/e1 N faces. bs2/bs3
   sit at y 527.04, so the ROM S-face <-> bank bus has a 43 um apron instead of 34.56 and the bank glue side has a
   15 um gap instead of 23-um-into-the-row. The legaliser keeps the facing-face clearance and re-sites bs0
   (371.52, 155.52), t1 (596.16, 535.68) and n6-n8 itself.
- Tried and rejected:
  - v1/v2: cf MX in place or up. Stations 0 or 7 gain a register.
  - v2/v4e: bs1/bs3 under the e1/e3 junction. The street right above the bank gets worse (1.15-1.24).
  - v4d: rows -38.88. Best score (0.891), but off the 8.64 lattice.

## Scores (ready7 -> form v5a)
All scores use route_supply --grt-halving edge_outline with the ring-bin fix and the netlist-augmented core_conns.
Columns are verdict / region / dir / p99 / max / hot bins.

| type | before | after |
|---|---|---|
| col_h9_r0_p1__t1 | FLAG/street/H/1.684/2.105/335 | ok/street/H/0.943/1.001/3 |
| col_h9_r0_p2__t1__cl0045af7b | FLAG/street/H/1.596/2.105/323 | ok/street/H/0.943/1.001/3 |
| col_h9_r0_p2__t1__cl9f71e63d | FLAG/street/H/1.576/2.033/338 | ok/street/H/0.923/0.964/2 |
| col_h9_r0_p3__t1__cl0cd90c0e | FLAG/street/H/1.643/1.95/277 | ok/street/H/0.928/0.982/2 |
| col_h9_r0_p3__t1__cl31d0dc4b | FLAG/street/H/1.642/1.994/272 | ok/street/H/0.943/1.001/3 |
| col_h9_r0_p3__t1__cl8ce97bcb | FLAG/street/H/1.642/1.994/272 | ok/street/H/0.943/1.001/3 |
| col_h9_r0_p4__t1__cl8ef405e8 | FLAG/street/H/1.179/1.34/35 | ok/street/H/0.759/0.882/0 |
| col_h9_r0_p4__t1__clcb2fbfe8 | FLAG/street/H/1.179/1.34/35 | ok/street/H/0.759/0.882/0 |
| col_h9_r0_p5__t1 | FLAG/street/H/1.557/2.047/281 | ok/street/H/0.942/1.001/3 |
| col_h9_r0_p6__t1 | FLAG/street/H/1.511/1.923/275 | ok/street/H/0.917/0.963/2 |

- RUDY ovfH (p5) 6.01M -> 4.37M. The worst cut V goes 0.82 -> 0.62 at y 605.
- explorer bit-mm +0.7 % (p4) to +4.8 % (p6). This is the cost of the lowered c rows and the lifted cf.
- Stations: 0 need_more on all 10 types. The no-move base misses registers on [1, 2, 3, 4, 7] (p4-p6) and [3, 4]
  (p1-p3).
- Added taps: legal on all types after taptune; max added radius 191.5-209.4 um, inside the 1.10x slack of 220.
- G0 on ready7 + R2 + h10 + h9_r1 + h9_r0 (580d790a93c3): 77 -> 77 errors, 0 new. col_h9_r0 warnings 1440 -> 1529, all
  [internal_station] length advisories on 1-bit relay / reset nets (cf.rs, n-node fi/fo). This is the same class as
  the earlier families.
- Plans:
  - ready7 chain: 2908467b9e39 -> 580d790a93c3 (delta_h9r0_on_ready7.json).
  - h2_2249 chain: bc9a35da06d3 -> e05d5710b3e1 (delta_h9r0_on_h2_2249.json).
  - Chained apply MATCH on both.
