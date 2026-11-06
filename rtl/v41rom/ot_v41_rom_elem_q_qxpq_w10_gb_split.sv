`timescale 1ns/1ps
// ot_v41_rom_elem_q_qxpq_w10_gb_split (S81 rom_q 2-way split, DIE-S81-65 2026-11-05, COORD 16:41 approved as the parallel
// safe form): the NB = 2 PQ element ot_v41_rom_elem_q_qxpq_w10_gb as TWO NB = 1 hard halves on one configuration / x
// stream, ~135k cells and 2 ROMs each instead of 235k cells and 4 ROMs in one core.
// Halves = the hard cores ot_v41_rom_elem_q_qxpq_w10_gb_hw / _he (below; parameter defaults = the rom_q kit's):
//   u_w = the pair's first macro (MSEL 0: output rows from configuration words s < NSEG; the second-macro words
//         2NSEG+1+s are ignored), ROM instances INSTANCE_0 / _1;
//   u_e = the pair's second macro (MSEL 1: output rows from words 2NSEG+1+s; words s still give idx / n), ROM
//         instances INSTANCEb_0 / _1 (the names macro 1 of the NB = 2 element gives its ROMs).
// Every input reaches both halves unchanged.  Both halves run the same walkers / issue / shadow / bank state on the same
// inputs, so their walking / bank_free / sh_free / busy are equal by construction and the pair's are u_w's (u_e's are
// left open); fault = u_w.fault | u_e.fault (the NB = 2 fault ORs the per-half bank faults: QY registers each half's
// OR, so the OR of the two registered faults is the registered OR).  pv / pval / prow / pseg / pnseg / perr / ppos: bit
// field 0 from u_w, field 1 from u_e.  0 added cycles; the only parent logic is one OR2 (fault).
// Bench: tools/dsrom_qelem_cl/tb_qxpq_split.sv (all-output lock-step vs the NB = 2 _gb element, and the halves' status
// equality checked every edge).
module ot_v41_rom_elem_q_qxpq_w10_gb_split #(
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 1,
    parameter integer PP = 1,
    parameter integer FRONT_PAR = 0,
    parameter integer QTIMING_FIX = 1,
    parameter integer QPIPE = 1,
    parameter integer QP_XS = 1,
    parameter integer QP_CAP = 0,
    parameter integer QP_P1 = 1,
    parameter integer QP_CSAM = 10,
    parameter integer QZ = 1,
    parameter integer QZ_NS = 8,
    parameter integer QZ_NE = 4,
    parameter integer QY = 1,
    parameter integer QX = 10,
    parameter integer PQ = 1,
    parameter integer QW = 0,
    parameter integer QM = 5,
    parameter integer QS = 5,
    parameter integer GO_BOUNDARY = 1,
    parameter integer RSTP = 1,
    parameter integer CGR = 0,
    parameter integer OLAT = 0,
    parameter integer IFN = 1,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire [1:0]   go_tag,
    output wire         walking,
    output wire         bank_free,
    output wire         sh_free,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire [1:0]   pv,
    output wire [63:0]  pval,
    output wire [31:0]  prow,
    output wire [9:0]   pseg,
    output wire [9:0]   pnseg,
    output wire [1:0]   perr,
    output wire [5:0]   ppos,
    output wire         busy,
    output wire         fault
);
    wire w_fault, e_fault;
    /* verilator lint_off PINCONNECTEMPTY */
    ot_v41_rom_elem_q_qxpq_w10_gb_hw #(.MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QY(QY), .QX(QX), .PQ(PQ), .QW(QW), .QM(QM), .QS(QS), .GO_BOUNDARY(GO_BOUNDARY), .RSTP(RSTP), .CGR(CGR), .OLAT(OLAT), .IFN(IFN), .INSTANCE(INSTANCE)) u_w (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag),
        .walking(walking), .bank_free(bank_free), .sh_free(sh_free),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos),
        .pv(pv[0]), .pval(pval[31:0]), .prow(prow[15:0]), .pseg(pseg[4:0]), .pnseg(pnseg[4:0]), .perr(perr[0]), .ppos(ppos[2:0]),
        .busy(busy), .fault(w_fault));
    ot_v41_rom_elem_q_qxpq_w10_gb_he #(.MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QY(QY), .QX(QX), .PQ(PQ), .QW(QW), .QM(QM), .QS(QS), .GO_BOUNDARY(GO_BOUNDARY), .RSTP(RSTP), .CGR(CGR), .OLAT(OLAT), .IFN(IFN), .INSTANCE(INSTANCE)) u_e (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag),
        .walking(), .bank_free(), .sh_free(),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos),
        .pv(pv[1]), .pval(pval[63:32]), .prow(prow[31:16]), .pseg(pseg[9:5]), .pnseg(pnseg[9:5]), .perr(perr[1]), .ppos(ppos[5:3]),
        .busy(), .fault(e_fault));
    /* verilator lint_on PINCONNECTEMPTY */
    assign fault = w_fault | e_fault;
endmodule

// ot_v41_rom_elem_q_qxpq_w10_gb_hw: the pair's first macro (MSEL 0), ROMs INSTANCE_0 / _1.  The hard core of the split (one kit / one view); defaults = the rom_q kit parameters.
module ot_v41_rom_elem_q_qxpq_w10_gb_hw #(
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 1,
    parameter integer PP = 1,
    parameter integer FRONT_PAR = 0,
    parameter integer QTIMING_FIX = 1,
    parameter integer QPIPE = 1,
    parameter integer QP_XS = 1,
    parameter integer QP_CAP = 0,
    parameter integer QP_P1 = 1,
    parameter integer QP_CSAM = 10,
    parameter integer QZ = 1,
    parameter integer QZ_NS = 8,
    parameter integer QZ_NE = 4,
    parameter integer QY = 1,
    parameter integer QX = 10,
    parameter integer PQ = 1,
    parameter integer QW = 0,
    parameter integer QM = 5,
    parameter integer QS = 5,
    parameter integer GO_BOUNDARY = 1,
    parameter integer RSTP = 1,
    parameter integer CGR = 0,
    parameter integer OLAT = 0,
    parameter integer IFN = 1,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire [1:0]   go_tag,
    output wire         walking,
    output wire         bank_free,
    output wire         sh_free,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire         pv,
    output wire [31:0]  pval,
    output wire [15:0]  prow,
    output wire [4:0]   pseg,
    output wire [4:0]   pnseg,
    output wire         perr,
    output wire [2:0]   ppos,
    output wire         busy,
    output wire         fault
);
    localparam integer HM = 0;
    ot_v41_rom_elem_q_qxpq_w10_gb #(.NB(1), .MSEL(HM), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QY(QY), .QX(QX), .PQ(PQ), .QW(QW), .QM(QM), .QS(QS), .GO_BOUNDARY(GO_BOUNDARY), .RSTP(RSTP), .CGR(CGR), .OLAT(OLAT), .IFN(IFN), .INSTANCE(INSTANCE)) u_h (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag),
        .walking(walking), .bank_free(bank_free), .sh_free(sh_free),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos), .busy(busy), .fault(fault));
endmodule

// ot_v41_rom_elem_q_qxpq_w10_gb_he: the pair's second macro (MSEL 1), ROMs INSTANCEb_0 / _1 (macro 1's names in the NB = 2 element).  The hard core of the split (one kit / one view); defaults = the rom_q kit parameters.
module ot_v41_rom_elem_q_qxpq_w10_gb_he #(
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 1,
    parameter integer PP = 1,
    parameter integer FRONT_PAR = 0,
    parameter integer QTIMING_FIX = 1,
    parameter integer QPIPE = 1,
    parameter integer QP_XS = 1,
    parameter integer QP_CAP = 0,
    parameter integer QP_P1 = 1,
    parameter integer QP_CSAM = 10,
    parameter integer QZ = 1,
    parameter integer QZ_NS = 8,
    parameter integer QZ_NE = 4,
    parameter integer QY = 1,
    parameter integer QX = 10,
    parameter integer PQ = 1,
    parameter integer QW = 0,
    parameter integer QM = 5,
    parameter integer QS = 5,
    parameter integer GO_BOUNDARY = 1,
    parameter integer RSTP = 1,
    parameter integer CGR = 0,
    parameter integer OLAT = 0,
    parameter integer IFN = 1,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire [1:0]   go_tag,
    output wire         walking,
    output wire         bank_free,
    output wire         sh_free,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire         pv,
    output wire [31:0]  pval,
    output wire [15:0]  prow,
    output wire [4:0]   pseg,
    output wire [4:0]   pnseg,
    output wire         perr,
    output wire [2:0]   ppos,
    output wire         busy,
    output wire         fault
);
`ifdef OT_QXPQ_SPLIT_MUT_MSEL
    localparam integer HM = 0;         // MUTANT: the second half reads the first macro's rows (the bench must catch it)
`else
    localparam integer HM = 1;
`endif
    ot_v41_rom_elem_q_qxpq_w10_gb #(.NB(1), .MSEL(HM), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QY(QY), .QX(QX), .PQ(PQ), .QW(QW), .QM(QM), .QS(QS), .GO_BOUNDARY(GO_BOUNDARY), .RSTP(RSTP), .CGR(CGR), .OLAT(OLAT), .IFN(IFN), .INSTANCE($sformatf("%sb", INSTANCE))) u_h (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag),
        .walking(walking), .bank_free(bank_free), .sh_free(sh_free),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos), .busy(busy), .fault(fault));
endmodule
