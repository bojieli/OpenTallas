`timescale 1ns/1ps
`default_nettype none
// S81/PORTFIX-DEAD D-CAPEND (2026-10-25): flat parent of the 6-frame row-end capture root (lp.py source of ot_s81sl_capc5r_e6,
// spec tools/landed_parent/specs/ot_s81sl_capc5r_e6.json).  = ot_s81sl_capc5cf with E lanes 4, 5 only: rt_e 140 b,
// u_te = ot_s81sl_cap_tr2 (lanes 6, 7 had no frame: the as-built die tied rt_e[279:140] = 0).
module ot_s81sl_capc5cf_e6 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [279:0]  rt_w,
    input  wire [139:0]  rt_e,
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
    wire [279:0] wq;
    wire [139:0] eq;
    wire         cq_v;
    wire [159:0] cq_d;
    wire [69:0]  wd3;
    wire         w_v, w_e, w_f, x_v, x_e, x_f, e_v, e_e, e_f;
    wire [31:0]  w_t, w_d, x_t, x_d, e_t, e_d;
    wire [3:0]   nv_o;
    wire [47:0]  na_o;
    wire [127:0] nd_o;
    wire [5:0]   sv_o;
    wire [71:0]  sa_o;
    wire [191:0] sd_o;
    wire         f_o;
    ot_pl_pad #(.W(280), .N(1)) u_fw (.ck(clk), .d(rt_w), .q(wq));
    ot_pl_pad #(.W(140), .N(1)) u_fe (.ck(clk), .d(rt_e), .q(eq));
    ot_pl_pad #(.W(1), .N(1)) u_fcv (.ck(clk), .d(cfg_v), .q(cq_v));
    ot_pl_pad #(.W(160), .N(1)) u_fcd (.ck(clk), .d(cfg_d), .q(cq_d));
    ot_s81sl_cap_ld #(.D(16)) u_ld3 (.clk(clk), .rst_n(rst_n), .i_w(wq[279:210]), .o_w(wd3));
    ot_s81sl_cap_tr u_tw (.clk(clk), .rst_n(rst_n), .rt({wd3, wq[209:0]}), .o_v(w_v), .o_t(w_t), .o_d(w_d), .o_e(w_e),
        .fault(w_f));
    ot_s81sl_cap_tr2 u_te (.clk(clk), .rst_n(rst_n), .rt(eq), .o_v(x_v), .o_t(x_t), .o_d(x_d), .o_e(x_e), .fault(x_f));
    ot_s81sl_cap_ed #(.D(24)) u_ed (.clk(clk), .rst_n(rst_n), .i_v(x_v), .i_t(x_t), .i_d(x_d), .i_e(x_e), .i_f(x_f),
        .o_v(e_v), .o_t(e_t), .o_d(e_d), .o_e(e_e), .o_f(e_f));
    ot_s81sl_cap_rt u_rt (.clk(clk), .rst_n(rst_n),
        .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f), .e_v(e_v), .e_t(e_t), .e_d(e_d), .e_e(e_e), .e_f(e_f),
        .cfg_v(cq_v), .cfg_d(cq_d),
        .cw_s_v(sv_o), .cw_s_a(sa_o), .cw_s_d(sd_o), .cw_n_v(nv_o), .cw_n_a(na_o), .cw_n_d(nd_o),
        .fault(f_o));
    ot_pl_pad #(.W(6), .N(1)) u_osv (.ck(clk), .d(sv_o), .q(cw_s_v));
    ot_pl_pad #(.W(72), .N(1)) u_osa (.ck(clk), .d(sa_o), .q(cw_s_a));
    ot_pl_pad #(.W(192), .N(1)) u_osd (.ck(clk), .d(sd_o), .q(cw_s_d));
    ot_pl_pad #(.W(1), .N(1)) u_osf (.ck(clk), .d(f_o), .q(fault));
    ot_pl_pad #(.W(4), .N(1)) u_onv (.ck(clk), .d(nv_o), .q(cw_n_v));
    ot_pl_pad #(.W(48), .N(1)) u_ona (.ck(clk), .d(na_o), .q(cw_n_a));
    ot_pl_pad #(.W(128), .N(1)) u_ond (.ck(clk), .d(nd_o), .q(cw_n_d));
endmodule
`default_nettype wire
