`timescale 1ns/1ps
// SIMULATION-ONLY stand-ins for ot_hdc_fp32_add_lat / ot_hdc_fp32_mul_lat (rtl/hdc/ot_hdc_fp32_{add,mul}_lat.sv): the
// same ports, the same LAT register stages and II 1, the same function -- IEEE binary32 RNE with gradual underflow
// (host float arithmetic, sim_nhb_fp_lat_dpi.cpp), every zero result +0, a nonfinite operand -> err 1, an
// overflowing result -> err 2, y = 0 on error.  The units' bit-level Kogge-Stone prefix networks make Verilator emit
// ~1 MB of C++ per instance, so the full-width (head_dim 128) 4-stack bench cannot be compiled with ~13,000 of them;
// the same bench at head_dim 16 runs the REAL units, and rtl/test/nearhbm/run_nearhbm_gate.sh runs it both ways on
// the same vectors and requires identical results (the precedent: rtl/test/sim_hdc_v41x_fastfp_dpi.sv).
// Never synthesised.
module ot_hdc_fp32_add_lat #(
    parameter integer LAT = 3,
    parameter integer CUTS = -1
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
    import "DPI-C" function int unsigned nhb_fadd(input int unsigned a, input int unsigned b, output int err);
    reg [31:0] yl [0:LAT-1];
    reg [1:0]  el [0:LAT-1];
    reg [LAT-1:0] vl;
    int e;
    integer i;
    always @(posedge clk) begin
        yl[0] <= nhb_fadd(a, b, e);
        el[0] <= e[1:0];
        for (i = 1; i < LAT; i = i + 1) begin yl[i] <= yl[i-1]; el[i] <= el[i-1]; end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vl <= 0;
        else vl <= {vl[LAT-2:0], valid_in};
    end
    assign y = yl[LAT-1];
    assign err = el[LAT-1];
    assign valid_out = vl[LAT-1];
endmodule

module ot_hdc_fp32_mul_lat #(
    parameter integer LAT = 3,
    parameter integer CUTS = -1
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
    import "DPI-C" function int unsigned nhb_fmul(input int unsigned a, input int unsigned b, output int err);
    reg [31:0] yl [0:LAT-1];
    reg [1:0]  el [0:LAT-1];
    reg [LAT-1:0] vl;
    int e;
    integer i;
    always @(posedge clk) begin
        yl[0] <= nhb_fmul(a, b, e);
        el[0] <= e[1:0];
        for (i = 1; i < LAT; i = i + 1) begin yl[i] <= yl[i-1]; el[i] <= el[i-1]; end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) vl <= 0;
        else vl <= {vl[LAT-2:0], valid_in};
    end
    assign y = yl[LAT-1];
    assign err = el[LAT-1];
    assign valid_out = vl[LAT-1];
endmodule
