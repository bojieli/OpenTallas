# hidx_link_r4t -- L2H-IDX r4 SAFE successor of the HBM top-k link tile (ot_hbm_idx_topk_link_static_p), 10-19
Predecessor route hidx_link_g4p-r3-e11cba3a3 NEEDS_RTL TT -0.62 / FF -47.62 / DRC 0 (GRT hold repair stopped at 62
buffers by HOLD-STOP; DRT then lost ~34 ps). Classified: 23 wd_r -> SRAM wd_in hold -41.5 (flop -> macro pin, 1 INV),
12 s4_r -> wd_r -41.1, 79 wr -> wd_r -36.4, grp_d -> grp_d setup -0.62 (control tap fanned to 8 SRAMs over 650 um).
Structural change (RTL, no function/latency change; outputs historical +5, calendar --link-pipe 5 unchanged):
- SRAM write port passes a NEGATIVE-EDGE isolation stage (we_n/wa_n/wd_n) beside each macro: the SRAM captures at the
  same rising edge as before, but its inputs change T/2 after the macro edge, so the macro-input hold class has ~T/2
  margin by construction (no hold buffers in the macro pin field).
- Per-bank kept registered read enable / address (re_b/ra_b) loaded from the tap one edge earlier: one local load each.
Clock: TritonCTS single root (parallel clock-construction variant; spread measured at this gate).
Parallel variants (owner PARALLEL rule): hidx_link_r4h (spine) and hidx_link_r4t (CTS), same RTL and geometry; bind the
first to close, cancel the other.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every data input and output is one kept pin flop (die-master shell); rst_n 2-flop sync + reset_landing 2 stages.
2 Reach: PASS -- longest single-cycle runs are the rotator outputs to the W/E bank stacks (~215 um each side) < 405 um.
3 Fanout: PASS with note -- r3 kept copies (4 lane-valid copies, s1_nac/s1_nqc, 16 trep copies, per-bank fill/f0 copies) plus
  new per-bank re_b/ra_b; trep copies drive one rotate stage of 4 slots (144 mux bits) each: measured positive TT slack in r3.
4 Depth: PASS -- r3 gate depth 366.7 ps, no reg->reg path over ~20 levels.
5 Storage: PASS -- 8 SRAM macros 64x512; ring W is fixed-index (slot-masked writes, no runtime-indexed read). Waived: the
  5-deep control delay line is 105 bits of local control (not a data delay line).
6 Floorplan: waived-with-reason -- exact d4g sub-slot 650 x 500 (grants_d4g FACES_ONLY); 8 macros in two 4-high stacks
  with 21.6-um channels cannot sit on the 43.2 lattice in 500 um; fill 38% is macro-dominated and the S/N faces are
  pin-limited (2,424 / 2,219 pins at ~97% face use); aspect 1.3; full-width std-cell band between the stacks.
7 Clock: TritonCTS single root (parallel clock-construction variant; spread measured at this gate); macro-input hold isolated by the negedge stage; io_hold_margin 0.03.
8 Schedule: PASS -- static, no credits/backpressure, no cycle added.
