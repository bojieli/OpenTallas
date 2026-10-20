`timescale 1ns/1ps
// Legacy reference rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_clocks.sv sha256=af0693e553d32a0539fd72cd93973e475ec1f51de5b1d47c28d164fbead0ab08

module ot_hbm_smh_rp4_leafh_legacy #(
    parameter integer LBS = 2, parameter integer LSB = 16, parameter integer IL = 8, parameter integer TAGW = 16,
    parameter integer XD = 128, parameter integer NBEAT = 13, parameter integer TCK = 1, parameter integer NMG = 32,
    parameter integer A1B = 9, parameter integer A2B = 7
) (
    input wire clk, clk_xb, clk_xf, input wire [4:0] clk_hard, input wire rst_n,
    input  wire [A1B-1:0] xs_a1, input wire [4:0] xs_g1, input wire [A2B-1:0] xs_a2, input wire [4:0] xs_g2,
    input  wire [6+TAGW+LBS*266+LSB*16+1+$clog2(XD)-1:0] rl1,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]            bk1,
    input  wire [NBEAT-1:0]                              ohl1,
    output wire gv, output wire gf, output wire [31:0] gy, output wire [TAGW-1:0] gt
);
    wire iv_b, iv_f, ifirst, ilast, ifp4, ifirst_e, ilast_e;
    wire [TAGW-1:0] itag, itag_e;
    wire [LBS*266+LSB*16-1:0] iw, ix;

    // el1013-smh-r11: the leaf band's reset copy lands in one kept register per consumer (x store, block-dot column, the
    // three BF16 column tiles, the G1 select), each beside its consumer's rst_a pin
    (* keep *) reg [4:0] rq;
    always @(posedge clk) rq <= {5{rst_n}};
    wire r_xs = rq[0], r_bdc = rq[1], r_tcc = rq[2], r_g = rq[3], r_x = rq[4];



    ot_hbm_accel_smh_xs  u_xs (.clk(clk_hard[0]), .rst_a(r_xs), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2),
        .rl1(rl1), .bk1(bk1), .ohl1(ohl1), .o_iv_b(iv_b), .o_iv_f(iv_f), .o_ifirst(ifirst), .o_ilast(ilast),
        .o_ifp4(ifp4), .o_itag(itag), .o_iw(iw), .o_ix(ix), .o_ifirst_e(ifirst_e), .o_ilast_e(ilast_e), .o_itag_e(itag_e));
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;

    // el1013-smh-r15 OT_SMH_XREL (r14 --cts gate, sign-off reference: xs o_ix / o_iw -> tcl h1 i_x / i_w is 630-1,023 um of
    // wire between two hard children, -65 / -103 ps on 112 / 176 endpoints before repair, -95 after repair in r13; xs ->
    // bdc 693 um on 8): one leaf-owned register on EVERY operand / control bit between the x store and BOTH columns, at
    // fixed stations midway (xb_*: in the xs | bdc gap; xf_*: in the centre channel on the way to the BF16 columns).
    // +1 cycle on both columns alike, so the G1 select sees the same order; every leaf of every tile alike, so the
    // gather lanes and the front's result deskew are unchanged.
    reg xb_v, xf_v, xb_first, xb_last, xb_fp4, xf_first, xf_last;
    reg [TAGW-1:0] xb_tag, xf_tag;
    reg [LBS*266-1:0] xb_w, xb_x;
    reg [LSB*16-1:0] xf_w, xf_x;
    always @(`OT_RP4_AR(clk_xb, r_x)) if (!r_x) xb_v<=0; else xb_v<=iv_b;
    always @(`OT_RP4_AR(clk_xf, r_x)) if (!r_x) xf_v<=0; else xf_v<=iv_f;
    always @(posedge clk_xb) begin
        xb_first <= ifirst; xb_last <= ilast; xb_fp4 <= ifp4; xb_tag <= itag;
        xb_w <= iw[0 +: LBS*266]; xb_x <= ix[0 +: LBS*266];
    end
    always @(posedge clk_xf) begin
        xf_first <= ifirst_e; xf_last <= ilast_e; xf_tag <= itag_e;
        xf_w <= iw[LBS*266 +: LSB*16]; xf_x <= ix[LBS*266 +: LSB*16];
    end
    ot_hbm_accel_smh_bdc  u_bdc (.clk(clk_hard[1]), .rst_a(r_bdc), .i_v(xb_v), .i_first(xb_first), .i_last(xb_last), .i_fp4(xb_fp4),
        .i_tag(xb_tag), .i_w(xb_w), .i_x(xb_x), .ov(bov), .y(by), .otag(btag), .fault(bfault));
    ot_hbm_smh_rp4_tcc  u_tcc (.clk_hard(clk_hard[4:2]), .rst_a(r_tcc), .i_v(xf_v), .i_first(xf_first), .i_last(xf_last), .i_tag(xf_tag),
        .i_w(xf_w), .i_x(xf_x), .ov(fov), .y(fy), .otag(ftag), .fault(ffault));






    // G1: select by the producing column, registered (was the leaf's last stage)
    wire g_n;

    assign g_n = r_g;





    reg gv_q, gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    always @(`OT_RP4_AR(clk, g_n))
        if (!g_n) begin gv_q <= 1'b0; gf_q <= 1'b0; end
        else begin gv_q <= bov | fov; gf_q <= bfault | ffault | (bov & fov); end
    always @(posedge clk) begin gy_q <= bov ? by : fy; gt_q <= bov ? btag : ftag; end
    assign gv = gv_q; assign gf = gf_q; assign gy = gy_q; assign gt = gt_q;
