# hcoll_link_e2u -- HBM-COLLECT10/LINK 10-21 MAIN: hcoll_link_e2s + RX-CRC precompute (0 added cycles)
Predecessor route hcoll_link_e2s-*-2d5040f13: NEEDS_RTL TT -139.72 / FF -3.37, DRC 0.
Worst TT setup (w18_sta_tt.log, both routes the same cone): u_codec.rf[*] -> ot_qwen_crc_parallel over 580 b (~10 XNOR levels)
-> 32-b compare -> OR4/OR4 -> fault/valid gating -> rx_v / epoch_abort / fault_cause (+ flow copies ot_prs_*), ~22 levels,
~890 ps data at TT in one cycle. CLASS: logic depth (spine clock fine: spread 33.6/32.1, equal insertion at launch/capture).
FIX (RTL ot_hgi_coll_link_e2_seq): the RX CRC is computed one edge earlier from the pin stage (p_rx_flit = rx_pin_flit_pin,
the value rf captures) and its 32 per-bit mismatches are registered beside rf (rx_crc_mm); crc_bad = rv&&ev&&|rx_crc_mm,
bit- and edge-identical to the old crc(rf)!=rf[611:580]. Stage A (pin flop -> CRC tree -> XOR -> rx_crc_mm) ~11 levels;
stage B (rx_crc_mm -> OR32 -> fault/valid) ~8 levels. Route hold margin 0.03 -> 0.05 ns (FF residual on e2s).
Geometry/spine = e2s geometry 475.2 x 172.8 (S band, SRAMs side by side), clk S centre, unchanged.

## SAFE-design checklist (owner 10-19)
1 Pins: PASS - every input at a pin flop, every output a flop Q (pin_regs opt-out reason in spec); reset_landing 2 stages, 16 copies.
2 Reach: PASS - tile faces <= 475 um, pin flops at the faces; no single-cycle wire > 405 um.
3 Fanout: PASS - rx_pin_flit_pin bits now drive rf + ~16 CRC XOR inputs (< 32); census verdict = this gate (native_census).
4 Depth: FIXED - RX CRC check split across the existing pin->rf edge (was ~22 levels / ~890 ps in one stage).
5 Storage: PASS - 2 x 282-b retry banks in 64x512 SRAM macros.
6 Floorplan: PASS - unchanged from e2s (macros on the 43.2 lattice, halo 5.4, full-width std-cell band).
7 Clock: PASS - pre-placed clock spine (e2s gate spread 33.6/32.1 TT/FF); io_hold_margin 0.03, internal hold margin 0.05.
8 Schedule: PASS - 0 added cycles (link miter vs ot_hgi_coll_link_e every output every cycle; parent schedule unchanged).
