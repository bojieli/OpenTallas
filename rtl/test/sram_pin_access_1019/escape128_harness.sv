// QW-SRAM3 10-19: external native-pin escape coupon for the CTL128x64 dual-clock family
// (ot_sram_1r1w2c_128x64_m1, W/E 105 pins over 27.576 um = 3.81/um). Both native clocks are
// driven by one synchronous clock here; production dual-clock CDC/collision stays client-owned.
module ot_sram_escape128x64_1019(input wire clk,rst_n,r_ce_in,w_ce_in,
  input wire [6:0] r_addr_in,w_addr_in,
  input wire [63:0] wd_in,w_mask_in,
  output wire [63:0] rd_out);
  ot_sram_1r1w2c_128x64_m1 u_mem(.rclk(clk),.wclk(clk),
    .r_ce_in(r_ce_in),.w_ce_in(w_ce_in),.r_addr_in(r_addr_in),.w_addr_in(w_addr_in),
    .wd_in(wd_in),.w_mask_in(w_mask_in),.rd_out(rd_out));
endmodule
