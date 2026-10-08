`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// qwen-lane-band 2026-10-08: the spine lanes (ot_qwen_spine_lane = ot_qwen_me_sptree_w12 GT 6,144, SMIN = TCUT = 7,
// TREE_LAT 7: levels 8..12 over 48 level-7 positions, x 16 lanes) cut by BAND for the r21m die
// (tools/qwen_rom_fulldie_b3r2.py, recipe r21m):
//
//   qfd_sp_band_lanes x 6  ot_qfd_band_lanes: the band's 8 level-7 positions (global 8b .. 8b+7) x NL lanes; tree
//                          levels 8, 9, 10 inside the band (4, 2, 1 FP32 adders a lane, the lane's pairing:
//                          position p of level lv adds positions 2p, 2p+1 of level lv-1, else holds p); the band word
//                          (level-10 position 0, NL x 32 b + valid) leaves through a pin station to the tree top; the
//                          band's 8 result-position words (ty) leave through a pin station to the band's slab.
//   (tree top) x 1         ot_qfd_band_upper: levels 11 and 12 over the 6 band words (3 + 1 adders a lane, the lane's
//                          pairing: (b0,b1) (b2,b3) (b4,b5), then (L11[0], L11[1])), the result words of splits 11 / 12
//                          (3 positions) back to band 0 through a pin station.
//
// RESULT FRAME (band-local).  The band blocks never exchange words, so an op's result group g sits in the band that
// reduced it: at split s <= 10 band b's slot k holds global group g = b * 2^(10-s) + k (k < 2^(10-s)); at s = 11 / 12
// band 0 slot k holds g = k (k < 6,144 >> s, the tree top's words); s = 13 has no result group (GT >> 13 = 0, as the
// lane).  At s = 7 the frame is the lane's (g = 8b + k).  Every in-range group's word is bit-identical to the lane's
// y[g] (same adders, same operand pairs, same order: tb_qfd_band_lanes); out-of-range slots carry don't-care words,
// exactly as the lane's out-of-range positions (the port groups mask them: g >= GT >> split).  The result-port groups
// that receive ty (the band slab's port groups, r21m: 8 per band) must index their row / address / argmax row by this
// g (OPEN in the slab element RTL; the argmax compare is a total order on (key, row), so the port order is free).
//
// Contract: sel / tv per level are the lane's (sel_e[lv] = split >= lv when level lv's sums emerge, one cycle early;
// tv_e[lv] the adders' valid), i.e. generated from the op's split (monotone over levels for a valid op), as
// ot_qwen_me_spctl_w12 and ot_qwen_spine_lane_credit do.  Arbitrary non-monotone sel patterns are not reproduced.
//
// Timing (edges after the band's tw is presented; the lane's y is at 41):
//   tw pin flop 1, L8 9, L9 17, L10 25, pw station 26, [LNK relays], tree-top pin flop 27+LNK, L11 35+LNK, L12 43+LNK,
//   tree-top station 44+LNK, [LNK relays], band pin flop 45+2LNK, ty station 46+2LNK.  The band's own words wait in a
//   ring delay of 20+2LNK (the lane's level-11/12 holds plus the round trip), so ty is the lane's y + 5 + 2 LNK edges
//   (cost: +5 + 2 LNK edges per ME op result, recorded, not priced).  The tree top's level-11/12 select / valid are the
//   lane-timed c taps delayed DLY = 2 + LNK (+ any relay stages on the c link, set at integration).
// Link protocol: both ends are fixed-latency pipelines that never stall, so the links carry VALID with the words and
// no credits (a credit counter would be a constant).  Each receiver checks the arriving valid against its own expected
// valid (lockstep check) and raises fault on a mismatch.
// Every block input lands in a flop at the pin, every output leaves a station flop (no logic between pin and flop).
// MUT = 1 (band): level 9 pairs (0,2)(1,3) instead of (0,1)(2,3); MUT = 2 (upper): level 11 pairs (b0,b3)(b1,b4)(b2,b5).
// ---------------------------------------------------------------------------------------------------------------------

// NLV tree levels over GI positions of one lane (ot_qwen_me_sptree_w12 g_lvl with HOLD_TO = GI): level j (1..NLV)
// position p adds positions 2p, 2p+1 of level j-1 when p < GI >> j and sel, else holds p for TA edges; then lq.
module ot_qfd_bt_levels #(
    parameter integer GI = 8,
    parameter integer NLV = 3,
    parameter integer TREE_LAT = 7,
    parameter integer MUTLV = 0          // > 0: level MUTLV pairs (p, p + R0) instead of (2p, 2p+1) (negative mutant)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [GI*32-1:0]  l0,          // level 0 words (already in flops)
    input  wire [NLV-1:0]    sel_r,       // per level, registered (bit j-1 = level j)
    input  wire [NLV-1:0]    tv_r,
    output wire [GI*32-1:0]  lo,          // level NLV words (lq flops)
    output wire              pf           // OR of this lane's adder faults (combinational from the adders)
);
    localparam integer TA = TREE_LAT;
    wire [(NLV+1)*GI*32-1:0] lvf;
    wire [NLV:1] lf;
    assign lvf[0 +: GI*32] = l0;
    genvar j, p;
    generate for (j = 1; j <= NLV; j = j + 1) begin : g_lvl
        localparam integer R0 = GI >> j;
        reg  [GI*32-1:0] lq;
        wire [GI*32-1:0] held;
        wire [(R0 > 0 ? R0 : 1)-1:0] pfj;
        ot_qwen_me_rdelay_w12 #(.W(GI*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_n),
            .d(lvf[(j-1)*GI*32 +: GI*32]), .q(held));
        if (R0 == 0) begin : g_nopf
            assign pfj = 1'b0;
        end
        for (p = 0; p < R0; p = p + 1) begin : g_add
            localparam integer IA = (MUTLV == j) ? p : 2 * p;
            localparam integer IB = (MUTLV == j) ? p + R0 : 2 * p + 1;
            wire [31:0] s_out;
            ot_qwen_w12_tadd #(.LAT(TREE_LAT)) u_add (clk, rst_n, tv_r[j-1],
                lvf[(j-1)*GI*32 + 32*IA +: 32], lvf[(j-1)*GI*32 + 32*IB +: 32], s_out, pfj[p]);
            always @(posedge clk) lq[32*p +: 32] <= sel_r[j-1] ? s_out : held[32*p +: 32];
        end
        always @(posedge clk) lq[GI*32-1 : R0*32] <= held[GI*32-1 : R0*32];
        assign lvf[j*GI*32 +: GI*32] = lq;
        assign lf[j] = |pfj;
    end endgenerate
    assign lo = lvf[NLV*GI*32 +: GI*32];
    assign pf = |lf;
endmodule

// One band of NL lanes: levels 8..10 of the band's 8 positions; band word to the tree top; result words to the slab.
// Word layout (as ot_qwen_me_spport_w12 lv_in): word (position k, lane l) at [32*(k*NL + l) +: 32].
module ot_qfd_band_lanes #(
    parameter integer NL = 16,
    parameter integer LNK = 0,           // relay stages on each of the band -> tree top and tree top -> band links
    parameter integer TREE_LAT = 7,
    parameter integer MUT = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               b0,                // strap: 1 on band 0 (takes the tree top's split-11/12 words)
    input  wire [8*NL*32-1:0] tw,                // the band's level-7 words (from the slab)
    input  wire [13:0]        sel_e,             // lane-timed per-level select / valid ([$clog2(6144):0])
    input  wire [13:0]        tv_e,
    input  wire [3*NL*32-1:0] tt_ty,             // tree top: split-11/12 words (positions 0..2), band 0 only
    input  wire               tt_use,            // tree top: the op's split >= 11 (take tt_ty for slots 0..2)
    input  wire               tt_v,              // tree top: the op's level-11 valid (lockstep check)
    output wire [NL*32-1:0]   pw,                // band word (level 10 position 0) to the tree top
    output wire               pw_v,              // its valid (the op's level-11 adder valid)
    output wire [8*NL*32-1:0] ty,                // the band's 8 result-slot words (band-local frame)
    output wire               fault
);
    localparam integer TA = TREE_LAT;
    localparam integer DU = 2 * (TA + 1) + 4 + 2 * LNK;     // 20 + 2 LNK at TREE_LAT 7
    // -- pin flops ------------------------------------------------------------------------------------------------
    // (the per-level selects, b0 and tt_use land in one flop copy per lane: each copy drives one lane's <= 128 mux
    //  bits instead of NL x 128)
    (* keep *) reg [8*NL*32-1:0] tin_q;
    (* keep *) reg [3*NL*32-1:0] tt_q;
    (* keep *) reg [NL-1:0] b0_q, use_q;
    reg tv11_r, tt_v_q;
    always @(posedge clk) begin tin_q <= tw; tt_q <= tt_ty; b0_q <= {NL{b0}}; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin tv11_r <= 1'b0; use_q <= {NL{1'b0}}; tt_v_q <= 1'b0; end
        else begin tv11_r <= tv_e[11]; use_q <= {NL{tt_use}}; tt_v_q <= tt_v; end
    // -- levels 8..10 per lane --------------------------------------------------------------------------------------
    wire [8*NL*32-1:0] l10;
    wire [NL-1:0] lpf;
    genvar l, k;
    generate for (l = 0; l < NL; l = l + 1) begin : g_lane
        wire [8*32-1:0] li, lo;
        (* keep *) reg [2:0] sel_r, tv_r;      // levels 10..8, this lane's copy
        always @(posedge clk) sel_r <= sel_e[10:8];
        always @(posedge clk or negedge rst_n) if (!rst_n) tv_r <= 3'd0; else tv_r <= tv_e[10:8];
        for (k = 0; k < 8; k = k + 1) begin : g_k
            assign li[32*k +: 32] = tin_q[32*(k*NL + l) +: 32];
            assign l10[32*(k*NL + l) +: 32] = lo[32*k +: 32];
        end
        ot_qfd_bt_levels #(.GI(8), .NLV(3), .TREE_LAT(TREE_LAT), .MUTLV(MUT == 1 ? 2 : 0)) u_lv (
            .clk(clk), .rst_n(rst_n), .l0(li), .sel_r(sel_r), .tv_r(tv_r), .lo(lo), .pf(lpf[l]));
    end endgenerate
    // -- band word: level 10 position 0 + the op's level-11 valid, through the pin station --------------------------
    (* keep *) reg [NL*32-1:0] pw_s;
    (* keep *) reg pw_vs;
    always @(posedge clk) pw_s <= l10[0 +: NL*32];
    always @(posedge clk or negedge rst_n) if (!rst_n) pw_vs <= 1'b0; else pw_vs <= tv11_r;
    assign pw = pw_s; assign pw_v = pw_vs;
    // -- the band's own words wait for the round trip (the lane's level-11/12 holds + 4 + 2 LNK) ---------------------
    wire [8*NL*32-1:0] lw;
    ot_qwen_me_rdelay_w12 #(.W(8*NL*32), .D(DU)) u_wait (.clk(clk), .rst_n(rst_n), .d(l10), .q(lw));
    wire vexp;          // the op's level-11 valid, aligned with tt_v_q (lockstep check)
    ot_hdc_delay #(.W(1), .D(DU), .RESET(1)) u_vexp (.clk(clk), .rst_n(rst_n), .d(tv11_r), .q(vexp));
    // -- result slots: band 0 slots 0..2 take the tree top's words at split >= 11 ----------------------------------
    (* keep *) reg [8*NL*32-1:0] ty_s;
    integer q, ll;
    always @(posedge clk) begin
        ty_s[3*NL*32 +: 5*NL*32] <= lw[3*NL*32 +: 5*NL*32];
        for (q = 0; q < 3; q = q + 1)
            for (ll = 0; ll < NL; ll = ll + 1)
                ty_s[32*(q*NL + ll) +: 32] <= (b0_q[ll] && use_q[ll]) ? tt_q[32*(q*NL + ll) +: 32] : lw[32*(q*NL + ll) +: 32];
    end
    assign ty = ty_s;
    // -- fault: adder faults, a tree-top valid out of lockstep (band 0) ---------------------------------------------
    reg f_q;
    (* keep *) reg f_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin f_q <= 1'b0; f_s <= 1'b0; end
        else begin f_q <= (|lpf) || (b0_q[0] && (tt_v_q != vexp)); f_s <= f_q; end
    assign fault = f_s;
endmodule

// The tree top's part of the lanes: levels 11 and 12 over the NB = 6 band words, NL lanes.
module ot_qfd_band_upper #(
    parameter integer NL = 16,
    parameter integer NB = 6,
    parameter integer LNK = 0,
    parameter integer DLY = 2 + LNK,     // c-tap delay: the band word's pw station + this pin flop + the link relays
    parameter integer TREE_LAT = 7,
    parameter integer MUT = 0
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire [NB*NL*32-1:0] pw,              // band b's word at [32*(b*NL + l)]
    input  wire [NB-1:0]       pw_v,
    input  wire [NB-1:0]       lf,              // the bands' faults
    input  wire [13:0]         sel_e,           // lane-timed per-level select / valid (as the bands get them)
    input  wire [13:0]         tv_e,
    output wire [3*NL*32-1:0]  tt_ty,           // positions 0..2 of level 12, word (k, l) at [32*(k*NL + l)]
    output wire                tt_use,
    output wire                tt_v,
    output wire                fault
);
    localparam integer TA = TREE_LAT;
    // -- pin flops --------------------------------------------------------------------------------------------------
    (* keep *) reg [NB*NL*32-1:0] pw_q;
    reg [NB-1:0] pv_q, lf_q;
    always @(posedge clk) pw_q <= pw;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin pv_q <= 0; lf_q <= 0; end else begin pv_q <= pw_v; lf_q <= lf; end
    // the lane's sel_r / tv_r (sel_e / tv_e registered) DLY edges later: DLY delay stages, then one flop copy per lane
    wire [1:0] sel_d, tv_d;
    ot_hdc_delay #(.W(2), .D(DLY)) u_sd (.clk(clk), .rst_n(rst_n), .d(sel_e[12:11]), .q(sel_d));
    ot_hdc_delay #(.W(2), .D(DLY), .RESET(1)) u_td (.clk(clk), .rst_n(rst_n), .d(tv_e[12:11]), .q(tv_d));
    reg [1:0] sel_r, tv_r;   // the control copy (use / valid / lockstep)
    always @(posedge clk) sel_r <= sel_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) tv_r <= 2'b00; else tv_r <= tv_d;
    // -- levels 11, 12 per lane --------------------------------------------------------------------------------------
    wire [NL-1:0] lpf;
    wire [3*NL*32-1:0] y;
    genvar l, b;
    generate for (l = 0; l < NL; l = l + 1) begin : g_lane
        wire [NB*32-1:0] li, lo;
        (* keep *) reg [1:0] sl, tl;          // this lane's copy of sel_r / tv_r
        always @(posedge clk) sl <= sel_d;
        always @(posedge clk or negedge rst_n) if (!rst_n) tl <= 2'b00; else tl <= tv_d;
        for (b = 0; b < NB; b = b + 1) begin : g_b
            assign li[32*b +: 32] = pw_q[32*(b*NL + l) +: 32];
        end
        for (b = 0; b < 3; b = b + 1) begin : g_o
            assign y[32*(b*NL + l) +: 32] = lo[32*b +: 32];
        end
        ot_qfd_bt_levels #(.GI(NB), .NLV(2), .TREE_LAT(TREE_LAT), .MUTLV(MUT == 2 ? 1 : 0)) u_lv (
            .clk(clk), .rst_n(rst_n), .l0(li), .sel_r(sl), .tv_r(tl), .lo(lo), .pf(lpf[l]));
    end endgenerate
    // use = the op's level-11 select at its L11 capture, carried to the L12 output; v = its level-11 valid
    wire uv, vv;
    reg use11;          // captured on the L11 lq edge, from the select that edge uses
    always @(posedge clk or negedge rst_n) if (!rst_n) use11 <= 1'b0; else use11 <= sel_r[0];
    ot_hdc_delay #(.W(1), .D(TA + 1), .RESET(1)) u_use (.clk(clk), .rst_n(rst_n), .d(use11), .q(uv));
    ot_hdc_delay #(.W(1), .D(2 * (TA + 1)), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(tv_r[0]), .q(vv));
    // -- output station ---------------------------------------------------------------------------------------------
    (* keep *) reg [3*NL*32-1:0] ty_s;
    (* keep *) reg use_s, v_s;
    always @(posedge clk) ty_s <= y;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin use_s <= 1'b0; v_s <= 1'b0; end
        else begin use_s <= uv; v_s <= vv; end
    assign tt_ty = ty_s; assign tt_use = use_s; assign tt_v = v_s;
    // -- fault: adder faults, the bands' faults, a band word out of lockstep -----------------------------------------
    reg f_q;
    (* keep *) reg f_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin f_q <= 1'b0; f_s <= 1'b0; end
        else begin f_q <= (|lpf) || (|lf_q) || (pv_q != {NB{tv_r[0]}}); f_s <= f_q; end
    assign fault = f_s;
endmodule
