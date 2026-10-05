`timescale 1ns/1ps
// SIMULATION-ONLY behavioural stand-ins for rtl/hdc/ot_hdc_prefix.sv: the same ports and the same function (W-bit
// integer add with carry in / carry out; W-bit increment with carry out), written as the `+` the (* keep *)
// Kogge-Stone networks exist only to stop synthesis from re-rippling.  Combinational in both, so cycle timing is
// unchanged.  For the N = 1,024 stream-unit bench (tools/dshbm_baseline_measure.py --fp dpi_beh), whose ~40,000
// prefix networks Verilator elaborates bit by bit.  Never synthesised.
module ot_hdc_ksadd_k #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
endmodule

module ot_hdc_inc_k #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    assign {co, y} = {1'b0, a} + {{W{1'b0}}, inc};
endmodule
