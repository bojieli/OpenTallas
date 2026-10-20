`timescale 1ns/1ps
// KV-ATTN2 2026-10-19 (r16: <= 16-flop kept copies; i_ctl[35] run also lands in 3 kept copies): face-landed SAFE attention tile view qkd_kvs_attn_fl (die binds it with OT_KV_FACE_LAND kvs_attn,
// same ports as qkd_kvs_attn_fl_ba5 / the bs kits).  Core = rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_r16.sv.
//   reset rst_n: NOT relayed in the RTL -- the kit lands it (ref_tile "reset_landing" balanced: 2 plain registered stages at
//     the face, kept final copies, <= 32 reset loads per copy via reset_relay_split / ot_rst_copies.tcl); assertion and
//     release are delayed by 2 ck edges (ba5's ot_rst_relay: async assert, release +3) -- a scheduled reset constant.
//   landed buses: fin +1, i_ctl +1 (ot_pin_land, one capture flop per bit at the face), unchanged from ba5;
//     i_ctl[34] (issue) lands in NIS kept copies (one pin, NIS face flops; each copy enables <= 16 captures), +1 as before.
// MUT: passed to the core (bench mutants only).
module qkd_kvs_attn_fl #(parameter integer MUT=0) (
    input wire ck, input wire rst_n,
    input wire ufs_WS, input wire ufs_WN, input wire ufs_ES, input wire ufs_EN,
    input wire ufh, input wire ufp0, input wire ufp1, input wire uff,
    input wire ufk_WS, input wire ufk_WN, input wire ufk_ES, input wire ufk_EN,
    input wire [521:0] d2d__srx, input wire [547:0] d2d__rx_payload, input wire d2d__att_tx_slot,
    input wire [3:0] d2d__att_tx_kind, input wire [4:0] d2d__att_tx_beat, input wire [533:0] fin,
    output wire attn__tx_valid, output wire [547:0] attn__tx_payload, output wire [30:0] pvst, output wire [64:0] pvfst,
    output wire [164:0] ahs, output wire [536:0] prg,
    output wire [47:0] acal_WS, output wire [47:0] acal_WN, output wire [47:0] acal_ES, output wire [47:0] acal_EN,
    output wire [7:0] arh, input wire [108:0] i_ctl
);
    localparam integer NIS = 24;
    wire [533:0] fl_land__fin;
    ot_pin_land #(.W(534), .LAT(1), .MUT(0)) u_fl_land_fin (.clk(ck), .d(fin), .q(fl_land__fin));
    wire [108:0] fl_land__i_ctl;
    ot_pin_land #(.W(109), .LAT(1), .MUT(0)) u_fl_land_i_ctl (.clk(ck), .d(i_ctl), .q(fl_land__i_ctl));
    (* keep = "true", dont_touch = "true" *) reg [NIS-1:0] fl_iss_c;
    always @(posedge ck) fl_iss_c <= {NIS{i_ctl[34]}};
    (* keep = "true", dont_touch = "true" *) reg [2:0] fl_run_c;
    always @(posedge ck) fl_run_c <= {3{i_ctl[35]}};
    qkd_kvs_attn_r16 #(.MUT(MUT), .NIS(NIS)) u_core (.ck(ck), .rst_n(rst_n), .ufs_WS(ufs_WS), .ufs_WN(ufs_WN), .ufs_ES(ufs_ES),
        .ufs_EN(ufs_EN), .ufh(ufh), .ufp0(ufp0), .ufp1(ufp1), .uff(uff), .ufk_WS(ufk_WS), .ufk_WN(ufk_WN), .ufk_ES(ufk_ES),
        .ufk_EN(ufk_EN), .d2d__srx(d2d__srx), .d2d__rx_payload(d2d__rx_payload), .d2d__att_tx_slot(d2d__att_tx_slot),
        .d2d__att_tx_kind(d2d__att_tx_kind), .d2d__att_tx_beat(d2d__att_tx_beat), .fin(fl_land__fin),
        .attn__tx_valid(attn__tx_valid), .attn__tx_payload(attn__tx_payload), .pvst(pvst), .pvfst(pvfst), .ahs(ahs), .prg(prg),
        .acal_WS(acal_WS), .acal_WN(acal_WN), .acal_ES(acal_ES), .acal_EN(acal_EN), .arh(arh), .i_ctl(fl_land__i_ctl),
        .issue_c(fl_iss_c), .run_c(fl_run_c));
endmodule
