`timescale 1ns/1ps
// SIMULATION-ONLY (hbm-fmax-su): the 1.2 GHz unit tops of rtl/hdc/ot_hdc_fp32_f12.sv as the DPI stand-ins of the
// parameterised units (rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv: same ports, same LAT, II 1, same function), for the
// N = 1,024 stream-unit benches built from rtl/hdc/ot_hdc_fastfp_lat_f12.sv.  Bit-level equivalence of the real
// units: rtl/test/tb_su_fp32_f12.sv; the N = 64 su-equiv runs both.  Never synthesised.
module ot_hdc_fp32_mul_f12_l5 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_f12_l6i (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_add_f12_l4 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_f12_l5i (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_add_f12_l5x (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_f12_l6 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(6)) u (.*);
endmodule
