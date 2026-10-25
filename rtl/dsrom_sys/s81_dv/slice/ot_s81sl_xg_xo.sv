`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): ot_s81sl_xg -- the centre leaf's gather sub-leaf, one hardened tile: the ring stop
// data plane (ot_s81sl_rstop) and the x streamer (ot_s81sl_xs, slice-local x buffer + production static PQ stream path).
// The rstop -> xs gather port is internal (3 x 1,031 b a cycle would otherwise cross a tile boundary).  The 5 beat
// leaves' x beats enter as 276-b fragments (5 x 278 pins).
// S81-RTLGAP/RG-HEAD (TOK.DS.BENCH.4.1, 2026-10-21): ot_s81sl_xg_xo = ot_s81sl_xg with the ring stop ot_s81sl_rstop_xo
// (head XB egress at sid 1 = s_0N -> ro_w, flagged beats only; identical behaviour at every other sid and for every
// unflagged beat).  Same ports as ot_s81sl_xg: the die binding is a master swap of u_xg in the slice cluster, no port or
// net change.  0 added edges.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xg_xo (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [4:0]      xf_v, input wire [4:0] xf_s, input wire [5*276-1:0] xf,
    output wire [172:0]    nx_wi, output wire [172:0] nx_ei, input wire [172:0] nx_eo, input wire [172:0] nx_wo,
    output wire            dl_ev, output wire [1103:0] dl_e, output wire dl_wv, output wire [1103:0] dl_w,
    output wire            dl_vv, output wire [275:0] dl_vb,
    input  wire [2:0]      ci_dir, input wire [1103:0] ci_b,
    input  wire            is_v,  input wire [159:0] is_d,
    // S81/PORTFIX-DEAD D-XWV (10-25): no xw_v port -- it was xw_d[0] (the streamer's xw_q[0]) and had no load anywhere
    output wire [1100:0]   xw_d,
    output wire            fault
);
    wire [2:0] g_v, g_fam; wire [20:0] g_idx; wire [3071:0] g_d; wire f_r, f_s;
    ot_s81sl_rstop_xo u_r (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w),
        .vi(vi), .vo(vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(nx_wi), .nx_ei(nx_ei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .fault(f_r));
    ot_s81sl_xs u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d),
        .is_v(is_v), .is_d(is_d), .xw_v(), .xw_d(xw_d), .fault(f_s));
    reg flt;
    always @(posedge clk) flt <= f_r | f_s;
    assign fault = flt;
endmodule
