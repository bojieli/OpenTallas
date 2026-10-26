`timescale 1ns/1ps
// PATH-HBM/TOK 2026-10-25: TKM conv deskew for face-shelled tile chains (see ot_hgi_coll_tkm_static_p HOP).
// The conv shift is a lock-step systolic move through up_out -> up_in, and every up hop carries HOP face edges, so
// tile t must shift exactly HOP edges after tile t+1.  conv_in (the root's conv pin after the root face register) enters
// at the DEEPEST tile (NT-1) and travels toward tile 0 through HOP flops per tile pitch (parallel to the up chain):
// conv_o[t] = conv_in delayed by HOP*(NT-1-t).  No reset (datapath-style control relay, flushed by the root, which
// drives conv 0 from reset).  1 bit, HOP*(NT-1) flops (62 at NT 32, HOP 2).  clr is NOT skewed (broadcast, equal
// latency); the root timeline (SETTLE / clear2 / capture tap) is derived for exactly this skew.
module ot_hgi_coll_tkm_conv_skew #(parameter integer NT=32, HOP=2)(
 input wire clk, input wire conv_in, output wire [NT-1:0] conv_o);
 localparam integer D=HOP*(NT-1);
 reg [(D>0?D:1)-1:0] q;
 always @(posedge clk) q <= {q[(D>1?D-2:0):0], conv_in};
 for (genvar t = 0; t < NT; t = t + 1) begin : g_tap
  localparam integer K = HOP*(NT-1-t);
  if (K == 0) begin : g0 assign conv_o[t] = conv_in; end
  else begin : gk assign conv_o[t] = q[K-1]; end
 end
endmodule
