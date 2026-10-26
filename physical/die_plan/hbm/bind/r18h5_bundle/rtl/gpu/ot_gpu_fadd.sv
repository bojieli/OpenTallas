`timescale 1ns/1ps
// FP32 RNE add of the GPU-organised SM at the 1.2 GHz SS clock: W11's ot_hdc_fp32_add_lat (bit-identical to the
// qualified ot_fp32_add_rne_pipe through ot_hdc_fp32_add_fast) with LAT register stages, in the ot_hdc_fadd
// port shape (y, fault).  LAT = 5 is the qualified depth; LAT = 7 closes 1.2 GHz at SS (W11, routed).
module ot_gpu_fadd #(
    parameter integer LAT = 7
) (
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
    ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                         .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

// FP32 RNE multiply (row scale) at the SS clock: W11's ot_hdc_fp32_mul_lat, in the ot_hdc_fmul port shape.
module ot_gpu_fmul #(
    parameter integer LAT = 7
) (
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
    ot_hdc_fp32_mul_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                         .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule
