`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-TILES-E (LEAD9-S81 decision 10-20 14:30, owner REPARTITION rule 09:09): ot_s81sl_xg5 -- the slice gather sub-leaf
// s81sl_xg re-merged from its native-bounded halves, so the 3 x 1,031-b rs -> xs gather port stays INSIDE one hard tile
// (the split rs4 leaf was pin-bound: 13,750 signal pins, util 2.6%, minimum outline at <= 6 pins/um ~3.7%).
//   u_r  ot_s81sl_rs  (S81-XG4: current-main rstop function, every output +1 edge, RELAY = 1 incl. the gather port;
//                      rs_equiv vs main rstop + 1-edge relay)
//   u_s  ot_s81sl_xs4 (S81-XG4XS + XG5 census fixes: current-main xs function, every output +1 edge; xs4_equiv)
//   is_v / is_d: one relay edge here, so the x streamer sees gather beats AND issuer words one edge later than main xg
//   (gather: rs relay; issuer: this relay) -> xw_v / xw_d = main ot_s81sl_xg + 2 edges, uniformly.
//   fault: rs fault (+1) gets one more edge -> fault = main + 2.  Ring outputs (ro_*, vo, nx_*, dl_*) = main + 1.
// Schedule (MU.S81.CAL): ring hop +1 per stop; slice x path +2 (was +1 gather / +1 issuer in the XG4/XG4XS split).
// Checked by tools/s81_slice/xg5_bench.sh (production PQ slot lockstep at the xg ring pins, compare offset +2).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xg5 (
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
    output wire            xw_v,  output wire [1100:0] xw_d,
    output wire            fault
);
    wire [2:0] g_v, g_fam; wire [20:0] g_idx; wire [3071:0] g_d; wire f_r, f_s;
    ot_s81sl_rs u_r (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w),
        .vi(vi), .vo(vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(nx_wi), .nx_ei(nx_ei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .fault(f_r));
    // issuer relay: valid reset by a local 2-flop landing of rst_n (released before the x streamer's own capture valids)
    (* keep = "true" *) reg ir0, ir1;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin ir0 <= 1'b0; ir1 <= 1'b0; end else begin ir0 <= 1'b1; ir1 <= ir0; end
    reg is_vq; reg [159:0] is_dq;
    always @(posedge clk or negedge ir1) if (!ir1) is_vq <= 1'b0; else is_vq <= is_v;
    always @(posedge clk) is_dq <= is_d;
    ot_s81sl_xs4 u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d),
        .is_v(is_vq), .is_d(is_dq), .xw_v(xw_v), .xw_d(xw_d), .fault(f_s));
    reg f_rq, flt;
    always @(posedge clk) begin f_rq <= f_r; flt <= f_rq | f_s; end
    assign fault = flt;
endmodule
