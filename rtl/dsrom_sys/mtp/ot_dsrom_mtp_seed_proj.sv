`timescale 1ns/1ps
// ot_dsrom_mtp_seed_proj (mtp-lead 2026-10-09): one production seed-projection slice = ot_dsrom_mtp_seed_ctl
// (routed block) + the native q-element ot_v41_rom_elem_q_qxpq_w10 at the selected QS5f parameters (separately
// hardened; its ROM macros hold RP row pairs x 480 words of mtp.0.main_proj).  5120 rows = 5120 / (2 RP) slices.
module ot_dsrom_mtp_seed_proj #(
    parameter integer RP = 8,
    parameter integer ROW0 = 0,
    parameter integer MUT_JOIN = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_x_v,
    input  wire [511:0]  in_xa_bf16,
    input  wire [511:0]  in_xb_bf16,
    output wire          out_x_rdy,
    output wire          out_y_v,
    output wire [15:0]   out_y_row,
    output wire [15:0]   out_y_bf16,
    output wire [31:0]   out_y_root,
    output wire          out_done,
    output wire          out_busy,
    output wire [3:0]    out_fault
);
    wire cfg_v, go, xs_v, walking, bank_free, sh_free, busy, fault;
    wire [4:0] cfg_a; wire [47:0] cfg_d; wire [1:0] go_tag, xs_sv, pv, perr; wire [7:0] xs_p; wire [2:0] xs_b, xs_pos;
    wire [255:0] xs_q0, xs_q1; wire [9:0] xs_e0, xs_e1, pseg, pnseg; wire [63:0] pval; wire [31:0] prow; wire [5:0] ppos;
    ot_dsrom_mtp_seed_ctl #(.RP(RP), .ROW0(ROW0), .MUT_JOIN(MUT_JOIN)) u_ctl (
        .clk(clk), .rst_n(rst_n), .in_x_v(in_x_v), .in_xa_bf16(in_xa_bf16), .in_xb_bf16(in_xb_bf16),
        .out_x_rdy(out_x_rdy), .out_y_v(out_y_v), .out_y_row(out_y_row), .out_y_bf16(out_y_bf16),
        .out_y_root(out_y_root), .out_done(out_done), .out_busy(out_busy), .out_fault(out_fault),
        .e_cfg_v(cfg_v), .e_cfg_a(cfg_a), .e_cfg_d(cfg_d), .e_go(go), .e_go_tag(go_tag), .e_xs_v(xs_v),
        .e_xs_p(xs_p), .e_xs_b(xs_b), .e_xs_sv(xs_sv), .e_xs_q0(xs_q0), .e_xs_e0(xs_e0), .e_xs_q1(xs_q1),
        .e_xs_e1(xs_e1), .e_xs_pos(xs_pos), .e_walking(walking), .e_bank_free(bank_free), .e_sh_free(sh_free),
        .e_pv(pv), .e_pval(pval), .e_prow(prow), .e_pseg(pseg), .e_pnseg(pnseg), .e_perr(perr), .e_ppos(ppos),
        .e_busy(busy), .e_fault(fault));
    ot_v41_rom_elem_q_qxpq_w10 #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .QTIMING_FIX(1), .QPIPE(1),
        .QP_XS(1), .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .QZ(1), .QZ_NS(8), .QZ_NE(4), .QY(1), .QX(10), .PQ(1),
        .QW(0), .QM(5), .QS(5), .INSTANCE("seed")) u_elem (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag),
        .walking(walking), .bank_free(bank_free), .sh_free(sh_free), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b),
        .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .pv(pv),
        .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos), .busy(busy), .fault(fault));
endmodule
