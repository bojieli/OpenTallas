`timescale 1ns/1ps
// ot_v41_bf_col3_hw (DIE-S81-51/RF-H 2026-11-03): the S81 hardened configuration of ot_v41_bf_col3 with no
// parameters, for the die bind (rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col3_kit.sv: u_view).  Synthesis: the three
// hard cores u_c / u_ha / u_hb (black boxes at their kit parameters, the plan hard_cores u_view.u_c / .u_ha / .u_hb)
// and wires.  Simulation: ot_v41_bf_col3 at the same parameters (ot_v41_bf_col g48 + BRNECUT 1).
module ot_v41_bf_col3_hw (
    input  wire          clk,
    input  wire          rst_n_pin,
    input  wire          ze_d,
    input  wire          issue,
    input  wire [13:0]   a_ctr,
    input  wire          i1_v,
    input  wire          i1_bk,
    input  wire          i1_bf,
    input  wire [16:0]   i1_t,
    input  wire [255:0]  i2x_q0,
    input  wire [9:0]    i2x_e0,
    input  wire [255:0]  i2x_q1,
    input  wire [9:0]    i2x_e1,
    input  wire [127:0]  so_row,
    input  wire [39:0]   so_idx,
    input  wire [39:0]   so_n,
    output wire          pv,
    output wire [31:0]   pval,
    output wire [15:0]   prow,
    output wire [4:0]    pseg,
    output wire [4:0]    pnseg,
    output wire          perr,
    output wire [2:0]    ppos,
    output wire          qy_bkf
);
`ifdef SYNTHESIS
    wire          h_v_a, h_v_b, r_v_a, r_v_b, r_err_a, r_err_b, r_f_a, r_f_b;
    wire          h_rst_a, h_ze_a, h_rst_b, h_ze_b;
    wire [127:0]  h_w_a, h_x_a, h_w_b, h_x_b;
    wire [12:0]   h_t_a, h_t_b;
    wire [31:0]   r_val_a, r_val_b;
    wire [7:0]    r_t_a, r_t_b;
    ot_v41_bf_col3_c u_c (
        .clk(clk), .rst_n_pin(rst_n_pin), .ze_d(ze_d), .issue(issue), .a_ctr(a_ctr), .i1_v(i1_v), .i1_bk(i1_bk), .i1_bf(i1_bf),
        .i1_t(i1_t), .i2x_q0(i2x_q0), .i2x_e0(i2x_e0), .i2x_q1(i2x_q1), .i2x_e1(i2x_e1), .so_row(so_row), .so_idx(so_idx),
        .so_n(so_n), .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos), .qy_bkf(qy_bkf),
        .h_v_a(h_v_a), .h_v_b(h_v_b), .h_w_a(h_w_a), .h_x_a(h_x_a), .h_w_b(h_w_b), .h_x_b(h_x_b), .h_t_a(h_t_a), .h_t_b(h_t_b),
        .r_v_a(r_v_a), .r_val_a(r_val_a), .r_val_b(r_val_b), .r_err_a(r_err_a), .r_err_b(r_err_b), .r_t_a(r_t_a),
        .r_f_a(r_f_a), .r_f_b(r_f_b), .h_rst_a(h_rst_a), .h_ze_a(h_ze_a), .h_rst_b(h_rst_b), .h_ze_b(h_ze_b));
    ot_v41_bf16_half u_ha (.clk(clk), .rst_c(h_rst_a), .ze_c(h_ze_a), .v(h_v_a), .w(h_w_a), .x(h_x_a),
        .t(h_t_a), .ov(r_v_a), .oval(r_val_a), .oerr(r_err_a), .otag(r_t_a), .fault(r_f_a));
    ot_v41_bf16_half u_hb (.clk(clk), .rst_c(h_rst_b), .ze_c(h_ze_b), .v(h_v_b), .w(h_w_b), .x(h_x_b),
        .t(h_t_b), .ov(r_v_b), .oval(r_val_b), .oerr(r_err_b), .otag(r_t_b), .fault(r_f_b));
`else
    ot_v41_bf_col3 #(.NSEG(8), .NCH(16), .XF(8), .LV(5), .BF16(1), .NCHB(8), .NB(2), .MTP(1), .EARLY(1), .CG(1), .DRAIN(200),
        .FAST(1), .PP(1), .BP(0), .QTIMING_FIX(1), .QPIPE(1), .QP_XS(1), .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .QZ(1), .QZ_NS(8),
        .QZ_NE(4), .QY(1), .QX(10), .QBF(2), .QZE(1), .TCG(1), .GRADUAL_RNE(1), .BXST(2), .FXST(2), .RCG(1), .KEEP_XPOS(1),
        .BRNECUT(1)) u_view (
        .clk(clk), .rst_n_pin(rst_n_pin), .ze_d(ze_d), .issue(issue), .a_ctr(a_ctr), .i1_v(i1_v), .i1_bk(i1_bk), .i1_bf(i1_bf),
        .i1_t(i1_t), .i2x_q0(i2x_q0), .i2x_e0(i2x_e0), .i2x_q1(i2x_q1), .i2x_e1(i2x_e1), .so_row(so_row), .so_idx(so_idx),
        .so_n(so_n), .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos), .qy_bkf(qy_bkf));
`endif
endmodule
