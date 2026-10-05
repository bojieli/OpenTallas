`timescale 1ns/1ps
// SIMULATION-ONLY companion of rtl/test/sim_hdc_v41x_fastfp_dpi.sv: the fault-reporting wrappers
// ot_hdc_qadd / ot_hdc_qmul of rtl/hdc/ot_hdc_fastfp.sv, verbatim, for builds that replace
// ot_hdc_fastfp.sv by the host-float stand-ins (tools/rtl_hdc_v41x_decode_campaign.py --fp dpi).
// Never synthesised.
// Fault-reporting wrappers, as ot_hdc_fadd / ot_hdc_fmul but LATENCY 3.
module ot_hdc_qadd (
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
    ot_hdc_fp32_add_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_qmul (
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
    ot_hdc_fp32_mul_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule
