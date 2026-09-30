`timescale 1ns/1ps
// FP32 RNE add of the GPU-organised SM at the 1.2 GHz SS clock, in the ot_hdc_fadd port shape (y, fault).
// LAT = 8: W10's ot_v41_fadd (bit-identical to the qualified ot_fp32_add_rne_pipe; explicit (* keep *) prefix
// adders, which ABC cannot re-ripple -- W11's LAT-7 adder rippled to -239 ps at SS inside the routed column).
// LAT 3..7: W11's ot_hdc_fp32_add_lat (pathfinding).
module ot_gpu_fadd #(
    parameter integer LAT = 8
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
    generate if (LAT == 8) begin : g_w10
        ot_v41_fadd u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_w11
        ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                             .valid_out(vo));
    end endgenerate
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
