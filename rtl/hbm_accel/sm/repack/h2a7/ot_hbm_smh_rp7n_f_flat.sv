`timescale 1ns/1ps
module ot_hbm_smh_rp7n_f_flat #(parameter integer HMUT=0) (
input wire clk,
input wire rst_n,
input wire [8:0] xs_a1,
input wire [4:0] xs_g1,
input wire [6:0] xs_a2,
input wire [4:0] xs_g2,
input wire [4:0] attn,
input wire [817:0] rin_n,
input wire [2068:0] bin,
input wire [99:0] gin,
output wire [817:0] rout_n,
output wire [2068:0] bout,
output wire [2068:0] xo_b,
output wire [49:0] xo_g0,
output wire [99:0] xo_gp
);
wire [99:0] r7p_0;
wire [4:0] r7p_1;
wire [4:0] r7p_2;
wire [4:0] r7p_3;
wire [817:0] r7p_4;
wire [25:0] r7p_5;
wire r7rst_u_bt1;
wire r7rst_u_bt2;
wire r7rst_u_be1;
wire r7rst_u_be2;
wire r7rst_u_landn;
wire r7rst_u_row0;
wire r7rst_u_rowe0;
wire r7rst_u_xbc;
wire r7rst_u_xs0;
wire r7rst_u_xq0;
wire r7rst_u_bdc0;
wire r7rst_u_h00;
wire r7rst_u_h10;
wire r7rst_u_qk0;
wire r7rst_u_cap0;
wire r7rst_u_pub0;
wire r7rst_u_mg0;
wire r7rst_u_go0;
wire r7rst_u_gn;
wire r7rst_u_xbo;
wire r7rst_u_xgr;
wire r7rst_u_xpr;
wire r7rst_u_xgo;
wire r7rst_u_xpo;

    wire lpr_pin;
    wire [25:0] st_n;
    wire [817:0] rl_n, rl1_n, rpm_n, rout_q;
    wire [2068:0] bin_l, bt1, bm, be1, bk1_n, xbc;
    wire [99:0] gin_a, gin_r, gpm, gpr;
    wire [49:0] g0m, g0r;
    wire [4:0] at_t;
    wire [25:0] st_r0;
    wire [817:0] rl1_r0;
    wire [2068:0] bk1_r0;
    wire [12:0] ohl_r0;
    wire x0_iv_b, x0_iv_f, x0_ifirst, x0_ilast, x0_ifp4, x0_ifirst_e, x0_ilast_e;
    wire [15:0] x0_itag, x0_itag_e;
    wire [787:0] x0_iw, x0_ix;
    wire [1083:0] bb0;
    wire [533:0] fb0;
    wire [4:0] pp0;
    wire [6:0] pf0, pfp0;
    wire bov0, bf0, fov0, qf0, mf0, ev0, pst0, ph0, pv0;
    wire [31:0] by0, fy0, pd0;
    wire [15:0] bt0, ft0, et0, ptg0;
    wire [511:0] es0;
    wire [255:0] s0_0, s1_0;
    wire lf0_0, lf1_0;
    wire [2:0] psl0, pos0;
    wire [3:0] pw0;
    wire [49:0] g0;
    wire [0:0] r_c7;
    wire [0:0] r_c9;
    wire [6:0] r_c10;
    wire [1:0] r_u7;
    
    
    
    
    ot_rp5_pad #(.W(1), .N(1)) u_lpr_pin (.clk(clk), .d(rst_n), .q(lpr_pin));
    ot_rp4l_strap  u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
    ot_rp4a_astrap  u_as (.clk(clk), .d((HMUT == 5) ? {attn[4:3] + 2'd1, attn[2:0]} : attn), .q(at_t));
    ot_rp4l_pinbeat  u_pb (.clk(clk), .rst_n(lpr_pin), .d(bin), .q(bin_l));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_bt1 (.clk(clk), .rst_n(r7rst_u_bt1), .d(bin_l), .q(bt1));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_bt2 (.clk(clk), .rst_n(r7rst_u_bt2), .d(bt1), .q(bm));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_be1 (.clk(clk), .rst_n(r7rst_u_be1), .d(bm), .q(be1));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_be2 (.clk(clk), .rst_n(r7rst_u_be2), .d(be1), .q(bout));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_landn (.clk(clk), .rst_n(r7rst_u_landn), .d(bin_l), .q(bk1_n));
    ot_rp4a_relay #(.W(100), .N(2), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_gi1 (.clk(clk), .rst_n(lpr_pin), .d(gin), .q(gin_a));
    ot_rp4l_pinrow  u_pr_n (.clk(clk), .rst_n(lpr_pin), .d(rin_n), .q(rl_n));
    ot_smh_tr_group_row_w  u_row0 (.clk(clk), .rst_a(r7rst_u_row0), .d(rl_n), .first(rl1_n), .last(rpm_n));
    ot_smh_tr_group_row_e  u_rowe0 (.clk(clk), .rst_a(r7rst_u_rowe0), .d(rpm_n), .last(rout_q));
    ot_rp5_pad #(.W(818), .N(1)) u_ro_n (.clk(clk), .d(rout_q), .q(rout_n));
    ot_rp4a_relay #(.W(2069), .N((HMUT == 1) ? 1 : 0), .VMASK({1'b1, 2068'b0})) u_xbc (.clk(clk), .rst_n(r7rst_u_xbc), .d(bk1_n), .q(xbc));
    ot_rp4a_relay #(.W(26), .N(0)) u_st0 (.clk(clk), .rst_n(1'b1), .d(st_n), .q(st_r0));
    ot_rp4a_relay #(.W(2069), .N(0)) u_bk0 (.clk(clk), .rst_n(1'b1), .d(bk1_n), .q(bk1_r0));
    ot_rp4a_relay #(.W(13), .N(0)) u_oh0 (.clk(clk), .rst_n(1'b1), .d(bk1_n[2060:2048]), .q(ohl_r0));
    ot_hbm_accel_smh_xs  u_xs0 (.clk(clk), .rst_a(r7rst_u_xs0), .xs_a1(r7p_5[8:0]), .xs_g1(r7p_5[13:9]), .xs_a2(r7p_5[20:14]), .xs_g2(r7p_5[25:21]), .rl1(r7p_4), .bk1(bk1_r0), .ohl1(ohl_r0), .o_iv_b(x0_iv_b), .o_iv_f(x0_iv_f), .o_ifirst(x0_ifirst), .o_ilast(x0_ilast), .o_ifp4(x0_ifp4), .o_itag(x0_itag), .o_iw(x0_iw), .o_ix(x0_ix), .o_ifirst_e(x0_ifirst_e), .o_ilast_e(x0_ilast_e), .o_itag_e(x0_itag_e));
    ot_rp5_xq  u_xq0 (.clk(clk), .rst_n(r7rst_u_xq0), .at(r7p_3), .x_iv_b(x0_iv_b), .x_iv_f(x0_iv_f), .x_ifirst(x0_ifirst), .x_ilast(x0_ilast), .x_ifp4(x0_ifp4), .x_itag(x0_itag), .x_iw(x0_iw), .x_ix(x0_ix), .x_ifirst_e(x0_ifirst_e), .x_ilast_e(x0_ilast_e), .x_itag_e(x0_itag_e), .bb(bb0), .fb(fb0), .pp(pp0), .pf(pf0));
    ot_hbm_accel_smh_bdc  u_bdc0 (.clk(clk), .rst_a(r7rst_u_bdc0), .i_v(bb0[1083]), .i_first(bb0[1082]), .i_last(bb0[1081]), .i_fp4(bb0[1080]), .i_tag(bb0[1079:1064]), .i_w(bb0[1063:532]), .i_x(bb0[531:0]), .ov(bov0), .y(by0), .otag(bt0), .fault(bf0));
    ot_hbm_accel_smh_tcl_gu  u_h00 (.clk(clk), .rst_a(r7rst_u_h00), .i_v(fb0[533]), .i_first(fb0[532]), .i_w(fb0[383:256]), .i_x(fb0[127:0]), .sum_o(s0_0), .lfault(lf0_0));
    ot_hbm_accel_smh_tcl_gu  u_h10 (.clk(clk), .rst_a(r7rst_u_h10), .i_v(fb0[533]), .i_first(fb0[532]), .i_w(fb0[511:384]), .i_x(fb0[255:128]), .sum_o(s1_0), .lfault(lf1_0));
    ot_hbm_accel_smh_tct  u_qk0 (.clk(clk), .rst_a(r7rst_u_qk0), .i_v(fb0[533]), .i_last(fb0[531]), .i_tag(fb0[527:512]), .sum_i({s1_0, s0_0}), .lf_a(lf0_0), .lf_b(lf1_0), .ov(fov0), .y(fy0), .otag(ft0), .fault(qf0));
    ot_rp4a_cap #(.TAGW(16)) u_cap0 (.clk(clk), .rst_n(r7rst_u_cap0), .i_v(fb0[533]), .i_last(fb0[530]), .i_run_first(fb0[529]), .i_run_last(fb0[528]), .i_tag(fb0[527:512]), .sum_i({s1_0, s0_0}), .event_v(ev0), .event_sum(es0), .event_tag(et0));
    ot_rp5_pub  u_pub0 (.clk(clk), .rst_n(r7rst_u_pub0), .at(r7p_2), .pp(pp0), .pub_start(pst0), .pub_slot(psl0), .published_h128(ph0));
    ot_rp5_pad #(.W(7), .N(0)) u_fp0 (.clk(clk), .d(pf0), .q(pfp0));
    ot_rp5_merge  u_mg0 (.clk(clk), .rst_n(r7rst_u_mg0), .ev(ev0), .sum(es0), .tag_d(et0), .pub_start(pst0), .pub_slot(psl0), .fold_start(pfp0[6]), .fold_a(pfp0[5:3]), .fold_b(pfp0[2:0]), .pub_v(pv0), .pub_data(pd0), .pub_word(pw0), .pub_out_slot(pos0), .pub_tag(ptg0), .fault(mf0));
    ot_rp5_go  u_go0 (.clk(clk), .rst_n(r7rst_u_go0), .at(r7p_1), .bov(bov0), .by(by0), .bt(bt0), .bfault(bf0), .fov(fov0), .fy(fy0), .ft(ft0), .qf(qf0), .mf(mf0), .ps_v(pv0), .ps_data(pd0), .ps_word(pw0), .ps_slot(pos0), .published_h128(ph0), .g(g0));
    ot_rp4a_relay #(.W(100), .N(3), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_gim (.clk(clk), .rst_n(lpr_pin), .d(gin_a), .q(gin_r));
    ot_rp4l_gn  u_gn (.clk(clk), .rst_n(r7rst_u_gn), .g0(g0), .gin(r7p_0), .g0m(g0m), .gpm(gpm));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_xbo (.clk(clk), .rst_n(r7rst_u_xbo), .d(xbc), .q(xo_b));
    ot_rp4a_relay #(.W(50), .N(2), .VMASK({2'b11, 48'b0})) u_xgr (.clk(clk), .rst_n(r7rst_u_xgr), .d(g0m), .q(g0r));
    ot_rp4a_relay #(.W(100), .N(2), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpr (.clk(clk), .rst_n(r7rst_u_xpr), .d(gpm), .q(gpr));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgo (.clk(clk), .rst_n(r7rst_u_xgo), .d(g0r), .q(xo_g0));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpo (.clk(clk), .rst_n(r7rst_u_xpo), .d(gpr), .q(xo_gp));

ot_rp7_delay_ring #(.W(100), .N(9)) u_r7p_0 (.clk(clk), .rst_n(lpr_pin), .d(gin_r), .q(r7p_0));
ot_rp7_delay_ring #(.W(5), .N(9)) u_r7p_1 (.clk(clk), .rst_n(lpr_pin), .d(at_t), .q(r7p_1));
ot_rp7_delay_ring #(.W(5), .N(9)) u_r7p_2 (.clk(clk), .rst_n(lpr_pin), .d(at_t), .q(r7p_2));
ot_rp7_delay_ring #(.W(5), .N(9)) u_r7p_3 (.clk(clk), .rst_n(lpr_pin), .d(at_t), .q(r7p_3));
ot_rp7_delay_ring #(.W(818), .N(3)) u_r7p_4 (.clk(clk), .rst_n(lpr_pin), .d(rl1_n), .q(r7p_4));
ot_rp7_delay_ring #(.W(26), .N(3)) u_r7p_5 (.clk(clk), .rst_n(lpr_pin), .d(st_r0), .q(r7p_5));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_bt1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_bt1));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_bt2 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_bt2));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_be1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_be1));
ot_rp5_rst #(.N(5), .NC(1)) u_r7rst_u_be2 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_be2));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_landn (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_landn));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_row0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_row0));
ot_rp5_rst #(.N(5), .NC(1)) u_r7rst_u_rowe0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_rowe0));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_xbc (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xbc));
ot_rp5_rst #(.N(9), .NC(1)) u_r7rst_u_xs0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xs0));
ot_rp5_rst #(.N(12), .NC(1)) u_r7rst_u_xq0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xq0));
ot_rp5_rst #(.N(15), .NC(1)) u_r7rst_u_bdc0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_bdc0));
ot_rp5_rst #(.N(15), .NC(1)) u_r7rst_u_h00 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_h00));
ot_rp5_rst #(.N(15), .NC(1)) u_r7rst_u_h10 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_h10));
ot_rp5_rst #(.N(15), .NC(1)) u_r7rst_u_qk0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_qk0));
ot_rp5_rst #(.N(15), .NC(1)) u_r7rst_u_cap0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_cap0));
ot_rp5_rst #(.N(14), .NC(1)) u_r7rst_u_pub0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_pub0));
ot_rp5_rst #(.N(15), .NC(1)) u_r7rst_u_mg0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_mg0));
ot_rp5_rst #(.N(15), .NC(1)) u_r7rst_u_go0 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_go0));
ot_rp5_rst #(.N(12), .NC(1)) u_r7rst_u_gn (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_gn));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_xbo (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xbo));
ot_rp5_rst #(.N(8), .NC(1)) u_r7rst_u_xgr (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xgr));
ot_rp5_rst #(.N(8), .NC(1)) u_r7rst_u_xpr (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xpr));
ot_rp5_rst #(.N(8), .NC(1)) u_r7rst_u_xgo (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xgo));
ot_rp5_rst #(.N(8), .NC(1)) u_r7rst_u_xpo (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xpo));
endmodule
