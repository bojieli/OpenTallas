`timescale 1ns/1ps
// Dedicated bench-only provider. Unlike the historical native provider this
// implements every actual macro write mask bit. Historical provider is untouched.
module ot_sram_1r1w_128x256_m1_r2c2(input wire clk,r_ce_in,input wire[6:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[6:0]w_addr_in,input wire[255:0]wd_in,w_mask_in,
 input wire[1:0]rr_en,input wire[11:0]rr_addr,input wire[1:0]cr_en,input wire[15:0]cr_sel);
 reg[255:0]mem[0:127];integer j;
 always @(posedge clk)begin
  if(r_ce_in)rd_out<=mem[r_addr_in];
  `ifdef MASKMUT
  if(w_ce_in)mem[w_addr_in]<=wd_in;
`else
  if(w_ce_in)for(j=0;j<256;j=j+1)if(w_mask_in[j])mem[w_addr_in][j]<=wd_in[j];
`endif
 end
endmodule
