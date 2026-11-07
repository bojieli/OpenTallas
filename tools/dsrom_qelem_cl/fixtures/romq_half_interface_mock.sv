`timescale 1ns/1ps
// Interface fixture for the ACTUAL split RTL: half data/control lockups and autonomous reset age.
// MSEL perturbs data; this is not a replacement arithmetic or ROM-mask model.
module ot_v41_rom_elem_q_qxpq_w10_gb #(
    parameter integer NB = 1,
    parameter integer MSEL = 0,
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
    wire [603:0] input_face;
    assign input_face={cfg_v, cfg_a, cfg_d, go, go_tag, xs_v, xs_p, xs_b, xs_q0, xs_e0, xs_q1, xs_e1, xs_pos};
    reg [603:0] input_n;
    reg [67:0] state_q,autonomous;
    wire [67:0] mixed=input_n[67:0]^input_n[135:68]^input_n[203:136]^input_n[271:204]^input_n[339:272]^input_n[407:340]^input_n[475:408]^input_n[543:476]^{8'b0,input_n[603:544]};
    always @(negedge clk) input_n<=input_face;
    always @(posedge clk)
        if (!rst_n) begin state_q<=0; autonomous<=0; end
        else begin
            autonomous<=autonomous+1'b1;
            if(input_n[603]||input_n[549]||input_n[546]) state_q<=mixed^autonomous^(MSEL != 0 ? 68'h591bd8af328c48751 : 0);
        end
    wire [67:0] result;
    if (OLAT != 0) begin : g_olat
        reg [67:0] q;
        always @(negedge clk) q<=state_q;
        assign result=q;
    end else assign result=state_q;
    assign {walking, bank_free, sh_free, pv, pval, prow, pseg, pnseg, perr, ppos, busy, fault}=result;
endmodule
