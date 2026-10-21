# s81hd_tile_m (S81-HEAD HD-TILE 10-21)

S81-HEAD HD-TILE 10-21 MAIN: new tile ot_s81hd_tile (SPEC v1 4e30e8f3a section 1: LM-head array tile, 253 a die) = census-safe bundle copy ot_s81hd_bundle (5 elements, 10 ROM4096, 128 rows; IOREG 1, SAFE 1) on bus B (565 b) with the chain-best merge.  Outline 648.0 x 648.0: each element's ROM pair is one abutted N-S stack (ROM pins sit on the W / E faces, lowest 14 um, M4; stack pin ends face the band): N stacks A0 / B / A1 at x 86.4 / 259.2 / 432 (y 477.36), S stacks A2 / A3 at x 172.8 / 345.6 (y 43.2); one full-width std-cell band y 169.1..477.36 plus the column channels; i on W, o on E, straps / ck / rst_n on W.

SAFE checklist (owner 10-19 / safe_1021, 8 points) -- ot_s81hd_tile:
1 pins: PASS -- every input lands in a W-face flop (x_q / go_q / xv_q / 3 kept rv_q copies / row_q / bits_q / flt_q,
  straps row0_q / ten_q), every output leaves an E-face flop (xo_q / goo_q / xvo_q, o_rv / o_row / o_bits / o_flt); no
  combinational in -> out.  Reset lands in 2 registered stages at the face (kit reset_landing, balanced first_copies /
  copies + reset_relay_split max 32).  Faces: W 568 pins on 608.0 um (0.93/um), E 565 (0.93/um).
2 reach: PASS -- the x stream is registered at both faces (2 stages a tile; tile pitch 648.0 um, so no single-cycle wire
  crosses the tile); chain best: W pin regs -> holds -> select (kept copies) -> E output regs.  Bundle internal: BST 2
  broadcast stages + skew lines + element IOREG / transport registers (unchanged from the bundle).
3 fanout: PASS (pre-gate native census, see "census" below; round 1 on the original element arithmetic: 2,575
  drivers > 32, max 126, in ot_v41_fadd / ot_dsrom_bmul3 selects + element enables) -- census-safe bundle copy
  ot_s81hd_bundle / ot_s81hd_elem NC 1: native-census arithmetic (adders ot_hdc_fp32_add_lat_fan32 LAT 7 SAFE_DIST 1,
  products ot_hdc_fp32_mul_lat_ncr LAT 6), every wide enable / select a kept copy per <= 16 bits (a mapped select
  costs 2 load pins a bit): capture RP 18, tree hold x3, FIFO pointers, SAFE apply x10, go x4, bundle compare tree 11
  copies a level; FP32 keys via ot_s81hd_key; tile rv x5 / select x7 copies; reset by kit copies (<= 32 a copy).
4 depth: PASS -- reviewed native arithmetic (fan32 adder native estimate 288 ps / 9 levels; ncr multiply LAT 6),
  SAFE = 1 registered argmax apply, compares on registered keys into registered selects (fits 833 ps at TT).
5 storage: WAIVED with reason -- the 10 ROM macros hold the weights; the only bulk flops are the bundle's fixed
  systolic skew lines (16 lanes x 2 streams x SK*(j mod 8), SK 7: <= 49 deep x 16 b = 12.5 kb total, <= 784 b a lane): fixed
  delay shift registers, never runtime-indexed storage; turning them into ring-buffer SRAMs needs a bundle redesign
  (or skewing x once at ot_s81hd_ctl and carrying the skewed stream on bus B, an HD-CTL option recorded in the lane).
6 floorplan: PASS -- macro columns on the 43.2 lattice (x N 86.4 / 259.2 / 432, S 172.8 / 345.6; N stacks y 477.36, S stacks y 43.2; the MX upper
  ROM of each abutted stack at +62.976 at_exact), element pin ends toward the band, >= 47.5-um column channels for the
  M4 side pins (~9 pins/um over 14 um of ROM side, escaping into the channel), one full-width std-cell band y 169.1..477.36,
  outline 648.0 x 648.0 (aspect 1.00); macro-bound, std-cell utilisation reported by the gate (fill_reason).
7 clock: one region (the tile is one region of its row-pair chain clock region, SPEC 6), one TritonCTS tree, r6g
  sink recipe; pin-flop spread <= 80 ps TT+FF measured by the gate; io_hold_margin 0.03.
8 schedule: static, valid-only pipeline (no credits / backpressure).  Added cycles vs SPEC v1: +1 a tile on the x
  stream (2-stage forward); bundle IOREG / SAFE / key / census compare tree, with the LAT 7 adders (SK 7: shorter
  chains and ROM read span); fire = 4 edges after both bests (2 key stages, select, output);
  measured mini array (spo -> 2 tiles -> spr) go -> result 8375 cycles; handed to the calendar via lanes/S81-HEAD.md.

census: pending (pre-gate native census run with the first gate).
