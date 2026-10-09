`timescale 1ns/1ps
// HGI-1 plain accept endpoint. Legacy DS width remains default; routes enable18.
module ot_hgi_mtp_accept18 #(
    parameter integer GENERIC18 = 0,
    parameter integer TW = GENERIC18 ? 18 : 17
)(
    input wire clk, rst_n, start_v, tokx_v, amax_v, acc_v,
    input wire [TW-1:0] start_tok, tokx_tok, amax_tok,
    input wire [2:0] tokx_slot, amax_slot, acc_g,
    output wire [8*TW-1:0] stok, ttok,
    output wire acc_done, acc_any,
    output wire [2:0] acc_a,
    output wire [3:0] n_emit,
    output wire [TW-1:0] bonus
);
    ot_hdc_accept #(.NSLOT(8),.NW(TW)) u_accept (
        .clk(clk),.rst_n(rst_n),.start_v(start_v),.start_tok(start_tok),
        .tokx_v(tokx_v),.tokx_slot(tokx_slot),.tokx_tok(tokx_tok),
        .amax_v(amax_v),.amax_slot(amax_slot),.amax_tok(amax_tok),
        .acc_v(acc_v),.acc_g(acc_g),.stok(stok),.ttok(ttok),
        .acc_done(acc_done),.acc_any(acc_any),.acc_a(acc_a),
        .n_emit(n_emit),.bonus(bonus));
endmodule
