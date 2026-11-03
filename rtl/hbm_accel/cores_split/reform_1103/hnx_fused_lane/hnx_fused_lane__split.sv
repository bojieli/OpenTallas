`default_nettype none
// DIE-HBM-61/SPLIT 11-03: split composition of hnx_fused_lane (same ports as the kit core, face-shelled form):
// hnx_fused_lane_c + 4 x hnx_fused_lane_elp, each in its face-shelled form (<sub>__fs = reform_1103/facewrap.py model
// of the kit face shell), so this module is edge-exact with the hardened composition.
module hnx_fused_lane__split #(parameter integer SMUT = 0) (
    input wire clk, input wire [127:0] dn_d, input wire [2:0] dn_op, input wire dn_v, input wire [7:0] dn_x,
    output wire fin, output wire flt, input wire [4:0] lid, input wire [31:0] r_d, input wire r_v,
    output wire [15:0] rq_s, output wire rq_v, input wire [255:0] rr_d, input wire rr_v, input wire rst_n,
    output wire [255:0] up_d, output wire up_t, output wire up_v, output wire [9:0] up_x, output wire [255:0] wq_d,
    output wire [15:0] wq_s, output wire wq_v);
    wire [255:0] e_rd, e_xo, e_wo, e_ho, e_xl, e_sq, e_qq; wire [159:0] e_b; wire [31:0] e_rh; wire [1:0] e_asb_i;
    wire e_asb_we, e_pre, e_post, e_v, e_xv, e_xov, e_wv; wire [3:0] e_hv, e_flag;
    hnx_fused_lane_c__fs #(.SMUT(SMUT)) u_c (.clk(clk), .rst_n(rst_n), .lid(lid), .rq_v(rq_v), .rq_s(rq_s), .rr_v(rr_v),
        .rr_d(rr_d), .wq_v(wq_v), .wq_s(wq_s), .wq_d(wq_d), .dn_v(dn_v), .dn_op(dn_op), .dn_x(dn_x), .dn_d(dn_d),
        .r_v(r_v), .r_d(r_d), .up_v(up_v), .up_t(up_t), .up_x(up_x), .up_d(up_d), .fin(fin), .flt(flt),
        .e_rd(e_rd), .e_asb_we(e_asb_we), .e_asb_i(e_asb_i), .e_pre(e_pre), .e_post(e_post), .e_v(e_v), .e_xv(e_xv),
        .e_xov(e_xov), .e_wv(e_wv), .e_b(e_b), .e_xo(e_xo), .e_rh(e_rh), .e_wo(e_wo), .e_hv(e_hv), .e_flag(e_flag),
        .e_ho(e_ho), .e_xl(e_xl), .e_sq(e_sq), .e_qq(e_qq));
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_p
        hnx_fused_lane_elp__fs u_p (.clk(clk), .rst_n(rst_n), .e_rd(e_rd[64*q +: 64]), .e_asb_we(e_asb_we),
            .e_asb_i(e_asb_i), .e_pre(e_pre), .e_post(e_post), .e_v(e_v), .e_xv(e_xv), .e_xov(e_xov), .e_wv(e_wv),
            .e_b(e_b), .e_xo(e_xo[64*q +: 64]), .e_rh(e_rh), .e_wo(e_wo[64*q +: 64]), .e_hv(e_hv[q]),
            .e_flag(e_flag[q]), .e_ho(e_ho[64*q +: 64]), .e_xl(e_xl[64*q +: 64]), .e_sq(e_sq[64*q +: 64]),
            .e_qq(e_qq[64*q +: 64]));
    end endgenerate
endmodule
`default_nettype wire
