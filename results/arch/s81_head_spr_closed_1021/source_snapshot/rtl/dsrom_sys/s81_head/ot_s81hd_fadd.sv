`timescale 1ns/1ps
// ot_s81hd_fadd (S81-HEAD HD-TILE 10-21): the head element's binary32 adder.  NC = 1: the bounded native-census
// fp32_add_rne netlist ot_hdc_fp32_add_lat_fan32 #(LAT 7, DRST 0, SAFE_DIST 1) (only valid bits reset; y / err are
// qualified by valid_out); NC = 0: ot_v41_fadd #(CUT, SPLIT9) (the original element adder).  Both are bit-identical to
// fp32_add_rne (every zero result +0; err != 0 on a nonfinite operand or overflow).
module ot_s81hd_fadd #(
    parameter integer NC = 1,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SPLIT9 = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire [1:0]  err,
    output wire        valid_out
);
    generate if (NC) begin : g_nc
        ot_hdc_fp32_add_lat_fan32 #(.LAT(7), .CUTS(-1), .DRST(0), .SAFE_DIST(1)) u_a (
            .clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b), .y(y), .err(err), .valid_out(valid_out));
    end else begin : g_v41
        ot_v41_fadd #(.CUT(CUT), .SPLIT9(SPLIT9)) u_a (
            .clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b), .y(y), .err(err), .valid_out(valid_out));
    end endgenerate
endmodule
