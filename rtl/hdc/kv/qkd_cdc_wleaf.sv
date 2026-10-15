`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qkd_cdc_wleaf: the die cell of the KV write-side CDC leaf (Qwen3-8B ROM TP8 contract v3, 128 instances; KV die
// tools/qwen_kv_die/kv_die.py BINDINGS['qkd_cdc_wleaf']).  A pure rename of ot_qwen_stream4_cdc_pc at the routed
// parameters (MARGIN 1, r2: LD 32 + WPIPE 1: every data input registered at its pin in its own domain, every output a flop; LCRED 6,
// SYNC 2, RSEL 1, RNG 10 = the closed qfd_cdc_eco_h1 structure), so the hardened view carries the slot's cell name and
// the real RTL port names.  Die bus -> ports (BINDINGS order): ho = {h_cred, h_wv, h_wsec, h_cv, h_csec, h_cdata,
// h_ctag, h_fault} E; hi = {h_lv, h_lsec, h_lrow, h_ldata, h_hand, h_wcon, h_av, h_atag} N; co = {l_v, l_sec, l_row,
// l_data, l_pop} W; wi = {w_v, w_sec, w_data, w_tag} S; wr = {w_room, wd_v, wd_tag} S; cf = c_fault S; clk N
// (contract clock_entry ck); hclk, c_arst_n, h_arst_n W.  No logic here.
// r2 2026-10-13 (clock rule: the r1 kit had 19,280 hclk sinks, measured TT insertion 442.7 ps): (1) landing depth LD
// 64 -> 32 = the controller's credit count (ot_qwen_hbm_stream4_* CRED 32, fault above it): every RD holds a credit
// and credits return from the synchronised read pointer the full flag uses, so occupancy never exceeds 32; the
// storage is 32 x 281 flops (hclk root ~10.4k sinks).  CONTRACT: controller CRED <= 32.  (2) WPIPE 1: h_wcon is a
// pin flop (h_cv / h_c* one HCLK edge later: h_cv = two edges after h_wcon), per-group kept selects; h_hand is a
// final 2:1 select.  See ot_qwen_stream4_cdc_pc WPIPE.
// ---------------------------------------------------------------------------
module qkd_cdc_wleaf #(parameter integer HANDPIPE = 0, parameter integer WCPIN = 0) (
    input  wire         clk,
    input  wire         c_arst_n,
    output wire         l_v,
    output wire [16:0]  l_sec,
    output wire [7:0]   l_row,
    output wire [255:0] l_data,
    input  wire         l_pop,
    input  wire         w_v,
    input  wire [23:0]  w_sec,
    input  wire [255:0] w_data,
    input  wire [8:0]   w_tag,
    output wire         w_room,
    output wire         wd_v,
    output wire [8:0]   wd_tag,
    output wire         c_fault,
    input  wire         hclk,
    input  wire         h_arst_n,
    input  wire         h_lv,
    input  wire [16:0]  h_lsec,
    input  wire [7:0]   h_lrow,
    input  wire [255:0] h_ldata,
    output wire [2:0]   h_cred,
    output wire         h_wv,
    output wire [23:0]  h_wsec,
    input  wire         h_hand,
    input  wire         h_wcon,
    output wire         h_cv,
    output wire [23:0]  h_csec,
    output wire [255:0] h_cdata,
    output wire [8:0]   h_ctag,
    input  wire         h_av,
    input  wire [8:0]   h_atag,
    output wire         h_fault
);
    // Optional native input capture: the controller's HOFF guard spans the added hand-off edge.
    (* keep *) reg hand_pin;
    always @(posedge hclk or negedge h_arst_n)
        if (!h_arst_n) hand_pin <= 1'b0; else hand_pin <= h_hand;
    wire hand_local = HANDPIPE != 0 ? hand_pin : h_hand;
    ot_qwen_stream4_cdc_pc #(.TAGW(9), .LD(32), .WB(16), .AD(64), .SYNC(2), .RSEL(1), .RNG(10), .MARGIN(1), .LCRED(6), .WPIPE(1), .WCE(WCPIN)) u_cdc (
        .clk(clk), .c_arst_n(c_arst_n), .l_v(l_v), .l_sec(l_sec), .l_row(l_row), .l_data(l_data), .l_pop(l_pop),
        .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(w_room), .wd_v(wd_v), .wd_tag(wd_tag),
        .c_fault(c_fault), .hclk(hclk), .h_arst_n(h_arst_n), .h_lv(h_lv), .h_lsec(h_lsec), .h_lrow(h_lrow),
        .h_ldata(h_ldata), .h_cred(h_cred), .h_wv(h_wv), .h_wsec(h_wsec), .h_hand(hand_local), .h_wcon(h_wcon),
        .h_cv(h_cv), .h_csec(h_csec), .h_cdata(h_cdata), .h_ctag(h_ctag), .h_av(h_av), .h_atag(h_atag), .h_fault(h_fault));
endmodule
