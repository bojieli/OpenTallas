`timescale 1ns/1ps
// ROMQ parent composition: registered whole input/reset and output bundles.
module ot_v41_rom_elem_q_qxpq_w10_gb_shell #(
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
    parameter INSTANCE = "",
    parameter integer IOREG = 0,
    parameter integer OUTPUT_NEG = 1
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

    // Default IOREG=0 is transparent. New parameters are appended, preserving
    // the split module's parameter prefix. IOREG=1 captures ALL inputs together,
    // including reset, so free-running child state has the same age as payload
    // and go/tag after reset. It adds +1 child reset assertion/release edge.
    // The complete output word includes status/fault and adds +1 further edge:
    // +2 interface cycles at rising-edge producers/consumers, no child RTL edit.
    // OUTPUT_NEG=1 uses the OLAT1 child's falling edge, giving a full-cycle hop.
    // OUTPUT_NEG=0 is the targeted rising-output alternative; its phase differs.
    localparam integer IW=605, OW=131;
    wire [IW-1:0] input_face, child_input;
    wire [OW-1:0] child_face, output_face;
    assign input_face={rst_n, cfg_v, cfg_a, cfg_d, go, go_tag, xs_v, xs_p, xs_b, xs_q0, xs_e0, xs_q1, xs_e1, xs_pos};
    wire  c_rst_n;
    wire  c_cfg_v;
    wire [4:0] c_cfg_a;
    wire [47:0] c_cfg_d;
    wire  c_go;
    wire [1:0] c_go_tag;
    wire  c_xs_v;
    wire [7:0] c_xs_p;
    wire [2:0] c_xs_b;
    wire [255:0] c_xs_q0;
    wire [9:0] c_xs_e0;
    wire [255:0] c_xs_q1;
    wire [9:0] c_xs_e1;
    wire [2:0] c_xs_pos;
    wire  c_walking;
    wire  c_bank_free;
    wire  c_sh_free;
    wire [1:0] c_pv;
    wire [63:0] c_pval;
    wire [31:0] c_prow;
    wire [9:0] c_pseg;
    wire [9:0] c_pnseg;
    wire [1:0] c_perr;
    wire [5:0] c_ppos;
    wire  c_busy;
    wire  c_fault;
    assign {c_rst_n, c_cfg_v, c_cfg_a, c_cfg_d, c_go, c_go_tag, c_xs_v, c_xs_p, c_xs_b, c_xs_q0, c_xs_e0, c_xs_q1, c_xs_e1, c_xs_pos}=child_input;
    assign child_face={c_walking, c_bank_free, c_sh_free, c_pv, c_pval, c_prow, c_pseg, c_pnseg, c_perr, c_ppos, c_busy, c_fault};
    assign {walking, bank_free, sh_free, pv, pval, prow, pseg, pnseg, perr, ppos, busy, fault}=output_face;
    if (IOREG != 0) begin : g_ioreg
        // Preserve each selected parent physical capture bank. Different ROMQ
        // instances may share logical input nets but require separate local flops.
        (* keep = 1, dont_touch = 1 *) reg [IW-1:0] input_q;
        (* keep = 1, dont_touch = 1 *) reg [OW-1:0] output_q;
        always @(posedge clk) input_q<=input_face;
        if (OUTPUT_NEG != 0) begin : g_output_negative
            always @(negedge clk) output_q<=child_face;
        end else begin : g_output_positive
            always @(posedge clk) output_q<=child_face;
        end
`ifdef OT_ROMQ_SHELL_MUT_TAG
        assign child_input={input_q[604:549],input_face[548:547],input_q[546:0]};
`elsif OT_ROMQ_SHELL_MUT_RESET
        assign child_input={rst_n,input_q[603:0]};
`else
        assign child_input=input_q;
`endif
`ifdef OT_ROMQ_SHELL_MUT_OUTPUT
        assign output_face=output_q ^ 131'b1;
`elsif OT_ROMQ_SHELL_MUT_STATUS
        assign output_face={child_face[130],output_q[129:0]};
`else
        assign output_face=output_q;
`endif
    end else begin : g_bypass
        assign child_input=input_face;
        assign output_face=child_face;
    end
    ot_v41_rom_elem_q_qxpq_w10_gb_split #(
        .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(FRONT_PAR), .QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP), .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .QZ(QZ), .QZ_NS(QZ_NS), .QZ_NE(QZ_NE), .QY(QY), .QX(QX), .PQ(PQ), .QW(QW), .QM(QM), .QS(QS), .GO_BOUNDARY(GO_BOUNDARY), .RSTP(RSTP), .CGR(CGR), .OLAT(OLAT), .IFN(IFN), .INSTANCE(INSTANCE)
    ) u_split (
        .clk(clk), .rst_n(c_rst_n), .cfg_v(c_cfg_v), .cfg_a(c_cfg_a), .cfg_d(c_cfg_d), .go(c_go), .go_tag(c_go_tag), .walking(c_walking), .bank_free(c_bank_free), .sh_free(c_sh_free), .xs_v(c_xs_v), .xs_p(c_xs_p), .xs_b(c_xs_b), .xs_q0(c_xs_q0), .xs_e0(c_xs_e0), .xs_q1(c_xs_q1), .xs_e1(c_xs_e1), .xs_pos(c_xs_pos), .pv(c_pv), .pval(c_pval), .prow(c_prow), .pseg(c_pseg), .pnseg(c_pnseg), .perr(c_perr), .ppos(c_ppos), .busy(c_busy), .fault(c_fault)
    );
endmodule
