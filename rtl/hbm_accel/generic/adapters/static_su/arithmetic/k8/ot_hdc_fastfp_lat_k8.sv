`timescale 1ns/1ps
// HBM-KIND8 (10-20): KIND1/KIND2 lane-leaf wrappers of ot_hdc_qmul_lat / ot_hdc_qadd_lat (rtl/hdc/ot_hdc_fastfp_lat.sv)
// for the one shipped configuration (MLAT 4 input-cut, ALAT 3 keep-prefix): the multiply is the native-32
// ot_hdc_fp32_mul_lat4i_k8 (k8/ot_hdc_fp32_mul_lat_k8.sv); the add is ot_hdc_fp32_add_lat3 unchanged (DRST from
// OT_FP_DATA_NORST in the kit).  Same ports, same latency, bit for bit.
module ot_hdc_qmul_lat_k8 #(
    parameter integer LAT = 4
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
    generate if (LAT != 4) begin : g_bad
        ot_hdc_qmul_lat_k8_needs_LAT_4 u_trap ();
    end endgenerate
    ot_hdc_fp32_mul_lat4i_k8 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule
