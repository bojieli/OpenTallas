`timescale 1ns/1ps
// Existing fixed-latency D4/K2 landing transport. Exactly +3 destination edges.
// Resets affect epochs/valid only; data bank is the existing reset-free body.
module ot_s81_mu72_land #(parameter integer W=1)(
    input wire ck_w, ck_r, rs_w, rs_r,
    input wire [W-1:0] i, output wire [W-1:0] o
);
    localparam integer N=(W+7)/8;
    wire [N-1:0] rw, rr;
    wire [4*W-1:0] bank;
    wire [11:0] epo;
    wire [4*N-1:0] vld;
    ot_pl_land_reset_forest #(.DEPTH(3),.LEAVES(N),.ROOT_LOADS(2)) u_rw(
        .ck(ck_w),.d(rs_w),.q(rw));
    ot_pl_land_reset_forest #(.DEPTH(3),.LEAVES(N),.ROOT_LOADS(2)) u_rr(
        .ck(ck_r),.d(rs_r),.q(rr));
    ot_pl_land_vector_reset_kw_w #(.W(W),.D(4),.CHUNK_BITS(8)) u_w(
        .ck(ck_w),.rsi(rw),.i(i),.bank(bank),.epo(epo),.vld(vld));
    ot_pl_land_vector_reset_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(8)) u_r(
        .ck(ck_r),.rsi(rr),.bank(bank),.epo(epo),.vld(vld),.o(o));
endmodule
