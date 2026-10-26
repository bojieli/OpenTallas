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
`ifndef OT_QFD_BL_HARD
// Native parent kit supplies this already-CLOSED leaf as a hard child.
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
    // q14 r8 (2026-10-14): reset pin register.  Native pin audit of the CLOSED leaf qfd_bl_lane_ce (TT R 414.2):
    // rst_n capture 303.6 ps > 190 (the die reset fanned out to every async-reset flop of the lane); the reset now lands
    // in ONE flop at the pin (async assert, registered deassert one edge later) and the lane resets from it.
    (* keep *) reg rs_q;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs_q <= 1'b0; else rs_q <= 1'b1;
    ot_qfd_band_lanes #(.NL(1), .LNK(0), .TREE_LAT(7), .MUT(M), .TCUT(7), .LG(12), .RDMEM(1), .BANR(1), .LNKS(1)) u_l (
        .clk(ck), .rst_n(rs_q), .lnk(lnk), .b0(b0), .tw(tw), .sel_e(c[12:0]), .tv_e(c[25:13]),
        .tt_ty(tt[95:0]), .tt_use(tt[96]), .tt_v(tt[97]), .pw(pw[31:0]), .pw_v(pw[32]), .ty(ty), .fault(f));
endmodule

`ifdef OT_QFD_BL_MUT
// bench-only copy of the leaf with the level-9 pairing mutant (one lane of the slot)
module qfd_bl_lane_mut (
    input  wire ck, input wire rst_n, input wire b0, input wire [5:0] lnk, input wire [255:0] tw, input wire [25:0] c,
    input  wire [97:0] tt, output wire [32:0] pw, output wire [255:0] ty, output wire f
);
    (* keep *) reg rs_q;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs_q <= 1'b0; else rs_q <= 1'b1;
    ot_qfd_band_lanes #(.NL(1), .LNK(0), .TREE_LAT(7), .MUT(1), .TCUT(7), .LG(12), .RDMEM(1), .BANR(1), .LNKS(1)) u_l (
        .clk(ck), .rst_n(rs_q), .lnk(lnk), .b0(b0), .tw(tw), .sel_e(c[12:0]), .tv_e(c[25:13]),
        .tt_ty(tt[95:0]), .tt_use(tt[96]), .tt_v(tt[97]), .pw(pw[31:0]), .pw_v(pw[32]), .ty(ty), .fault(f));
endmodule
`endif

`endif // OT_QFD_BL_HARD: keep the actual parent body in both modes

module qfd_sp_band_lanes (
    input  wire          ck,
    input wire ck_l0,
    input wire ck_l1,
    input wire ck_l2,
    input wire ck_l3,
    input wire ck_l4,
    input wire ck_l5,
    input wire ck_l6,
    input wire ck_l7,
    input wire ck_l8,
    input wire ck_l9,
    input wire ck_l10,
    input wire ck_l11,
    input wire ck_l12,
    input wire ck_l13,
    input wire ck_l14,
    input wire ck_l15,

    input  wire          rst_n,
    input  wire          b0,
    input  wire [5:0]    lnk,
    input  wire [4095:0] tw,
    input  wire [25:0]   c,
    input  wire [1537:0] tt,
    output wire [512:0]  pw,
    // Direct upper-tree leaves: one independent registered quarter word and
    // fault per leaf, so the die has point-to-point fixed-cycle links.
    output wire [128:0] pw_l0, pw_l1, pw_l2, pw_l3,
    output wire [3:0] f_up,
    output wire [4095:0] ty,
    output wire          f
);
    (* keep *) reg reset_q,b0_q;
    (* keep *) reg [5:0] lnk_q;
    (* keep *) reg [4095:0] tw_q;
    (* keep *) reg [25:0] c_q;
    (* keep *) reg [1537:0] tt_q;
    always @(posedge ck) begin
        reset_q<=rst_n;b0_q<=b0;lnk_q<=lnk;
        tw_q<=tw;c_q<=c;tt_q<=tt;
    end
    // The parent contributes one output and one return-input edge to the
    // band/upper round trip: two edges, represented by one LNK unit.
    wire [5:0] leaf_lnk=lnk_q+6'd1;
    wire [512:0] pw_i;
    wire [4095:0] ty_i;
    (* keep *) reg [512:0] pw_q;
    (* keep *) reg [4095:0] ty_q;
    always @(posedge ck) begin
        pw_q[511:0]<=pw_i[511:0];pw_q[512]<=reset_q & pw_i[512];
        ty_q<=ty_i;
    end
    assign pw=pw_q;assign ty=ty_q;
    wire [15:0] leaf_ck = {ck_l15, ck_l14, ck_l13, ck_l12, ck_l11, ck_l10, ck_l9, ck_l8, ck_l7, ck_l6, ck_l5, ck_l4, ck_l3, ck_l2, ck_l1, ck_l0};
    wire [15:0] lf, lpv;
    genvar l, k;
    generate for (l = 0; l < 16; l = l + 1) begin : g_lane
        wire [255:0] ltw, lty;
        wire [97:0]  ltt;
        wire [32:0]  lpw;
        for (k = 0; k < 8; k = k + 1) begin : g_k
            assign ltw[32*k +: 32] = tw_q[32*(16*k + l) +: 32];
            assign ty_i[32*(16*k + l) +: 32] = lty[32*k +: 32];
        end
        for (k = 0; k < 3; k = k + 1) begin : g_t
            assign ltt[32*k +: 32] = tt_q[32*(16*k + l) +: 32];
        end
        assign ltt[97:96] = tt_q[1537:1536];
        assign pw_i[32*l +: 32] = lpw[31:0];
        assign lpv[l] = lpw[32];
