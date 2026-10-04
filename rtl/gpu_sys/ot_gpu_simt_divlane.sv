`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_simt_divlane: one SIMT lane of the optional div.rn / sqrt.rn unit:
// the qualified correctly-rounded binary32 divider rtl/abi3/
// ot_a3_fp32_div_rne_pipe.sv and square root rtl/abi3/ot_a3_fp32_sqrt_rne.sv
// (IEEE RNE results, as CUDA's div.rn.f32 / sqrt.rn.f32), each failing
// closed on an invalid operand.  Non-inlined, as ot_gpu_simt_lane.
// ---------------------------------------------------------------------------
module ot_gpu_simt_divlane (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        go,
    input  wire        sqrt,
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire        take,
    output wire        dv_v,
    output wire [31:0] dv_y,
    output wire        dv_e,
    output wire        sq_v,
    output wire [31:0] sq_y,
    output wire        sq_e
);
    /*verilator no_inline_module*/
    wire [1:0] de;
    wire inr, sb;
    ot_a3_fp32_div_rne_pipe u_div (.clk(clk), .rst_n(rst_n), .in_valid(go && !sqrt), .in_ready(inr),
        .numerator_code(a), .denominator_code(b), .out_valid(dv_v), .out_ready(take), .result_code(dv_y),
        .result_error(de));
    assign dv_e = de != 2'd0;
    ot_a3_fp32_sqrt_rne u_sqrt (.clk(clk), .rst_n(rst_n), .valid_in(go && sqrt), .a(a), .y(sq_y), .invalid(sq_e),
        .valid_out(sq_v), .busy(sb));
endmodule
