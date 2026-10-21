# s81sl_lepnhwd_r5b (DRIVE-S81-LEPNH 10-20)
DRIVE-S81-LEPNH r5b (10-20), successor of r4m (full core rows, no region; GRT overflow 0, native32 PASS). CLOCK (r4m gate 18:28 FAIL TT/FF pin-flop spread 114.6/106.8): clock_split_km K=8 made 8 local BUFx24 roots over clusters of 658..2,879 sinks spanning up to 325 um; TritonCTS builds each cluster net alone (path depth 4..6) and the 8-sink top H-tree (570 um avg sink wire) does not see the subtree latency, so cluster roots arrive unequal. The pre-native kit s81sl_lepnh (one TritonCTS tree, no KM) measured 40.2/36.8. r5 drops the KM split: ONE balanced TritonCTS tree over the whole tile. r5b: explicit sink clustering 24 sinks / 30 um, 15-um buffer spacing, -balance_levels (the dsfd_vm_direct_scatter cb3 recipe: spread 63 -> 28 ps). RX (r4m path_classes: 297 macro->reg paths, worst -94.9 ps TT at placement: RX SRAM q (32x128 rows across the full width) -> rid -> E-face ri pin over up to ~430 um in one cycle, the RX twin of the S81-FIX3 TXRP route failure): RTL RXOP=1 adds an RX output stage -- rid/riv stay beside the RX SRAM rows, ri leaves a second flop rank at the E face (+1104 flops, +1 lane->ri edge on the elastic off-die receive path; beat order/content unchanged; phase miter vs slice3 reference with ri delayed 1 PASS; mutant RXOPSKEW FAIL). Same outline 475.2x561.6, macros, pins, SDC as r4m.

## Safe-design checklist (owner 10-19)
1 Pins: PASS -- source-registered faces (li/ro/ml land in pin flops; ri now leaves the RXOP rank, lo the TXRP/od flops); reset_landing 2 stages.
2 Reach: FIXED -- RX SRAM q -> ri pin (~430 um single cycle, -94.9 ps) split by RXOP; TX already split by TXRP (S81-FIX3).
3 Fanout: PASS -- native census (gate synthesis) max 32 on r4m; RXOP adds 1:1 flops + 1 rnx load (gate re-checks).
4 Depth: PASS -- r4m reg->reg worst +283.9 ps at placement RC.
5 Storage: PASS -- TX 512x128 and RX 32x128 SRAM macros (no runtime-indexed flop arrays > 2 kb).
6 Floorplan: PASS (pin-bound, see fill_reason) -- macros on 43.2 lattice, full core rows, no region (r4m GRT overflow 0).
7 Clock: FIXED -- KM 8-root split removed (unequal cluster depths: TT/FF spread 114.6/106.8); one balanced TritonCTS tree
  (clustering 24/30 um, 15-um buffers, -balance_levels); io_hold_margin 0.03.
8 Schedule: +1 lane->ri edge on the elastic off-die receive path (no on-die static calendar change); priced = 0 on-die cycles.
Benches (Verilator 5.050, results/rtl/drive_s81_lepnh_1020/bench1): lep_nh / lep_nhr PASS, phase miter RXOP=1 PASS (ri vs
reference delayed 1), RXOP=0 PASS; mutants nhacc / rxopskew FAIL.
