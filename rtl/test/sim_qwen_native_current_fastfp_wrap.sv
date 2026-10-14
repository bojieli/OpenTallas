`timescale 1ns/1ps
// SIMULATION ONLY. Current parameterized wrappers copied verbatim from ot_hdc_fastfp.sv.
// Fault-reporting wrappers, as ot_hdc_fadd / ot_hdc_fmul but LATENCY 3.
module ot_hdc_qadd #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_add_fast (unchanged); L > 3 is ot_hdc_fp32_add_lat #(L), bit for bit
    // the same values, with the extra cuts (rtl/hdc/ot_hdc_fp32_add_lat.sv) so no stage carries two prefix adders.
    parameter integer L = 3
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
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_add_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_add_lat #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_qmul #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_mul_fast (unchanged); L > 3 is ot_hdc_fp32_mul_lat #(L), bit for bit
    // the same values; L >= 5 cuts the four carry-save levels from the 48-bit prefix add (fast stage 2, the lane
    // tile's -180 ps TT path s1_rows -> s2_prod).
    parameter integer L = 3
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
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_mul_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_mul_lat #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule
