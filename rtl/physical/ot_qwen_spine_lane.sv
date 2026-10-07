`timescale 1ns/1ps
// Full-shape spatial lane. Six-band serialization is deliberately not implicit.
// Opt-in physical candidate: current token RTL and its latency remain unchanged.
module ot_qwen_spine_lane #(
    parameter integer TREE_LAT = 7
) (
    input wire clk,
    input wire rst_n,
    input wire [1535:0] t_in,
    input wire [13:0] sel_e,
    input wire [13:0] tv_e,
    output wire [1535:0] y,
    output wire fault
);
    ot_qwen_me_sptree_w12 #(.GT(6144),.SMIN(7),.TCUT(7),
        .TREE_LAT(TREE_LAT),.TINREG(1)) u_lane (
        .clk(clk),.rst_n(rst_n),.t_in(t_in),.sel_e(sel_e),.tv_e(tv_e),.y(y),.fault(fault));
endmodule
