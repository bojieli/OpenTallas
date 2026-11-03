`timescale 1ns/1ps
`default_nettype none
// SIMULATION-ONLY body of ot_tkm_lt_live (TOK-QK-2/HBMSRC 2026-11-01).
// The production body (rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv) is a bit-level (* keep *)
// carry-lookahead compare tree, kept on purpose for synthesis (no insbuf padding).  Its function is exactly
// unsigned a < b.  In a whole-die Verilator elaboration each instance costs ~8.5k AST nodes; the HBM root_4
// partition holds 13,312 of them (32 TKM tiles x 416), 95.5 % of its flattened netlist, and the frontend went
// past 96 GiB.  This body has the same ports, parameter and function and is proven equal to the production body
// by yosys SAT (tools/hbm_layer_vehicle/test_tkm_lt_live_sim.py).  Use it only via an explicit simulation
// module-source map.  Never synthesise it and never put it in a physical file list.
module ot_tkm_lt_live #(parameter integer W = 85) (input wire [W-1:0] a, input wire [W-1:0] b, output wire lt);
    assign lt = a < b;
endmodule
`default_nettype wire
