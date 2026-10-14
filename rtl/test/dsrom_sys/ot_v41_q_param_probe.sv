// Parameter probe for the DeepSeek-V4.1 ROM q-element bench (s81-qelem 2026-10-13).  Simulation only, never synthesized.
// Bound (no edit of the routed RTL) into every elaborated ot_v41_rom_elem_q_qxpq_w10 (the routed S81 top, LVL 0) and its
// body ot_v41_rom_elem_qx_pq_w10 (LVL 1): each instance prints the parameters it was ELABORATED with at time 0, so a
// bench log proves which configuration it exercised.  tools/dsrom_qelem_cl/pq1_routed_bench.py compares every line with
// the parameters of the closed route (results/rtl/dsrom_qelem_pq_20261006/closed_qs5f/receipt.json driver_args --param).
module ot_v41_q_param_probe #(
    parameter integer LVL = 0,
    parameter integer NB = -1, parameter integer MTP = -1, parameter integer EARLY = -1, parameter integer FAST = -1,
    parameter integer PP = -1, parameter integer FRONT_PAR = -1, parameter integer QTIMING_FIX = -1,
    parameter integer QPIPE = -1, parameter integer QP_XS = -1, parameter integer QP_CAP = -1,
    parameter integer QP_P1 = -1, parameter integer QP_CSAM = -1, parameter integer QZ = -1,
    parameter integer QZ_NS = -1, parameter integer QZ_NE = -1, parameter integer QY = -1, parameter integer QX = -1,
    parameter integer PQ = -1, parameter integer QW = -1, parameter integer QM = -1, parameter integer QS = -1,
    parameter integer BF16 = -1
) ();
    initial $display("QPROBE lvl=%0d NB=%0d MTP=%0d EARLY=%0d FAST=%0d PP=%0d FRONT_PAR=%0d QTIMING_FIX=%0d QPIPE=%0d QP_XS=%0d QP_CAP=%0d QP_P1=%0d QP_CSAM=%0d QZ=%0d QZ_NS=%0d QZ_NE=%0d QY=%0d QX=%0d PQ=%0d QW=%0d QM=%0d QS=%0d BF16=%0d inst=%m",
                     LVL, NB, MTP, EARLY, FAST, PP, FRONT_PAR, QTIMING_FIX, QPIPE, QP_XS, QP_CAP, QP_P1, QP_CSAM, QZ,
                     QZ_NS, QZ_NE, QY, QX, PQ, QW, QM, QS, BF16);
endmodule

bind ot_v41_rom_elem_q_qxpq_w10 ot_v41_q_param_probe #(.LVL(0), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP),
    .FRONT_PAR(FRONT_PAR), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1),
    .QP_CSAM(QP_CSAM), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QY(QY), .QX(QX), .PQ(PQ), .QW(QW), .QM(QM), .QS(QS),
    .BF16(0)) u_ot_qprobe ();
bind ot_v41_rom_elem_qx_pq_w10 ot_v41_q_param_probe #(.LVL(1), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP),
    .FRONT_PAR(FRONT_PAR), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1),
    .QP_CSAM(QP_CSAM), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QY(QY), .QX(QX), .PQ(PQ), .QW(QW), .QM(QM), .QS(QS),
    .BF16(BF16)) u_ot_qprobe ();
