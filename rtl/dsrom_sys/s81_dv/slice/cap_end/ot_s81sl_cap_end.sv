`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81/PORTFIX-DEAD D-CAPEND (2026-10-25): capture roots of the slice-row END slices, without the lanes no frame drives.
// The as-built die tied them (die_asb.v: .rt({350'd0, 3 lanes}) on the 3-frame slices 1N/1S/3N/3S/4N/4S/6N/6S and
// .rt({140'd0, 6 lanes}) on the 6-frame slices 0N/0S/2N/2S/5N/5S/7N/7S).  OWNER DECISION 8: dropped on both ends.
//   ot_s81sl_cap_w3  rt_w[209:0] (lanes 0..2), no E column: u_tw = ot_s81sl_cap_tr3, u_rt = ot_s81sl_cap_rt_w; the lane-3
//                    static delay (cap_ld, WL3DLY) and the E delay (cap_ed, EDLY) have no word to delay and are not built.
//   ot_s81sl_cap_e6  rt_w[279:0] + rt_e[139:0] (lanes 4, 5): u_te = ot_s81sl_cap_tr2, the rest as ot_s81sl_cap.
// Same structure/latencies as ot_s81sl_cap #(EDLY, WL3DLY) (the capc2 / capc5r core): every output bit every edge equal
// to it with the dropped lanes 0 (tools/s81_slice/cap_end/cap_end_eq.sh).  Hard views: these are the soft cores the
// end-slice variants of capc2 (cap_p1 PINPIPE 1) and capc5r (landed parent, lp.py) instantiate -- see the PORTFIX-DEAD
// report: new kits s81sl_cap_tr3 / s81sl_cap_tr2 / s81sl_cap_rt_w and parents.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_w3 #(
    parameter integer WIN = 2
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [209:0]  rt_w,         // lanes 0..2 (the row-end slice's three frames)
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);
    wire w_v, w_e, w_f; wire [31:0] w_t, w_d;
    ot_s81sl_cap_tr3 u_tw (.clk(clk), .rst_n(rst_n), .rt(rt_w), .o_v(w_v), .o_t(w_t), .o_d(w_d), .o_e(w_e), .fault(w_f));
    ot_s81sl_cap_rt_w u_rt (.clk(clk), .rst_n(rst_n), .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f),
        .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_s_v(cw_s_v), .cw_s_a(cw_s_a), .cw_s_d(cw_s_d), .cw_n_v(cw_n_v), .cw_n_a(cw_n_a), .cw_n_d(cw_n_d), .fault(fault));
endmodule

module ot_s81sl_cap_e6 #(
    parameter integer WIN = 2,
    parameter integer EDLY = 24,
    parameter integer WL3DLY = 16
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [279:0]  rt_w,         // lanes 0..3
    input  wire [139:0]  rt_e,         // lanes 4, 5 (lanes 6, 7: no frame)
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);
    wire w_v, w_e, w_f, e_v, e_e, e_f, ex_v, ex_e, ex_f; wire [31:0] w_t, w_d, e_t, e_d, ex_t, ex_d;
    wire [279:0] rt_wd;
    generate if (WL3DLY != 0) begin : g_ld3
        assign rt_wd[209:0] = rt_w[209:0];
        ot_s81sl_cap_ld #(.D(WL3DLY)) u_ld3 (.clk(clk), .rst_n(rst_n), .i_w(rt_w[279:210]), .o_w(rt_wd[279:210]));
    end else begin : g_nold3
        assign rt_wd = rt_w;
    end endgenerate
    generate if (EDLY != 0) begin : g_ed
        ot_s81sl_cap_ed #(.D(EDLY)) u_ed (.clk(clk), .rst_n(rst_n), .i_v(ex_v), .i_t(ex_t), .i_d(ex_d), .i_e(ex_e),
            .i_f(ex_f), .o_v(e_v), .o_t(e_t), .o_d(e_d), .o_e(e_e), .o_f(e_f));
    end else begin : g_noed
        assign e_v = ex_v; assign e_t = ex_t; assign e_d = ex_d; assign e_e = ex_e; assign e_f = ex_f;
    end endgenerate
    ot_s81sl_cap_tr  u_tw (.clk(clk), .rst_n(rst_n), .rt(rt_wd), .o_v(w_v), .o_t(w_t), .o_d(w_d), .o_e(w_e), .fault(w_f));
    ot_s81sl_cap_tr2 u_te (.clk(clk), .rst_n(rst_n), .rt(rt_e), .o_v(ex_v), .o_t(ex_t), .o_d(ex_d), .o_e(ex_e), .fault(ex_f));
    ot_s81sl_cap_rt u_rt (.clk(clk), .rst_n(rst_n),
        .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f), .e_v(e_v), .e_t(e_t), .e_d(e_d), .e_e(e_e), .e_f(e_f),
        .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_s_v(cw_s_v), .cw_s_a(cw_s_a), .cw_s_d(cw_s_d), .cw_n_v(cw_n_v), .cw_n_a(cw_n_a), .cw_n_d(cw_n_d), .fault(fault));
endmodule
`default_nettype wire
