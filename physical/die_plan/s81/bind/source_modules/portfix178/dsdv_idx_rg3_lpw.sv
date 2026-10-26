`timescale 1ns/1ps
// STW-S81c-TOK4-BAND (10-22): FROZEN-PORT wrapper of the banded, landed idx rg3 -- the dsdv_idx_rg3 port list (ck, rst,
// sid, qi, qo, si, so, rqo, rri, st; MUT / SRAM_MACRO / DQR / IQD / SQD) over the hard parent dsdv_idx_rg3_bf_lp, whose
// four band roots ck_r / ck_x / ck_s01 / ck_s23 are the ONE die clock ck at the parent face (die obligation: one die
// net to the four clock pins, neighbour-matched like any landed parent).  Wires only.
// Latency vs dsdv_idx_rg3 #(IH 1, OH 2, RH 2, KR 1) (the rg3p kit): q / s chains 0, rq lane 0, response pop -> budget +1,
// key -> score -> metadata ring +8 (internal: LX 8, absorbed by T0), st +3, reset release +4 (lp reset runs).
// OH / RH / IH / KR are accepted and ignored (benches pass them; the banded chain is fixed: W pin flop, 1 S23 stage).
// S81/PORTFIX-FLT 10-25: follows dsdv_idx_rg3's port change st[9:0] -> fault (1-bit sticky = the parent's st[0] flop);
// act (st[1]) stays an internal net for the bench's end-of-window check.
module dsdv_idx_rg3_lpw #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 1,
    parameter integer DQR = 24,
    parameter integer IQD = 512,
    parameter integer SQD = 256,
    parameter integer OH = 3,
    parameter integer RH = 1,
    parameter integer IH = 0,
    parameter integer KR = 1
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,
    output wire [512:0]  qo,
    input  wire [275:0]  si,
    output wire [275:0]  so,
    output wire [183:0]  rqo,
    input  wire [1087:0] rri,
    output wire          fault
);
    wire [9:0] st;
    assign fault = st[0];
    wire act = st[1];   // bench tap only
    dsdv_idx_rg3_bf_lp #(.MUTR(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .IQD(IQD), .SQD(SQD), .RH(1), .KR(1), .LX(8), .PD(2)
`ifdef OT_LPW_LPMUT
        , .MUT(`OT_LPW_LPMUT)                     // lp.py's own landing / reset mutants (negative campaigns only)
`endif
    ) u_lp (
        .ck_r(ck), .ck_x(ck), .ck_s01(ck), .ck_s23(ck), .rst(rst), .sid(sid), .qi(qi), .qo(qo), .si(si), .so(so),
        .rqo(rqo), .rri(rri), .st(st));
endmodule
