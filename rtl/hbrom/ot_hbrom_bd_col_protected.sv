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
module ot_hbrom_bd_col_protected #(
    parameter integer PROTECT = 0,
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
    generate if(!PROTECT) begin:g_original
    ot_gpu_bd_col #(.LB(LB),.IL(IL),.TAGW(TAGW)) u_original(.*);
    end else begin:g_protected
    // 1.2 GHz at SS: the block term is W10's ot_v41_bterm2 (ot_hdc_blockdot's P0..P8 re-cut, bit-identical,
    // LATENCY 11), accumulated per golden chunk on an IL-slot circulating ring around the LAT-7 FP32 adder
    // (ot_gpu_fadd): the term of slot s arrives BT cycles after its issue, so the ring runs BT cycles late and
    // keeps the slot rotation; a bubble adds +0 (the slot's sum holds, bit for bit).
    localparam integer BT = 11;
    localparam integer ALAT = 7;
    localparam integer FB = IL - ALAT;
    wire [LB-1:0] tv_l, tf_l;
    wire [LB*32-1:0] term;
    genvar l;
    for (l = 0; l < LB; l = l + 1) begin : g_bt
        ot_v41_bterm2 #(.TW(1)) u_bt (.clk(clk), .rst_n(rst_n), .v(v), .fp4(fp4),
            .xq(xq[256*l +: 256]), .xe(xe[10*l +: 10]), .wq(wq[256*l +: 256]), .we(we[10*l +: 10]),
            .tag(1'b0), .ov(tv_l[l]), .y(term[32*l +: 32]), .f(tf_l[l]), .otag());
    end
    // first / last / tag aligned with the terms
    wire [BT:0] fl_d, ll_d;
    wire pf0; ot_hbrom_metadata_pipe #(.W(1),.D(BT)) u_fd (.clk(clk),.rst_n(rst_n),.d(v && first),.q(),.taps(fl_d),.fault(pf0));
    wire pf1; ot_hbrom_metadata_pipe #(.W(1),.D(BT)) u_ld (.clk(clk),.rst_n(rst_n),.d(v && last),.q(),.taps(ll_d),.fault(pf1));
    wire [TAGW-1:0] tag_t;
    wire pf3; ot_hbrom_metadata_pipe #(.W(TAGW),.D(BT)) u_tt (.clk(clk), .rst_n(rst_n), .d(tag), .q(tag_t),.taps(),.fault(pf3));
    // ring: acc register (1) + adder (ALAT) + feedback delay (FB - 1) = IL
    reg  [LB*32-1:0] tm_q;
    reg              first_q, last_q, tv_q;
    reg  [TAGW-1:0]  tag_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin first_q <= 1'b0; last_q <= 1'b0; tv_q <= 1'b0; end
        else begin first_q <= fl_d[BT]; last_q <= ll_d[BT]; tv_q <= tv_l[0]; end
    end
    integer k;
    always @(posedge clk) begin
        if(!rst_n) tag_q<=0;else tag_q <= tag_t;
        for (k = 0; k < LB; k = k + 1) tm_q[32*k +: 32] <= tv_l[k] ? term[32*k +: 32] : 32'd0;
    end
    wire [LB*32-1:0] acc;
    wire [LB-1:0] af;
    for (l = 0; l < LB; l = l + 1) begin : g_ring
        wire [31:0] sum, fb_pre;
        reg  [31:0] acc_q;
        always @(posedge clk) acc_q <= first_q ? 32'd0 : fb_pre;
        reg [31:0] tm_d;
        always @(posedge clk) tm_d <= tm_q[32*l +: 32];
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(acc_q), .b(tm_d), .y(sum), .fault(af[l]));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum), .q(fb_pre));
        assign acc[32*l +: 32] = sum;
    end
    // the chunk's final sum leaves the adder 1 + ALAT cycles after its last term is registered
    localparam integer LS = 1 + ALAT;
    wire [LS:0] lo;
    wire pf2; ot_hbrom_metadata_pipe #(.W(1),.D(LS)) u_lo (.clk(clk),.rst_n(rst_n),.d(last_q),.q(),.taps(lo),.fault(pf2));
    wire [TAGW-1:0] tag_d;
    wire pf4; ot_hbrom_metadata_pipe #(.W(TAGW),.D(LS)) u_td (.clk(clk), .rst_n(rst_n), .d(tag_q), .q(tag_d),.taps(),.fault(pf4));
    wire [LB-1:0] lov = {LB{lo[LS]}};
    reg sticky;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sticky <= 1'b0;
        else sticky <= sticky | (|(tf_l & tv_l)) | (|af);
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_hbrom_tree_protected #(.PROTECT(1),.N(LB), .TAGW(TAGW), .ALAT(7)) u_tree (.clk(clk), .rst_n(rst_n), .v(lov[0]), .d(acc), .tag(tag_d),
                                              .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    // output registers: the hardened macro's outputs leave flops
    reg ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin ov_q <= t_ov; fault_q <= sticky | tf; end
    always @(posedge clk) begin y_q <= t_y; if(!rst_n) otag_q<=0;else otag_q <= t_tag; end
    assign ov = ov_q && !fault;
    assign y = y_q;
    assign otag = otag_q;
    assign fault = fault_q | fault_b | ctrl_bad | poison_a | poison_b;

    (* keep *) reg first_b,last_b,tv_b;
    (* keep *) reg [TAGW-1:0] tag_b;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin first_b<=0;last_b<=0;tv_b<=0;tag_b<=0;end
      else begin first_b<=fl_d[BT];last_b<=ll_d[BT];tv_b<=tv_l[0];tag_b<=tag_t;end
    end
    wire ingress_bad=({first_q,last_q,tv_q,tag_q}!={first_b,last_b,tv_b,tag_b});
    (* keep *) reg sticky_b;
    always @(posedge clk or negedge rst_n) if(!rst_n) sticky_b<=0;else sticky_b<=sticky_b|(|(tf_l & tv_l))|(|af);

    (* keep *) reg ov_b,fault_b,poison_a,poison_b;
    (* keep *) reg [TAGW-1:0] otag_b;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin ov_b<=0;fault_b<=0;otag_b<=0;end
      else begin ov_b<=t_ov;fault_b<=sticky_b|tf;otag_b<=t_tag;end
    end
    wire ctrl_bad=ingress_bad|(sticky!=sticky_b)|(ov_q!=ov_b)|(fault_q!=fault_b)|(otag_q!=otag_b)|pf0|pf1|pf2|pf3|pf4;
    always @(posedge clk or negedge rst_n) if(!rst_n) poison_a<=0;else poison_a<=poison_a|poison_b|ctrl_bad;
    always @(posedge clk or negedge rst_n) if(!rst_n) poison_b<=0;else poison_b<=poison_b|poison_a|ctrl_bad;
    end endgenerate
endmodule