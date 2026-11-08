`timescale 1ns/1ps
// A register in its own kept hierarchy: duplicate copies of one signal stay separate cells (yosys merges equal
// flip-flops inside a flattened module whatever their wire attributes).  R = 1: asynchronous active-low reset to 0.
(* keep_hierarchy *)
module ot_hdc_v41x_kreg #(
    parameter integer W = 1,
    parameter integer R = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    generate if (R != 0) begin : g_r
        always @(posedge clk or negedge rst_n)
            if (!rst_n) q <= {W{1'b0}};
            else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule
