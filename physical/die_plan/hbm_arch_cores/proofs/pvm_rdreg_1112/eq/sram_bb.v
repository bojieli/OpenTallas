// equivalence-only: the stack macro as a blackbox (identical in gold and gate); equiv_make proves its inputs equal and
// drives both sides from the gold outputs.
(* blackbox *)
module ot_sram_1r1w_64x512_m1_r2c2 (input clk, input r_ce_in, input [5:0] r_addr_in, output [511:0] rd_out,
    input w_ce_in, input [5:0] w_addr_in, input [511:0] wd_in, input [511:0] w_mask_in,
    input [1:0] rr_en, input [11:0] rr_addr, input [1:0] cr_en, input [17:0] cr_sel);
endmodule
