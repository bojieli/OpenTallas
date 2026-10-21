`timescale 1ns/1ps
// ATTN1 (DRIVE-S81-ATTN1, 10-20, G4 re-plan): FLAT NARROWED attw parent for tools/landed_parent/lp.py (wires only).
//   u_c   dsdv_svc_rs_attw1 #(TEXT 1, NTP 1): the attention share with ONE physical engine tile exported on tx_i0 / tx_o0
//         (ot_hdc_v41x_attn_s NTP 1: the 4 virtual tiles run as 4 sub-beats; the p feed paced 1 step / 4 cycles);
//   u_t0  ot_hdc_v41x_attn_tile_s at the S81 engine parameters (with -DOT_ATTN_HGRP_HARD = 4 hard head groups).
// Two regions (c, t0), the tile bundle LANDED both ways (TLX 6 as dsdv_svc_attw_f).  Bit maps as dsdv_svc_attw_f.
module dsdv_svc_attw_n1_f #(parameter integer AMUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                         parameter integer SRAM_MACRO = 0, parameter integer ROOT = 0, parameter integer PMEM = 1,
                         parameter integer TLX = 0, parameter integer TXD = 0, parameter integer ROLE_EXT = 0) (
    input  wire             ck,
    input  wire             rst,
    input  wire [3:0]       sid,
    input  wire [804:0]     cs,
    output wire [681:0]     qrq,
    input  wire [1:0]       qrk,
    input  wire [1:0]       qwd,
    input  wire [1:0]       qrv,
    input  wire [511:0]     qr_data,
    input  wire [33:0]      qr_tag,
    input  wire [7:0]       qr_beat,
    output wire             l_v,
    output wire [2131:0]    l_d,
    output wire             pv_ov,
    output wire [512:0]     pv_od,
    output wire             sm_st,
    output wire [3:0]       sm_kind,
    output wire [7:0]       sm_jid,
    output wire             sm_rv,
    output wire             sm_rp,
    output wire [2:0]       sm_rj,
    output wire [511:0]     sm_rd,
    output wire             go_o,
    output wire [9:0]       tjob_o,
    output wire             done,
    output wire [7:0]       tagj,
    output wire [1:0]       hcr,
    output wire [1:0]       hack,
    output wire             fault,

    output wire [31:0] fault_code, output wire [15:0] pio_o, pvo_o, jc_o, output wire [1:0] st_o,
    input wire [21:0] role_i, input wire [7:0] pvs_i
);
    wire [1617:0] txi0;
    wire [528:0]  txo0;
    dsdv_svc_rs_attw1 #(.MUT(AMUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .ROOT(ROOT), .PMEM(PMEM), .TEXT(1), .NTP(1), .ROLE_EXT(ROLE_EXT),
                       .TLX(TLX), .TXD(TXD)) u_c (
        .ck(ck), .rst(rst), .sid(sid), .cs(cs), .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data),
        .qr_tag(qr_tag), .qr_beat(qr_beat), .l_v(l_v), .l_d(l_d), .pv_ov(pv_ov), .pv_od(pv_od), .sm_st(sm_st),
        .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd), .go_o(go_o),
        .tjob_o(tjob_o), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(fault), .fault_code(fault_code), .pio_o(pio_o), .pvo_o(pvo_o), .jc_o(jc_o), .st_o(st_o), .role_i(role_i), .pvs_i(pvs_i),
        .tx_i0(txi0), .tx_o0(txo0));
    ot_hdc_v41x_attn_tile_s #(.H(16), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1)) u_t0 (
        .clk(ck), .rst_n(rst), .ld_v(txi0[0]), .ld_mode(txi0[1]), .ld_bank(txi0[4:2]), .ld_grp(txi0[12:5]),
        .ld_w(txi0[1036:13]), .ld_w2v(txi0[1037]), .iv(txi0[1038]), .ibank(txi0[1041:1039]), .ib(txi0[1617:1042]),
        .ov(txo0[0]), .oy(txo0[512:1]), .oflt(txo0[528:513]));
endmodule
