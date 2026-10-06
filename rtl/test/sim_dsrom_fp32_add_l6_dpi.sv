`timescale 1ns/1ps
// SIMULATION-ONLY: the LAT-6 1.2 GHz adder top of rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv as the DPI stand-in of the
// parameterised adder (rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv: same ports, same LAT, II 1, same function), for the
// full-shape su_norm benches (tools/dsrom_su_norm.py --fp dpi).  Never synthesised.
module ot_dsrom_fp32_add_f12_l6 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                 output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(6)) u (.*);
endmodule
