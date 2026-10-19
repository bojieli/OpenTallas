`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_att4_slice: one SM's KV-line-stationary NL-query attention datapath (HBM-NEXT-ATT4 2026-10-19, DS head dim
// 512).  The P = 1 slice (tb_hbm_sm_attn: kv_line -> attn_issue -> 4 x tcpv_col -> 4-leaf combine) with NL query lanes:
//   ONE KV converter (ot_hnx_att_kv_line, the union line stream from the SM's own stack, shared),
//   ONE issue (ot_hnx_att4_issue: lane masks, per-lane ordinals / flags / x stores),
//   per lane: 4 x ot_hnx_att_tcpv_col (the SM's 4 BF16 sub-rows: exact BF16 products, the circulating FP32 ring, the
//   per-lane PV binary-counter merge on its own 64x512 stack macro) + the back end's 4-leaf combine (ot_gpu_tree N 4)
//   for the QK score.  Every lane's arithmetic is the P = 1 column's, bit for bit; only the beat valids, the chunk flags
//   and the x word differ per lane.  The KV beat (c_w) fans out to the NL lanes (registered in the issue).
// Outputs per lane l: sc_* = the score of the lane's row with ordinal sc_tag[11:3]; pv_* = the lane's run node
// (4 sub-rows x 16 lanes x 32 b; sub-row q lane j slot b = head dim 8 (16 q + j) + b), pv_tag[2:0] = slot.
// No credit / ready / stall on any path; every fault is sticky.
// A1 (2026-10-19): SHARED = 1 replaces the NL per-lane merges of each sub-row column by ONE ot_hnx_att4_smerge (shared
// adders, per-lane flop rings); STORE = 1 keeps per-lane merges but on flop stacks (the fallback).  Arithmetic identical.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att4_slice #(
    parameter integer NL    = 3,       // query lanes = SM accumulator lanes P (P3 default, owner 10-19; generic 1..4)
    parameter integer LV    = 4,
    parameter integer KVMUT = 0,
    parameter integer PVMUT = 0,
    parameter integer IMUT  = 0,
    parameter integer SHARED = 0,       // A1: 1 = ONE shared 4-lane merge a sub-row column (ot_hnx_att4_smerge)
    parameter integer STORE  = 0,       // A1: per-lane merges (SHARED 0) on 0 = 64x512 macro, 1 = flop stack
    parameter integer SMUT   = 0        // shared-merge mutant
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 cfg_v,
    input  wire                 cfg_qk,
    input  wire                 cfg_kv4,
    input  wire [12:0]          cfg_n8,
    input  wire [12:0]          cfg_rows,
    // union line stream (136-B lines of the SM's own stack)
    input  wire                 s_valid,
    output wire                 s_ready,
    input  wire [1087:0]        s_data,
    // loaders
    input  wire                 xw_en,
    input  wire [1:0]           xw_lane,
    input  wire [6:0]           xw_addr,
    input  wire [1023:0]        xw_data,
    input  wire                 mclr,
    input  wire                 mw_en,
    input  wire [3:0]           mw_addr,
    input  wire [63:0]          mw_data,     // fixed R10 layout: row 16 a + i, lane l = bit 4 i + l
    // per-lane results
    output wire [NL-1:0]        sc_v,
    output wire [32*NL-1:0]     sc_y,
    output wire [16*NL-1:0]     sc_tag,
    output wire [NL-1:0]        pv_v,
    output wire [2048*NL-1:0]   pv_y,
    output wire [16*NL-1:0]     pv_tag,
    output wire                 op_issued,
    output wire [2:0]           c_ph,
    output wire [NL-1:0]        c_v_o,
    output wire [16*NL-1:0]     c_tag_o,
    output wire                 fault
);
    wire m_valid, m_ready, m_last, m_wend, busy, kfault, ifault;
    wire [1023:0] m_data; wire [2:0] m_slot, m_step;
    ot_hnx_att_kv_line #(.MUT(KVMUT)) u_kv (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_qk(cfg_qk), .cfg_kv4(cfg_kv4),
        .cfg_n8(cfg_n8), .cfg_h128(1'b0), .cfg_rows(cfg_rows), .s_valid(s_valid), .s_ready(s_ready), .s_data(s_data),
        .m_valid(m_valid), .m_ready(m_ready), .m_data(m_data), .m_slot(m_slot), .m_step(m_step), .m_wend(m_wend),
        .m_last(m_last), .busy(busy), .fault(kfault));
    wire [NL-1:0] c_v, c_first, c_last; wire [16*NL-1:0] c_tag; wire [1023:0] c_w; wire [NL*1024-1:0] c_x;
    ot_hnx_att4_issue #(.NL(NL), .MUT(IMUT)) u_is (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_qk(cfg_qk),
        .cfg_rows(cfg_rows), .xw_en(xw_en), .xw_lane(xw_lane), .xw_addr(xw_addr), .xw_data(xw_data), .mclr(mclr),
        .mw_en(mw_en), .mw_addr(mw_addr), .mw_data(mw_data), .b_valid(m_valid), .b_ready(m_ready), .b_data(m_data),
        .b_slot(m_slot), .b_step(m_step), .b_wend(m_wend), .b_last(m_last), .c_v(c_v), .c_first(c_first),
        .c_last(c_last), .c_tag(c_tag), .c_w(c_w), .c_x(c_x), .c_ph(c_ph), .op_issued(op_issued), .fault(ifault));
    assign c_v_o = c_v; assign c_tag_o = c_tag;
    wire [4*NL-1:0] ov, pvv, cf; wire [128*NL-1:0] y; wire [64*NL-1:0] otag, pvt; wire [2048*NL-1:0] pvy;
    wire [NL-1:0] t_f;
    wire [4*NL-1:0] mev; wire [512*4*NL-1:0] msum; wire [64*NL-1:0] mtag;
    wire [3:0] sm_f;
    genvar l, q;
    generate for (l = 0; l < NL; l = l + 1) begin : g_lane
        for (q = 0; q < 4; q = q + 1) begin : g_c
            localparam integer I = 4 * l + q;
            wire [511:0] c_pvy; wire [15:0] c_pvt; wire c_pvv;
            ot_hnx_att_tcpv_col #(.L(16), .IL(8), .TAGW(16), .ALAT(7), .LV(LV), .MUT(PVMUT), .STORE(STORE),
                .MERGE(SHARED ? 0 : 1)) u_c (.clk(clk), .rst_n(rst_n),
                .v(c_v[l]), .first(c_first[l]), .last(c_last[l]), .tag(c_tag[16*l +: 16]), .w(c_w[256*q +: 256]),
                .x(c_x[1024*l + 256*q +: 256]), .ov(ov[I]), .y(y[32*I +: 32]), .otag(otag[16*I +: 16]),
                .pv_v(c_pvv), .pv_y(c_pvy), .pv_tag(c_pvt),
                .m_ev(mev[I]), .m_sum(msum[512*I +: 512]), .m_tag(mtag[16*I +: 16]), .fault(cf[I]));
            if (SHARED == 0) begin : g_own
                assign pvv[I] = c_pvv; assign pvy[512*I +: 512] = c_pvy; assign pvt[16*I +: 16] = c_pvt;
            end
        end
        ot_gpu_tree #(.N(4), .TAGW(16), .ALAT(7)) u_be (.clk(clk), .rst_n(rst_n), .v(ov[4*l]), .d(y[128*l +: 128]),
            .tag(otag[64*l +: 16]), .ov(sc_v[l]), .y(sc_y[32*l +: 32]), .otag(sc_tag[16*l +: 16]), .fault(t_f[l]));
        assign pv_v[l] = pvv[4*l];
        assign pv_y[2048*l +: 2048] = pvy[2048*l +: 2048];
        assign pv_tag[16*l +: 16] = pvt[64*l +: 16];
    end endgenerate
    // A1 PRIMARY: one shared merge per sub-row column q, serving the NL lanes' column q
    generate if (SHARED != 0) begin : g_shared
        for (q = 0; q < 4; q = q + 1) begin : g_sm
            wire [NL-1:0] e; wire [512*NL-1:0] su; wire [16*NL-1:0] tg;
            wire smv; wire [511:0] smy; wire [15:0] smt; wire [1:0] sml;
            for (l = 0; l < NL; l = l + 1) begin : g_in
                assign e[l] = mev[4*l + q]; assign su[512*l +: 512] = msum[512*(4*l + q) +: 512];
                assign tg[16*l +: 16] = mtag[16*(4*l + q) +: 16];
            end
            ot_hnx_att4_smerge #(.NL(NL), .L(16), .TAGW(16), .ALAT(7), .LV(LV), .MUT(SMUT), .PUBLISH(0)) u_sm (
                .clk(clk), .rst_n(rst_n), .ev(e), .sum(su), .tag_d(tg), .pv_v(smv), .pv_y(smy), .pv_tag(smt),
                .pv_lane(sml), .pub_start(1'b0), .pub_lane(2'd0), .pub_slot(3'd0), .pub_v(), .pub_data(), .pub_word(),
                .pub_out_slot(), .pub_out_lane(), .pub_tag(), .fault(sm_f[q]));
            for (l = 0; l < NL; l = l + 1) begin : g_out
                assign pvv[4*l + q] = smv && (sml == l);
                assign pvy[512*(4*l + q) +: 512] = smy;
                assign pvt[16*(4*l + q) +: 16] = smt;
            end
        end
    end else begin : g_noshared
        assign sm_f = 4'd0;
    end endgenerate
    // the 4 sub-rows of a lane always finish together (same beats): a misaligned lane is a fault
    reg mis;
    integer k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) mis <= 1'b0;
        else for (k = 0; k < NL; k = k + 1)
            if ((pvv[4*k +: 4] != 4'h0 && pvv[4*k +: 4] != 4'hf) || (ov[4*k +: 4] != 4'h0 && ov[4*k +: 4] != 4'hf)) mis <= 1'b1;
    assign fault = kfault | ifault | (|cf) | (|t_f) | mis | (|sm_f);
endmodule
`default_nettype wire
