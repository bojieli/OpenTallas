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
`default_nettype wire
