`timescale 1ns/1ps
`default_nettype none
// Existing FP8 quantizer's original codes/exponent, aligned with its BF16 y.
module ot_hgi_att_fp8_provenance #(parameter integer ENABLE=0)(
 input wire clk,rst_n,v,input wire[1023:0] x,
 output wire vo,output wire[511:0] y,output wire fault,
 output wire[264:0] packed_word
);
 wire[255:0] q;wire signed[9:0] e;wire qfault;
 ot_hdc_actquant u_q(.clk(clk),.rst_n(rst_n),.v(v),.fp4(1'b0),.x(x),
  .vo(vo),.q(q),.e(e),.y(y),.fault(qfault));
 wire[7:0] ue8m0=8'(e+10'sd127);
 assign packed_word=ENABLE ? {1'b0,ue8m0,q} : 265'd0;
 assign fault=qfault || (ENABLE && vo && (e < -10'sd127 || e > 10'sd127));
endmodule
`default_nettype wire
