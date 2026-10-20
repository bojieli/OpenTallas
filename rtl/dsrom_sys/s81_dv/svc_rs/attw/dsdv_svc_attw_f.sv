`timescale 1ns/1ps
// SVC4 (LEAD2-S81, 10-19): FLAT attw parent for tools/landed_parent/lp.py (wires only: child instances + wires).
//   u_c        dsdv_svc_rs_attw #(TEXT 1): the attention share (control, landing / p store / staging SRAMs, engine
//              control, lane trees, merges) with the engine's 4 tiles exported on tx_i<t> / tx_o<t>;
//   u_t0..u_t3 ot_hdc_v41x_attn_tile_s at the S81 engine parameters (H16 TD32 NBANK5 BW3 PWORDS2 FPL4 FML6 F12; with
//              -DOT_ATTN_HGRP_HARD each = 4 hard ot_hdc_v41x_attn_hgrp_s81 head groups, kit s81svc_attn_hgrp).
// The attw outline is ~2.5 x 2.0 mm (16 hard groups), so per the landed-regions standard it is a landed parent: one clock
// region per engine tile (t0..t3) + the core region c; every tile bundle crossing is LANDED (ring + read, D 4, E 2,
// +3 edges each way) -> the engine re-schedule TLX = 6 (tags / lane trees wait 6 more edges).  This flat module with
// TLX = 0 is the unlanded attw (cycle-equal to dsdv_svc_rs_attw at the production engine); lp.py's lockstep reference is
// it with TLX = TXD = 6 (6 register stages on the returning bundles), the landed build uses TLX 6, TXD 0.
// tx_i bit map (lsb first): ld_v 0, ld_mode 1, ld_bank 4:2, ld_grp 12:5, ld_w 1036:13, ld_w2v 1037, iv 1038,
//   ibank 1041:1039, ib 1617:1042;  tx_o: ov 0, oy 512:1, oflt 528:513  (ot_hdc_v41x_attn_s TEXT 1).
module dsdv_svc_attw_f #(parameter integer AMUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                         parameter integer SRAM_MACRO = 0, parameter integer ROOT = 0, parameter integer PMEM = 1,
                         parameter integer TLX = 0, parameter integer TXD = 0) (
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
    output wire             fault
);
    wire [1617:0] txi0;
    wire [528:0]  txo0;
    wire [1617:0] txi1;
    wire [528:0]  txo1;
    wire [1617:0] txi2;
    wire [528:0]  txo2;
    wire [1617:0] txi3;
    wire [528:0]  txo3;
    dsdv_svc_rs_attw #(.MUT(AMUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .ROOT(ROOT), .PMEM(PMEM), .TEXT(1),
                       .TLX(TLX), .TXD(TXD)) u_c (
        .ck(ck), .rst(rst), .sid(sid), .cs(cs), .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data),
        .qr_tag(qr_tag), .qr_beat(qr_beat), .l_v(l_v), .l_d(l_d), .pv_ov(pv_ov), .pv_od(pv_od), .sm_st(sm_st),
        .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd), .go_o(go_o),
        .tjob_o(tjob_o), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(fault),
        .tx_i0(txi0), .tx_i1(txi1), .tx_i2(txi2), .tx_i3(txi3), .tx_o0(txo0), .tx_o1(txo1), .tx_o2(txo2), .tx_o3(txo3));
    ot_hdc_v41x_attn_tile_s #(.H(16), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1)) u_t0 (
        .clk(ck), .rst_n(rst), .ld_v(txi0[0]), .ld_mode(txi0[1]), .ld_bank(txi0[4:2]), .ld_grp(txi0[12:5]),
        .ld_w(txi0[1036:13]), .ld_w2v(txi0[1037]), .iv(txi0[1038]), .ibank(txi0[1041:1039]), .ib(txi0[1617:1042]),
        .ov(txo0[0]), .oy(txo0[512:1]), .oflt(txo0[528:513]));
    ot_hdc_v41x_attn_tile_s #(.H(16), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1)) u_t1 (
        .clk(ck), .rst_n(rst), .ld_v(txi1[0]), .ld_mode(txi1[1]), .ld_bank(txi1[4:2]), .ld_grp(txi1[12:5]),
        .ld_w(txi1[1036:13]), .ld_w2v(txi1[1037]), .iv(txi1[1038]), .ibank(txi1[1041:1039]), .ib(txi1[1617:1042]),
        .ov(txo1[0]), .oy(txo1[512:1]), .oflt(txo1[528:513]));
    ot_hdc_v41x_attn_tile_s #(.H(16), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1)) u_t2 (
        .clk(ck), .rst_n(rst), .ld_v(txi2[0]), .ld_mode(txi2[1]), .ld_bank(txi2[4:2]), .ld_grp(txi2[12:5]),
        .ld_w(txi2[1036:13]), .ld_w2v(txi2[1037]), .iv(txi2[1038]), .ibank(txi2[1041:1039]), .ib(txi2[1617:1042]),
        .ov(txo2[0]), .oy(txo2[512:1]), .oflt(txo2[528:513]));
    ot_hdc_v41x_attn_tile_s #(.H(16), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1)) u_t3 (
        .clk(ck), .rst_n(rst), .ld_v(txi3[0]), .ld_mode(txi3[1]), .ld_bank(txi3[4:2]), .ld_grp(txi3[12:5]),
        .ld_w(txi3[1036:13]), .ld_w2v(txi3[1037]), .iv(txi3[1038]), .ibank(txi3[1041:1039]), .ib(txi3[1617:1042]),
        .ov(txo3[0]), .oy(txo3[512:1]), .oflt(txo3[528:513]));
endmodule
