`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): the DV vector slice, one hardened CLUSTER (p4c-lanes; contract
// results/rtl/s81_slice_1017/SLICE_CONTRACT.md).  Wires and registered relay stages only; every function is in a hardened
// sub-leaf with its own clock root:
//   beat leaves k = 0..4 (0.95 x 0.92 mm each, N -> S stacked; k = 2 is the centre): ot_s81sl_vn + ot_s81sl_vq + ot_s81sl_vp
//   centre: ot_s81sl_xg (ring stop + x streamer), ot_s81sl_xr1 / _xr3 (control plane), ot_s81sl_cap (capture root),
//           ot_s81dv_xfin (S81-DV: norm exchange + replicated finish)
// Glue: ot_s81sl_rly relay stages (registers only, <= 405 um a stage by the floorplan) on every leaf <-> centre link, EQUAL
// depth DL for all 5 leaves (the x beats and partials keep their compiled stagger), DR on the return lanes, DX on the x
// chains.  Straps: sid (die pins, captured in each sub-leaf), leaf index k (cluster constants at each vq's strap pins).
// Forwarded clocks (F1, die stations): one clock output per 276-b lane, a branch of the slice root (ck_*).
// HB = 1: the C3 variant (band port B on the S face: attention q / P.V); HB = 0: C1.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_rly #(parameter integer W = 1, parameter integer D = 1) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (D == 0) begin : g0 assign q = d; end
    else begin : gd
        reg [W-1:0] r [0:D-1];
        integer i;
        always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i - 1]; end
        assign q = r[D-1];
    end endgenerate
endmodule

module ot_s81sl_slice #(
    parameter integer HB = 0,
    parameter integer DL = 4,        // leaf <-> centre relay stages (equal for every leaf: the farthest leaf, 1.84 mm)
    parameter integer DR = 6,        // frame return lanes -> capture root (worst entry face to the centre, 2.3 mm)
    parameter integer DX = 6         // x streamer -> x-chain heads (centre to the bottom face)
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    // tier line (4 x 276-b lanes each) and V rung
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    // band port (C3)
    input  wire [1103:0]   bi,   output wire [1103:0] bo,
    // x chains: 0 / 1 = down (W / E frame of row 1), 2 / 3 = up (row 2)
    output wire [4*1104-1:0] xc,
    // frame return lanes (cfifo rd)
    input  wire [8*70-1:0] rt,
    // forwarded clocks: line E in/out, W in/out (4 lanes each), V in/out, x chains (4 x 4), returns (8)
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    output wire            fault
);
    assign ck_line = {16{clk}}; assign ck_v = {2{clk}}; assign ck_xc = {16{clk}}; assign ck_rt = {8{clk}};
    // ---------------------------------------------------------------- beat leaves
    wire [4:0] c_v_x, c_v_l, sw_v_x, sw_v_l, lo_v_l, lo_v_x, p_v_l, p_v_x, rb_v_x, rb_v_l;
    wire [799:0] c_d_x, c_d_l; wire [49:0] sw_a_x, sw_a_l; wire [39:0] sw_m_x, sw_m_l; wire [1279:0] sw_d_x, sw_d_l;
    wire [1279:0] lo_d_l, lo_d_x; wire [159:0] p_d_l, p_d_x, rb_d_x, rb_d_l;
    wire [9:0] cw_v_x, cw_v_l; wire [119:0] cw_a_x, cw_a_l; wire [319:0] cw_d_x, cw_d_l;
    wire [4:0] xfv_l, xfv_x, xfs_l, xfs_x; wire [5*276-1:0] xf_l, xf_x;
    wire [4:0] f_vn, f_vq, f_vp;
    genvar k;
    generate for (k = 0; k < 5; k = k + 1) begin : lf
        wire hw_v, hw_hf, hr_v, hr_hf, hq_v, n_go, m_v, m_q, m_b, wl_v, y_v;
        wire [2:0] hw_j, hr_j, wl_i, y_i; wire [255:0] hw_d, hq_d, wl_d, y; wire [127:0] n_pre;
        ot_s81sl_vp u_vp (.clk(clk), .rst_n(rst_n), .c_v(c_v_l[k]), .c_d(c_d_l[160 * k +: 160]),
            .sw_v(sw_v_l[k]), .sw_a(sw_a_l[10 * k +: 10]), .sw_m(sw_m_l[8 * k +: 8]), .sw_d(sw_d_l[256 * k +: 256]),
            .cw_v(cw_v_l[2 * k +: 2]), .cw_a(cw_a_l[24 * k +: 24]), .cw_d(cw_d_l[64 * k +: 64]),
            .lo_v(lo_v_l[k]), .lo_d(lo_d_l[256 * k +: 256]),
            .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d), .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf),
            .hq_v(hq_v), .hq_d(hq_d), .n_go(n_go), .n_pre(n_pre), .m_v(m_v), .m_q(m_q), .m_b(m_b),
            .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .fault(f_vp[k]));
        ot_s81sl_vn u_vn (.clk(clk), .rst_n(rst_n), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf), .hw_d(hw_d),
            .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(hq_v), .hq_d(hq_d), .n_go(n_go), .n_pre(n_pre),
            .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .rb_v(rb_v_l[k]), .rb_d(rb_d_l[32 * k +: 32]),
            .p_v(p_v_l[k]), .p_d(p_d_l[32 * k +: 32]), .y_v(y_v), .y_i(y_i), .y(y), .fault(f_vn[k]));
        ot_s81sl_vq u_vq (.clk(clk), .rst_n(rst_n), .y_v(y_v), .y_i(y_i), .y(y), .sid(sid), .k(k[2:0]), .m_v(m_v),
            .m_q(m_q), .m_b(m_b), .xf_v(xfv_l[k]), .xf_s(xfs_l[k]), .xf(xf_l[276 * k +: 276]),
            .fault(f_vq[k]));
        // leaf <-> centre glue: equal depth for every leaf
        ot_s81sl_rly #(.W(1 + 160 + 1 + 10 + 8 + 256 + 2 + 24 + 64 + 1 + 32), .D(DL)) u_dn (.clk(clk),
            .d({c_v_x[k], c_d_x[160 * k +: 160], sw_v_x[k], sw_a_x[10 * k +: 10], sw_m_x[8 * k +: 8], sw_d_x[256 * k +: 256],
                cw_v_x[2 * k +: 2], cw_a_x[24 * k +: 24], cw_d_x[64 * k +: 64], rb_v_x[k], rb_d_x[32 * k +: 32]}),
            .q({c_v_l[k], c_d_l[160 * k +: 160], sw_v_l[k], sw_a_l[10 * k +: 10], sw_m_l[8 * k +: 8], sw_d_l[256 * k +: 256],
                cw_v_l[2 * k +: 2], cw_a_l[24 * k +: 24], cw_d_l[64 * k +: 64], rb_v_l[k], rb_d_l[32 * k +: 32]}));
        ot_s81sl_rly #(.W(1 + 256 + 1 + 32 + 2 + 276), .D(DL)) u_up (.clk(clk),
            .d({lo_v_l[k], lo_d_l[256 * k +: 256], p_v_l[k], p_d_l[32 * k +: 32], xfv_l[k], xfs_l[k], xf_l[276 * k +: 276]}),
            .q({lo_v_x[k], lo_d_x[256 * k +: 256], p_v_x[k], p_d_x[32 * k +: 32], xfv_x[k], xfs_x[k], xf_x[276 * k +: 276]}));
    end endgenerate

    // ---------------------------------------------------------------- centre
    wire dl_ev, dl_wv, dl_vv, is_v, cfg_v, x_go, x_sv, x_rbv, f_xg, f_xr, f_cap, f_xf, xw_v;
    wire [1103:0] dl_e, dl_w, ci_b; wire [275:0] dl_vb; wire [2:0] ci_dir; wire [159:0] is_d, cfg_d;
    wire [31:0] x_eps, x_s, x_rbd; wire [7:0] x_si; wire [172:0] nx_wi, nx_ei, nx_eo, nx_wo; wire [1100:0] xw_d;
    ot_s81sl_xg u_xg (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w),
        .vi(vi), .vo(vo), .xf_v(xfv_x), .xf_s(xfs_x), .xf(xf_x), .nx_wi(nx_wi), .nx_ei(nx_ei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w), .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b),
        .is_v(is_v), .is_d(is_d), .xw_v(xw_v), .xw_d(xw_d), .fault(f_xg));
    generate if (HB != 0) begin : g_c3
        ot_s81sl_xr3 u_xr (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
            .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .bi(bi), .bo(bo),
            .c_v(c_v_x), .c_d(c_d_x), .sw_v(sw_v_x), .sw_a(sw_a_x), .sw_m(sw_m_x), .sw_d(sw_d_x), .lo_v(lo_v_x), .lo_d(lo_d_x),
            .p_v(p_v_x), .p_d(p_d_x), .rb_v(rb_v_x), .rb_d(rb_d_x), .x_go(x_go), .x_eps(x_eps), .x_sv(x_sv), .x_si(x_si),
            .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd), .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(f_xr));
    end else begin : g_c1
        ot_s81sl_xr1 u_xr (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
            .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b),
            .c_v(c_v_x), .c_d(c_d_x), .sw_v(sw_v_x), .sw_a(sw_a_x), .sw_m(sw_m_x), .sw_d(sw_d_x), .lo_v(lo_v_x), .lo_d(lo_d_x),
            .p_v(p_v_x), .p_d(p_d_x), .rb_v(rb_v_x), .rb_d(rb_d_x), .x_go(x_go), .x_eps(x_eps), .x_sv(x_sv), .x_si(x_si),
            .x_s(x_s), .x_rbv(x_rbv), .x_rbd(x_rbd), .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(f_xr));
        assign bo = 1104'd0;     // C1 has no band port: the C1 cluster master does not expose bi / bo
    end endgenerate
    // xfin (S81-DV leaf): sid strap pending (S81-DV to convert SID to a strap pin before its view is final)
    ot_s81dv_xfin u_xf (.clk(clk), .rst_n(rst_n), .go(x_go), .eps(x_eps), .s_v(x_sv), .s_i(x_si), .s(x_s),
        .wi_v(nx_wi[172]), .wi_h(nx_wi[171:168]), .wi_b(nx_wi[167:160]), .wi_d(nx_wi[159:0]),
        .ei_v(nx_ei[172]), .ei_h(nx_ei[171:168]), .ei_b(nx_ei[167:160]), .ei_d(nx_ei[159:0]),
        .eo_v(nx_eo[172]), .eo_h(nx_eo[171:168]), .eo_b(nx_eo[167:160]), .eo_d(nx_eo[159:0]),
        .wo_v(nx_wo[172]), .wo_h(nx_wo[171:168]), .wo_b(nx_wo[167:160]), .wo_d(nx_wo[159:0]),
        .rb_v(x_rbv), .rb_d(x_rbd), .fault(f_xf));
    // capture root: return lanes through DR relay stages
    wire [8*70-1:0] rt_q;
    ot_s81sl_rly #(.W(8 * 70), .D(DR)) u_rt (.clk(clk), .d(rt), .q(rt_q));
    ot_s81sl_cap u_cap (.clk(clk), .rst_n(rst_n), .rt(rt_q), .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_v(cw_v_x), .cw_a(cw_a_x), .cw_d(cw_d_x), .fault(f_cap));
    // x chains: the frame cfifo ingress word (dsfd_cfifo_crs): xd = {record xw[564:0], marker} (566 b, lanes 0..2),
    // xd2 = {record xw[1100:565], valid copy xw[0], marker} (538 b); marker = the slice's released reset (the forwarded
    // epoch marker of ot_s81_static_column_ingress_hr), from a registered relay of rst_n
    reg [1:0] mkq;
    always @(posedge clk or negedge rst_n) if (!rst_n) mkq <= 2'b00; else mkq <= {mkq[0], 1'b1};
    wire [1103:0] xw4 = {xw_d[1100:565], xw_d[0], mkq[1], xw_d[564:0], mkq[1]};
    genvar c;
    generate for (c = 0; c < 4; c = c + 1) begin : g_xc
        ot_s81sl_rly #(.W(1104), .D(DX)) u_x (.clk(clk), .d(xw4), .q(xc[1104 * c +: 1104]));
    end endgenerate
    // slice fault (sticky in every sub-leaf), registered
    reg flt;
    always @(posedge clk) flt <= (|f_vn) | (|f_vq) | (|f_vp) | f_xg | f_xr | f_cap | f_xf;
    assign fault = flt;
endmodule
