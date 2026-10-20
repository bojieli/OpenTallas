`timescale 1ns/1ps
// Qwen clients explicitly bypass a same-address read/write; this assertion is
// a test-only monitor, not a restriction of the native portable SRAM model.
module qwen_native_sram_checker(input wire clk,r_ce_in,w_ce_in,input wire[4:0] r_addr_in,w_addr_in);
 always @(posedge clk)
  if(r_ce_in&&w_ce_in&&r_addr_in==w_addr_in) $fatal(1,"QW_NATIVE_SRAM_COLLISION");
endmodule
bind ot_sram_1r1w_32x64_m1 qwen_native_sram_checker u_qwen_check(
 .clk(clk),.r_ce_in(r_ce_in),.w_ce_in(w_ce_in),.r_addr_in(r_addr_in),.w_addr_in(w_addr_in));
