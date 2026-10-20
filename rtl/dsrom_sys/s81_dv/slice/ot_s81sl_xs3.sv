`timescale 1ns/1ps
// S81-XG3 (10-19): the x streamer hard leaf (kit s81sl_xs3) = ot_s81sl_xs #(.RD2(2)) under an unparameterised name, so the
// slice parent instantiates the hard child without a #() override (ref_tile rtl rule) and Yosys cannot $paramod-rename it.
module ot_s81sl_xs3 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [2:0]    g_v,
    input  wire [2:0]    g_fam,
    input  wire [20:0]   g_idx,
    input  wire [3071:0] g_d,
    input  wire          is_v,
    input  wire [159:0]  is_d,
    output wire          xw_v,
    output wire [1100:0] xw_d,
    output wire          fault,
    input  wire          fi,
    output wire          fo
);
    ot_s81sl_xs #(.RD2(2)) u_x (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .is_v(is_v),
        .is_d(is_d), .xw_v(xw_v), .xw_d(xw_d), .fault(fault), .fi(fi), .fo(fo));
endmodule
