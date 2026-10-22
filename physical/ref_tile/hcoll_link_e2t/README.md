# hcoll_link_e2t -- FAM-HBM-A/COLLQ8 10-21 FALLBACK: enlarged compact geometry + clock spine
e2/e2c trial GRT overflow (171/57, M4) sat in the 43.2 um S band under the lower SRAM (S-face PHY pin flops + CRC).
Fix: outline 259.2x280.8 -> 302.4x345.6 (S band 86.4 um, E channel 86.4 um), SRAMs (43.2,86.4)/(43.2,216.0), clk S centre
x150.6; aspect 1.14; clock spine instead of TritonCTS.

## SAFE-design checklist (owner 10-19; RTL 731c935c2 ot_hgi_coll_link_e2, unchanged)
1 Pins: PASS - body registers every input at a pin flop and every output is a flop Q (pin_regs opt-out reason in spec); reset_landing 2 stages, 16 copies.
2 Reach: PASS - longest pin->flop run inside the tile < 405 um (tile faces <= 475 um, flops placed at the faces).
3 Fanout: PASS - pre-gate native census on the mapped netlist (round 2, 731c935c2): max 31 loads, reset relay max 24, kept copies survived.
4 Depth: PASS - e2 gate reg->reg setup TT positive except e2c -107 ps attributed to the late TritonCTS SRAM/face clock (fixed by spine, item 7).
5 Storage: PASS - 2 x 282-b retry banks in 64x512 SRAM macros; no runtime-indexed flop arrays.
6 Floorplan: PASS - macros on the 43.2 lattice, halo 5.4, full-width std-cell band.
7 Clock: FIXED - pre-placed equal-delay clock spine (clock_spine.tcl, SRAM clock pins own leaves) replaces TritonCTS (e2/e2b/e2c spread 139/121/131 TT); io_hold_margin 0.03. Spread verdict = this gate.
8 Schedule: PASS - 0 added cycles; link miter tb_hgi_coll_link_e2_eq PASS vs link_e, mutant OT_COLL_LINK2_MUT_DATA REJECTED.
