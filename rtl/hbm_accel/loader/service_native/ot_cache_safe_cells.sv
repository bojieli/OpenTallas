`timescale 1ns/1ps
`default_nettype none
(* keep_hierarchy=1 *) module ot_cache_safe_q #(parameter W=1)(input wire clk,input wire[W-1:0]d,output reg[W-1:0]q);always @(posedge clk)q<=d;endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_rq #(parameter W=1)(input wire clk,rst_n,input wire[W-1:0]d,output reg[W-1:0]q);always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=d;endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_reset_phase(input wire clk,rst_n,output reg q);always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=1;endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_write16(input wire clk,rst_n,input wire[3:0]select_d,input wire[15:0]data0,data1,data2,data3,output reg[15:0]q);
 wire [3:0] sel;
 ot_cache_safe_rq #(.W(4)) u_sel(.clk(clk),.rst_n(rst_n),.d(select_d),.q(sel));
 wire [15:0] incoming=({16{sel[0]}}&data0)|({16{sel[1]}}&data1)|({16{sel[2]}}&data2)|({16{sel[3]}}&data3);
 always @(posedge clk)if(|sel)q<=incoming;
endmodule
`default_nettype wire
