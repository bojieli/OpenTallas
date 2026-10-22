`timescale 1ns/1ps
module ot_hbm_smh_rp7s_f_flat #(parameter integer HMUT=0) (
input wire clk,
input wire rst_n,
input wire [8:0] xss_a1,
input wire [4:0] xss_g1,
input wire [6:0] xss_a2,
input wire [4:0] xss_g2,
input wire [4:0] attn,
input wire [817:0] rin_s,
output wire [817:0] rout_s,
input wire [2068:0] xi_b,
input wire [49:0] xi_g0,
input wire [99:0] xi_gp,
output wire [199:0] gout
);
wire [4:0] r7p_0;
wire [49:0] r7p_1;
wire [99:0] r7p_2;
wire [4:0] r7p_3;
wire [4:0] r7p_4;
wire [2068:0] r7p_5;
wire [12:0] r7p_6;
wire [25:0] r7p_7;
wire r7rst_u_lands;
wire r7rst_u_row1;
wire r7rst_u_rowe1;
wire r7rst_u_xs1;
wire r7rst_u_xq1;
wire r7rst_u_bdc1;
wire r7rst_u_h01;
wire r7rst_u_h11;
wire r7rst_u_qk1;
wire r7rst_u_cap1;
wire r7rst_u_pub1;
wire r7rst_u_mg1;
wire r7rst_u_go1;
wire r7rst_u_g1p;
wire r7rst_u_gs;

    wire lpr_pin;
    wire [25:0] st_s, st_p;
    wire [817:0] rl_s, rl1_s, rl1_p, rpm_s, rout_q;
    wire [2068:0] bk1_s;
    wire [49:0] xg, xg2o, g1p;
    wire [99:0] xp, xp2;
    wire [4:0] at_m;
    wire [25:0] st_r1;
    wire [817:0] rl1_r1;
    wire [2068:0] bk1_r1;
    wire [12:0] ohl_r1;
    wire x1_iv_b, x1_iv_f, x1_ifirst, x1_ilast, x1_ifp4, x1_ifirst_e, x1_ilast_e;
    wire [15:0] x1_itag, x1_itag_e;
    wire [787:0] x1_iw, x1_ix;
    wire [1083:0] bb1;
    wire [533:0] fb1;
    wire [4:0] pp1;
    wire [6:0] pf1, pfp1;
    wire bov1, bf1, fov1, qf1, mf1, ev1, pst1, ph1, pv1;
    wire [31:0] by1, fy1, pd1;
    wire [15:0] bt1, ft1, et1, ptg1;
    wire [511:0] es1;
    wire [255:0] s0_1, s1_1;
    wire lf0_1, lf1_1;
    wire [2:0] psl1, pos1;
    wire [3:0] pw1;
    wire [49:0] g1;
    wire [1:0] r_c13;
    wire [0:0] r_c14;
    wire [6:0] r_c15;
    wire [0:0] r_t8;
    wire [1:0] r_u12;
    
    
    
    
    
    ot_rp5_pad #(.W(1), .N(1)) u_lpr_pin (.clk(clk), .d(rst_n), .q(lpr_pin));
    ot_rp4h_xreg #(.W(2069), .VMASK({1'b1, 2068'b0})) u_lands (.clk(clk), .rst_n(r7rst_u_lands), .d(xi_b), .q(bk1_s));
    ot_rp4h_xreg #(.W(50), .VMASK({2'b11, 48'b0})) u_xgi (.clk(clk), .rst_n(lpr_pin), .d(xi_g0), .q(xg));
    ot_rp4h_xreg #(.W(100), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xpi (.clk(clk), .rst_n(lpr_pin), .d(xi_gp), .q(xp));
    ot_rp4a_relay #(.W(50), .N(1), .VMASK({2'b11, 48'b0})) u_xg2 (.clk(clk), .rst_n(lpr_pin), .d(xg), .q(xg2o));
    ot_rp4a_relay #(.W(100), .N((HMUT == 2) ? 2 : 1), .VMASK({2'b11, 48'b0, 2'b11, 48'b0})) u_xp2 (.clk(clk), .rst_n(lpr_pin), .d(xp), .q(xp2));
    ot_rp4l_strap  u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
    ot_rp4a_astrap  u_as (.clk(clk), .d({attn[4:3] + 2'd1, attn[2:0]}), .q(at_m));
    ot_rp4l_pinrow  u_pr_s (.clk(clk), .rst_n(lpr_pin), .d(rin_s), .q(rl_s));
    ot_smh_tr_group_row_w  u_row1 (.clk(clk), .rst_a(r7rst_u_row1), .d(rl_s), .first(rl1_s), .last(rpm_s));
    ot_smh_tr_group_row_e  u_rowe1 (.clk(clk), .rst_a(r7rst_u_rowe1), .d(rpm_s), .last(rout_q));
    ot_rp5_pad #(.W(818), .N(1)) u_ro_s (.clk(clk), .d(rout_q), .q(rout_s));
    ot_rp5_pad #(.W(818), .N((HMUT == 3) ? 2 : 3)) u_prl (.clk(clk), .d(rl1_s), .q(rl1_p));
    ot_rp5_pad #(.W(26), .N(3)) u_pst (.clk(clk), .d(st_s), .q(st_p));
    ot_rp4a_relay #(.W(818), .N((HMUT == 6) ? 1 : 2)) u_rl1 (.clk(clk), .rst_n(1'b1), .d(rl1_p), .q(rl1_r1));
    ot_rp4a_relay #(.W(26), .N(2)) u_st1 (.clk(clk), .rst_n(1'b1), .d(st_p), .q(st_r1));
    ot_rp4a_relay #(.W(2069), .N(0)) u_bk1 (.clk(clk), .rst_n(1'b1), .d(bk1_s), .q(bk1_r1));
    ot_rp4a_relay #(.W(13), .N(0)) u_oh1 (.clk(clk), .rst_n(1'b1), .d(bk1_s[2060:2048]), .q(ohl_r1));
    ot_hbm_accel_smh_xs  u_xs1 (.clk(clk), .rst_a(r7rst_u_xs1), .xs_a1(r7p_7[8:0]), .xs_g1(r7p_7[13:9]), .xs_a2(r7p_7[20:14]), .xs_g2(r7p_7[25:21]), .rl1(rl1_r1), .bk1(r7p_5), .ohl1(r7p_6), .o_iv_b(x1_iv_b), .o_iv_f(x1_iv_f), .o_ifirst(x1_ifirst), .o_ilast(x1_ilast), .o_ifp4(x1_ifp4), .o_itag(x1_itag), .o_iw(x1_iw), .o_ix(x1_ix), .o_ifirst_e(x1_ifirst_e), .o_ilast_e(x1_ilast_e), .o_itag_e(x1_itag_e));
    ot_rp5_xq  u_xq1 (.clk(clk), .rst_n(r7rst_u_xq1), .at(r7p_4), .x_iv_b(x1_iv_b), .x_iv_f(x1_iv_f), .x_ifirst(x1_ifirst), .x_ilast(x1_ilast), .x_ifp4(x1_ifp4), .x_itag(x1_itag), .x_iw(x1_iw), .x_ix(x1_ix), .x_ifirst_e(x1_ifirst_e), .x_ilast_e(x1_ilast_e), .x_itag_e(x1_itag_e), .bb(bb1), .fb(fb1), .pp(pp1), .pf(pf1));
    ot_hbm_accel_smh_bdc  u_bdc1 (.clk(clk), .rst_a(r7rst_u_bdc1), .i_v(bb1[1083]), .i_first(bb1[1082]), .i_last(bb1[1081]), .i_fp4(bb1[1080]), .i_tag(bb1[1079:1064]), .i_w(bb1[1063:532]), .i_x(bb1[531:0]), .ov(bov1), .y(by1), .otag(bt1), .fault(bf1));
    ot_hbm_accel_smh_tcl_gu  u_h01 (.clk(clk), .rst_a(r7rst_u_h01), .i_v(fb1[533]), .i_first(fb1[532]), .i_w(fb1[383:256]), .i_x(fb1[127:0]), .sum_o(s0_1), .lfault(lf0_1));
    ot_hbm_accel_smh_tcl_gu  u_h11 (.clk(clk), .rst_a(r7rst_u_h11), .i_v(fb1[533]), .i_first(fb1[532]), .i_w(fb1[511:384]), .i_x(fb1[255:128]), .sum_o(s1_1), .lfault(lf1_1));
    ot_hbm_accel_smh_tct  u_qk1 (.clk(clk), .rst_a(r7rst_u_qk1), .i_v(fb1[533]), .i_last(fb1[531]), .i_tag(fb1[527:512]), .sum_i({s1_1, s0_1}), .lf_a(lf0_1), .lf_b(lf1_1), .ov(fov1), .y(fy1), .otag(ft1), .fault(qf1));
    ot_rp4a_cap #(.TAGW(16)) u_cap1 (.clk(clk), .rst_n(r7rst_u_cap1), .i_v(fb1[533]), .i_last(fb1[530]), .i_run_first(fb1[529]), .i_run_last(fb1[528]), .i_tag(fb1[527:512]), .sum_i({s1_1, s0_1}), .event_v(ev1), .event_sum(es1), .event_tag(et1));
    ot_rp5_pub  u_pub1 (.clk(clk), .rst_n(r7rst_u_pub1), .at(r7p_3), .pp(pp1), .pub_start(pst1), .pub_slot(psl1), .published_h128(ph1));
    ot_rp5_pad #(.W(7), .N(0)) u_fp1 (.clk(clk), .d(pf1), .q(pfp1));
    ot_rp5_merge  u_mg1 (.clk(clk), .rst_n(r7rst_u_mg1), .ev(ev1), .sum(es1), .tag_d(et1), .pub_start(pst1), .pub_slot(psl1), .fold_start(pfp1[6]), .fold_a(pfp1[5:3]), .fold_b(pfp1[2:0]), .pub_v(pv1), .pub_data(pd1), .pub_word(pw1), .pub_out_slot(pos1), .pub_tag(ptg1), .fault(mf1));
    ot_rp5_go  u_go1 (.clk(clk), .rst_n(r7rst_u_go1), .at(r7p_0), .bov(bov1), .by(by1), .bt(bt1), .bfault(bf1), .fov(fov1), .fy(fy1), .ft(ft1), .qf(qf1), .mf(mf1), .ps_v(pv1), .ps_data(pd1), .ps_word(pw1), .ps_slot(pos1), .published_h128(ph1), .g(g1));
    ot_rp4a_relay #(.W(50), .N(3), .VMASK({2'b11, 48'b0})) u_g1p (.clk(clk), .rst_n(r7rst_u_g1p), .d(g1), .q(g1p));
    ot_rp4l_gs  u_gs (.clk(clk), .rst_n(r7rst_u_gs), .g1in(g1p), .g0m(r7p_1), .gpm(r7p_2), .gout(gout));

ot_rp7_delay_ring #(.W(5), .N(12)) u_r7p_0 (.clk(clk), .rst_n(lpr_pin), .d(at_m), .q(r7p_0));
ot_rp7_delay_ring #(.W(50), .N(12)) u_r7p_1 (.clk(clk), .rst_n(lpr_pin), .d(xg2o), .q(r7p_1));
ot_rp7_delay_ring #(.W(100), .N(12)) u_r7p_2 (.clk(clk), .rst_n(lpr_pin), .d(xp2), .q(r7p_2));
ot_rp7_delay_ring #(.W(5), .N(12)) u_r7p_3 (.clk(clk), .rst_n(lpr_pin), .d(at_m), .q(r7p_3));
ot_rp7_delay_ring #(.W(5), .N(12)) u_r7p_4 (.clk(clk), .rst_n(lpr_pin), .d(at_m), .q(r7p_4));
ot_rp7_delay_ring #(.W(2069), .N(6)) u_r7p_5 (.clk(clk), .rst_n(lpr_pin), .d(bk1_r1), .q(r7p_5));
ot_rp7_delay_ring #(.W(13), .N(6)) u_r7p_6 (.clk(clk), .rst_n(lpr_pin), .d(ohl_r1), .q(r7p_6));
ot_rp7_delay_ring #(.W(26), .N(6)) u_r7p_7 (.clk(clk), .rst_n(lpr_pin), .d(st_r1), .q(r7p_7));
ot_rp5_rst #(.N(4), .NC(1)) u_r7rst_u_lands (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_lands));
ot_rp5_rst #(.N(2), .NC(1)) u_r7rst_u_row1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_row1));
ot_rp5_rst #(.N(5), .NC(1)) u_r7rst_u_rowe1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_rowe1));
ot_rp5_rst #(.N(17), .NC(1)) u_r7rst_u_xs1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xs1));
ot_rp5_rst #(.N(20), .NC(1)) u_r7rst_u_xq1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_xq1));
ot_rp5_rst #(.N(23), .NC(1)) u_r7rst_u_bdc1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_bdc1));
ot_rp5_rst #(.N(23), .NC(1)) u_r7rst_u_h01 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_h01));
ot_rp5_rst #(.N(23), .NC(1)) u_r7rst_u_h11 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_h11));
ot_rp5_rst #(.N(23), .NC(1)) u_r7rst_u_qk1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_qk1));
ot_rp5_rst #(.N(23), .NC(1)) u_r7rst_u_cap1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_cap1));
ot_rp5_rst #(.N(22), .NC(1)) u_r7rst_u_pub1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_pub1));
ot_rp5_rst #(.N(23), .NC(1)) u_r7rst_u_mg1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_mg1));
ot_rp5_rst #(.N(23), .NC(1)) u_r7rst_u_go1 (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_go1));
ot_rp5_rst #(.N(21), .NC(1)) u_r7rst_u_g1p (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_g1p));
ot_rp5_rst #(.N(24), .NC(1)) u_r7rst_u_gs (.clk(clk), .rst_n(lpr_pin), .r(r7rst_u_gs));
endmodule
