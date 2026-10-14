`timescale 1ns/1ps
`default_nettype none
// FUSED.QDQ_* wide engine (WQ2, serial records), WIRES-ONLY parent (el1013-hbm-quant-split, 2026-10-13).
// The flat cluster had 31.9k flops + 20 macro clock pins on one root (clock rule: <= 15k sinks per root).
// Now: 1 x ot_hgi_qw_hh (head: control, gather tail, decoder, result SRAM) + 4 x ot_hgi_qw_lg2
// (lane-group leaf, 8 lanes each, hardened once), each with its own clock root.  No register, gate or reset logic here.
// Cycle-exact with the flat cluster: each former two-stage relay is now head register -> wire -> leaf register.
module ot_hgi_quant_wide_h #(
    parameter integer NB = 32,
    parameter integer LQ = 16,
    parameter integer MUT = 0,
`ifdef OT_QW_DEC3
    parameter integer DEC3 = 1
`else
    parameter integer DEC3 = 0
`endif
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [1408:0] cmd,
    output wire          idle,
    output wire          done,
    output wire          fault,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    wire [3:0] l_rst_n; wire [31:0] l_hit_r, l_hit_p, l_wv, l_push, l_rcr, l_wcr, l_done;
    wire [32*15-1:0] l_rs, l_wsec; wire [32*4-1:0] l_sl, l_ws; wire [511:0] l_wy; wire [4*1024-1:0] l_gp;
    ot_hgi_qw_hh #(.NB(NB), .LQ(LQ), .MUT(MUT), .DEC3(DEC3)) u_h (.clk(clk), .rst_n(rst_n), .go(go), .cmd(cmd),
        .idle(idle), .done(done), .fault(fault), .l_rst_n(l_rst_n), .l_hit_r(l_hit_r),
        .l_hit_p(l_hit_p), .l_wv(l_wv), .l_rs(l_rs), .l_wsec(l_wsec), .l_sl(l_sl), .l_ws(l_ws), .l_wy(l_wy), .l_gp(l_gp),
        .l_push(l_push), .l_rcr(l_rcr), .l_wcr(l_wcr), .l_done(l_done),
        .rg_req(rg_req), .rg_gnt(rg_gnt), .wg_req(wg_req), .wg_gnt(wg_gnt));
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_lg
        ot_hgi_qw_lg2 u_lg (.clk(clk), .rst_n(l_rst_n[k]), .wrr(wrr[k*8*257 +: 8*257]), .wrq(wrq[k*128 +: 128]),
            .wrq_cr(wrq_cr[k*8 +: 8]), .wwq(wwq[k*8*280 +: 8*280]), .wwq_cr(wwq_cr[k*8 +: 8]), .wwq_done(wwq_done[k*8 +: 8]),
            .c_hit_r(l_hit_r[k*8 +: 8]), .c_hit_p(l_hit_p[k*8 +: 8]), .c_wv(l_wv[k*8 +: 8]), .c_rs(l_rs[k*120 +: 120]),
            .c_wsec(l_wsec[k*120 +: 120]), .c_sl(l_sl[k*32 +: 32]), .c_ws(l_ws[k*32 +: 32]), .c_wy(l_wy), .gp(l_gp[k*1024 +: 1024]),
            .e_push(l_push[k*8 +: 8]), .e_rcr(l_rcr[k*8 +: 8]), .e_wcr(l_wcr[k*8 +: 8]), .e_done(l_done[k*8 +: 8]));
    end endgenerate
endmodule
`default_nettype wire
