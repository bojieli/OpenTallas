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
    parameter integer LB   = 2,         // defaults = the hardened macro (V4.1 SM: 2 lanes, 16-bit tag)
    parameter integer IL   = 8,
    parameter integer TAGW = 16
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
    // 1.2 GHz at SS: the block term is W10's ot_v41_bterm2 (ot_hdc_blockdot's P0..P8 re-cut, bit-identical,
    // LATENCY 11), accumulated per golden chunk on an IL-slot circulating ring around the LAT-7 FP32 adder
    // (ot_gpu_fadd): the term of slot s arrives BT cycles after its issue, so the ring runs BT cycles late and
    // keeps the slot rotation; a bubble adds +0 (the slot's sum holds, bit for bit).
    localparam integer BT = 12;          // lane input register + ot_v41_bterm2 (LAT 11)
    localparam integer ALAT = 7;
    localparam integer FB = IL - ALAT;
    wire [LB-1:0] tv_l, tf_l;
    wire [LB*32-1:0] term;
    genvar l;
    generate for (l = 0; l < LB; l = l + 1) begin : g_bt
        // one registered fp4 per lane, kept, so synthesis cannot merge the lanes' format flops into one net
        // driving every lane's decoders (the -71 ps SS path of the first 1.2 GHz route)
        // (and the block term decodes E2M1 ahead of its P0 register, DEC_P0 = 1: the -51.6 ps P1 path of the
        // second route was this flop's fanout into the decode + 4x4 product)
        (* keep *) reg fp4_l;
        always @(posedge clk) fp4_l <= fp4;
        reg [255:0] xq_l, wq_l;
        reg [9:0]   xe_l, we_l;
        reg         v_l;
        always @(posedge clk) begin xq_l <= xq[256*l +: 256]; wq_l <= wq[256*l +: 256]; xe_l <= xe[10*l +: 10]; we_l <= we[10*l +: 10]; end
        always @(posedge clk or negedge rst_n) if (!rst_n) v_l <= 1'b0; else v_l <= v;
        ot_v41_bterm2 #(.TW(1), .DEC_P0(1), .SH_DUP(1)) u_bt (.clk(clk), .rst_n(rst_n), .v(v_l), .fp4(fp4_l),
            .xq(xq_l), .xe(xe_l), .wq(wq_l), .we(we_l),
            .tag(1'b0), .ov(tv_l[l]), .y(term[32*l +: 32]), .f(tf_l[l]), .otag());
    end endgenerate
    // first / last / tag aligned with the terms
    wire [BT:0] fl_d, ll_d;
    ot_hdc_vline #(.D(BT)) u_fd (.clk(clk), .rst_n(rst_n), .v(v && first), .vd(fl_d));
    ot_hdc_vline #(.D(BT)) u_ld (.clk(clk), .rst_n(rst_n), .v(v && last), .vd(ll_d));
    wire [TAGW-1:0] tag_t;
    ot_hdc_delay #(.W(TAGW), .D(BT)) u_tt (.clk(clk), .rst_n(rst_n), .d(tag), .q(tag_t));
    // ring: adder (ALAT) + feedback delay (FB) = IL; the first-select is combinational at the adder input
    reg  [LB*32-1:0] tm_q;
    reg              first_q, last_q, tv_q;
    reg  [TAGW-1:0]  tag_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin first_q <= 1'b0; last_q <= 1'b0; tv_q <= 1'b0; end
        else begin first_q <= fl_d[BT]; last_q <= ll_d[BT]; tv_q <= tv_l[0]; end
    end
    integer k;
    always @(posedge clk) begin
        tag_q <= tag_t;
        for (k = 0; k < LB; k = k + 1) tm_q[32*k +: 32] <= tv_l[k] ? term[32*k +: 32] : 32'd0;
    end
    wire [LB*32-1:0] acc;
    wire [LB-1:0] af;
    generate for (l = 0; l < LB; l = l + 1) begin : g_ring
        wire [31:0] sum, fb_pre;
        reg  [31:0] tm_d;
        reg         first_d, tv_d;
        always @(posedge clk) begin tm_d <= tm_q[32*l +: 32]; first_d <= first_q; tv_d <= tv_q; end
        wire [31:0] acc_in = first_d ? 32'd0 : fb_pre;
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(tv_d), .a(acc_in), .b(tm_d), .y(sum), .fault(af[l]));
        ot_hdc_delay #(.W(32), .D(FB)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum), .q(fb_pre));
        assign acc[32*l +: 32] = sum;
    end endgenerate
    // the chunk's final sum leaves the adder 1 + ALAT cycles after its last term is registered
    localparam integer LS = 1 + ALAT;
    wire [LS:0] lo;
    ot_hdc_vline #(.D(LS)) u_lo (.clk(clk), .rst_n(rst_n), .v(last_q), .vd(lo));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(LS)) u_td (.clk(clk), .rst_n(rst_n), .d(tag_q), .q(tag_d));
    wire [LB-1:0] lov = {LB{lo[LS]}};
    reg sticky;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sticky <= 1'b0;
        else sticky <= sticky | (|(tf_l & tv_l)) | (|af);
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(LB), .TAGW(TAGW), .ALAT(7)) u_tree (.clk(clk), .rst_n(rst_n), .v(lov[0]), .d(acc), .tag(tag_d),
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
