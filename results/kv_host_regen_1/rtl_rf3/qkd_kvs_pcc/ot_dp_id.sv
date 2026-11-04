`timescale 1ns/1ps
// KV-P3-LEAF 10-23: generic position-ID cells of the top-down die plan.  The plan carries position IDs (pc index, slice
// lpc, quadrant stack id, astk row, ...) as counted ID lanes between partitions instead of per-instance straps:
//   ot_dp_id_src  the ONLY place a position constant originates (used only in singleton partition types);
//   ot_dp_id_add  y = a + K (mod 2^W): each partition of a chain of identical partitions forwards its own ID + K;
//   ot_dp_id_rot  rotate an N-element table by one element (element 1 becomes element 0): carries a non-affine position
//                 table (e.g. slg cfg_group = PHYS[row] = 4,5,0,1,2,3,6,7) down a chain of identical partitions; o is the
//                 partition's own entry (element 0).
// All three are pure wiring / constant adders (no state): the receiving leaf's pin register registers the ID.

/* verilator lint_off DECLFILENAME */
module ot_dp_id_src #(
    parameter integer W = 1,
    parameter [W-1:0] V = 0
) (
    output wire [W-1:0] y
);
    assign y = V;
endmodule

module ot_dp_id_add #(
    parameter integer W = 1,
    parameter integer K = 0
) (
    input  wire [W-1:0] a,
    output wire [W-1:0] y
);
    localparam [W+31:0] KX = {{W{K[31]}}, K};   // K sign-extended
    localparam [W-1:0]  KW = KX[W-1:0];          // K mod 2^W
    assign y = a + KW;
endmodule

module ot_dp_id_rot #(
    parameter integer N = 2,
    parameter integer W = 1
) (
    input  wire [N*W-1:0] a,
    output wire [W-1:0]   o,
    output wire [N*W-1:0] y
);
    assign o = a[W-1:0];
    generate
        if (N == 1) begin : g_one
            assign y = a;
        end else begin : g_rot
            assign y = {a[W-1:0], a[N*W-1:W]};
        end
    endgenerate
endmodule
/* verilator lint_on DECLFILENAME */
