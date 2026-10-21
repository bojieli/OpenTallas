`timescale 1ns/1ps
`default_nettype none
// QW-CB16REG 10-20 (main line a): HARDENED landing ring = one CB16 region crossing as ONE closed tile.
// The flat CB16 parent (qfd_c_b16_fullm / fulln) placed each crossing as two soft halves -- the writer ring
// qfd_c_land_w1k on the SOURCE region root (56 x 56 um bay) and the reader qfd_c_land_r1k on the DESTINATION root
// (43 x 43 um bay, ~280 um away) -- so each region root fanned out to 6.7k-20.9k ring flops spread over 1-2 mm and the
// gates measured within-region TT spread 410-813 ps and WNS -1.4..-1.7 ns at the reader (fulln/fullnb/fullm 10-20).
// Here the writer + reader of one crossing are hardened together once per width (69 instances in the parent, two
// masters W=514 / W=516): each tile clock (ck_w = source region, ck_r = destination region) gets its own small tree
// inside an 86.4-um tile, the 4 x W bank -> reader path never leaves the tile, and the parent clock of a region only
// sees ONE clock pin per ring tile instead of ~2.7k flops.
// Function, ports semantics, epochs and latency are EXACTLY qfd_c_land_w1k + qfd_c_land_r1k (D 4, K 2; same instance
// parameters as the parent): o = the value written K edges earlier (static schedule; no ready / credit / backpressure).
// Pins: i lands directly in the 4 bank slots (each slot a register, enable = registered one-hot), o is the reader's
// output register, rsi_w / rsi_r land in the halves' kept reset copies (1 + NGS loads each) -- every pin registered,
// no combinational in->out path.
module qfd_c_ring_t #(
    parameter integer W = 516,
    parameter integer D = 4,
    parameter integer K = 2
) (
    input  wire         ck_w,
    input  wire         rsi_w,
    input  wire [W-1:0] i,
    input  wire         ck_r,
    input  wire         rsi_r,
    output wire [W-1:0] o
);
    localparam integer AW  = (D <= 2) ? 1 : $clog2(D);
    localparam integer NGS = (W + 30 - 1) / 30;
    wire [D*W-1:0]      bank;
    wire [D*(AW+1)-1:0] epo;
    wire [D*NGS-1:0]    vld;
    qfd_c_land_w1k #(.W(W), .D(D)) u_w (.ck(ck_w), .rsi(rsi_w), .i(i), .bank(bank), .epo(epo), .vld(vld));
    qfd_c_land_r1k #(.W(W), .D(D), .K(K)) u_r (.ck(ck_r), .rsi(rsi_r), .bank(bank), .epo(epo), .vld(vld), .o(o));
endmodule

// fixed-width tops (one closed master each; the parent instantiates these)
module qfd_c_ring516 (input wire ck_w, rsi_w, input wire [515:0] i, input wire ck_r, rsi_r, output wire [515:0] o);
    qfd_c_ring_t #(.W(516), .D(4), .K(2)) u_ring (.ck_w(ck_w), .rsi_w(rsi_w), .i(i), .ck_r(ck_r), .rsi_r(rsi_r), .o(o));
endmodule
module qfd_c_ring514 (input wire ck_w, rsi_w, input wire [513:0] i, input wire ck_r, rsi_r, output wire [513:0] o);
    qfd_c_ring_t #(.W(514), .D(4), .K(2)) u_ring (.ck_w(ck_w), .rsi_w(rsi_w), .i(i), .ck_r(ck_r), .rsi_r(rsi_r), .o(o));
endmodule
`default_nettype wire
