`timescale 1ns/1ps
// S81-IDX3M (10-20): chain-end variant of dsdv_idx_rg3 for the LAST reader of the die query chain (irg_07, dv_plan
// --idxrd 4).  The query chain qi -> qo ends there: no reader downstream, so qo has no consumer.  Same reader RTL with
// qo left inside (its only drivers are the qo pin flops, removed by synthesis) -- the bind-table chain_end rule
// (dv_bind.py: "the same RTL without that output and its only drivers"), so the die top carries no consumer-less output.
module dsdv_idx_rg3_nq #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,
    parameter integer IQD = 512,
    parameter integer SQD = 256,
    parameter integer LFD = 256,
    parameter integer EL = 124
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,
    input  wire [275:0]  si,
    output wire [275:0]  so,
    output wire [183:0]  rqo,
    input  wire [1087:0] rri,
    output wire [9:0]    st
);
    wire [512:0] qo_end;      // chain end: no downstream reader
    dsdv_idx_rg3 #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL)) u_rg3 (
        .ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(qo_end), .si(si), .so(so), .rqo(rqo), .rri(rri), .st(st));
endmodule
