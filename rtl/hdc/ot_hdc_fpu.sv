`timescale 1ns/1ps
// Thin wrappers over the qualified binary32 pipes (rtl/proto): one result per
// cycle, LATENCY = 5, IEEE RNE with gradual underflow and canonical +0 zeros.
// A nonfinite operand or an overflow raises `fault` on a valid result; the
// decode core ORs every fault into one sticky status bit.
module ot_hdc_fadd (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    ot_fp32_add_rne_pipe u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b),
                            .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_fmul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    ot_fp32_mul_rne_pipe u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b),
                            .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule
