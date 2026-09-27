`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// BF16/FP32-weight MAC lane of the V4.1x weight engine (block `wgt`, the "ME"):
// the product of tools/hdc_golden_v41.matvec_c under R-ARITH,
// mul(w, to_bf16(x)) -- one IEEE binary32 multiply, RNE, gradual underflow,
// a zero operand giving +0 -- by the qualified ot_hdc_qmul with the
// activation's low 16 bits tied to zero (x is BF16: synthesis keeps an 24 x 8
// significand product).  The chunk's adds are the chain
// (ot_hdc_v41x_wgt_chain): a chunk of 8 = a chain of 8 MACs.
//
// WEIGHT WORD (32 bits per lane), by the op's format:
//   f8 = 0: the weight's binary32 bits -- a BF16 weight (lm_head, the router
//           gate, the compressor, the index projection) as {bf16, 16'h0}: the
//           ROM bank is 16 bits wide and the read network appends the zeros;
//           an FP32 weight as stored (kept for generality).
//   f8 = 1: an FP8 weight stored at its checkpoint precision (wo_a: E4M3 with
//           one UE8M0 scale per 32 x 32 block): w[7:0] the E4M3 code, w[15:8]
//           the block's UE8M0 byte (1 B per weight in the ROM + 1 B per 1,024
//           weights, broadcast to the block's 32 rows by the read network).
//           The lane dequantises EXACTLY (e4m3 x 2^(s-127) has a 4-bit
//           significand, so the release's BF16 dequantisation -- the golden's
//           to_bf16(Q8.dense()) -- is the identity on it): a stage D decodes
//           the code into binary32.  A NaN code, or a scaled value outside the
//           binary32 normal range (where the golden's float32 rounding would
//           act), fails closed through the lane fault.
// M positions (MTP lane multiplier) share the weight word.
// LATENCY 5: P0 input register, D decode register, the 3-cycle multiply.
// z forces +0.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_wgt_mlane #(
    parameter integer M = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            z,
    input  wire            f8,
    input  wire [31:0]     w,
    input  wire [M*16-1:0] x,
    output wire            ov,
    output wire [M*32-1:0] y,
    output wire [M-1:0]    f
);
    reg            p0_v, p0_f8, p0_z;
    reg [31:0]     p0_w;
    reg [M*16-1:0] p0_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p0_v <= 1'b0;
        else p0_v <= v;
    end
    always @(posedge clk) begin
        p0_z <= z; p0_f8 <= f8;
        p0_w <= w;
        p0_x <= x;
    end

    // -- D: E4M3 x 2^(s-127) -> binary32 ------------------------------------------------------
    wire [7:0] c = p0_w[7:0];
    wire [7:0] s = p0_w[15:8];
    wire [3:0] ce = c[6:3];
    wire [2:0] cm = c[2:0];
    //: a subnormal code m/8 * 2^-6 normalised: leading one of m at position p, value 1.r * 2^(p-9)
    wire [1:0] lp = cm[2] ? 2'd2 : (cm[1] ? 2'd1 : 2'd0);
    wire [2:0] sm = cm[2] ? {cm[1:0], 1'b0} : (cm[1] ? {cm[0], 2'b00} : 3'b000);
    //: biased binary32 exponent: normal e + s - 7, subnormal p + s - 9
    wire signed [10:0] eb = (ce != 4'd0) ? $signed({3'd0, s}) + $signed({7'd0, ce}) - 11'sd7
                                         : $signed({3'd0, s}) + $signed({9'd0, lp}) - 11'sd9;
    wire [2:0]  mt = (ce != 4'd0) ? cm : sm;
    wire        cz = (c[6:0] == 7'd0);
    wire        cn = (c[6:0] == 7'h7F);
    wire        rng = (eb < 11'sd1) || (eb > 11'sd254);
    wire [31:0] w8 = cz ? 32'd0 : {c[7], eb[7:0], mt, 20'd0};
    reg            d_v;
    reg [31:0]     d_w;
    reg            d_f;
    reg [M*16-1:0] d_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) d_v <= 1'b0;
        else d_v <= p0_v;
    end
    always @(posedge clk) begin
        d_w <= p0_z ? 32'd0 : (p0_f8 ? w8 : p0_w);
        d_f <= !p0_z && p0_f8 && !cz && (cn || rng);
        d_x <= p0_x;
    end

    wire [M-1:0] mf;
    wire         df;
    genvar p;
    generate
        for (p = 0; p < M; p = p + 1) begin : g_p
            ot_hdc_qmul u_mul (.clk(clk), .rst_n(rst_n), .v(d_v), .a(d_w), .b({d_x[16*p +: 16], 16'h0000}),
                               .y(y[32*p +: 32]), .fault(mf[p]));
        end
    endgenerate
    ot_hdc_delay #(.W(1), .D(3), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(d_v), .q(ov));
    ot_hdc_delay #(.W(1), .D(3)) u_f (.clk(clk), .rst_n(rst_n), .d(d_f), .q(df));
    assign f = mf | {M{df & ov}};
endmodule

// Eight MAC lanes and their chain: one chunk of 8 contiguous K terms.  Lane c's operands
// are presented at t + SK(c) (SK = 0,0,3,..,18); the chunk sum leaves at t + 26.
module ot_hdc_v41x_wgt_mchunk #(
    parameter integer M = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        v,
    input  wire [7:0]        z,
    input  wire [7:0]        f8,
    input  wire [8*32-1:0]   w,
    input  wire [8*M*16-1:0] x,
    output wire              ov,
    output wire [M*32-1:0]   s,
    output wire [M-1:0]      sf
);
    wire [7:0]        pv;
    wire [8*M*32-1:0] py;
    wire [8*M-1:0]    pf;
    genvar c;
    generate
        for (c = 0; c < 8; c = c + 1) begin : g_l
            ot_hdc_v41x_wgt_mlane #(.M(M)) u_l (.clk(clk), .rst_n(rst_n), .v(v[c]), .z(z[c]), .f8(f8[c]),
                                                .w(w[32*c +: 32]), .x(x[c*M*16 +: M*16]), .ov(pv[c]),
                                                .y(py[c*M*32 +: M*32]), .f(pf[c*M +: M]));
        end
    endgenerate
    ot_hdc_v41x_wgt_chain #(.M(M)) u_ch (.clk(clk), .rst_n(rst_n), .v(pv), .t(py), .tf(pf), .ov(ov), .s(s), .sf(sf));
endmodule

// Eight block-dot lanes and their chain: one chunk of 8 contiguous 32-blocks (256 K terms).
// Lane c's operands at t + SK(c); the chunk sum leaves at t + 30.
module ot_hdc_v41x_wgt_qchunk #(
    parameter integer M = 1
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [7:0]         v,
    input  wire [7:0]         z,
    input  wire [7:0]         fp4,
    input  wire [8*264-1:0]   w,
    input  wire [8*M*264-1:0] x,
    output wire               ov,
    output wire [M*32-1:0]    s,
    output wire [M-1:0]       sf
);
    wire [7:0]        pv;
    wire [8*M*32-1:0] py;
    wire [8*M-1:0]    pf;
    genvar c;
    generate
        for (c = 0; c < 8; c = c + 1) begin : g_l
            ot_hdc_v41x_wgt_bdot #(.M(M)) u_l (.clk(clk), .rst_n(rst_n), .v(v[c]), .z(z[c]), .fp4(fp4[c]),
                                               .w(w[264*c +: 264]), .x(x[c*M*264 +: M*264]), .ov(pv[c]),
                                               .y(py[c*M*32 +: M*32]), .f(pf[c*M +: M]));
        end
    endgenerate
    ot_hdc_v41x_wgt_chain #(.M(M)) u_ch (.clk(clk), .rst_n(rst_n), .v(pv), .t(py), .tf(pf), .ov(ov), .s(s), .sf(sf));
endmodule
