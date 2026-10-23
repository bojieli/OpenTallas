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
    // ATTW R3: same-edge, source-level reset distribution. No storage or cycle is added.
    wire [0:0] attw_reset_leaf;
`ifdef OT_S81_ATTW_RESET_R3
    ot_s81_attw_reset_fork #(.N(1)) u_attw_reset_fork (.d(rst_n), .q(attw_reset_leaf));
`else
    assign attw_reset_leaf = {1{rst_n}};
`endif

    generate if (R != 0) begin : g_r
        always @(posedge clk or negedge attw_reset_leaf[0])
            if (!attw_reset_leaf[0]) q <= {W{1'b0}};
            else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule
