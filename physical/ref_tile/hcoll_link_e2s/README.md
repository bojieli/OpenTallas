# hcoll_link_e2s -- FAM-HBM-A/COLLQ8 10-21 MAIN: e2b band geometry + clock spine
Predecessor gates (--cts, 731c935c2): e2 FAIL spread TT/FF 139.3/119.2 + GRT ovf 171; e2b FAIL clock only 121.1/108.4 (GRT clean);
e2c FAIL 131.3/120.7 + GRT 57. Class: sink-driven TritonCTS over a macro tile with ~2.4k face pin flops (6,902 sinks).
Fix: clock spine as HBM-COLLQ7-ISS r128v9 (spread 59.1/57.0 vs TritonCTS 150.3/141.9 on the same geometry).
Geometry = e2b: 475.2 x 172.8, SRAMs at (64.8,64.8)/(259.2,64.8), S-band PHY flops, clk S centre. Aspect 2.75 waived (side-by-side macro row).

## SAFE-design checklist (owner 10-19; RTL 731c935c2 ot_hgi_coll_link_e2, unchanged)
1 Pins: PASS - body registers every input at a pin flop and every output is a flop Q (pin_regs opt-out reason in spec); reset_landing 2 stages, 16 copies.
2 Reach: PASS - longest pin->flop run inside the tile < 405 um (tile faces <= 475 um, flops placed at the faces).
3 Fanout: PASS - pre-gate native census on the mapped netlist (round 2, 731c935c2): max 31 loads, reset relay max 24, kept copies survived.
4 Depth: PASS - e2 gate reg->reg setup TT positive except e2c -107 ps attributed to the late TritonCTS SRAM/face clock (fixed by spine, item 7).
5 Storage: PASS - 2 x 282-b retry banks in 64x512 SRAM macros; no runtime-indexed flop arrays.
6 Floorplan: PASS - macros on the 43.2 lattice, halo 5.4, full-width std-cell band.
7 Clock: FIXED - pre-placed equal-delay clock spine (clock_spine.tcl, SRAM clock pins own leaves) replaces TritonCTS (e2/e2b/e2c spread 139/121/131 TT); io_hold_margin 0.03. Spread verdict = this gate.
8 Schedule: PASS - 0 added cycles; link miter tb_hgi_coll_link_e2_eq PASS vs link_e, mutant OT_COLL_LINK2_MUT_DATA REJECTED.