`ifdef OT_QFD_BL_MUT
        if (l == 5) begin : g_mut
            qfd_bl_lane_mut u_lane (.ck(leaf_ck[l]), .rst_n(reset_q), .b0(b0_q), .lnk(leaf_lnk), .tw(ltw), .c(c_q), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
        end else begin : g_ok
            qfd_bl_lane u_lane (.ck(leaf_ck[l]), .rst_n(reset_q), .b0(b0_q), .lnk(leaf_lnk), .tw(ltw), .c(c_q), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
        end
`else
        qfd_bl_lane u_lane (.ck(leaf_ck[l]), .rst_n(reset_q), .b0(b0_q), .lnk(leaf_lnk), .tw(ltw), .c(c_q), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
`endif
    end endgenerate
    wire [3:0] quarter_pv, quarter_fault;
    ot_qfd_band_upper_faces u_upper_faces (.clk(ck),.reset_q(reset_q),.lnk(lnk_q),
        .lpv(lpv),.lf(lf),.quarter_pv(quarter_pv),.quarter_fault(quarter_fault));
    assign pw_l0={quarter_pv[0],pw_q[127:0]};
    assign pw_l1={quarter_pv[1],pw_q[255:128]};
    assign pw_l2={quarter_pv[2],pw_q[383:256]};
    assign pw_l3={quarter_pv[3],pw_q[511:384]};
    assign f_up=quarter_fault;
    assign pw_i[512] = lpv[0];        // every lane carries the same valid copy
    (* keep *) reg f_q;
    always @(posedge ck)
        if (!reset_q) f_q <= 1'b0;
        else f_q <= (&lnk_q) | |lf | (|(lpv ^ {16{lpv[0]}}));
    assign f = f_q;
endmodule

// Real registered quarter boundary for direct upper leaves. Data registers
// remain the existing pw_q stations; these status copies observe distinct
// hardened lane outputs, so they cannot collapse into one remote face pin.
module ot_qfd_band_upper_faces #(parameter integer MUT=0) (
    input wire clk,reset_q,input wire [5:0] lnk,
    input wire [15:0] lpv,lf,
    output reg [3:0] quarter_pv,quarter_fault
);
    genvar u;
    generate for(u=0;u<4;u=u+1) begin:g_upper_face
        always @(posedge clk) begin
            quarter_pv[u] <= reset_q & lpv[4*u];
            if(!reset_q) quarter_fault[u] <= 1'b0;
            else quarter_fault[u] <= (&lnk) |
                ((MUT==1 && u==3) ? 1'b0 : (|lf[4*u +: 4])) |
                (|(lpv ^ {16{lpv[0]}}));
        end
    end endgenerate
endmodule
