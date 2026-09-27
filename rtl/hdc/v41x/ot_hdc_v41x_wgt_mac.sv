`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// BF16/FP32-weight MAC lane of the V4.1x weight engine (block `wgt`, the "ME"):
// the product of tools/hdc_golden_v41.matvec_c under R-ARITH,
// mul(w, to_bf16(x)) -- one IEEE binary32 multiply, RNE, gradual underflow,
// a zero operand giving +0 -- by the qualified ot_hdc_qmul with the
// activation's low 16 bits tied to zero (x is BF16: synthesis keeps an 24 x 8
// significand product).  w is the weight's binary32 bits: an FP32 weight (the
// router gate) as stored, a BF16 weight as {bf16, 16'h0} (the ROM bank of a
// BF16 matrix is 16 bits wide; the read network appends the zeros).  The
// product is exact for a BF16 weight, rounded once for an FP32 one, as the
// golden.  The chunk's adds are the chain (ot_hdc_v41x_wgt_chain): a chunk of
// 8 = a chain of 8 MACs.
// M positions (MTP lane multiplier) share the weight word.
// LATENCY 4: P0 input register + the 3-cycle multiply.  z forces +0.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_wgt_mlane #(
    parameter integer M = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            z,
    input  wire [31:0]     w,
    input  wire [M*16-1:0] x,
    output wire            ov,
    output wire [M*32-1:0] y,
    output wire [M-1:0]    f
);
    reg            p0_v;
    reg [31:0]     p0_w;
    reg [M*16-1:0] p0_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) p0_v <= 1'b0;
        else p0_v <= v;
    end
    always @(posedge clk) begin
        p0_w <= z ? 32'd0 : w;
        p0_x <= x;
    end
    genvar p;
    generate
        for (p = 0; p < M; p = p + 1) begin : g_p
            ot_hdc_qmul u_mul (.clk(clk), .rst_n(rst_n), .v(p0_v), .a(p0_w), .b({p0_x[16*p +: 16], 16'h0000}),
                               .y(y[32*p +: 32]), .fault(f[p]));
        end
    endgenerate
    ot_hdc_delay #(.W(1), .D(3), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(p0_v), .q(ov));
endmodule

// Eight MAC lanes and their chain: one chunk of 8 contiguous K terms.  Lane c's operands
// are presented at t + SK(c) (SK = 0,0,3,..,18); the chunk sum leaves at t + 25.
module ot_hdc_v41x_wgt_mchunk #(
    parameter integer M = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        v,
    input  wire [7:0]        z,
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
            ot_hdc_v41x_wgt_mlane #(.M(M)) u_l (.clk(clk), .rst_n(rst_n), .v(v[c]), .z(z[c]), .w(w[32*c +: 32]),
                                                .x(x[c*M*16 +: M*16]), .ov(pv[c]), .y(py[c*M*32 +: M*32]),
                                                .f(pf[c*M +: M]));
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
