`timescale 1ns/1ps
module ot_sram_1r1w_32x546_m1 (
 input wire clk,r_ce_in,w_ce_in,input wire [4:0] r_addr_in,w_addr_in,
 output reg [545:0] rd_out,input wire [545:0] wd_in,w_mask_in
);
 reg [545:0] mem[0:31];
 integer i;
 always @(posedge clk) begin
  if(r_ce_in && w_ce_in && r_addr_in==w_addr_in) $fatal(1,"SAFE_SRAM_COLLISION");
  if(r_ce_in) rd_out<=mem[r_addr_in];
  if(w_ce_in) for(i=0;i<546;i=i+1) if(w_mask_in[i]) mem[w_addr_in][i]<=wd_in[i];
 end
endmodule

module ot_sram_1r1w_32x64_m1 (
 input wire clk,r_ce_in,w_ce_in,input wire[4:0] r_addr_in,w_addr_in,
 output reg[63:0] rd_out,input wire[63:0] wd_in,w_mask_in
);
 reg[63:0] mem[0:31];integer i;
 always @(posedge clk) begin
  if(r_ce_in&&w_ce_in&&r_addr_in==w_addr_in) $fatal(1,"SAFE_SRAM64_COLLISION");
  if(r_ce_in) rd_out<=mem[r_addr_in];
  if(w_ce_in) for(i=0;i<64;i=i+1) if(w_mask_in[i]) mem[w_addr_in][i]<=wd_in[i];
 end
endmodule
