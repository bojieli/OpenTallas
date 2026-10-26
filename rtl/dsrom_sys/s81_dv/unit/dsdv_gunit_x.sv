`timescale 1ns/1ps
// PL-GUNIT (10-18): dsdv_gunit_x -- dsdv_gunit (dsdv_gunit.sv) EXPANDED for tools/landed_parent/lp.py: the four L1f fronts
// written as plain instances u_l1f0..3 (the generate loop unrolled, constant slices) and the bench-only MUT macro removed
// (the hardened leaves carry no MUT).  Wires only; otherwise identical to dsdv_gunit (same ports, same nets).
module dsdv_gunit_x #(
    parameter integer V    = 276
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,      // from / to s_3S
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,      // from / to s_3N
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d,
    output wire          fault
);
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8): leaf seams carry no constant / unread bits -- CTL rows packed to 170 bits
    // (h5_b, h4_b, h0_b, r_b, w_b), hp_a / hp_b [243:40], dl_a / dl_b packed 237, c45_a / c21_a packed 8, rw_x [191:0],
    // L1f o_d 245 per front; L1c reads f_v / f_f / f_l / f_g of front 0 only (fronts 1..3 leave them open).
    // rung segments: d_* southbound (from N), u_* northbound (from S)
    wire [275:0] d54, u45, d40, u04, d02, u20, d21, u12, d13, u31;
    // L5 <-> L4
    wire l_launch, l_tset, l_tw, l_mv; wire [4:0] l_mi; wire [31:0] l_my; wire [9:0] l_trow; wire [4:0] l_tlm; wire [15:0] l_tsm;
    wire c45_v; wire [7:0] c45_a; wire [255:0] c45_d; wire [3:0] s45; wire h5_v; wire [169:0] h5_b; wire f5;
    // L4 <-> L0
    wire g_v, j_v, j_set, j_w; wire [3:0] g_i; wire [4:0] g_acc, j_lm; wire [319:0] g_d; wire [9:0] j_row; wire [15:0] j_sm;
    wire c04_v; wire [7:0] c04_a; wire [255:0] c04_d; wire [3:0] s04; wire h4_v; wire [169:0] h4_b; wire mix_go, launch_s, f4;
    // L0 <-> L2
    wire hp_av, hp_bv; wire [243:40] hp_a, hp_b; wire c20_v; wire [7:0] c20_a; wire [255:0] c20_d; wire [3:0] s20;
    wire h0_v; wire [169:0] h0_b; wire f0;
    // L2 <-> L1
    wire dl_av, dl_bv; wire [236:0] dl_a, dl_b; wire c21_v; wire [7:0] c21_a; wire [255:0] c21_d; wire [3:0] s21;
    wire r_v; wire [169:0] r_b; wire f1;
    // L1 <-> L3
    // side leaves
    wire xe_v, ye_v, ye_f, xd_v, yd_v, yd_f; wire [31:0] xe_x, ye_y, xd_b, yd_y;
    wire ss_v, r4_v, r4_f; wire [31:0] ss, eps_c, r4_y;
    wire wr_av, wr_bv, wr_b, go_a, go_b, r0_v, r0_f; wire [4:0] wr_agh, wr_bgh, go_acc, r0_acc; wire [191:0] wr_ad, wr_bd;
    wire [3:0] r0_i; wire [319:0] r0_d;
    wire rw_st, rw_v, rw_l; wire [191:0] rw_x; wire [31:0] rw_scale; wire [9:0] rw_row; wire [4:0] rw_lm;
    wire [15:0] rw_sm; wire [3:0] s13; wire w_v; wire [169:0] w_b; wire f3;

    dsdv_gunit_l5 u_l5 (.clk(clk), .rst_n(rst_n), .rs_i(u45), .rs_o(d54), .launch(l_launch), .mx_v(l_mv), .mx_i(l_mi), .mx_y(l_my),
        .t_set(l_tset), .t_w(l_tw), .t_row(l_trow), .t_lm(l_tlm), .t_sm(l_tsm), .cw_v(c45_v), .cw_a(c45_a), .cw_d(c45_d),
        .sid_i(s45), .ct_v(h5_v), .ct_b(h5_b), .fault(f5), .vo_n(vo_n), .vi_n(vi_n),
        .xe_v(xe_v), .xe_x(xe_x), .ye_v(ye_v), .ye_y(ye_y), .ye_f(ye_f), .xd_v(xd_v), .xd_b(xd_b), .yd_v(yd_v), .yd_y(yd_y),
        .yd_f(yd_f));
    dsdv_gunit_l5f u_l5f (.clk(clk), .rst_n(rst_n), .xe_v(xe_v), .xe_x(xe_x), .ye_v(ye_v), .ye_y(ye_y),
        .ye_f(ye_f), .xd_v(xd_v), .xd_b(xd_b), .yd_v(yd_v), .yd_y(yd_y), .yd_f(yd_f));
    dsdv_gunit_l4 u_l4 (.clk(clk), .rst_n(rst_n), .rs_i(u04), .rs_o(d40), .g_v(g_v), .g_i(g_i),
        .g_acc(g_acc), .g_d(g_d), .j_v(j_v), .j_set(j_set), .j_w(j_w), .j_row(j_row), .j_lm(j_lm), .j_sm(j_sm),
        .cw_v(c04_v), .cw_a(c04_a), .cw_d(c04_d), .sid_i(s04), .hct_v(h4_v), .hct_b(h4_b), .mix_go_s(mix_go),
        .launch_s(launch_s), .fault(f4), .rn_o(u45), .rn_i(d54), .launch(l_launch), .mx_v(l_mv), .mx_i(l_mi), .mx_y(l_my), .t_set(l_tset),
        .t_w(l_tw), .t_row(l_trow), .t_lm(l_tlm), .t_sm(l_tsm), .cwo_v(c45_v), .cwo_a(c45_a), .cwo_d(c45_d),
        .sid_o(s45), .hct5_v(h5_v), .hct5_b(h5_b), .f5(f5), .ss_v(ss_v), .ss(ss), .eps_c(eps_c), .r_v(r4_v), .r_y(r4_y),
        .r_f(r4_f));
    dsdv_gunit_l4r u_l4r (.clk(clk), .rst_n(rst_n), .ss_v(ss_v), .ss(ss), .eps_c(eps_c), .r_v(r4_v),
        .r_y(r4_y), .r_f(r4_f));
    dsdv_gunit_l0 u_l0 (.clk(clk), .rst_n(rst_n), .rs_i(u20), .rs_o(d02), .hp_av(hp_av), .hp_a(hp_a),
        .hp_bv(hp_bv), .hp_b(hp_b), .cw_v(c20_v), .cw_a(c20_a), .cw_d(c20_d), .sid_i(s20), .hct_v(h0_v), .hct_b(h0_b),
        .fault(f0), .rn_o(u04), .rn_i(d40), .g_v(g_v), .g_i(g_i), .g_acc(g_acc), .g_d(g_d), .j_v(j_v), .j_set(j_set),
        .j_w(j_w), .j_row(j_row), .j_lm(j_lm), .j_sm(j_sm), .cwo_v(c04_v), .cwo_a(c04_a), .cwo_d(c04_d), .sid_o(s04),
        .hct4_v(h4_v), .hct4_b(h4_b), .mix_go(mix_go), .launch(launch_s), .f4(f4),
        .wr_av(wr_av), .wr_agh(wr_agh), .wr_ad(wr_ad), .wr_bv(wr_bv), .wr_bgh(wr_bgh), .wr_bd(wr_bd), .wr_b(wr_b),
        .go_a(go_a), .go_acc(go_acc), .go_b(go_b), .r_v(r0_v), .r_i(r0_i), .r_acc(r0_acc), .r_d(r0_d), .r_f(r0_f));
    dsdv_gunit_l0r u_l0r (.clk(clk), .rst_n(rst_n), .wr_av(wr_av), .wr_agh(wr_agh), .wr_ad(wr_ad),
        .wr_bv(wr_bv), .wr_bgh(wr_bgh), .wr_bd(wr_bd), .wr_b(wr_b), .go_a(go_a), .go_acc(go_acc), .go_b(go_b),
        .r_v(r0_v), .r_i(r0_i), .r_acc(r0_acc), .r_d(r0_d), .r_f(r0_f));
    dsdv_gunit_l2 u_l2 (.clk(clk), .rst_n(rst_n), .rn_i(d02), .rn_o(u20), .hp_av(hp_av), .hp_a(hp_a), .hp_bv(hp_bv),
        .hp_b(hp_b), .cwn_v(c20_v), .cwn_a(c20_a), .cwn_d(c20_d), .sidn(s20), .hct_v(h0_v), .hct_b(h0_b), .hf(f0),
        .rs_i(u12), .rs_o(d21), .dl_av(dl_av), .dl_a(dl_a), .dl_bv(dl_bv), .dl_b(dl_b), .cws_v(c21_v), .cws_a(c21_a),
        .cws_d(c21_d), .sids(s21), .rct_v(r_v), .rct_b(r_b), .rf(f1), .sid(sid), .cw_v(cw_v), .cw_a({cw_a[9:8], cw_a[5:0]}),
        .cw_d(cw_d), .fault(fault));
    // L1 <-> the router select leaves (S81U-GUNIT-L1): four fronts L1f0..3 + the collector L1c, E of L1
    wire [5:0] sa_r, sb_r; wire [223:0] sa_d, sb_d; wire [55:0] f_we; wire c_go, c_fw, c_l, f_re; wire [2:0] c_bn;
    wire [19:0] c_lvn; wire [3:0] f_ra, bw_a; wire [7:0] bw_e; wire [255:0] bw_d;
    wire [3:0] fo_v, fo_f, fo_l, fo_g, fo_flt; wire [4*245-1:0] fo_d; wire g_go; wire [23:0] g_hit; wire [41:0] g_a;
    wire i_v, gs_v, f1c; wire [53:0] i_ids; wire [191:0] gs_d;
    dsdv_gunit_l1 u_l1 (.clk(clk), .rst_n(rst_n), .rn_i(d21), .rn_o(u12), .dl_av(dl_av), .dl_a(dl_a),
        .dl_bv(dl_bv), .dl_b(dl_b), .cw_v(c21_v), .cw_a(c21_a), .cw_d(c21_d), .sid_i(s21), .ct_v(r_v), .ct_b(r_b),
        .fault(f1), .rs_o(d13), .rs_i(u31), .rw_st(rw_st), .rw_v(rw_v), .rw_l(rw_l), .rw_x(rw_x), .rw_scale(rw_scale),
        .rw_row(rw_row), .rw_lm(rw_lm), .rw_sm(rw_sm), .sid_o(s13), .w_v(w_v), .w_b(w_b), .f3(f3),
        .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d), .we(f_we), .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn),
        .c_lvn(c_lvn), .re(f_re), .ra(f_ra), .bw_e(bw_e), .bw_a(bw_a), .bw_d(bw_d),
        .i_v(i_v), .i_ids(i_ids), .gs_v(gs_v), .gs_d(gs_d), .fc(f1c));
    dsdv_gunit_l1f u_l1f0 (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d),
                .we(f_we[13:0]), .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn[4:0]),
                .re(f_re), .ra(f_ra), .bw_e(bw_e[1:0]), .bw_a(bw_a), .bw_d(bw_d),
                .g_go(g_go), .g_hit(g_hit[5:0]), .g_a(g_a),
                .o_v(fo_v[0]), .o_f(fo_f[0]), .o_l(fo_l[0]), .o_g(fo_g[0]), .o_d(fo_d[244:0]), .o_flt(fo_flt[0]));
    dsdv_gunit_l1f u_l1f1 (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d),
                .we(f_we[27:14]), .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn[9:5]),
                .re(f_re), .ra(f_ra), .bw_e(bw_e[3:2]), .bw_a(bw_a), .bw_d(bw_d),
                .g_go(g_go), .g_hit(g_hit[11:6]), .g_a(g_a),
                .o_v(fo_v[1]), .o_f(fo_f[1]), .o_l(fo_l[1]), .o_g(fo_g[1]), .o_d(fo_d[489:245]), .o_flt(fo_flt[1]));
    dsdv_gunit_l1f u_l1f2 (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d),
                .we(f_we[41:28]), .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn[14:10]),
                .re(f_re), .ra(f_ra), .bw_e(bw_e[5:4]), .bw_a(bw_a), .bw_d(bw_d),
                .g_go(g_go), .g_hit(g_hit[17:12]), .g_a(g_a),
                .o_v(fo_v[2]), .o_f(fo_f[2]), .o_l(fo_l[2]), .o_g(fo_g[2]), .o_d(fo_d[734:490]), .o_flt(fo_flt[2]));
    dsdv_gunit_l1f u_l1f3 (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d),
                .we(f_we[55:42]), .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn[19:15]),
                .re(f_re), .ra(f_ra), .bw_e(bw_e[7:6]), .bw_a(bw_a), .bw_d(bw_d),
                .g_go(g_go), .g_hit(g_hit[23:18]), .g_a(g_a),
                .o_v(fo_v[3]), .o_f(fo_f[3]), .o_l(fo_l[3]), .o_g(fo_g[3]), .o_d(fo_d[979:735]), .o_flt(fo_flt[3]));
    dsdv_gunit_l1c u_l1c (.clk(clk), .rst_n(rst_n), .f_v(fo_v[0]), .f_f(fo_f[0]), .f_l(fo_l[0]), .f_g(fo_g[0]),
        .f_d(fo_d), .f_flt(fo_flt), .g_go(g_go), .g_hit(g_hit), .g_a(g_a), .i_v(i_v), .i_ids(i_ids), .s_v(gs_v),
        .s_d(gs_d), .fault(f1c));
    dsdv_gunit_l3 u_l3 (.clk(clk), .rst_n(rst_n), .rn_i(d13), .rn_o(u31), .rw_st(rw_st), .rw_v(rw_v),
        .rw_l(rw_l), .rw_x(rw_x), .rw_scale(rw_scale), .rw_row(rw_row), .rw_lm(rw_lm), .rw_sm(rw_sm), .sid_i(s13),
        .w_v(w_v), .w_b(w_b), .fault(f3), .vo_s(vo_s), .vi_s(vi_s));
endmodule
