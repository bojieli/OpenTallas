// External escape coupon only. Both native clocks are intentionally exercised
// by one synchronous clock here; production dual-clock CDC remains client-owned.
module ot_sram_escape64_1019(input wire clk,rst_n,r_ce_in,w_ce_in,
  input wire [4:0] r_addr_in,w_addr_in,
  input wire [63:0] wd_in,w_mask_in,
  output wire [63:0] rd_out);
  ot_sram_1r1w2c_32x64_m1 u_mem(.rclk(clk),.wclk(clk),
    .r_ce_in(r_ce_in),.w_ce_in(w_ce_in),.r_addr_in(r_addr_in),.w_addr_in(w_addr_in),
    .wd_in(wd_in),.w_mask_in(w_mask_in),.rd_out(rd_out));
endmodule
