`timescale 1ns/1ps
// Fixed nativeK6144VRD64 pin-location variants; identical logic and epochs.
module ot_s81_pq_ix_left_native (

    input  wire            clk,
    input  wire            rst_n,
    input  wire            consume,
    input  wire [1023:0]   xw,               // x_q words 32 g[0] .. 32 g[0] + 31
    input  wire            ba_wv,            // stage A write enable of this tile's block parity (controller register)
    input  wire [7:0]  ba_blk,
    input  wire [35:0]     h_hi,             // the streamer head's row indices (registers)
    input  wire [6:0]      hw7,              // the head word bits [7:1]
    output wire           fault,
    output wire [255:0]    bt_d              // lane (ku, kl - 4g) at [64 ku + 16 (kl - 4g) +: 16]
);
 ot_s81_pq_ix_sram #(.KMAX(6144),.VRD(64),.WBW(8)) u_native (
 .clk(clk), .rst_n(rst_n), .consume(consume), .xw(xw), .ba_wv(ba_wv), .ba_blk(ba_blk), .h_hi(h_hi), .hw7(hw7), .fault(fault), .bt_d(bt_d));
endmodule

module ot_s81_pq_ix_right_native (

    input  wire            clk,
    input  wire            rst_n,
    input  wire            consume,
    input  wire [1023:0]   xw,               // x_q words 32 g[0] .. 32 g[0] + 31
    input  wire            ba_wv,            // stage A write enable of this tile's block parity (controller register)
    input  wire [7:0]  ba_blk,
    input  wire [35:0]     h_hi,             // the streamer head's row indices (registers)
    input  wire [6:0]      hw7,              // the head word bits [7:1]
    output wire           fault,
    output wire [255:0]    bt_d              // lane (ku, kl - 4g) at [64 ku + 16 (kl - 4g) +: 16]
);
 ot_s81_pq_ix_sram #(.KMAX(6144),.VRD(64),.WBW(8)) u_native (
 .clk(clk), .rst_n(rst_n), .consume(consume), .xw(xw), .ba_wv(ba_wv), .ba_blk(ba_blk), .h_hi(h_hi), .hw7(hw7), .fault(fault), .bt_d(bt_d));
endmodule
