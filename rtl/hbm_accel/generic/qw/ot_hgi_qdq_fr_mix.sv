`timescale 1ns/1ps
`default_nettype none
// Off by default. Explicit new master composition, preserving the closed general source.
module ot_hgi_qdq_fr_mix #(parameter integer ONE_ROW=0, MUT_ORDER=0, MUT_END=0) (
 input wire clk, rst_n, input wire [682:0] rec,
 output wire s1_v,s3_v,output wire [189:0] s3, output wire nfault
);
 generate if(ONE_ROW==0) begin:g_closed
  ot_hgi_qdq_fr u_general(.*);
 end else begin:g_mix
  wire gv,gs1,gfault,fv,fs1,one,one_s1,ffault,overflow;
  wire [189:0] gs3;
  wire [332:0] fs2;
  ot_hgi_qdq_fr u_general(.clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(gs1),.s3_v(gv),.s3(gs3),.nfault(gfault));
  ot_hgi_qdq_fr_one_s2 u_one(.clk(clk),.rst_n(rst_n),.rec(rec),.s1_v(fs1),.s2_v(fv),.one(one),.one_s1(one_s1),.s2(fs2),.nfault(ffault));
`ifdef OT_HARD_CHILDREN
  ot_hgi_qdq_fr_retire u_retire(
`else
  ot_hgi_qdq_fr_retire #(.MUT_ORDER(MUT_ORDER),.MUT_END(MUT_END)) u_retire(
`endif
   .clk(clk),.rst_n(rst_n),.accept(fs1),.accept_one(one_s1),.fast_v(fv),.fast_one(one),.fast_s2(fs2),
   .general_v(gv),.general_s3(gs3),.s3_v(s3_v),.s3(s3),.overflow(overflow));
  assign s1_v=fs1;
  assign nfault=gfault|ffault|overflow;
 end endgenerate
endmodule
`default_nettype wire
