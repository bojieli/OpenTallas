`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// V4.1x CANDIDATE-BLOCK SELECT (layer 20): tools/hdc_golden_v41.py `Model.candidate_blocks`
// at the indexer's ingest rate -- Q x SL score lanes per cycle (4 x 16 = 64), Q x SL/8
// block lanes (8 blocks per cycle) -- in place of the 64 x 64 candidate array.
//
// Semantics: block b holds positions 8b .. 8b+7; its score is the maximum of its scores
// with positions past the end padded -inf; the block holding the newest position is
// pinned to +inf; the top-k blocks by (score desc, block index asc) are kept, except
// blocks whose score is -inf.  Output: the kept block indices, ascending.
//
// Contract.  As ot_hdc_v41x_sel (Q contiguous position quarters, one port each, valid/
// ready, in_last per quarter), plus:
//   * beats are dense and block-aligned: lane j of a beat holds position base + j with
//     base a multiple of 8; only the final beat of a quarter may be partial (lanes past
//     the end invalid, a prefix valid); a quarter's range starts on a multiple of 8;
//   * quarter Q-1 is non-empty and holds the newest position (its in_last beat carries
//     the pinned block: the last block with a valid lane);
//   * in_k is the runtime candidate count (clamped to K).
// Output port q: kept blocks of quarter q, W = SL/8 lanes per beat, ascending; the
// concatenation over q is the kept list.  -inf blocks (selected only when fewer than k
// blocks are finite) leave with out_lv = 0.
//
// Datapath: a registered front end per quarter computes the SL/8 block maxima of a beat
// (an 8-way key-max tree), pins the newest block, and feeds ot_hdc_v41x_sel (Q quarters x
// SL/8 lanes, K, block-index width IWP-3): the streaming filter + GC + threshold select.
// Latency budget: the mask is consumed >= 4 layers later (~20 us); at 1M per die (262,144
// scores, 32,768 blocks) the ingest takes 4,096 cycles and the tail is measured by
// tools/rtl_hdc_v41x_sel_cand_campaign.py.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_sel_cand #(
    parameter integer Q   = 4,
    parameter integer SL  = 16,       // score lanes per quarter (multiple of 8)
    parameter integer IWP = 20,       // position width
    parameter integer K   = 2048,     // largest runtime k (blocks)
    parameter integer AW  = 10,       // line-memory address width per quarter
    parameter integer DG  = 4,
    parameter integer OD  = 4,
    parameter integer KW  = $clog2(K + 1)
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire [Q-1:0]                 in_valid,
    output wire [Q-1:0]                 in_ready,
    input  wire [Q-1:0]                 in_last,
    input  wire [Q*SL-1:0]              in_lv,
    input  wire [Q*SL*16-1:0]           in_val,
    input  wire [Q*SL*IWP-1:0]          in_idx,
    input  wire [KW-1:0]                in_k,
    output wire [Q-1:0]                 out_valid,
    input  wire [Q-1:0]                 out_ready,
    output wire [Q-1:0]                 out_last,
    output wire [Q*(SL/8)-1:0]          out_lv,
    output wire [Q*(SL/8)*(IWP-3)-1:0]  out_blk,
    output wire [Q-1:0]                 mem_we,
    output wire [Q*AW-1:0]              mem_waddr,
    output wire [Q*(SL/8)*(14+IWP)-1:0] mem_wdata,
    output wire [Q-1:0]                 mem_re,
    output wire [Q*AW-1:0]              mem_raddr,
    input  wire [Q*(SL/8)*(14+IWP)-1:0] mem_rdata,
    output wire                         rep_req,
    output wire                         ovf,
    output wire                         busy,
    output wire [Q*3*(AW+1)-1:0]        stats
);
    localparam integer BL = SL / 8;                 // block lanes per quarter
    localparam integer BW = IWP - 3;                // block-index width

    function automatic [15:0] fkey(input [15:0] v);
        fkey = (v[14:0] == 0) ? 16'h8000 : v[15] ? ~v : {1'b1, v[14:0]};
    endfunction
    // the max of two (key, value) pairs; invalid = -inf
    function automatic [31:0] kmax(input [31:0] a, input [31:0] b);
        kmax = (b[31:16] > a[31:16]) ? b : a;
    endfunction

    wire [Q-1:0]         c_ready;
    wire [Q*BL-1:0]      c_lv;
    wire [Q*BL*16-1:0]   c_val;
    wire [Q*BL*BW-1:0]   c_idx;
    wire [Q-1:0]         f_v, f_last;
    reg  [KW-1:0]        k_r;

    genvar gq, gb, gl;
    generate
        for (gq = 0; gq < Q; gq = gq + 1) begin : g_q
            // front-end register (the block boundary); the max trees feed the core's input register
            wire take = in_valid[gq] && in_ready[gq];
            assign in_ready[gq] = c_ready[gq];         // no beat is taken before the core ingests
            reg [SL-1:0]    r_lv;
            reg [SL*16-1:0] r_val;
            reg [SL*IWP-1:0] r_idx;
            reg fv, fl;
            assign f_v[gq] = fv;
            assign f_last[gq] = fl;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin fv <= 1'b0; fl <= 1'b0; end
                else if (in_ready[gq]) begin fv <= in_valid[gq]; fl <= in_valid[gq] && in_last[gq]; end
            end
            always @(posedge clk) if (take) begin
                r_lv <= in_lv[SL*gq +: SL]; r_val <= in_val[SL*16*gq +: SL*16]; r_idx <= in_idx[SL*IWP*gq +: SL*IWP];
            end
            // block maxima
            wire [BL-1:0] blk_v;
            for (gb = 0; gb < BL; gb = gb + 1) begin : g_b
                wire [8*32-1:0] kv;
                for (gl = 0; gl < 8; gl = gl + 1) begin : g_l
                    wire [15:0] v = r_val[16*(8*gb + gl) +: 16];
                    assign kv[32*gl +: 32] = r_lv[8*gb + gl] ? {fkey(v), v} : {16'h007F, 16'hFF80};
                end
                wire [31:0] m01 = kmax(kv[31:0], kv[63:32]), m23 = kmax(kv[95:64], kv[127:96]);
                wire [31:0] m45 = kmax(kv[159:128], kv[191:160]), m67 = kmax(kv[223:192], kv[255:224]);
                wire [31:0] mx  = kmax(kmax(m01, m23), kmax(m45, m67));
                assign blk_v[gb] = r_lv[8*gb];
                // pinned: the last valid block of quarter Q-1's last beat
                wire pin_last;
                if (gb + 1 < BL) begin : g_nx
                    assign pin_last = !r_lv[8*(gb + 1)];
                end else begin : g_ln
                    assign pin_last = 1'b1;
                end
                wire pin = (gq == Q - 1) && f_last[gq] && r_lv[8*gb] && pin_last;
                assign c_val[(BL*gq + gb)*16 +: 16] = pin ? 16'h7F80 : mx[15:0];
                assign c_idx[(BL*gq + gb)*BW +: BW] = r_idx[IWP*(8*gb) + 3 +: BW];
                assign c_lv[BL*gq + gb] = blk_v[gb];
            end
        end
    endgenerate
    always @(posedge clk) if (|(in_valid & in_ready)) k_r <= in_k;

    wire [Q*BL*16-1:0] o_val;
    wire [Q*BL-1:0]    o_lv, o_ninf;
    ot_hdc_v41x_sel #(.Q(Q), .W(BL), .IW(BW), .K(K), .AW(AW), .DG(DG), .OD(OD), .KW(KW)) u_sel (
        .clk(clk), .rst_n(rst_n), .in_valid(f_v), .in_ready(c_ready), .in_last(f_last),
        .in_lv(c_lv), .in_val(c_val), .in_idx(c_idx), .in_k(k_r),
        .out_valid(out_valid), .out_ready(out_ready), .out_last(out_last), .out_lv(o_lv), .out_val(o_val),
        .out_idx(out_blk), .out_ninf(o_ninf),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata), .mem_re(mem_re), .mem_raddr(mem_raddr),
        .mem_rdata(mem_rdata), .rep_req(rep_req), .ovf(ovf), .busy(busy), .stats(stats));
    assign out_lv = o_lv & ~o_ninf;
endmodule
