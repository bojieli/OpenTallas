`timescale 1ns/1ps
`default_nettype none
// S81/PORTFIX-DEAD D-CAPEND (2026-10-25): flat parent of the 3-frame row-end capture root (lp.py source of ot_s81sl_capc5r_w3,
// spec tools/landed_parent/specs/ot_s81sl_capc5r_w3.json).  = ot_s81sl_capc5cf with no E column and no W lane 3: rt_w 210 b,
// u_tw = ot_s81sl_cap_tr3, u_rt = ot_s81sl_cap_rt_w; u_ld3 / u_fe / u_te / u_ed are not built (no word to carry).
module ot_s81sl_capc5cf_w3 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [209:0]  rt_w,
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
    wire [209:0] wq;
    wire         cq_v;
    wire [159:0] cq_d;
    wire         w_v, w_e, w_f;
    wire [31:0]  w_t, w_d;
    wire [3:0]   nv_o;
    wire [47:0]  na_o;
    wire [127:0] nd_o;
    wire [5:0]   sv_o;
    wire [71:0]  sa_o;
    wire [191:0] sd_o;
    wire         f_o;
    ot_pl_pad #(.W(210), .N(1)) u_fw (.ck(clk), .d(rt_w), .q(wq));
    ot_pl_pad #(.W(1), .N(1)) u_fcv (.ck(clk), .d(cfg_v), .q(cq_v));
    ot_pl_pad #(.W(160), .N(1)) u_fcd (.ck(clk), .d(cfg_d), .q(cq_d));
    ot_s81sl_cap_tr3 u_tw (.clk(clk), .rst_n(rst_n), .rt(wq), .o_v(w_v), .o_t(w_t), .o_d(w_d), .o_e(w_e), .fault(w_f));
    ot_s81sl_cap_rt_w u_rt (.clk(clk), .rst_n(rst_n),
        .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f),
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
