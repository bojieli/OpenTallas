`timescale 1ns/1ps
// ot_v41_rom_elem_q_qx_w10: ot_v41_rom_elem_q_qy_w10 on ot_v41_rom_elem_qx_w10 with the opt-in QX (default 0; see
// ot_v41_rom_elem_qx_w10.sv: zero added cycles, the walker step in one-hot form).
// ot_v41_rom_elem_q_qy_w10: ot_v41_rom_elem_q_qz_w10 on ot_v41_rom_elem_qy_w10 with the opt-in QY (default 0; see
// ot_v41_rom_elem_qy_w10.sv: zero added data cycles, fault port 2 cycles later).
// ot_v41_rom_elem_q_qz_w10: ot_v41_rom_elem_q_qp_w10 on ot_v41_rom_elem_qz_w10 with the opt-in QZ (default 0; see
// ot_v41_rom_elem_qz_w10.sv: zero added cycles, outputs cycle-identical to the qp element).
// ot_v41_rom_elem_q_qp_w10: ot_v41_rom_elem_q_qt_w10 on ot_v41_rom_elem_qp_w10 with the opt-in QPIPE (default 0; see
// ot_v41_rom_elem_qp_w10.sv: every output delayed by 1 + QP_CAP + QP_P1 cycles, nothing else changed).
// ot_v41_rom_elem_q_qt_w10: ot_v41_rom_elem_q_w10 on ot_v41_rom_elem_qt_w10 with the opt-in QTIMING_FIX (default 0).
// ot_v41_rom_elem_q_w10: the FP8/FP4 element (or W1 macro pair, NB = 2) as hardened: ot_v41_rom_elem_w10 with BF16 = 0
// and without the BF16 x port, which an FP8/FP4 macro never receives (W10, tools/v41_w10_elem_pnr.py).
module ot_v41_rom_elem_q_qx_w10 #(
    parameter integer NB = 1,
    parameter integer MTP = 0,
    parameter integer EARLY = 0,
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer FRONT_PAR = 0,
    parameter integer QTIMING_FIX = 0,
    parameter integer QPIPE = 0,
    parameter integer QP_XS = 1,
    parameter integer QP_CAP = 0,
    parameter integer QP_P1 = 1,
    parameter integer QP_CSAM = 10,
    parameter integer QZ = 0,
    parameter integer QZ_NS = 8,
    parameter integer QZ_NE = 4,
    parameter integer QY = 0,
    parameter integer QX = 0,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault
);
    ot_v41_rom_elem_qx_w10 #(.QX(QX), .QY(QY), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .BF16(0), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .INSTANCE(INSTANCE)) u_e (
        .clk(clk), .rst_n_pin(rst_n), .cfg_v_pin(cfg_v), .cfg_a_pin(cfg_a), .cfg_d_pin(cfg_d), .go_pin(go), .go_bf_pin(1'b0),
        .xs_v_pin(xs_v), .xs_p_pin(xs_p), .xs_b_pin(xs_b), .xs_sv_pin(xs_sv), .xs_q0_pin(xs_q0), .xs_e0_pin(xs_e0), .xs_q1_pin(xs_q1),
        .xs_e1_pin(xs_e1), .xs_pos_pin(xs_pos), .xb_pos_pin(3'd0), .ppos(ppos), .xb_v_pin(1'b0), .xb_b_pin(3'd0), .xb_sv_pin(4'd0),
        .xb_u_pin(32'd0), .xb_d_pin(1024'd0),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .busy(busy), .fault(fault));
endmodule
