// Explicit STATUS observer ABI v1; legacy source remains unchanged. Payload is meaningful after its real event.
`timescale 1ns/1ps
// Recompute the capture AND inside each kept local block.  A shared wide
// enable never crosses the block boundary; each local root serves <=15 bits.
(* keep_hierarchy = "yes" *)
module qfd_status_obs_hold_chunk #(parameter integer W=15, FINAL_DECODE=0) (
 input wire ck, a, b, c, input wire [W-1:0] d, output reg [W-1:0] q
);
 wire accept;
 generate if(FINAL_DECODE)begin:g_final
  qfd_n59_final_decode #(.N(3)) u_decode(.a({a,b,c}),.y(accept));
 end else begin:g_legacy assign accept=a&&b&&c;end endgenerate
 always @(posedge ck) if (accept) q <= d;
endmodule

// A real final AND gate stays inside each local capture domain. Prevent ABC
// from factoring its inputs into every payload mux across sibling domains.
(* keep_hierarchy = "yes" *)
module qfd_n59_final_decode #(parameter integer N=3)(input wire[N-1:0]a,output wire y);
 assign y=&a;
endmodule
