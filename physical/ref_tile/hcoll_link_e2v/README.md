# hcoll_link_e2v -- HBM-COLLECT10/LINK 10-21 FALLBACK: hcoll_link_e2t + RX-CRC precompute (0 added cycles)
Predecessor route hcoll_link_e2t-*-2d5040f13: NEEDS_RTL TT -109.51 / FF -22.92, DRC 0.
Worst TT setup (w18_sta_tt.log, both routes the same cone): u_codec.rf[*] -> ot_qwen_crc_parallel over 580 b (~10 XNOR levels)
-> 32-b compare -> OR4/OR4 -> fault/valid gating -> rx_v / epoch_abort / fault_cause (+ flow copies ot_prs_*), ~22 levels,
~890 ps data at TT in one cycle. CLASS: logic depth (spine clock fine: spread 33.6/32.1, equal insertion at launch/capture).
FIX (RTL ot_hgi_coll_link_e2_seq): the RX CRC is computed one edge earlier from the pin stage (p_rx_flit = rx_pin_flit_pin,
the value rf captures) and its 32 per-bit mismatches are registered beside rf (rx_crc_mm); crc_bad = rv&&ev&&|rx_crc_mm,
bit- and edge-identical to the old crc(rf)!=rf[611:580]. Stage A (pin flop -> CRC tree -> XOR -> rx_crc_mm) ~11 levels;
stage B (rx_crc_mm -> OR32 -> fault/valid) ~8 levels. Route hold margin 0.03 (as e2t; 0.05 gave spread 84.4/91.8 in round 1).
Geometry/spine = e2t geometry 302.4 x 345.6 (S band / E channel 86.4), unchanged.

## SAFE-design checklist (owner 10-19)
1 Pins: PASS - every input at a pin flop, every output a flop Q (pin_regs opt-out reason in spec); reset_landing 2 stages, 16 copies.
2 Reach: PASS - tile faces <= 475 um, pin flops at the faces; no single-cycle wire > 405 um.
3 Fanout: PASS - rx_pin_flit_pin bits now drive rf + ~16 CRC XOR inputs (< 32); census verdict = this gate (native_census).
4 Depth: FIXED - RX CRC check split across the existing pin->rf edge (was ~22 levels / ~890 ps in one stage).
5 Storage: PASS - 2 x 282-b retry banks in 64x512 SRAM macros.
6 Floorplan: PASS - unchanged from e2t (macros on the 43.2 lattice, halo 5.4, full-width std-cell band).
7 Clock: PASS - pre-placed clock spine (e2t gate spread 33.6/32.1 TT/FF); io_hold_margin 0.03, internal hold margin 0.03.
8 Schedule: PASS - 0 added cycles (link miter vs ot_hgi_coll_link_e every output every cycle; parent schedule unchanged).

## Round 2 (HBM-COLLECT10/LINK 10-21 07:20)
Round-1 gate (175cbd68a): CRC cone gone (textbook depth 490 -> 350 ps) but reg->reg -104.6 (+ clock spread 84.4/91.8 FAIL at hold margin 0.05, GRT 0) at rx_v:
write_sequence -> 16-b compare (XNOR/AND4/AND5/AND4) -> seq_bad -> abort_in -> full_fault -> rx_v, ~9 levels + ~300 ps
of wire buffers (W-face sequence inputs -> E-face rx_v). CLASS: depth + reach. FIX: seq_bad / epoch_bad RETIMED across
the pin stage in ot_hgi_coll_link_e2 (computed from the ports and the counters' / epoch registers' next state, registered
with reset 0) -> abort_in is two flops OR'd; rx_v cone now = flops -> ~5 levels. Edge/bit-identical, 0 added cycles:
link miter EQ PASS compared=59994 (16,873 TX / 16,637 RX / 54 aborted epochs, 52 injected faults), mutant m_data REJECTED.
Checklist item 1 note: the sequence/epoch checks now sit between the W-face ports and their capture flops (~5 levels from
an input port; in->reg slack was +248 ps); every port is still captured at a flop before any output.
