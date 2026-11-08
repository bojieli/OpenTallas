`timescale 1ns/1ps
// DS-ROM recovery su_swiglu: the six-cut f12 binary32 adder top (the _l5x cut set of rtl/hdc/ot_hdc_fp32_f12.sv plus a
// cut between the magnitude compare and the alignment, CUTS bit 0).  Same function as every ot_hdc_fp32_add_f12 cut
// set; a fixed top so a simulation bench can swap in its DPI stand-in (rtl/test/sim_dsrom_su_add6_dpi.sv).
module ot_hdc_fp32_add_f12_l6x (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_f12 #(.CUTS(7'b1101011)) u (.*);
endmodule
