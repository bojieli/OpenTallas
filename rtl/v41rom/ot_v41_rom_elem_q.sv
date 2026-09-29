`timescale 1ns/1ps
// ot_v41_rom_elem_q: the FP8/FP4 element (or W1 macro pair, NB = 2) as hardened: ot_v41_rom_elem with BF16 = 0
// and without the BF16 x port, which an FP8/FP4 macro never receives (W10, tools/v41_w10_elem_pnr.py).
module ot_v41_rom_elem_q #(
    parameter integer NB = 1,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire         busy,
    output wire         fault
);
    ot_v41_rom_elem #(.BF16(0), .NB(NB), .INSTANCE(INSTANCE)) u_e (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_bf(1'b0),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1),
        .xs_e1(xs_e1), .xb_v(1'b0), .xb_b(3'd0), .xb_sv(4'd0), .xb_u(32'd0), .xb_d(1024'd0),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .busy(busy), .fault(fault));
endmodule
