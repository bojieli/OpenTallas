`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-FIX2/XG (10-21): ot_s81sl_xgt_xo -- the ONE combined end-slice gather sub-leaf master (u_xg) for the die72 slice
// parents: head XB egress (RG-HEAD ot_s81sl_xg_xo, 589110357) + structurally safe ring stop (RG-FFN ot_s81sl_xgt,
// 59a8155d3) + the native-bounded x streamer of the xg5 lineage (ot_s81sl_xs4, claude/s81-xg5fp-1021 ab6b3f7b4).
// SAME PORTS as ot_s81sl_xg / ot_s81sl_xg_xo / ot_s81sl_xgt (die binding = master swap of u_xg, no port or net change).
//   u_r  ot_s81sl_rstopt_xo  ring stop: rstopt (kept one-hot DKS selects, reset leaves on control/valid only, datapath
//                            unreset) + the head egress at s_0N -> ro_w.  0 added edges: ro_*, vo, nx_*, dl_*, gather port
//                            exactly as ot_s81sl_xg_xo.
//   u_s  ot_s81sl_xs4        x streamer: main ot_s81sl_xs function with a K=1 capture stage on every input (gather AND
//                            issuer alike, so all internal relative timing is main's) and every driver <= 32 loads by
//                            construction (xs4_equiv: main xs + 1 edge).  Main ot_s81sl_xs is NOT used: its mapped census
//                            is the 1,156-driver / 2,529-load (xs3) / 4,050-load ctl net failure of every xg / xg_xo gate.
// Cycle delta vs ot_s81sl_xg_xo (handed to MU.S81.CAL):
//   ring path (ro_e / ro_w / vo / nx_* / dl_* and the s_0N egress)          +0 edges
//   slice x path (is_d word -> xw_v / xw_d frame word; gather beat -> xw)   +1 edge  (xs4 capture stage, uniform)
//   fault                                                                   +1 edge  (status only)
//   The +1 sits at the x streamer input (one capture edge after the gather / issuer pins), so the calendar adds one edge
//   to the slice x-chain issue time (frame word = production lane word + OFF - 3 instead of OFF - 4); the ring
//   all-gather calendar and the head egress timing are unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xgt_xo (
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
    ot_s81sl_rstopt_xo u_r (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w),
        .vi(vi), .vo(vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(nx_wi), .nx_ei(nx_ei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .fault(f_r));
    ot_s81sl_xs4 u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d),
        .is_v(is_v), .is_d(is_d), .xw_v(), .xw_d(xw_d), .fault(f_s));
    // fault: rstopt_xo fault (registered) gets one edge so both halves reach the output together (= xg_xo fault + 1)
    reg f_rq, flt;
    always @(posedge clk) begin f_rq <= f_r; flt <= f_rq | f_s; end
    assign fault = flt;
endmodule
