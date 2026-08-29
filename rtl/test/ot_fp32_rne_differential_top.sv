`timescale 1ns/1ps
module ot_fp32_rne_differential_top (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] left_code,
    input  wire [31:0] right_code,
    output wire [33:0] add_result,
    output wire [33:0] mul_result,
    output wire [18:0] bf16_result,
    input  wire        rsqrt_in_valid,
    output wire        rsqrt_in_ready,
    input  wire [31:0] argument_code,
    output wire        rsqrt_out_valid,
    input  wire        rsqrt_out_ready,
    output wire [31:0] rsqrt_result_code,
    output wire [1:0]  rsqrt_result_error
);
    import ot_fp32_rne_pkg::*;

    assign add_result = fp32_add_positive_rne(left_code, right_code);
    assign mul_result = fp32_mul_rne(left_code, right_code);
    assign bf16_result = fp32_to_bf16_rne(left_code);

    ot_fp32_rsqrt_rne rsqrt (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(rsqrt_in_valid),
        .in_ready(rsqrt_in_ready),
        .argument_code(argument_code),
        .out_valid(rsqrt_out_valid),
        .out_ready(rsqrt_out_ready),
        .result_code(rsqrt_result_code),
        .result_error(rsqrt_result_error)
    );
endmodule
