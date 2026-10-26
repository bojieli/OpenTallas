`timescale 1ns/1ps
// ot_s81hd_oreg (S81-HEAD 10-24): dedicated output (face) register of the rebuilt head element A macro.  W data bits,
// asynchronously cleared by rst_n.  (* keep_hierarchy, keep *) like the die_plan ot_dp_st cells (CP1-R10 face_guard):
// the flop survives Yosys as its own cell, is not folded into an identical internal flop by opt_merge, and its q drives
// only the port.
(* keep_hierarchy, keep *)
module ot_s81hd_oreg #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q <= '0; else q <= d;
endmodule
