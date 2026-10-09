`timescale 1ns/1ps
// Two-hop vehicle for the exact bench only (west station s0, east station s1, inter-station wire = die level).
module ot_qwen_link_fwd_cx_pair #(parameter integer LW=528, CW=16)(
    input wire rst_n, clk_ab, clk_ba,
    input wire [LW-1:0] a_i, b_i,
    output wire [LW-1:0] a_o, b_o,
    output wire clk_ab_o, clk_ba_o
);
    wire ab_mid, ba_mid;
    wire [LW-1:0] ab_data, ba_data;
    ot_qwen_link_fwd_cx_station #(.LW(LW),.CW(CW)) s0(
        .rst_n(rst_n),.fclk_ab_i(clk_ab),.fclk_ab_o(ab_mid),.fclk_ba_i(ba_mid),.fclk_ba_o(clk_ba_o),
        .ab_i(a_i),.ab_o(ab_data),.ba_i(ba_data),.ba_o(a_o));
    ot_qwen_link_fwd_cx_station #(.LW(LW),.CW(CW)) s1(
        .rst_n(rst_n),.fclk_ab_i(ab_mid),.fclk_ab_o(clk_ab_o),.fclk_ba_i(clk_ba),.fclk_ba_o(ba_mid),
        .ab_i(ab_data),.ab_o(b_o),.ba_i(b_i),.ba_o(ba_data));
endmodule
