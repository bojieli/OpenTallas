`timescale 1ns/1ps
`default_nettype none
// SVC-SMALL 2026-10-18: one hardened block per d4g fault-leaf parameter set that is not routed as ot_hbm_fault_leaf itself
// (closure-loop cap: 3 routes per block per source commit; coordinator 10-18: thin per-variant wrappers, no quantising
// with tied spare inputs).  Each wrapper is exactly ot_hbm_fault_leaf at its die parameters (no logic of its own, every
// input a real die net).  ot_hbm_fault_leaf itself stays the block of N4/0x8 (x4), N5/0x8 (x12) and N7/0x20 (x1).
// MUT passes through for the bench only.
// d4g instances: fs_SW, fs_NW
module ot_hbm_fault_leaf_n8_s0 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [7:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(8), .SYNC_MASK(64'h0), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
// d4g instances: fr_NE
module ot_hbm_fault_leaf_n8_s40 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [7:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(8), .SYNC_MASK(64'h40), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
// d4g instances: fr_NW
module ot_hbm_fault_leaf_n9_s40 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [8:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(9), .SYNC_MASK(64'h40), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
// d4g instances: fr_SW
module ot_hbm_fault_leaf_n11_s100 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [10:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(11), .SYNC_MASK(64'h100), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
`default_nettype wire
