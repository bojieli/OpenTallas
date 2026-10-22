# s81hd_tile_f (S81-HEAD HD-TILE 10-21)

S81-HEAD HD-TILE 10-21 FALLBACK: new tile ot_s81hd_tile (SPEC v1 4e30e8f3a section 1: LM-head array tile, 253 a die) = census-safe bundle copy ot_s81hd_bundle (5 elements, 10 ROM4096, 128 rows; IOREG 1, SAFE 1) on bus B (565 b) with the chain-best merge.  Outline 734.4 x 734.4: each element's ROM pair is one abutted N-S stack (ROM pins sit on the W / E faces, lowest 14 um, M4; stack pin ends face the band): N stacks A0 / B / A1 at x 86.4 / 302.4 / 518.4 (y 563.76), S stacks A2 / A3 at x 172.8 / 432 (y 43.2); one full-width std-cell band y 169.1..563.76 plus the column channels; i on W, o on E, straps / ck / rst_n on W.

SAFE checklist (owner 10-19 / safe_1021, 8 points) -- ot_s81hd_tile:
1 pins: PASS -- every input lands in a W-face flop (x_q / go_q / xv_q / 3 kept rv_q copies / row_q / bits_q / flt_q,
  straps row0_q / ten_q), every output leaves an E-face flop (xo_q / goo_q / xvo_q, o_rv / o_row / o_bits / o_flt); no
  combinational in -> out.  Reset lands in 2 registered stages at the face (kit reset_landing, balanced first_copies /
  copies + reset_relay_split max 32).  Faces: W 568 pins on 694.4 um (0.82/um), E 565 (0.81/um).
2 reach: PASS -- the x stream is registered at both faces (2 stages a tile; tile pitch 734.4 um, so no single-cycle wire
  crosses the tile); chain best: W pin regs -> holds -> select (kept copies) -> E output regs.  Bundle internal: BST 2
  broadcast stages + skew lines + element IOREG / transport registers (unchanged from the bundle).
3 fanout: PASS (pre-gate native census, see "census" below) -- census-safe bundle copy ot_s81hd_bundle /
  ot_s81hd_elem (RP 10 capture copies, kept go / FIFO pointer / SAFE apply copies, enable-free j / k registers); tile
  rv / select copies kept (3 each); reset by kit copies (<= 32 loads a copy).
4 depth: PASS -- unchanged arithmetic (ot_v41_fadd CUT 0x17b, ot_dsrom_bmul3), SAFE = 1 registered argmax apply,
  tile compare = one 32-bit key compare + 17-bit row compare into a registered select (fits 833 ps at TT).
5 storage: WAIVED with reason -- the 10 ROM macros hold the weights; the only bulk flops are the bundle's fixed
  systolic skew lines (16 lanes x 2 streams x SK*(j mod 8) <= 56 deep x 16 b = 14.3 kb total, <= 896 b a lane): fixed
  delay shift registers, never runtime-indexed storage; turning them into ring-buffer SRAMs needs a bundle redesign
  (or skewing x once at ot_s81hd_ctl and carrying the skewed stream on bus B, an HD-CTL option recorded in the lane).
6 floorplan: PASS -- macro columns on the 43.2 lattice (x N 86.4 / 302.4 / 518.4, S 172.8 / 432; N stacks y 563.76, S stacks y 43.2; the MX upper
  ROM of each abutted stack at +62.976 at_exact), element pin ends toward the band, >= 47.5-um column channels for the
  M4 side pins (~9 pins/um over 14 um of ROM side, escaping into the channel), one full-width std-cell band y 169.1..563.76,
  outline 734.4 x 734.4 (aspect 1.00); macro-bound, std-cell utilisation reported by the gate (fill_reason).
7 clock: one region (the tile is one region of its row-pair chain clock region, SPEC 6), one TritonCTS tree, r6g
  sink recipe; pin-flop spread <= 80 ps TT+FF measured by the gate; io_hold_margin 0.03.
8 schedule: static, valid-only pipeline (no credits / backpressure).  Added cycles vs SPEC v1: +1 a tile on the x
  stream (2-stage forward) and IOREG / SAFE +2 in the bundle (go -> result 8,359); fire = 2 edges after both bests;
  measured mini array (spo -> 2 tiles -> spr) go -> result 8375 cycles; handed to the calendar via lanes/S81-HEAD.md.

census: pending (pre-gate native census run with the first gate).
