`timescale 1ns/1ps
// SIMULATION-ONLY: DPI stand-in of ot_hdc_fp32_add_f12_l6x (rtl/hdc/v41x/ot_dsrom_su_add6.sv) for the N = 1,024 benches,
// as rtl/test/sim_hdc_fp32_f12_dpi_tops.sv does for the other f12 tops (same ports, LAT 6, same function).
module ot_hdc_fp32_add_f12_l6x (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(6)) u (.*);
endmodule
