`timescale 1ns/1ps
// Simulation stand-ins for rtl/hdc/ot_hdc_prefix.sv: the same modules and ports as behavioural
// adds.  The keep-level prefix networks there are an array of (* keep *) nets that Verilator
// cannot schedule flat (UNOPTFLAT), which makes a 2^32-input campaign ~1000x slower.  Each width
// the short softplus instantiates is proved equal to these by SAT (tools/w11_softplus_short.py
// prove; results/rtl/w11_softplus_short.json "prefix_adder_proofs"), so a result simulated with
// this file holds for the synthesised netlist's source.
module ot_hdc_ksadd_k #(parameter integer W = 28) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
endmodule

module ot_hdc_inc_k #(parameter integer W = 24) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    assign {co, y} = {1'b0, a} + {{W{1'b0}}, inc};
endmodule
