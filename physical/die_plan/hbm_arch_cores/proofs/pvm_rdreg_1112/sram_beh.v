// formal-only behavioural model of ot_sram_1r1w_64x512_m1_r2c2 (same ports): synchronous 1R1W, full-word write when w_ce_in
// (the pv_merge stack always drives w_mask_in all ones), registered read when r_ce_in. Identical on both miter sides.
module ot_sram_1r1w_64x512_m1_r2c2 (input clk, input r_ce_in, input [5:0] r_addr_in, output reg [511:0] rd_out,
    input w_ce_in, input [5:0] w_addr_in, input [511:0] wd_in, input [511:0] w_mask_in,
    input [1:0] rr_en, input [11:0] rr_addr, input [1:0] cr_en, input [17:0] cr_sel);
  reg [511:0] arr [0:63];
  always @(posedge clk) begin
    if (r_ce_in) rd_out <= arr[r_addr_in];
    if (w_ce_in) arr[w_addr_in] <= (arr[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in);
  end
endmodule
