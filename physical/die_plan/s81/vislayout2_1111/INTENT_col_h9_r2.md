# INTENT: col_h9_r2 family, form R2-APRON (VISLAYOUT2-S81, 2026-11-11)

Types: col_h9_r2__t1__{clce45cab5 (43 inst), cl774acf45 (5), clb8d86cd5 (6), clc9ad8f7e (5), cl87f3ff59 (1)} = 60 instances.
Outline 1442.88 x 1226.88 um (fixed die tile, unchanged). Positions-only delta: no cycle, port, RTL or outline change.

## What the placed layout showed (before)
- Real GRT, ce45 attempt_27 (kw43-wave-1109, epyc2): 57,273 overflow, mostly M6 H. Calibration rows for R2 are 50-68k, all M6 H.
- Hot column at x 1070-1120, y 0-320. bs11 (the bank broadcaster for the e11 ROM pair) sat in the E corner (1131.84, 155.52),
  about 300 um E of the junction it feeds. The t6p payload also sat in the E corner. Both 549-b fans crossed the e11 ROMs on M6.
- route_supply edge_outline p99 was 1.50. The worst bin is face_H at the S window (297, 16): all 1167 + 321 window bits from
  frame_int_i0 (x 6-330) run E under the c10 ROM row, at y < 40.
- The ROM pairs (e10/e11 row 1, e12/e14 row 2) sat right on the c-row bands. There was no channel between the ROM S face
  (xs_q pins, local x 145-189) and the bank/sequencer row, so the bank fans climbed over the macros.

## Dataflow (from VIS-TRIAGE INTENT + netlist-augmented core_conns)
S frame_int_i0 window (x 6-260, 1167 b) -> t6 / t6p -> t7 / t7p -> t8 / t8p -> e13 (bf).
Each bank bs1x broadcasts 549 b to both ROM halves of its pair: ROM S-face pins xs_q, N-face prow/pval.
bn1x drives the N pins. s1x is the cfg / go_tag sequencer of the c1x small ROMs. The n23..n28 node tree feeds frame_int_o0
(window x 261-329).

Timing pairs that set the form:
- frame_int_i0 -> t6 / t6p: window face to the first stage. Keep it short, going N not E.
- bs1x -> e1x.u_w / e1x.u_e: 549-b broadcast. The bank sits under the junction of its pair.
- t6 -> t7 -> t8 -> e13: row-to-row street hops of <= 405 um each.
- c10 row <-> s10 (addr / status): s10 sits mid-row.

## Hand arrangement (R2-APRON)
1. APRONS: the row-1 ROM pairs (e10/e11) and the band above them (c12/c14 row, s12/s14, bs12/bs14, t7) move N by 77.76 um.
   Row 2 (e12/e14), the c13 row, s13, t8, t8p, bn12/bn14 and the e13 group move N by 120.96 um. This opens a macro-free
   apron under each ROM row, so the S-face xs_q bundles (549 b, about 12 um of M6 per 600 b) run in a straight channel
   instead of over the macros.
2. BANKS UNDER THEIR JUNCTIONS: bs10 at (380.16, 120.96) sits under the e10 u_w|u_e junction. bs11 at (829.44, 120.96) sits
   under the e11 junction (it was 300 um E, in the corner). bn10 is at (198.72, 440.64) and bn11 at (768.96, 440.64), in the row-1/row-2 apron.
3. WINDOW CONSUMERS OVER THE WINDOW: t6 (60.48, 43.2) and t6p (181.44, 43.2) sit right over the S window (x 6-330), so
   frame_int_i0 goes N into them and no longer runs E under the c10 row. t7p (501.12, 552.96) sits beside t7 at the
   row-2 street mouth.
4. c10 ROW E OF THE WINDOW: the c10 row runs from x 285 to 669 (y 25.92), with s10 in its middle (440.64, 43.2).
   The c11 row and s11 move +34.56 in x. n23 moves into the freed E corner (1123.2, 43.2).
5. CLOCK: the added taps that the moved macros would cover or leave out of reach move to legal sites (taptune.py: 8.64-lattice
   search under the bind kit-rtl rule taps.grid_explicit_taps; outline/halo/spacing, load <= 1500, radius <= 200 um).
   ce45: clk_t17 (751.82, 557.24), clk_t20 (578.04, 616.32), clk_t23 (596.16, 730.04), clk_t24 (339.12, 613.44); max added
   radius 164.6 um. Other 4 types: clk_t20 (629.88, 616.32), t23/t24 as ce45, clk_t17 (1150.34, 609.08), clk_t22 (1126.44, 220.28);
   max 179.8 um. Grid taps are unchanged. Tap moves change the selected reset context (kit_topology), so the candidate needs
   its own strict bind (bind_r2.sh, same src_t51f + asbuilt_f as bind8) before kits.
6. Legaliser (core_place --no-search on the seed) nudged only: e13 x 518.4 -> 527.04, t7p y -> 552.96, c10_0 y -> 34.56,
   t6p y -> 69.12 (cl774/cl87f), and ROM snaps of 1-2 um. All positions are on the 8.64 lattice except the base ROM x.

## Scores (ready7 base -> R2-APRON)
- explorer bit-mm 15245 -> 15202 (-0.3%) for cl774/cl87f/clb8d/clc9a, and 15265 -> 15261 for ce45.
- RUDY ovf H 6.78M -> 2.65M, cut V 0.611 -> 0.394.
- route_supply --grt-halving edge_outline p99 1.50 -> 0.90 (max 1.13-1.14, 4 hot bins left, verdict ok).
- G0 on the composed plan: 74 errors = base 74, 0 new. R2 warnings 1011 -> 661. One new warning class per type:
  "core ports face away from their partners" (G0C advisory). The c10_6 -> s10 > 405 um warning from the first variant is gone.

## Not in this delta
Leaf station depth (S81-LEAF-CYC) and the top-metal bays (X-TIER-OTC) are untouched.
