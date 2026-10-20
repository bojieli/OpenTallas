// ot_v41_rom_elem_q_qxpq_w10 (2026-10-06): ot_v41_rom_elem_q_qx_w10 on the PQ successor ot_v41_rom_elem_qx_pq_w10
// (PQ default 0 = the q_qx element; go_tag / walking / bank_free / sh_free for the PQ field spine).
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
// RSTP (QXPQ-RST, coordinator-approved structural successor 2026-10-17, default 0 = the closed element unchanged): a
// synchronous reset relay at the rst_n pin.  The pin drives ONE flop (D only, no asynchronous clear), and that flop's
// output is the element's rst_n_pin, which then distributes locally (the element's own local reset flop rst_q and the
// boundary-register clears).  Closed view (dsrom-qelem-qs5f-efs-7fb23b7ff-tc-hm10-cl) native audit: capture 239.2 ps
// > 190 on rst_n only (the pin fanned straight into the asynchronous clears of the boundary registers across the
// 510.84-wide frame); every data pin passed.  Cost: 0 data cycles; reset assertion and release reach the element one
// clk edge later (die reset timing: the die releases this element's rst_n one cycle earlier, or the first
// configuration / go after release moves one cycle later).  Bench: tb_qxpq_rstp (lock-step vs RSTP = 0).
// CPR (S81-PINREG4 2026-10-19, SAFE item 1, default 0 = the closed element unchanged): control pin registers.  Native audit of
// the CLOSED ob2 view (physical/s81_die_views/q_elem_qs5f_ob2/native_receipt.json, dsrom-qelem-qs5f-ob2-tc-hm25-cl-4b2f835cb)
// failed ONLY on three control pins: launch busy 230.2 / fault 227.1 ps (their drivers busy_d / fq2 are internal state
// registers ~185 um from the N-face pins, fault an async-clear flop the out-flop band cannot claim) and capture go 216.7 ps
// (go fans combinationally into the bank_free / clock-gate lookahead logic).  CPR = 1 adds one dedicated, kept register per
// pin: go and go_tag captured at the face (the go command enters u_e one cycle later, so the die issues go + go_tag ONE
// cycle earlier: +1 command edge), busy and fault re-registered by a private pin flop (+1 visibility cycle each; the
// out-flop band then places them at their pins).  Every other output is cycle-identical.  Bench: tb_qxpq_cpr.
module ot_v41_rom_elem_q_qxpq_w10 #(
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
    parameter integer PQ = 0,
    parameter integer QW = 0,
    parameter integer QM = 0,
    parameter integer QS = 0,          // SAFE knobs (owner fail-fast 2026-10-06): 1 = bterm5 S1b decode stage (+1 lane cycle)
    parameter integer RSTP = 0,        // 1 = synchronous reset relay flop at the rst_n pin (+1 reset edge, 0 data cycles)
    parameter integer CPR = 0,         // 1 = go / go_tag / busy / fault pin registers (+1 go command edge, +1 busy / fault cycle)
    parameter integer NP = 0,          // 1 = native partition (S81-QXPQ3: no driver > 32 loads; see ot_v41_rom_elem_qx_pq_w10)
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
    wire rst_n_e;                      // the element's reset: the pin (RSTP = 0) or the pin relay flop (RSTP = 1)
    if (RSTP != 0) begin : g_rstp
        (* keep, dont_touch = "true" *) reg rst_pf;
        always @(posedge clk) rst_pf <= rst_n;
`ifdef OT_QXPQ_RSTP_MUT_BYPASS
        assign rst_n_e = rst_n;        // MUTANT: relay bypassed (the bench must catch the release edge)
`else
        assign rst_n_e = rst_pf;
`endif
    end else begin : g_nrstp
        assign rst_n_e = rst_n;
    end
    wire go_e; wire [1:0] go_tag_e;    // the go command into the element: the pins (CPR = 0) or the pin registers (CPR = 1)
    wire busy_e, fault_e;              // the element's busy / fault: to the pins (CPR = 0) or through the pin registers
    if (CPR != 0) begin : g_cpr
        (* keep, dont_touch = "true" *) reg go_pf;
        (* keep, dont_touch = "true" *) reg [1:0] go_tag_pf;
        (* keep, dont_touch = "true" *) reg busy_pf, fault_pf;
        always @(posedge clk) begin go_pf <= go; go_tag_pf <= go_tag; busy_pf <= busy_e; fault_pf <= fault_e; end
`ifdef OT_QXPQ_CPR_MUT_GO
        assign go_e = go;              // MUTANT: go pin register bypassed (the go command enters one cycle early)
`else
        assign go_e = go_pf;
`endif
        assign go_tag_e = go_tag_pf;
`ifdef OT_QXPQ_CPR_MUT_BUSY
        assign busy = busy_e;          // MUTANT: busy pin register bypassed (busy one cycle early)
`else
        assign busy = busy_pf;
`endif
        assign fault = fault_pf;
    end else begin : g_ncpr
        assign go_e = go; assign go_tag_e = go_tag; assign busy = busy_e; assign fault = fault_e;
    end
    ot_v41_rom_elem_qx_pq_w10 #(.PQ(PQ), .QW(QW), .QM(QM), .QS(QS), .QX(QX), .QY(QY), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .BF16(0), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .NP(NP), .INSTANCE(INSTANCE)) u_e (
        .clk(clk), .rst_n_pin(rst_n_e), .cfg_v_pin(cfg_v), .cfg_a_pin(cfg_a), .cfg_d_pin(cfg_d), .go_pin(go_e), .go_bf_pin(1'b0), .go_tag_pin(go_tag_e), .walking(walking), .bank_free(bank_free), .sh_free(sh_free),
        .xs_v_pin(xs_v), .xs_p_pin(xs_p), .xs_b_pin(xs_b), .xs_sv_pin(xs_sv), .xs_q0_pin(xs_q0), .xs_e0_pin(xs_e0), .xs_q1_pin(xs_q1),
        .xs_e1_pin(xs_e1), .xs_pos_pin(xs_pos), .xb_pos_pin(3'd0), .ppos(ppos), .xb_v_pin(1'b0), .xb_b_pin(3'd0), .xb_sv_pin(4'd0),
        .xb_u_pin(32'd0), .xb_d_pin(1024'd0),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .busy(busy_e), .fault(fault_e));
endmodule
