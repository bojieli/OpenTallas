`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One column of an exact Tensor-Core-style MMA sub-partition (GPU-organised
// HBM comparator, docs/MICROARCH_MODEL.md; the hardened replicated macro).
//
// L lanes share the sub-partition's BF16 weight word (w, one weight per lane,
// decoded upstream from INT8 or passed as BF16) and take this column's x
// (one BF16 activation per lane).  Every lane is the ROM lane's exact
// datapath (ot_hdc_lane_copy): exact BF16 x BF16 -> FP32 product (ot_hdc_bmul,
// LATENCY 5) into a CIRCULATING FP32 RNE adder (ot_hdc_fadd, LATENCY 5) that
// holds IL = 8 independent accumulations (slots) in flight, so each slot's
// products are added strictly in K order, one per revolution, from +0.
//   v      a k-step is presented for the slot whose turn it is (rotation);
//          without v the slot's sum circulates unchanged (product forced +0)
//   first  the slot's chunk restarts from +0 with this product
//   last   this product ends the chunk: every lane's chunk sum enters the
//          column's fixed pairwise tree (ot_gpu_tree) together
// Lane l of the column holds golden chunk (group * L + l) of the slot's row,
// so the tree's leaves are L consecutive aligned chunk sums -- the bottom
// log2(L) levels of the golden pairwise tree.
// Latency: v -> tree input 12 cycles; tree 5 * log2(L); one output register.
// Boundary (hardened macro): every input lands in a register (the bubble
// gate uses a per-lane registered copy of v, so the v pin drives L flops,
// not L x 16 gates) and every output leaves one.
// ---------------------------------------------------------------------------
module ot_gpu_tc_col #(
    parameter integer L    = 32,
    parameter integer IL   = 8,
    parameter integer TAGW = 12
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            first,
    input  wire            last,
    input  wire [TAGW-1:0] tag,
    input  wire [L*16-1:0] w,
    input  wire [L*16-1:0] x,
    output wire            ov,
    output wire [31:0]     y,
    output wire [TAGW-1:0] otag,
    output wire            fault
);
    localparam integer FB = IL - 5;
    reg            v_q, first_q, last_q;
    reg [L-1:0]    v_ql;                // per-lane copy of v for the bubble gate
    reg [TAGW-1:0] tag_q;
    reg [L*16-1:0] w_q, x_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v_q <= 1'b0; first_q <= 1'b0; last_q <= 1'b0; v_ql <= {L{1'b0}}; end
        else begin v_q <= v; first_q <= v && first; last_q <= v && last; v_ql <= {L{v}}; end
    end
    always @(posedge clk) begin
        w_q <= w;
        x_q <= x;
        tag_q <= tag;
    end
    wire [5:0] fl;
    ot_hdc_vline #(.D(5)) u_f (.clk(clk), .rst_n(rst_n), .v(first_q), .vd(fl));
    // chunk end: the lane's final sum leaves the adder 5 (mul) + 5 (add) cycles after the input register
    wire [10:0] ll;
    ot_hdc_vline #(.D(10)) u_l (.clk(clk), .rst_n(rst_n), .v(last_q), .vd(ll));
    wire [TAGW-1:0] tag_d;
    ot_hdc_delay #(.W(TAGW), .D(10)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_q), .q(tag_d));
    wire [5:0] vl;
    ot_hdc_vline #(.D(5)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vl));
    wire [L*32-1:0] sum;
    wire [L-1:0] lf;
    genvar l;
    generate for (l = 0; l < L; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        wire f0, f1;
        // a bubble multiplies by +0: the slot's sum holds
        wire [15:0] wg = v_ql[l] ? w_q[16*l +: 16] : 16'd0;
        ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(v_q), .a({wg, 16'd0}),
                           .b({x_q[16*l +: 16], 16'd0}), .y(prod), .fault(f0));
        always @(posedge clk) acc_q <= fl[4] ? 32'd0 : fb_pre;
        ot_hdc_fadd u_add (.clk(clk), .rst_n(rst_n), .v(vl[5]), .a(acc_q), .b(prod), .y(sum[32*l +: 32]), .fault(f1));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        assign lf[l] = f0 | f1;
    end endgenerate
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_gpu_tree #(.N(L), .TAGW(TAGW)) u_tree (.clk(clk), .rst_n(rst_n), .v(ll[10]), .d(sum), .tag(tag_d),
                                             .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    reg lane_fault, ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lane_fault <= 1'b0; ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin
            lane_fault <= lane_fault | (|lf);
            ov_q <= t_ov;
            fault_q <= lane_fault | tf;
        end
    always @(posedge clk) begin y_q <= t_y; otag_q <= t_tag; end
    assign ov = ov_q;
    assign y = y_q;
    assign otag = otag_q;
    assign fault = fault_q;
endmodule

// The V4.1 SM's BF16 column as a fixed macro (16 lanes, the 16-bit tag of a 4,096-row SM): a distinct
// module name so the V4.1 SM can place it beside the Qwen SM's 32-lane ot_gpu_tc_col macro.
module ot_gpu_tc16 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          first,
    input  wire          last,
    input  wire [15:0]   tag,
    input  wire [255:0]  w,
    input  wire [255:0]  x,
    output wire          ov,
    output wire [31:0]   y,
    output wire [15:0]   otag,
    output wire          fault
);
    ot_gpu_tc_col #(.L(16), .IL(8), .TAGW(16)) u (.clk(clk), .rst_n(rst_n), .v(v), .first(first), .last(last),
        .tag(tag), .w(w), .x(x), .ov(ov), .y(y), .otag(otag), .fault(fault));
endmodule
