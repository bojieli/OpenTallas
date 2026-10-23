// Explicit STATUS observer ABI v1; legacy source remains unchanged. Payload is meaningful after its real event.
`timescale 1ns/1ps
// Recompute the capture AND inside each kept local block.  A shared wide
// enable never crosses the block boundary; each local root serves <=15 bits.
(* keep_hierarchy = "yes" *)
module qfd_status_obs_hold_chunk #(parameter integer W=15) (
 input wire ck, a, b, c, input wire [W-1:0] d, output reg [W-1:0] q
);
 always @(posedge ck) if (a && b && c) q <= d;
endmodule
