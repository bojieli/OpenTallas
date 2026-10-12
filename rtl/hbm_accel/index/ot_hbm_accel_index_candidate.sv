`timescale 1ns/1ps
// Native HBM candidate publication boundary. Opt-in only; original selectors
// and their rounding/max tree/threshold/replay mechanisms are unchanged.
// Actual scored input IDs belong to blocks rank+96*j, each block's eight
// contiguous global keys, with quarter ranges ordered by global ID. No
// rank-local ordinal relabel, false newest pin, host topk or reference operand.
// Invalid tail lanes remain invalid; an empty quarter closes with last/lv0.
// held tuple is the parent's actual authority, held immutable until drain.
// SRAM ports are real one-read/one-write synchronous line stores per quarter;
// caller preserves the existing latency, finite capacity and replay contract.
// Prebuild: tools/hbm_index_candidate_model.py. No SS/FF clock qualification.
module ot_hbm_accel_index_candidate #(
    parameter bit ENABLE = 1'b0,
    parameter integer Q   = 4,
    parameter integer SL  = 16,       // score lanes per quarter (multiple of 8)
    parameter integer IWP = 20,       // position width
    parameter integer K   = 2048,     // largest runtime k (blocks)
    parameter integer AW  = 10,       // line-memory address width per quarter
    parameter integer DG  = 8,
    parameter integer OD  = 4,
    parameter integer KW  = $clog2(K + 1)
) (
    input  wire                         clk,
    input  wire                         rst_n,
    // These are the actual issuer's held tuple, stable through all accepted
    // quarter-last outputs and memory/replay drain. This wrapper grants no owner.
    input  wire                         held_valid,
    input  wire [31:0]                  held_job,
    input  wire [3:0]                   held_gen,
    input  wire [19:0]                  held_pos,
    input  wire [6:0]                   held_rank,
    output wire [31:0]                  out_job,
    output wire [3:0]                   out_gen,
    output wire [19:0]                  out_pos,
    output wire [6:0]                   out_rank,
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
    output wire [Q*(SL/8)*16-1:0]       out_val,
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
    assign out_job = held_job;
    assign out_gen = held_gen;
    assign out_pos = held_pos;
    assign out_rank = held_rank;
    generate if (ENABLE) begin : enabled
    if (Q != 4 || SL != 16 || IWP != 20 || K != 2048 || AW != 10)
        initial $fatal(1, "native HBM candidate requires Q4/SL16/ID20/K2048/AW10");
    localparam integer BL = SL / 8;                 // block lanes per quarter
    localparam integer BW = IWP - 3;                // block-index width

    wire [Q-1:0]         c_ready;
    wire [Q*BL-1:0]      c_lv;
    wire [Q*BL*16-1:0]   c_val;
    wire [Q*BL*BW-1:0]   c_idx;
    wire [Q-1:0]         f_v, f_last;
    reg  [KW-1:0]        k_r;

    wire [Q*SL*16-1:0] source_values;
    genvar pg, pb, pl;
    for (pg = 0; pg < Q; pg = pg + 1) begin : g_native_q
        for (pb = 0; pb < SL/8; pb = pb + 1) begin : g_native_b
            // No quarter/rank-local LAST inference: only the literal global
            // newest block is pinned, wherever it occurs in the actual stream.
            wire pin_newest = held_valid && in_lv[SL*pg + 8*pb] &&
                (in_idx[IWP*(SL*pg + 8*pb) + 3 +: IWP-3] == held_pos[19:3]);
            for (pl = 0; pl < 8; pl = pl + 1) begin : g_lane
                if (pl == 0) begin : g_pin
                    assign source_values[16*(SL*pg+8*pb+pl) +: 16] = pin_newest ?
                        16'h7f80 : in_val[16*(SL*pg+8*pb+pl) +: 16];
                end else begin : g_copy
                    assign source_values[16*(SL*pg+8*pb+pl) +: 16] = in_val[16*(SL*pg+8*pb+pl) +: 16];
                end
            end
        end
    end
    genvar gq;
        for (gq = 0; gq < Q; gq = gq + 1) begin : g_q
            assign in_ready[gq] = held_valid && c_ready[gq];      // the front end advances only with the core
            ot_hdc_v41x_sel_cfront #(.SL(SL), .IWP(IWP), .PIN(0)) u_f (
                .clk(clk), .rst_n(rst_n), .en(c_ready[gq]), .in_valid(in_valid[gq] && held_valid), .in_last(in_last[gq]),
                .in_lv(in_lv[SL*gq +: SL]), .in_val(source_values[SL*16*gq +: SL*16]), .in_idx(in_idx[SL*IWP*gq +: SL*IWP]),
                .o_v(f_v[gq]), .o_last(f_last[gq]), .o_lv(c_lv[BL*gq +: BL]), .o_val(c_val[BL*16*gq +: BL*16]),
                .o_idx(c_idx[BL*BW*gq +: BL*BW]));
        end
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
    // Real selected maxima for the candidate collective; never reconstruct
    // scores from host/oracle values or silently publish a false local pin.
    assign out_val = o_val;
    end else begin : disabled
        assign in_ready = '0;
        assign out_valid = '0; assign out_last = '0;
        assign out_lv = '0; assign out_blk = '0; assign out_val = '0;
        assign mem_we = '0; assign mem_waddr = '0; assign mem_wdata = '0;
        assign mem_re = '0; assign mem_raddr = '0;
        assign rep_req = 1'b0; assign ovf = 1'b0; assign busy = 1'b0;
    end endgenerate
endmodule
