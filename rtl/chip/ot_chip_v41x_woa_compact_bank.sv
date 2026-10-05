`timescale 1ns/1ps
// Experimental finite compact ME weight source. Eight independent 80-bit
// synchronous ROM banks:8 E4M3codes+2 UE8M0scales per bank address.
// External ROM latency1 + registered decoder1 = existing ME RL2.
module ot_chip_v41x_woa_compact_bank #(parameter integer AW=18)(
 input wire clk,rst_n,
 input wire [7:0] wb_re,input wire[8*AW-1:0]wb_addr,
 output wire[7:0]rom_re,output wire[8*AW-1:0]rom_addr,
 input wire[8*80-1:0]rom_q,
 output wire[8*8*32-1:0]wb_q,output wire fault
);
 assign rom_re=wb_re;assign rom_addr=wb_addr;
 reg[7:0]qv;
 always @(posedge clk)if(!rst_n)qv<=0;else qv<=wb_re;
 wire[63:0]fail;
 genvar c,u;
 generate for(c=0;c<8;c=c+1)begin:bank
 for(u=0;u<8;u=u+1)begin:lane
 wire[15:0]v;wire ov;
 ot_chip_v41x_woa_fp8_decode d(.clk(clk),.rst_n(rst_n),.in_v(qv[c]),
 .code(rom_q[c*80+u*8+:8]),.scale(rom_q[c*80+64+(u/4)*8+:8]),
 .out_v(ov),.fault(fail[u*8+c]),.value(v));
 assign wb_q[(8*u+c)*32+:32]={v,16'b0};
 end end endgenerate
 assign fault=|fail;
endmodule
