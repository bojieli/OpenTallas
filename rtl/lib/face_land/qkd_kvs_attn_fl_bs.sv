`timescale 1ns/1ps
// KV-ATTN 10-19: face-landed SAFE attention tile view qkd_kvs_attn_fl (die binds it with OT_KV_FACE_LAND kvs_attn).
// Core = rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_safe_pr.v: the safe-control native source 6326ff81a (fanout <=24,
// reset relay + 2-stage landing, fin +1 / i_ctl +1 face landing of fl_ba5 already inside) with every public input pin
// landing first in a flop D pin (tools/qwen_kv_die/attn_pinreg_1019/pinreg.py: zero added edges).  Ports = fl_ba5.
module qkd_kvs_attn_fl (
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
    qkd_kvs_attn_safe_pr u_core (.ck(ck), .rst_n(rst_n), .ufs_WS(ufs_WS), .ufs_WN(ufs_WN), .ufs_ES(ufs_ES), .ufs_EN(ufs_EN),
        .ufh(ufh), .ufp0(ufp0), .ufp1(ufp1), .uff(uff), .ufk_WS(ufk_WS), .ufk_WN(ufk_WN), .ufk_ES(ufk_ES), .ufk_EN(ufk_EN),
        .d2d__srx(d2d__srx), .d2d__rx_payload(d2d__rx_payload), .d2d__att_tx_slot(d2d__att_tx_slot),
        .d2d__att_tx_kind(d2d__att_tx_kind), .d2d__att_tx_beat(d2d__att_tx_beat), .fin(fin),
        .attn__tx_valid(attn__tx_valid), .attn__tx_payload(attn__tx_payload), .pvst(pvst), .pvfst(pvfst), .ahs(ahs),
        .prg(prg), .acal_WS(acal_WS), .acal_WN(acal_WN), .acal_ES(acal_ES), .acal_EN(acal_EN), .arh(arh), .i_ctl(i_ctl));
endmodule
