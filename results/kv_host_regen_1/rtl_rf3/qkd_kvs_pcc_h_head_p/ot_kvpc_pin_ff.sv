`timescale 1ns/1ps
// PATH-KV-PC 10-25: kept single-bit boundary flops (keep_hierarchy: opt_merge / const folding cannot fold them)
(* keep_hierarchy *) module ot_kvpc_pin_dff(input wire ck, input wire d, output reg q);
 always @(posedge ck) q <= d;
endmodule
(* keep_hierarchy *) module ot_kvpc_pin_ar0(input wire ck, input wire rn, input wire d, output reg q);
 always @(posedge ck or negedge rn) if (!rn) q <= 1'b0; else q <= d;
endmodule
