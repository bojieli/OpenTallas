`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One column of the V4.1 SM's block-dot tensor core (GPU-organised HBM
// comparator).  LB block-dot lanes (rtl/hdc/v41/ot_hdc_blockdot.sv, legacy
// sequential mode) share the weight line: each lane takes one 32-wide K
// block per cycle -- 32 E4M3, or E2M1 in the low nibble of each byte when
// `fp4` -- with its block exponent, and this column's activation block (32
// E4M3 codes and the block's scale exponent).  A lane forms the block dot
// EXACTLY (42-bit integer), rounds it once to binary32 and scales it by
// 2^(xe + we): the golden linear_q block term, i.e. a k32 FP8/FP4 MMA step.
// Its circulating FP32 accumulator adds the terms of one golden chunk (8
// blocks) in order from +0 across IL = 8 slots; at the chunk's last block the
// LB chunk sums enter the fixed pairwise tree together (the bottom log2(LB)
// levels of csum's tree).  Lane l holds chunk (group * LB + l).
// Latency: input -> chunk sum 15 cycles (block-dot P0..P8 + adder + output).
// ---------------------------------------------------------------------------
module ot_gpu_bd_col #(
    parameter integer LB   = 8,
    parameter integer IL   = 8,
    parameter integer TAGW = 12
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire              first,
    input  wire              last,
    input  wire              fp4,
    input  wire [TAGW-1:0]   tag,
    input  wire [LB*256-1:0] wq,
    input  wire [LB*10-1:0]  we,
    input  wire [LB*256-1:0] xq,
    input  wire [LB*10-1:0]  xe,
    output wire              ov,
    output wire [31:0]       y,
    output wire [TAGW-1:0]   otag,
    output wire              fault
);
    localparam integer LAT = 15;
    wire [LB-1:0] lov, lf;
    wire [LB*32-1:0] acc;
    genvar l;
    generate for (l = 0; l < LB; l = l + 1) begin : g_lane
        wire [$clog2(IL)-1:0] ph;
        wire [15:0] yb;
        ot_hdc_blockdot #(.IL(IL), .CHUNK8(0)) u_bd (
            .clk(clk), .rst_n(rst_n), .v(v), .first(first), .last(last), .fp4(fp4),
            .xq(xq[256*l +: 256]), .xe(xe[10*l +: 10]), .wq(wq[256*l +: 256]), .we(we[10*l +: 10]),
            .phase(ph), .ov(lov[l]), .y(yb), .acc(acc[32*l +: 32]), .fault(lf[l]));
    end endgenerate
    // the chunk's tag leaves with its sums; lanes retire together, so lane 0's ov times the tree
    wire [LAT:0] ll;
    ot_hdc_vline #(.D(LAT)) u_l (.clk(clk), .rst_n(rst_n), .v(v && last), .vd(ll));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(LAT)) u_t (.clk(clk), .rst_n(rst_n), .d(tag), .q(tag_d));
    reg sticky;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sticky <= 1'b0;
        else sticky <= sticky | (|lf) | (lov[0] != ll[LAT]) | (lov != {LB{lov[0]}});
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(LB), .TAGW(TAGW)) u_tree (.clk(clk), .rst_n(rst_n), .v(lov[0]), .d(acc), .tag(tag_d),
                                              .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    // output registers: the hardened macro's outputs leave flops
    reg ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin ov_q <= t_ov; fault_q <= sticky | tf; end
    always @(posedge clk) begin y_q <= t_y; otag_q <= t_tag; end
    assign ov = ov_q;
    assign y = y_q;
    assign otag = otag_q;
    assign fault = fault_q;
endmodule
