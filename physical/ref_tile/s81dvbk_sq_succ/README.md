# s81dvbk_sq_succ -- TOPK selector quarter successor (dsdv_bksel_q, S81-TOPK 2026-10-19)

Rebuild after the legacy INDEXED13 / RST64 gates were stopped on the FQ/OFQ flop-array storage gap (689851d41) and the
SAFE-AUDIT item-6 failure (128x256 SRAM W face 9.98-10.4 pins/um). Opt-in defines: OT_S81PH_SEL_INDEXED13,
OT_S81PH_SEL_RST64, OT_S81PH_FIFO_SRAM, OT_SRAM_P192, OT_S81PH_SEL_SUCC. Default RTL and every existing view unchanged.

Outline 324 x 540 um (aspect 1.67; two quarters 648 um fit the 680 um column). Macros (all on 43.2 lattice origins,
abutted N-S stacks with no N/S pins, abutment pitch = H + 0.024 = a multiple of the 48 nm M4 pitch, offtrack 0):
- line pool 6x ot_sram_1r1w_128x256_m1_r2c2_p192_mir (94.824 x 80.472, W 410 / E 409 = 5.09 / 5.08 pins/um):
  bank 0 x43.2 MY (rd face E), bank 1 x172.8 R0 (rd face W): both rd faces into the centre channel, rows = width slice.
- OFQ 5x ot_sram_1r1w_32x128_m1_p192_rc (51.408 x 39.96, W 199 / E 198 = 4.98 / 4.95 pins/um) x43.2 R0 stacked on bank 0,
  rd face toward t_o (W face). FQ 5x p192_rc x216.0 R0 stacked on bank 1, rd face into the centre gap.
- Full-width std-cell band y 490..538 (above the stacks) + W margin 41, centre channel 34.8 (mir) / 121 (rc), E margin 56.
N pins t_s 2.16-156.6 (5.60/um), ck 156.6-160.92 (centre), rst, f_c, f_cr, lane 180.36-321.84 (3.64/um); t_o W full face.

Safe-design checklist (owner 10-19):
1. Pins: PASS. Source-registered QIO pin flops (lane / f_c / f_cr in, t_s / t_o out) + io_flop_at_pins; reset_landing 2 stages.
2. Reach: PASS by construction (farthest macro-capture -> band ~300 um < 405); confirmed at gate placement.
3. Fanout: FIXED. Bank read mux b2 (592 loads) -> 3 KEPT b1 copies (<=13 pair loads) + 37 KEPT one-hot {oh0,oh1} pairs
   (16 AND-OR loads); FIFO forwarding flags 74/76 KEPT (<=16 loads, c2bfecdcf census); 27 KEPT INDEXED13 format selects.
   Gate synthesis must show the copies distinct (no opt_merge).
4. Depth: PASS. Registered one-hot AND-OR select replaces the b2-driven 2:1 mux; no in->out combinational path; no new arbitration.
5. Storage: FIXED. FQ 8x592 (4.7 kb) and OFQ 4x593 (2.4 kb) flop arrays -> 10 SRAM (registered showahead, exact, 0 cycles).
6. Floorplan: FIXED. p192 macros (<=5.09 pins/um faces), 43.2 lattice, rd faces into channels, halo 5.4 / halo_x 10.8,
   full-width top band. Fill: WAIVED-with-reason ~33% std fill: macro/pin-escape bound (66.3k um2 of 16 macros), gate measures.
7. Clock: PASS provisions. ck N centre over the band; regional quarter root; RST64 = 64 KEPT final-stage reset copies,
   ot_rst_copies <=256 loads each (baseline one reset 9751 loads); io_hold_margin 0.03. TT/FF pin-flop spread <=80 at gate.
8. Schedule: PASS. Static; FIFO SRAM + one-hot select add 0 cycles (exact cycle equivalence, suite below). INDEXED13 1037
   reserved cycles priced: accepted-cost ledger row S81.TOPK_FINAL proposed (AR +0.822 % / MTP +0.939 %).

Benches (Verilator 5.050, results/arch/s81_topk_succ_1019): legacy + indexed13 + ties/ninf/zeros PASS; identity/corrupt/early
and the one-hot stuck-select mutant (OT_S81PH_SEL_SUCC_MUT_OH) FAIL; FIFO component MUT0 PASS, MUT1/2 FAIL on the p192 macro.
Integration GAPs unchanged: TP4 score+index producer -> u_bk_sel.vi_s, IDX -> gather consumer (see s81_topk_final_1019).
