`timescale 1ns/1ps
// Contract fixture with both input/output lockups and autonomous reset-age state.
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
    wire [603:0] input_face;
    assign input_face={cfg_v, cfg_a, cfg_d, go, go_tag, xs_v, xs_p, xs_b, xs_q0, xs_e0, xs_q1, xs_e1, xs_pos};
    reg [603:0] input_n;
    reg [130:0] state_q, autonomous;
    wire [130:0] mixed=input_n[130:0]^input_n[261:131]^input_n[392:262]^input_n[523:393]^{51'b0,input_n[603:524]};
    always @(negedge clk) input_n<=input_face;
    always @(posedge clk)
        if (!rst_n) begin state_q<=0; autonomous<=0; end
        else begin
            autonomous<=autonomous+1'b1;
            if(input_n[603]||input_n[549]||input_n[546]) state_q<=mixed^autonomous;
        end
    wire [130:0] result;
    if (OLAT != 0) begin : g_olat
        reg [130:0] q;
        always @(negedge clk) q<=state_q;
        assign result=q;
    end else assign result=state_q;
    assign {walking, bank_free, sh_free, pv, pval, prow, pseg, pnseg, perr, ppos, busy, fault}=result;
endmodule
