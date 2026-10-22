`timescale 1ns/1ps
`default_nettype none
// Private production LP controls. Same functional capture edges as the original.
(* keep_hierarchy="yes" *)
module ot_coll_lp_pub_mode_decode #(parameter integer ID=0)(
 input wire rst_n,bf,output wire hi,lo);
 assign hi=bf&&rst_n;
 assign lo=!bf||!rst_n;
endmodule
(* keep_hierarchy="yes" *)
module ot_coll_lp_pub_mode_ff #(parameter integer ID=0)(
 input wire clk,rst_n,hi_d,lo_d,output reg hi,lo);
 always @(posedge clk or negedge rst_n)if(!rst_n)begin hi<=0;lo<=1;end
 else begin hi<=hi_d;lo<=lo_d;end
endmodule
// Existing child delay N, with sixteen retained copies of its final edge.
// The canonical source-pinned copy splitter proves identity before distributing
// registered loads; N=0 remains an exact wire with no manufactured reset edge.
module ot_coll_lp_reset_pad #(parameter integer N=1,COPIES=16)(
 input wire ck,d,output wire q);
 generate if(N==0)begin:g_wire assign q=d;end
 else begin:g_pad
  wire pre;
  ot_pl_pad #(.W(1),.N(N-1))u_pre(.ck(ck),.d(d),.q(pre));
  (* keep="true",dont_touch="true",ot_rst_split=1 *)reg[COPIES-1:0]reset_copies;
  always @(posedge ck)reset_copies<={COPIES{pre}};
  assign q=reset_copies[0];
 end endgenerate
endmodule
`default_nettype wire
