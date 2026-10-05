`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One-operation delay probes for the ABI 3.0 engine arithmetic.
//
// Each module wraps exactly one function of the numeric or storage-format
// package as a single combinational cloud between an input port and one
// register, so that a synthesis-plus-static-timing run attributes delay and
// area to that operation and to nothing else.  They exist to answer "which
// operation sets the lane's period", which a whole-lane number cannot.
//
// These are characterisation vehicles, not deliverable blocks: they compute a
// single element and carry no control, so their area is the arithmetic's area
// and their delay is the arithmetic's delay, and neither is a claim about a
// datapath's throughput.
// ---------------------------------------------------------------------------

module ot_a3_probe_fp32_mul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [33:0] r
);
    wire [33:0] w = ot_fp32_rne_pkg::fp32_mul_rne(a, b);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r <= 34'b0; else r <= w;
endmodule

module ot_a3_probe_fp32_add (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [33:0] r
);
    wire [33:0] w = ot_fp32_rne_pkg::fp32_add_rne(a, b);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r <= 34'b0; else r <= w;
endmodule

module ot_a3_probe_bf16_round (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [33:0] r
);
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(a ^ b);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r <= 34'b0; else r <= {15'b0, narrowed};
endmodule

module ot_a3_probe_format_decode (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [33:0] r
);
    wire [33:0] w = ot_a3_format_pkg::decode_element(a[7:0], b);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r <= 34'b0; else r <= w;
endmodule
