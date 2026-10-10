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
    parameter integer PREG = 0,        // ds-1010 2026-10-10: 1 = one free-clock register stage on every input + a registered
                                       // local reset (see the PREG note below): the element = the PREG 0 element one cycle later
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
    // PREG (ds-1010 2026-10-10, S81 option-B q element x1b): the PREG 0 element computes its clock-gate enable's next
    // state from go_pin in the SAME cycle (z_d = go_pin || ...) and resets its pin flops (b_go / b_cfg_v / b_xs_v, u_z,
    // u_we ...) straight from the rst_n pin.  Routed with x1 on the S-face east end that is two unrepairable CTS classes:
    // the gate-enable fanout from a same-cycle input (CTS setup -336 ps once the enable is copied per clone) and the pin
    // flops' reset removal (hold -31 ps on b_cfg_v RESETN).  PREG 1 registers every input once on the free clock (no reset:
    // plain pipeline flops) and gives the element a registered local reset (asserted with the pin, released on the next
    // edge), so the inner element sees exactly its PREG 0 stimulus one cycle late: every output is one cycle later
    // (+1 cycle), every internal enable / reset is register-driven.  The loader handshake keeps its timing: bank_free and
    // sh_free fall in the cycle after a go / configuration write as before (the registered input copy masks them), and
    // walking rises with the registered go.  Exactness: tools/dsrom_qx_exact.py pos_qs5p (+define+QX_PREG, L + 1).
    wire e_rst_n, e_cfg_v, e_go; wire [4:0] e_cfg_a; wire [47:0] e_cfg_d; wire [1:0] e_go_tag;
    wire e_xs_v; wire [7:0] e_xs_p; wire [2:0] e_xs_b, e_xs_pos; wire [1:0] e_xs_sv; wire [255:0] e_xs_q0, e_xs_q1;
    wire [9:0] e_xs_e0, e_xs_e1;
    wire u_walking, u_bank_free, u_sh_free;
    if (PREG != 0) begin : g_preg
        (* keep, dont_touch = "true" *) reg p_rst_n;
`ifdef PREG_MUTANT_RST
        assign e_rst_n = rst_n;           // negative control: the inner reset released one cycle early (unshifted)
`else
        always @(posedge clk or negedge rst_n) if (!rst_n) p_rst_n <= 1'b0; else p_rst_n <= 1'b1;
        assign e_rst_n = p_rst_n;
`endif
        reg p_cfg_v, p_go, p_xs_v; reg [4:0] p_cfg_a; reg [47:0] p_cfg_d; reg [1:0] p_go_tag;
        reg [7:0] p_xs_p; reg [2:0] p_xs_b, p_xs_pos; reg [1:0] p_xs_sv; reg [255:0] p_xs_q0, p_xs_q1; reg [9:0] p_xs_e0, p_xs_e1;
        always @(posedge clk) begin
            p_cfg_v <= cfg_v; p_cfg_a <= cfg_a; p_cfg_d <= cfg_d; p_go <= go; p_go_tag <= go_tag;
            p_xs_v <= xs_v; p_xs_p <= xs_p; p_xs_b <= xs_b; p_xs_sv <= xs_sv; p_xs_q0 <= xs_q0; p_xs_e0 <= xs_e0;
            p_xs_q1 <= xs_q1; p_xs_e1 <= xs_e1; p_xs_pos <= xs_pos;
        end
`ifdef PREG_MUTANT_GO
        assign e_go = go;                 // negative control: go unshifted while its configuration / beats are registered
`else
        assign e_go = p_go;
`endif
        assign e_cfg_v = p_cfg_v; assign e_cfg_a = p_cfg_a; assign e_cfg_d = p_cfg_d; assign e_go_tag = p_go_tag;
        assign e_xs_v = p_xs_v; assign e_xs_p = p_xs_p; assign e_xs_b = p_xs_b; assign e_xs_sv = p_xs_sv;
        assign e_xs_q0 = p_xs_q0; assign e_xs_e0 = p_xs_e0; assign e_xs_q1 = p_xs_q1; assign e_xs_e1 = p_xs_e1;
        assign e_xs_pos = p_xs_pos;
        assign walking = u_walking || p_go;
        assign bank_free = u_bank_free && !p_go;
        assign sh_free = u_sh_free && !p_cfg_v;
    end else begin : g_npreg
        assign e_rst_n = rst_n; assign e_cfg_v = cfg_v; assign e_cfg_a = cfg_a; assign e_cfg_d = cfg_d; assign e_go = go;
        assign e_go_tag = go_tag; assign e_xs_v = xs_v; assign e_xs_p = xs_p; assign e_xs_b = xs_b; assign e_xs_sv = xs_sv;
        assign e_xs_q0 = xs_q0; assign e_xs_e0 = xs_e0; assign e_xs_q1 = xs_q1; assign e_xs_e1 = xs_e1; assign e_xs_pos = xs_pos;
        assign walking = u_walking; assign bank_free = u_bank_free; assign sh_free = u_sh_free;
    end
    ot_v41_rom_elem_qx_pq_w10 #(.PQ(PQ), .QW(QW), .QM(QM), .QS(QS), .QX(QX), .QY(QY), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .BF16(0), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .INSTANCE(INSTANCE)) u_e (
        .clk(clk), .rst_n_pin(e_rst_n), .cfg_v_pin(e_cfg_v), .cfg_a_pin(e_cfg_a), .cfg_d_pin(e_cfg_d), .go_pin(e_go), .go_bf_pin(1'b0), .go_tag_pin(e_go_tag), .walking(u_walking), .bank_free(u_bank_free), .sh_free(u_sh_free),
        .xs_v_pin(e_xs_v), .xs_p_pin(e_xs_p), .xs_b_pin(e_xs_b), .xs_sv_pin(e_xs_sv), .xs_q0_pin(e_xs_q0), .xs_e0_pin(e_xs_e0), .xs_q1_pin(e_xs_q1),
        .xs_e1_pin(e_xs_e1), .xs_pos_pin(e_xs_pos), .xb_pos_pin(3'd0), .ppos(ppos), .xb_v_pin(1'b0), .xb_b_pin(3'd0), .xb_sv_pin(4'd0),
        .xb_u_pin(32'd0), .xb_d_pin(1024'd0),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .busy(busy), .fault(fault));
endmodule
