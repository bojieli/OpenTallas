// Experimental companion: FAST/PP/BP default off; no adoption or clock claim.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM field of an experimental V4.1 FAST/PP runtime baseline (W17 die integration of W10's element).
//
//   ot_v41_retn_w17w10   one return-tree node (rtl/v41die/ot_v41_retn_w17w10.sv): W10 ot_v41_ret_node + RST wire stages.
//                 (exactly the per-level stage of ot_v41_rom_array).
//   ot_v41_field_w17w10  NP element pairs (2*NP macro leaves) + the return tree cut into R REGIONS of
//                 2*NP/R leaves; each region ends in its own W10 ot_v41_ret_root and row port (root
//                 decision 2026-09-30 (c): a banked multi-root return, one root per VM write port).
//                 A row's segments must all lie in one region (the die bank map places them so).
//                 BF16 lanes are on the pairs whose index is listed in BFSET (floor(i * NP / NBF)).
//
// The broadcast (cfg and x beats) enters already through the spine's BST wire register stages.
// Flat build: this module.  Runtime composition (rtl/test/v41_runtime): the same ot_v41_pair_w17w10,
// ot_v41_retn_w17w10 and ot_v41_ret_root compiled once each and wired by the host exactly as here.
// ---------------------------------------------------------------------------
module ot_v41_field_w17w10 #(
    parameter integer NP = 8,           // element pairs (power of two)
    parameter integer R = 2,            // return regions / roots (power of two, <= 2*NP / 2)
    parameter integer NBF = 2,          // pairs with BF16 lanes
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XFQ = 4,
    parameter integer XFB = 8,
    parameter integer LV = 5,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer BYPASS = 1,
    parameter integer RST = 1,
    parameter integer RD = 64,
    parameter integer ROOTD = 128,
    parameter integer FIX_SECOND_ROW_INDEX = 0,
    parameter integer WAKE_REG = 0,
    parameter integer GRADUAL_RNE = 0,
    parameter integer PHW = 6
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_go,
    input  wire [PHW-1:0] cfg_ph,
    input  wire [2:0]   cfg_np,
    input  wire         go,
    input  wire         go_bf,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    input  wire [2:0]   xb_pos,
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
    output wire [R-1:0]    r_v,
    output wire [16*R-1:0] r_row,
    output wire [3*R-1:0]  r_pos,
    output wire [32*R-1:0] r_fp32,
    output wire [16*R-1:0] r_bf16,
    output wire [R-1:0]    r_e,
    output wire         busy,
    output wire         fault
);
    localparam integer NL = 2 * NP;               // leaves (macros)
    localparam integer L = $clog2(NL);
    localparam integer LR = $clog2(R);
    localparam integer LS = L - LR;               // levels inside a region
    function automatic is_bf(input integer p);
        integer i;
        begin
            is_bf = 1'b0;
            for (i = 0; i < NBF; i = i + 1) if ((i * NP) / NBF == p) is_bf = 1'b1;
        end
    endfunction
    wire        nv [0:LS][0:NL-1];
    wire [31:0] nt [0:LS][0:NL-1];
    wire [31:0] nd [0:LS][0:NL-1];
    wire        ne [0:LS][0:NL-1];
    wire [NP-1:0] p_busy, p_fault;
    wire [NL-1:0] n_fault;
    genvar g, l;
    generate for (g = 0; g < NP; g = g + 1) begin : g_p
        wire [1:0] pv, perr;
        wire [63:0] pval;
        wire [31:0] prow;
        wire [9:0] pseg, pnseg;
        wire [5:0] ppos;
        ot_v41_pair_w17w10 #(.NSEG(NSEG), .NCH(NCH), .XF(is_bf(g) ? XFB : XFQ), .LV(LV), .BF16(is_bf(g) ? 1 : 0),
                      .FAST(FAST), .PP(PP), .BP(BP), .MTP(MTP), .EARLY(EARLY), .FIX_SECOND_ROW_INDEX(FIX_SECOND_ROW_INDEX), .WAKE_REG(WAKE_REG), .GRADUAL_RNE(GRADUAL_RNE), .PHW(PHW), .INSTANCE($sformatf("e%0d", g))) u_p (
            .clk(clk), .rst_n(rst_n), .cfg_go(cfg_go), .cfg_ph(cfg_ph), .cfg_np(cfg_np), .go(go), .go_bf(go_bf),
            .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1),
            .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv),
            .xb_u(xb_u), .xb_d(xb_d), .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg),
            .perr(perr), .ppos(ppos), .busy(p_busy[g]), .fault(p_fault[g]), .quiet());
        genvar m;
        for (m = 0; m < 2; m = m + 1) begin : g_m
            assign nv[0][2*g+m] = pv[m];
            assign nt[0][2*g+m] = {ppos[3*m +: 3], prow[16*m +: 16], pseg[5*m +: 5], 3'd0, pnseg[5*m +: 5]};
            assign nd[0][2*g+m] = pval[32*m +: 32];
            assign ne[0][2*g+m] = perr[m];
        end
    end endgenerate
    generate for (l = 0; l < LS; l = l + 1) begin : g_lv
        for (g = 0; g < (NL >> (l + 1)); g = g + 1) begin : g_n
            ot_v41_retn_w17w10 #(.RD(RD), .RST(RST), .BYPASS(BYPASS)) u_n (.clk(clk), .rst_n(rst_n),
                .a_v(nv[l][2*g]), .a_t(nt[l][2*g]), .a_d(nd[l][2*g]), .a_e(ne[l][2*g]),
                .b_v(nv[l][2*g+1]), .b_t(nt[l][2*g+1]), .b_d(nd[l][2*g+1]), .b_e(ne[l][2*g+1]),
                .o_v(nv[l+1][g]), .o_t(nt[l+1][g]), .o_d(nd[l+1][g]), .o_e(ne[l+1][g]),
                .fault(n_fault[NL - (NL >> l) + g]), .quiet());     // level l starts after NL - NL/2^l nodes
        end
    end endgenerate
    wire [R-1:0] rf;
    generate for (g = 0; g < R; g = g + 1) begin : g_r
        ot_v41_ret_root #(.D(ROOTD), .QD(ROOTD)) u_root (.clk(clk), .rst_n(rst_n), .i_v(nv[LS][g]), .i_t(nt[LS][g]),
            .i_d(nd[LS][g]), .i_e(ne[LS][g]), .r_v(r_v[g]), .r_row(r_row[16*g +: 16]), .r_pos(r_pos[3*g +: 3]),
            .r_fp32(r_fp32[32*g +: 32]), .r_bf16(r_bf16[16*g +: 16]), .r_e(r_e[g]), .fault(rf[g]));
    end endgenerate
    assign n_fault[NL-1] = 1'b0;
    assign busy = |p_busy;
    assign fault = (|p_fault) | (|n_fault) | (|rf);
endmodule
