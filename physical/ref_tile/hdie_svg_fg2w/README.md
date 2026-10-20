# hdie_svg_fg2w -- HBM d4g SM service group (ot_hbm_svc_sm_group_id #(LBANKS 4, FIXED_GO 1)), SRAM-FIFO successor of hdie_svg_fg1

Lane LEAD2-HBM/L2H-IDXSCORE/SVG, 2026-10-19, branch claude/l2h-svg-fg2-1019. Outline 691.2 x 648.0 um (variant pair:
hdie_svg_fg2 648.0 x 604.8 sized toward 40 % fill from the fg1 synthesis area, hdie_svg_fg2w = the fg1 outline 691.2 x 648.0;
gated in parallel, the first clean one is bound).  fg1 (gate PID 3225945, pinned ot-epyc5) is kept running.

Change vs fg1: the 8 landing response FIFOs (285 b x 8 = 2,280 b each, 18,240 flop bits) and the descriptor FIFO
(97 b x 4) are dual-clock 1R1W SRAM macros (ot_hbm_svc_async_fifo_sram: ot_sram_1r1w2c_8x285_m1 x8, ot_sram_1r1w2c_4x97_m1 x1,
tools/mem_compiler sram_gen.py); only Gray pointers, online flags, the fetch pointer and a 2-entry read buffer are flops.
Each reset input lands in its own family (u_srst_land / u_hrst_land, ot_reset_sync 2 stages).  CDC admission:
tools/ref_tile/gray_fifo_cdc_constraints.py storage_macro profile (write pins in the writer family, read pins / rd_out in
the reader family, rd_out consumers gated by the publish predicate f_gray != wr_gray_r2, exact SAT miter); fleet lint
receipt lint_receipt.json PASS.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: WAIVED as fg1 (pin_regs off: a kit pin stage cannot span the two clock families; K ports keep their RTL
  2-entry pin skids, outputs are RTL registers).  Reset: FIXED -- each reset lands at the face in 2 registered stages in
  its own family (RTL), port -> 2 reset pins (textbook reset_landing <= 2); kit reset_landing opt-out records it.
2 Reach: gate measures (outline 691.2 x 648.0, macro rows; relays not needed below 405 um single-cycle spans per gate wire lint).
3 Fanout: unchanged control from fg1; the FIFO read select of 8 x 285 flop rows (8:1 mux per bit) is gone; gate lint decides.
4 Depth: no macro output reaches a macro input in one cycle (SRAM address from flops + consume bit; rd_out -> buffer flop only).
5 Storage: FIXED -- every runtime-indexed store > ~2 kb is an SRAM macro (8 response FIFOs + descriptor FIFO now; 15 landing /
  cache / programme SRAMs as fg1).  Remaining flop buffers: 2 x 285 b per response FIFO (not runtime indexed, 1-of-2 select).
6 Floorplan: 24 macros placed by ref_tile gen on the track lattice with >= 20 um channels; macro pin faces 4.5 / 3.8 pins/um
  (8x285 433 pins on 97 um, 4x97 150 on 39 um) < 6; util from the gate synthesis (target 40-60 %).  NOTE: macro origins are on
  the ref_tile track-alignment lattice (as fg1), not checked against the 43.2 um macro lattice -- coordinator review.
7 Clock: multiple_cts_roots per family (stream 833.333 / hbm 1024), regional roots as fg1; gate measures TT/FF pin-flop
  spread (<= 80); hold margin 0.03.
8 Schedule: the HBM response / descriptor crossings are elastic (HBM boundary, owner 10-14); added latency: +1 stream edge
  publish -> packet_v per response word (landing -> resident), +1 hbm edge descriptor -> issue, reset release +2 per family.
  The bench (run_sm_group_id_fg2.sh) proves the 8-group go-slot report line-for-line IDENTICAL to the parameterised flop-FIFO
  master at GOGAP 100 (go slots unchanged: done_ps identical), so no compiler slot moves.

## Benches (Verilator 5.050, fleet)
results/rtl/hbm_svc_sm_group_id_fg2_1019/: positive SVG_FG2_GATE PASS (REPORT_IDENTICAL), mutants msm1/msm4/mst/skew/earlygo
(fg1 set) + fwaddr (macro write one slot ahead) + fpub (capture on the unsynchronised write pointer) must FAIL.
