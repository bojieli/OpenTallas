`timescale 1ns/1ps
`default_nettype none
// IDLE-STANDIN 2026-10-19: per-variant wrapper blocks for the HBM d4g GEN2c fault-tree roots that GEN2c binds as SYNTH
// stand-ins (contract_l10 instances of ot_hbm_fault_leaf #(N,SYNC_MASK) with no closed view). Same scheme as
// ot_hbm_fault_leaf_variants.sv (SVC-SMALL 10-18: closure-loop cap 3 routes per block per commit -> thin wrappers, no
// quantising with tied spare inputs). Each wrapper is exactly ot_hbm_fault_leaf at its die parameters; MUT is bench-only.
// Kept in its own file so the closed SVC-SMALL wrapper views keep their source binding.
// GEN2c instances: fr_SW
module ot_hbm_fault_leaf_n11_s120 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [10:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(11), .SYNC_MASK(64'h120), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
// GEN2c instances: fr_SE
module ot_hbm_fault_leaf_n10_s30 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [9:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(10), .SYNC_MASK(64'h30), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
// GEN2c instances: fr_NE
module ot_hbm_fault_leaf_n11_s50 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [10:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(11), .SYNC_MASK(64'h50), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
// GEN2c instances: fr_NW
module ot_hbm_fault_leaf_n10_s50 #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [9:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(10), .SYNC_MASK(64'h50), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
// GEN2c instances: fcx_SW,fcx_SE,fcx_NW,fcx_NE
module ot_hbm_fault_leaf_n6_s3f #(parameter integer MUT = 0)(input wire clk, rst_n, input wire [5:0] in, output wire fault);
    ot_hbm_fault_leaf #(.N(6), .SYNC_MASK(64'h3f), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n), .in(in), .fault(fault));
endmodule
`default_nettype wire
