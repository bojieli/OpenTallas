`timescale 1ns/1ps
// SIMULATION-ONLY companion of rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv: the fixed-latency tops of
// rtl/hdc/ot_hdc_fp32_mul_lat.sv and rtl/hdc/ot_hdc_fp32_add_lat.sv, verbatim, for builds that replace those two
// files by the DPI stand-ins of the parameterised units (same ports, same LAT register stages, II 1, same function).
// The W11 stream unit at N = 1,024 light lanes elaborates ~6,000 bit-level FP units, which Verilator cannot build in
// memory (> 270 GB measured); tools/dshbm_baseline_measure.py su-equiv runs the same cases at N = 64 both ways and
// requires identical memory images and identical per-op cycle traces.  Never synthesised.
module ot_hdc_fp32_mul_lat4 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5i (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(5), .CUTS(5)) u (.*);
endmodule
module ot_hdc_fp32_add_lat3 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(3)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4i (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(4), .CUTS(1)) u (.*);
endmodule
