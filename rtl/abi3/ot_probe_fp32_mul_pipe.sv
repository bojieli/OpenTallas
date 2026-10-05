`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The pipelined twin of ``ot_probe_fp32_mul``.
//
// ``ot_probe_fp32_mul`` registers the output of the COMBINATIONAL
// ``ot_fp32_rne_pkg::fp32_mul_rne``; this registers the output of the
// five-stage ``ot_fp32_mul_rne_pipe``.  Same ports, same input and output
// registers, same corner and flow -- the only difference is the construct.
//
// It exists to measure that difference on ONE design rather than inferring it
// from two different blocks that happen to differ in it, which is the caveat
// recorded against the frequency comparison in
// ``results/physical_abi3/asap7/combinational_fp32_multiply_audit.json``.
//
// This is a characterisation probe.  Nothing instantiates it, and it is not on
// the ABI 3.0 datapath's clock.
// ---------------------------------------------------------------------------
module ot_probe_fp32_mul_pipe (
    input wire clk, input wire rst_n,
    input wire [31:0] a, input wire [31:0] b,
    output reg [33:0] y
);
    wire [31:0] product;
    wire [1:0]  product_err;
    wire        product_valid;

    ot_fp32_mul_rne_pipe multiply (
        .clk(clk),
        .rst_n(rst_n),
        .valid_in(1'b1),
        .a(a),
        .b(b),
        .y(product),
        .err(product_err),
        .valid_out(product_valid)
    );

    always @(posedge clk or negedge rst_n)
        if (!rst_n) y <= 34'b0;
        else y <= {product_err, product};
endmodule
