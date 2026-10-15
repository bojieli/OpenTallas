`timescale 1ns/1ps
`default_nettype none
// Two fixed alternating source payload banks. No ready, credit or arbitration.
// The clock/launch contract must guarantee that every toggle is sampled and
// each payload remains stable across its declared capture window. This RTL
// alone does not establish bounded physical3:4 phase or metastability margins.
module ot_s81_fixed_mailbox #(parameter integer W=52)(
 input wire s_clk,s_rst_n,s_v,input wire[W-1:0]s_d,
 input wire d_clk,d_rst_n,output reg d_v,output reg[W-1:0]d_d
);
 reg seq;reg[W-1:0]box[0:1];
 reg q1,q2,seen;reg[W-1:0]b1[0:1],b2[0:1];
 always @(posedge s_clk or negedge s_rst_n)begin
  if(!s_rst_n)begin seq<=0;box[0]<=0;box[1]<=0;end
  else if(s_v)begin seq<=~seq;box[~seq]<=s_d;end
 end
 always @(posedge d_clk or negedge d_rst_n)begin
  if(!d_rst_n)begin q1<=0;q2<=0;seen<=0;d_v<=0;d_d<=0;b1[0]<=0;b1[1]<=0;b2[0]<=0;b2[1]<=0;end
  else begin
   q1<=seq;q2<=q1;b1[0]<=box[0];b1[1]<=box[1];b2[0]<=b1[0];b2[1]<=b1[1];
   d_v<=q2!=seen;
   if(q2!=seen)begin d_d<=b2[q2];seen<=q2;end
  end
 end
endmodule
`default_nettype wire
