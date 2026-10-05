`timescale 1ns/1ps
// SIMULATION-ONLY stand-ins for ot_hdc_fp32_add_fast / ot_hdc_fp32_mul_fast
// (rtl/hdc/ot_hdc_fastfp.sv): the same ports, the same LATENCY 3 and II 1, the
// same function -- IEEE binary32 RNE with gradual underflow (host float
// arithmetic, rtl/test/sim_hdc_v41x_fastfp_dpi.cpp), every zero result +0, a
// nonfinite operand -> err 1, an overflowing result -> err 2, y = 0 on error.
// The RTL units' bit-level prefix networks cost Verilator ~0.05 GB per FP unit
// at elaboration, so the 2,048-lane engine (~4,400 units) cannot be compiled
// with them on this machine; this file lets the SPEC-width bench run.  The
// routed-tile bench runs the real units, and the campaign runs the tile both
// ways on the same vectors and requires identical results
// (tools/rtl_hdc_v41x_hcp_campaign.py).  Never synthesised.
import "DPI-C" function int unsigned ot_v41x_fadd(input int unsigned a, input int unsigned b, output int err);
import "DPI-C" function int unsigned ot_v41x_fmul(input int unsigned a, input int unsigned b, output int err);

module ot_hdc_fp32_add_fast (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    reg [31:0] y1, y2;
    reg [1:0]  e1, e2;
    reg        v1, v2;
    int        e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v1 <= 1'b0; v2 <= 1'b0; valid_out <= 1'b0; y <= 32'd0; err <= 2'd0; end
        else begin
            y1 <= ot_v41x_fadd(a, b, e); e1 <= e[1:0]; v1 <= valid_in;
            y2 <= y1; e2 <= e1; v2 <= v1;
            y <= y2; err <= e2; valid_out <= v2;
        end
    end
endmodule

module ot_hdc_fp32_mul_fast (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    reg [31:0] y1, y2;
    reg [1:0]  e1, e2;
    reg        v1, v2;
    int        e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v1 <= 1'b0; v2 <= 1'b0; valid_out <= 1'b0; y <= 32'd0; err <= 2'd0; end
        else begin
            y1 <= ot_v41x_fmul(a, b, e); e1 <= e[1:0]; v1 <= valid_in;
            y2 <= y1; e2 <= e1; v2 <= v1;
            y <= y2; err <= e2; valid_out <= v2;
        end
    end
endmodule
