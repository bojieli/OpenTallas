`timescale 1ns/1ps
// Qwen3-8B ROM TP8 die, slot sp_band_lanes_{0,1,2} (master qfd_sp_band_lanes) as a LEAF PARTITION
// (el1013-qwen-small-masters r3b, 2026-10-13).
// The flat master ot_qfd_band_lanes NL 16 is 128,608 flops + 64 SRAM delay-line macros on one clock root (37 flat
// routes: hold repair flooded with 224k-227k endpoints, setup -2,294 ps post-CTS); even the 4-lane quarter is 32,080
// flops (yosys bit level).  The block is lane-sliced by construction: every lane has its own pin flops, level adders,
// holds, round-trip wait and result stations, and the only shared signals are per-lane copies of the selects, the
// tree-top valid and the fault OR.  The hardened unit is therefore ONE LANE:
//   qfd_bl_lane       ot_qfd_band_lanes #(NL 1, LG 12 (TP8), RDMEM 1, BANR 1, LNKS 1): 8,038 flops + 4 SRAM
//                     128 x 256 macros, one clock root; every input lands in a pin flop, every output leaves a
//                     station flop.  The number of relay stages the die puts on the band <-> tree-top links is the
//                     strap lnk (static): one hardened view serves any die placement.
//   qfd_sp_band_lanes the slot = 16 x qfd_bl_lane, WIRES ONLY (no flop; the fault is the OR of the 16 registered
//                     lane faults: the only gate).  Slot bundles (contract v4 names):
//                       tw[4095:0] / ty[4095:0]  word (k, l) at [32 (16 k + l)] (the flat order)
//                       c[25:0]   = {tv_e[12:0], sel_e[12:0]}      (tt_ctlm lc<b>: t_sel_e low, t_tv_e high)
//                       tt[1537:0] = {tt_v, tt_use, tt_ty[1535:0]}  (band 0 only; else tied 0)
//                       pw[512:0] = {pw_v, pw[511:0]}
//                       f, b0 (strap), lnk[5:0] (strap), ck, rst_n
// OT_QFD_BL_MUT (bench only): lane 5's leaf pairs level 9 as (0,2)(1,3) (the band's MUT 1).
module qfd_bl_lane (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         b0,
    input  wire [5:0]   lnk,
    input  wire [255:0] tw,          // the lane's 8 level-7 words, position k at [32 k]
    input  wire [25:0]  c,           // {tv_e[12:0], sel_e[12:0]}
    input  wire [97:0]  tt,          // {tt_v, tt_use, tt_ty[95:0]}
    output wire [32:0]  pw,          // {pw_v, pw[31:0]}
    output wire [255:0] ty,
    output wire         f
);
`ifdef OT_QFD_BL_LANE_MUT
    localparam integer M = 1;
`else
    localparam integer M = 0;
`endif
    ot_qfd_band_lanes #(.NL(1), .LNK(0), .TREE_LAT(7), .MUT(M), .TCUT(7), .LG(12), .RDMEM(1), .BANR(1), .LNKS(1)) u_l (
        .clk(ck), .rst_n(rst_n), .lnk(lnk), .b0(b0), .tw(tw), .sel_e(c[12:0]), .tv_e(c[25:13]),
        .tt_ty(tt[95:0]), .tt_use(tt[96]), .tt_v(tt[97]), .pw(pw[31:0]), .pw_v(pw[32]), .ty(ty), .fault(f));
endmodule

`ifdef OT_QFD_BL_MUT
// bench-only copy of the leaf with the level-9 pairing mutant (one lane of the slot)
module qfd_bl_lane_mut (
    input  wire ck, input wire rst_n, input wire b0, input wire [5:0] lnk, input wire [255:0] tw, input wire [25:0] c,
    input  wire [97:0] tt, output wire [32:0] pw, output wire [255:0] ty, output wire f
);
    ot_qfd_band_lanes #(.NL(1), .LNK(0), .TREE_LAT(7), .MUT(1), .TCUT(7), .LG(12), .RDMEM(1), .BANR(1), .LNKS(1)) u_l (
        .clk(ck), .rst_n(rst_n), .lnk(lnk), .b0(b0), .tw(tw), .sel_e(c[12:0]), .tv_e(c[25:13]),
        .tt_ty(tt[95:0]), .tt_use(tt[96]), .tt_v(tt[97]), .pw(pw[31:0]), .pw_v(pw[32]), .ty(ty), .fault(f));
endmodule
`endif

module qfd_sp_band_lanes (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          b0,
    input  wire [5:0]    lnk,
    input  wire [4095:0] tw,
    input  wire [25:0]   c,
    input  wire [1537:0] tt,
    output wire [512:0]  pw,
    output wire [4095:0] ty,
    output wire          f
);
    wire [15:0] lf, lpv;
    genvar l, k;
    generate for (l = 0; l < 16; l = l + 1) begin : g_lane
        wire [255:0] ltw, lty;
        wire [97:0]  ltt;
        wire [32:0]  lpw;
        for (k = 0; k < 8; k = k + 1) begin : g_k
            assign ltw[32*k +: 32] = tw[32*(16*k + l) +: 32];
            assign ty[32*(16*k + l) +: 32] = lty[32*k +: 32];
        end
        for (k = 0; k < 3; k = k + 1) begin : g_t
            assign ltt[32*k +: 32] = tt[32*(16*k + l) +: 32];
        end
        assign ltt[97:96] = tt[1537:1536];
        assign pw[32*l +: 32] = lpw[31:0];
        assign lpv[l] = lpw[32];
`ifdef OT_QFD_BL_MUT
        if (l == 5) begin : g_mut
            qfd_bl_lane_mut u_lane (.ck(ck), .rst_n(rst_n), .b0(b0), .lnk(lnk), .tw(ltw), .c(c), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
        end else begin : g_ok
            qfd_bl_lane u_lane (.ck(ck), .rst_n(rst_n), .b0(b0), .lnk(lnk), .tw(ltw), .c(c), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
        end
`else
        qfd_bl_lane u_lane (.ck(ck), .rst_n(rst_n), .b0(b0), .lnk(lnk), .tw(ltw), .c(c), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
`endif
    end endgenerate
    assign pw[512] = lpv[0];        // every lane carries the same valid copy
    assign f = |lf;
endmodule
