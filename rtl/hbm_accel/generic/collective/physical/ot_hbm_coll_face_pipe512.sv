`timescale 1ns/1ps
// One true own-flop leaf: immutable five-cycle die-wrapper register depth, 2560 sinks.
module ot_hbm_coll_face_pipe512 (input wire clk, input wire [511:0] d, output wire [511:0] q);
    reg [511:0] r0, r1, r2, r3, r4;
    always @(posedge clk) begin r0 <= d; r1 <= r0; r2 <= r1; r3 <= r2; r4 <= r3; end
`ifdef OT_HBM_COLL_FACE_EARLY
    assign q = r3; // Mutation: publication crosses the face one cycle too early.
`else
    assign q = r4;
`endif
endmodule
