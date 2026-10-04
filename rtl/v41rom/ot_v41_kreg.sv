`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_kreg: a W-bit register that synthesis keeps as its own instance (DS-V4.1 ROM q-element QZ, 2026-10-04).
//
// Yosys opt_merge merges flip-flops with identical inputs even when the reg carries (* keep *) / dont_touch
// (measured on the ORFS image's Yosys 0.68: two `(* keep *) reg r` copies fed by one net leave one cell).  In the
// QPIPE q-pair that silently undid the per-macro copies of the issue control and merged the two macro halves'
// lanes (x operand registers, chain forward selects): one register drove both halves across the 510 um die
// (R_cap0 routed netlist: g_mac[0] p0_xq only, r_i2_bk only in g_mac[1]).  A keep_hierarchy module instance is
// not a built-in cell, so it is never merged; each instance is placed and timed on its own.
//
// Function: q <= d on every rising clk edge; with AR = 1, q is held at RV while arst_n is low (asynchronous).
// ---------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_v41_kreg #(
    parameter integer W = 1,
    parameter integer AR = 0,
    parameter [W-1:0] RV = '0
) (
    input  wire         clk,
    input  wire         arst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    if (AR != 0) begin : g_ar
        always @(posedge clk or negedge arst_n) if (!arst_n) q <= RV; else q <= d;
    end else begin : g_nar
        always @(posedge clk) q <= d;
    end
endmodule