endmodule
// Legacy reference rtl/hbm_accel/sm/repack/ot_rp4l_children.sv sha256=57f492d1119a5f2fa20b8cc51c0c0e360ecf98842c260d08a90054ab5570e55d

module ot_rp4l_leaf_legacy(input wire clk, input wire rst_n, input wire [25:0] st, input wire [817:0] rl1,
 input wire [2068:0] bk1, output wire [49:0] g);
 wire gv, gf; wire [31:0] gy; wire [15:0] gt;
 ot_hbm_smh_rp4_leafh_legacy u_lh (.clk(clk), .clk_xb(clk), .clk_xf(clk), .clk_hard({5{clk}}), .rst_n(rst_n),
  .xs_a1(st[8:0]), .xs_g1(st[13:9]), .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rl1), .bk1(bk1), .ohl1(bk1[2060:2048]),
  .gv(gv), .gf(gf), .gy(gy), .gt(gt));
 assign g = {gv, gf, gy, gt};
endmodule
module ot_rp4l_gs_legacy(input wire clk, input wire rst_n, input wire [49:0] g1in, input wire [49:0] g0m, input wire [99:0] gpm,
 output wire [199:0] gout);
 wire [49:0] g1, g2;
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1in[49:48]), .q(g1[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1in[47:0]), .q(g1[47:0]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[49:48]), .q(g2[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[47:0]), .q(g2[47:0]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_gov1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g2[49:48]), .q(gout[48 +: 2]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_god1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g2[47:0]), .q(gout[0 +: 48]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_gov0 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0m[49:48]), .q(gout[98 +: 2]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_god0 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0m[47:0]), .q(gout[50 +: 48]));
 genvar k;
 for (k = 0; k < 2; k = k + 1) begin : g_gl
  ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v3 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gpm[k*50+48 +: 2]), .q(gout[(2+k)*50+48 +: 2]));
  ot_hbm_accel_smh_kreg #(.W(48)) u_d3 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gpm[k*50 +: 48]), .q(gout[(2+k)*50 +: 48]));
 end
endmodule
// Legacy reference rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_flat_legacy.sv sha256=0673aa71ba51c1f905f2f329b07583eebe229775039d032fbc29a954a01801a8

module ot_hbm_smh_rp4_flat_legacy (input wire clk, input wire rst_n,
 input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
 input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
 input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
 output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
 input wire [99:0] gin, output wire [199:0] gout);
 wire [25:0] st_n, st_s;
 wire [817:0] rl_n, rl_s, rl1_n, rl1_s, rpm_n, rpm_s;
 wire [2068:0] bin_l, bm, bk1_n, bk1_s;
 wire [49:0] g0, g1, g0m;
 wire [99:0] gpm;
 ot_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));
 ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));
 ot_rp4l_pinrow u_pr_n (.clk(clk), .rst_n(rst_n), .d(rin_n), .q(rl_n));
 ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n(rst_n), .d(rin_s), .q(rl_s));
 ot_rp4l_pinbeat u_pb (.clk(clk), .rst_n(rst_n), .d(bin), .q(bin_l));
 ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a(rst_n), .d(rl_n), .first(rl1_n), .last(rpm_n));
 ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a(rst_n), .d(rl_s), .first(rl1_s), .last(rpm_s));
 ot_smh_tr_group_beat_e u_beat_t (.clk(clk), .rst_a(rst_n), .d(bin_l), .last(bm));
 ot_smh_tr_group_land u_land_n (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_n));
 ot_smh_tr_group_land u_land_s (.clk(clk), .rst_a(rst_n), .d(bin_l), .q(bk1_s));
 ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a(rst_n), .d(rpm_n), .last(rout_n));
 ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a(rst_n), .d(rpm_s), .last(rout_s));
 ot_smh_tr_group_beat_e u_beate (.clk(clk), .rst_a(rst_n), .d(bm), .last(bout));
 ot_rp4l_leaf_legacy u_lf0 (.clk(clk), .rst_n(rst_n), .st(st_n), .rl1(rl1_n), .bk1(bk1_n), .g(g0));
 ot_rp4l_leaf_legacy u_lf1 (.clk(clk), .rst_n(rst_n), .st(st_s), .rl1(rl1_s), .bk1(bk1_s), .g(g1));
 ot_rp4l_gn_legacy u_gn (.clk(clk), .rst_n(rst_n), .g0(g0), .gin(gin), .g0m(g0m), .gpm(gpm));
 ot_rp4l_gs_legacy u_gs (.clk(clk), .rst_n(rst_n), .g1in(g1), .g0m(g0m), .gpm(gpm), .gout(gout));
endmodule

module ot_rp4l_gn_legacy(input wire clk, input wire rst_n, input wire [49:0] g0, input wire [99:0] gin,
 output wire [49:0] g0m, output wire [99:0] gpm);
 wire [49:0] g1;
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0[49:48]), .q(g1[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd1 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g0[47:0]), .q(g1[47:0]));
 ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_grv2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[49:48]), .q(g0m[49:48]));
 ot_hbm_accel_smh_kreg #(.W(48)) u_grd2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(g1[47:0]), .q(g0m[47:0]));
 genvar k;
 for (k = 0; k < 2; k = k + 1) begin : g_gl
  wire [49:0] gm;
  ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gin[k*50+48 +: 2]), .q(gm[49:48]));
  ot_hbm_accel_smh_kreg #(.W(48)) u_d (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gin[k*50 +: 48]), .q(gm[47:0]));
  ot_hbm_accel_smh_kreg #(.W(2), .RST(`OT_RP4_RK)) u_v2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gm[49:48]), .q(gpm[k*50+48 +: 2]));
  ot_hbm_accel_smh_kreg #(.W(48)) u_d2 (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(gm[47:0]), .q(gpm[k*50 +: 48]));
 end
endmodule
