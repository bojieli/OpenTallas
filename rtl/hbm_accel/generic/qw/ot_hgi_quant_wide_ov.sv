`timescale 1ns/1ps
`default_nettype none
// Opt-in record-overlap quant cluster, WIRES-ONLY parent (el1013-hbm-quant-split, 2026-10-13).
// The flat cluster had 38,353 flops + 20 macro clock pins on one root and failed the clock rule three times.
// Now: 1 x ot_hgi_qw_ovc (control head: descriptors, scheduler, read issue, retirement) + 1 x ot_hgi_qw_ovd (data
// head: gather tail, result capture, result SRAM, write side) + the decoder tiles + 4 x ot_hgi_qw_lg2 (lane-group leaf,
// 8 lanes each, hardened once), each with its own clock root.  No register, gate or reset logic here.
// Cycle-exact with the flat cluster: each former two-stage relay is now head register -> wire -> leaf register.
module ot_hgi_quant_wide_ov #(
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
    output wire          drained,
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
    wire [32*15-1:0] l_rs, l_wsec; wire [32*4-1:0] l_sl, l_ws; wire [4*512-1:0] l_wy; wire [4*1024-1:0] l_gp;
    wire d_rst_n, c_gv, c_mw_v, c_wg, d_wf, d_bad, dec_rst_n, x_v, d_vo, d_f, d_df;
    wire [17:0] c_gh, x_hd; wire [5:0] c_mw_a; wire [14:0] c_mw_sec; wire [2:0] c_mw_n; wire [1023:0] x; wire [511:0] d_y;
    wire [127:0] beat_header = {x_hd[17:8], 46'd0, x_hd[7:0], 64'd0};   // the decode's only header fields (constants are wires)
`ifdef OT_HARD_CHILDREN
    ot_hgi_qw_ovc u_c (
`else
    ot_hgi_qw_ovc #(.NB(NB), .LQ(LQ), .MUT(MUT)) u_c (
`endif
        .clk(clk), .rst_n(rst_n), .go(go), .cmd(cmd),
        .idle(idle), .drained(drained), .done(done), .fault(fault), .l_rst_n(l_rst_n), .l_hit_r(l_hit_r),
        .l_hit_p(l_hit_p), .l_rs(l_rs), .l_sl(l_sl), .l_push(l_push), .l_rcr(l_rcr), .l_done(l_done),
        .d_rst_n(d_rst_n), .c_gv(c_gv), .c_gh(c_gh), .c_mw_v(c_mw_v), .c_mw_a(c_mw_a), .c_mw_sec(c_mw_sec),
        .c_mw_n(c_mw_n), .c_wg(c_wg), .d_wf(d_wf), .d_bad(d_bad), .rg_req(rg_req), .rg_gnt(rg_gnt), .wg_req(wg_req), .wg_gnt(wg_gnt));
`ifdef OT_HARD_CHILDREN
    ot_hgi_qw_ovd u_d (
`else
    ot_hgi_qw_ovd #(.LQ(LQ)) u_d (
`endif
        .clk(clk), .rst_n(d_rst_n),
        .l_gp0(l_gp[0 +: 1024]), .l_gp1(l_gp[1024 +: 1024]), .l_gp2(l_gp[2048 +: 1024]), .l_gp3(l_gp[3072 +: 1024]),
        .l_wcr0(l_wcr[0 +: 8]), .l_wcr1(l_wcr[8 +: 8]), .l_wcr2(l_wcr[16 +: 8]), .l_wcr3(l_wcr[24 +: 8]),
        .l_wv0(l_wv[0 +: 8]), .l_wv1(l_wv[8 +: 8]), .l_wv2(l_wv[16 +: 8]), .l_wv3(l_wv[24 +: 8]),
        .l_wsec0(l_wsec[0 +: 120]), .l_wsec1(l_wsec[120 +: 120]), .l_wsec2(l_wsec[240 +: 120]), .l_wsec3(l_wsec[360 +: 120]),
        .l_ws0(l_ws[0 +: 32]), .l_ws1(l_ws[32 +: 32]), .l_ws2(l_ws[64 +: 32]), .l_ws3(l_ws[96 +: 32]),
        .l_wy0(l_wy[0 +: 512]), .l_wy1(l_wy[512 +: 512]), .l_wy2(l_wy[1024 +: 512]), .l_wy3(l_wy[1536 +: 512]),
        .c_gv(c_gv), .c_gh(c_gh), .c_mw_v(c_mw_v), .c_mw_a(c_mw_a), .c_mw_sec(c_mw_sec),
        .c_mw_n(c_mw_n), .c_wg(c_wg), .d_wf(d_wf), .d_bad(d_bad), .dec_rst_n(dec_rst_n), .x_v(x_v), .x_hd(x_hd),
        .x(x), .d_vo(d_vo), .d_f(d_f), .d_df(d_df), .d_y(d_y));
    generate if (DEC3 != 0) begin : g_d3
        ot_hgi_qw_dec3 u_dec (.clk(clk), .rst_n(dec_rst_n), .v(x_v), .header(beat_header), .x(x), .vo(d_vo), .y(d_y),
            .fault(d_f), .decode_fault(d_df));
    end else begin : g_d1
        ot_hgi_qw_dec u_dec (.clk(clk), .rst_n(dec_rst_n), .v(x_v), .header(beat_header), .x(x), .vo(d_vo), .y(d_y),
            .fault(d_f), .decode_fault(d_df));
    end endgenerate
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_lg
        ot_hgi_qw_lg2 u_lg (.clk(clk), .rst_n(l_rst_n[k]), .wrr(wrr[k*8*257 +: 8*257]), .wrq(wrq[k*128 +: 128]),
            .wrq_cr(wrq_cr[k*8 +: 8]), .wwq(wwq[k*8*280 +: 8*280]), .wwq_cr(wwq_cr[k*8 +: 8]), .wwq_done(wwq_done[k*8 +: 8]),
            .c_hit_r(l_hit_r[k*8 +: 8]), .c_hit_p(l_hit_p[k*8 +: 8]), .c_wv(l_wv[k*8 +: 8]), .c_rs(l_rs[k*120 +: 120]),
            .c_wsec(l_wsec[k*120 +: 120]), .c_sl(l_sl[k*32 +: 32]), .c_ws(l_ws[k*32 +: 32]), .c_wy(l_wy[k*512 +: 512]), .gp(l_gp[k*1024 +: 1024]),
            .e_push(l_push[k*8 +: 8]), .e_rcr(l_rcr[k*8 +: 8]), .e_wcr(l_wcr[k*8 +: 8]), .e_done(l_done[k*8 +: 8]));
    end endgenerate
endmodule
`default_nettype wire
