// Simulation only. Exact original provider SRAM model; not a hardened macro.
// Actual RF service drives full write mask and disables redundancy ports.
`timescale 1ns/1ps
module ot_sram_1r1w_128x256_m1_r2c2(input wire clk,r_ce_in,input wire[6:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[6:0]w_addr_in,input wire[255:0]wd_in,w_mask_in,
 input wire[1:0]rr_en,input wire[11:0]rr_addr,input wire[1:0]cr_en,input wire[15:0]cr_sel);
 reg[255:0]mem[0:127];
 always @(posedge clk)begin if(r_ce_in)rd_out<=mem[r_addr_in];if(w_ce_in)mem[w_addr_in]<=wd_in;end
endmodule
