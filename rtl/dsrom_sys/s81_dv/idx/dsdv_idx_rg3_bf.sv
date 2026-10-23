`timescale 1ns/1ps
// STW-S81c-TOK4-BAND 10-22: the wires-only flat parent of the banded idx rg3 (bands in dsdv_idx_rg3_band.sv / _br.sv);
// the lp.py input (tools/landed_parent/specs/s81_idx_rg3_band.json -> lp/dsdv_idx_rg3_bf_lp.sv).
// ============================================================================ flat parent (wires only; lp.py input)
module dsdv_idx_rg3_bf #(
    parameter integer MUTR = 0,       // reader MUT (dsdv_idx_rg3 MUT); "MUT" is lp.py's landing-mutant parameter
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,
    parameter integer IQD = 512,
    parameter integer SQD = 256,
    parameter integer LFD = 256,
    parameter integer EL = 124,
    parameter integer RH = 1,
    parameter integer KR = 1,
    parameter integer LX = 0,
    parameter integer PD = 0
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
    output wire [9:0]    st
);
    wire [512:0] qoi;
    wire [275:0] soi;
    wire [9:0]   sti;
    wire [56:0]  ql;
    wire [17:0]  sx;
    wire [67:0]  xr;
    wire [16:0]  sc;
    wire [543:0] kq;
    wire [34:0]  a0;
    dsdv_idx_rg3_br #(.MUT(MUTR), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .IH(0),
                      .KR(KR), .LX(LX)) u_r (
        .ck(ck), .rst(rst), .sid(sid), .qi(qi), .si(si), .rqo(rqo), .qoi_o(qoi), .soi_o(soi), .st_o(sti), .ql_o(ql),
        .sx_o(sx), .xr_i(xr), .sc_i(sc));
    dsdv_idx_rg3_bx #(.MUT(MUTR), .SRAM_MACRO(SRAM_MACRO), .RH(RH)) u_x (
        .ck(ck), .rst(rst), .rri(rri), .sx_i(sx), .xr_o(xr), .kq_o(kq));
    dsdv_idx_rg3_bs01 #(.KR(KR)) u_s01 (.ck(ck), .rst(rst), .qoi_i(qoi), .ql_i(ql), .kq_i(kq), .a0_o(a0));
    dsdv_idx_rg3_bs23 #(.KR(KR), .PD(PD)) u_s23 (.ck(ck), .rst(rst), .qoi_i(qoi), .soi_i(soi), .st_i(sti), .ql_i(ql),
        .kq_i(kq), .a0_i(a0), .sc_o(sc), .qo(qo), .so(so), .st(st));
endmodule
