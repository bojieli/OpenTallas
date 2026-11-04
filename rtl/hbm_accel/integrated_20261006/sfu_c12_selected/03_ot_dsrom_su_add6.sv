// Integration-only c12 namespace export. Canonical source: rtl/hdc/v41x/ot_dsrom_su_add6.sv
`timescale 1ns/1ps
// DS-ROM recovery su_swiglu: the six-cut f12 binary32 adder top (the _l5x cut set of rtl/hdc/ot_hdc_fp32_f12.sv plus a
// cut between the magnitude compare and the alignment, CUTS bit 0).  Same function as every ot_hbm_selected_c12__ot_hdc_fp32_add_f12 cut
// set; a fixed top so a simulation bench can swap in its DPI stand-in (rtl/test/sim_dsrom_su_add6_dpi.sv).
module ot_hbm_selected_c12__ot_hdc_fp32_add_f12_l6x (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hbm_selected_c12__ot_hdc_fp32_add_f12 #(.CUTS(7'b1101011)) u (.*);
endmodule
// 11-03 (DIE-HBM-61 RE-FORM, opt-in only): the _l6x cut set plus CUTS bit 2 (the k1 -> k3 span missed 583 ps in the
// tailx_rest gate).  LAT 7, same function; no existing user selects it (ot_hbm_selected_c12__ot_hdc_qadd_lat L7X = 1).
module ot_hbm_selected_c12__ot_hdc_fp32_add_f12_l7x (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hbm_selected_c12__ot_hdc_fp32_add_f12 #(.CUTS(7'b1101111)) u (.*);
endmodule
