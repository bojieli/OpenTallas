# s81dvbk_sq_hk2 -- TOPK selector quarter, hard-child hierarchy on the literal 43.2 lattice (S81-TOPK9 2026-10-20)

Successor of hk1/hk1l (8dec8d8d5) after the ROOT/Codex manual review FAIL (07:48): 13/32 SRAM origins off the literal
43.2 lattice, >76% of std cells outside the modelled band, and the clock cause (07:58): the cluster kind's whole-port
clock_spine wrapper balanced the 16 K16 BUF roots and, with OT_SPINE_CTS_REST0, never built trees under them (hold
-656 / -464 ps at CTS). Same RTL and edges as hk1; 16 hist32 banks bind the CLOSED view
physical/ref_tile/s81dvbk_hist32_b0r3/views/ot_s81ph_native_sel_hist_bank (CLOSED 8cadc26d5).

## Structural changes vs hk1
- Outline 648 x 648 (Codex literal32 model 1aa8f6744). Hist banks at the model origins. The model's 5.9 um (line) and
  3.2 um (OFQ) non-pin gaps fail ref_tile's macro channel rule, so the SRAM stacks are re-pitched: line words w0/w1 at
  y 43.2 / 172.8 and w2 at y 388.8 (columns x 388.8 bank0 / 518.4 bank1); OFQ0..3 at y 216, OFQ4 (388.8, 518.4);
  FQ0..3 at y 388.8, FQ4 (475.2, 518.4). Every macro-macro gap >= 20 um; all 32 origins literal 43.2 multiples, R0.
- Full-width 64.8 um std band y 302.4..367.2 (no macro in it); POST_IO macro_channel_block (20 um rule) blocks any
  sub-20 um macro sliver, so no std islands between macros.
- Clock: spec "clock": "cts" -- NO spine. clock_split_km K16 regional BUFx24 roots, TritonCTS builds every regional
  tree under a balanced top tree; hard-child insertion is taken from the CLOSED view Liberty (max_clock_tree_path
  121 / 128 ps TT) by TritonCTS's default insertion-delay handling.
- Pins (N): t_s 43.2-302.4 (865 b, 3.3/um), ck, rst, f_c 308.9-345.6, f_cr, lane 388.8-626.4 (515 b, 2.2/um);
  W: t_o full height (as hk1).

## Safe-design checklist (owner 10-19)
1. Pins: PASS (unchanged hk1: QIO cq0/cq, sq/sq1, oq/oq1 pin flops, u_in s0; reset 2-stage landing, 160 copies).
2. Reach: corner-to-band-anchor bound <= 372.6 um for lines / OFQ / FQ (scratch s81-topk9 model check), hist banks
   <= 392.7 um (Codex native-pin anchors); the gate measures placed hops.
3. Fanout: PRE-GATE NATIVE CENSUS = hk1 mapped census on the identical RTL + defines (TOPK8: max 32, 0 viol,
   93.8k / 94.1k roots, 0 roles); geometry does not change the mapped netlist. The gate repeats it.
4. Depth: unchanged (hk1).
5. Storage: PASS (16 SRAM macros).
6. Floorplan: FIXED -- all 32 on the literal 43.2 lattice, >= 20 um gaps, full-width band, aspect 1.0.
   Fill 33.6% total (pin/lattice-limited; band fill 44.8% by the model) -- waived for the outline, measured at gate.
7. Clock: FIXED -- regional TritonCTS roots (no whole-port spine ownership), hard-child insertion from Liberty;
   io_hold_margin 0.03; the gate must show pin-flop spread <= 80 ps TT+FF.
8. Schedule: PASS, 0 added edges.
SLOT CHANGE: quarter 324x540 -> 648x648 (needs coordinator/die admission before binding).
