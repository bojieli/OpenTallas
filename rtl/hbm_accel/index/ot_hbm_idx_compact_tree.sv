`default_nettype none
// Stable, same-cycle compaction. Each node carries only its bounded subtree;
// the count width and shift destination never become a serial 32-bit index.
module ot_hbm_idx_compact_tree #(parameter integer N=64,W=64)(
 input wire[N-1:0]mask,input wire[N*W-1:0]words,
 output wire[N*W-1:0]packed_words,
 output wire[$clog2(N+1)-1:0]count
);
 generate if(N==1)begin:leaf
  assign packed_words=mask[0]?words:{W{1'b0}};
  assign count=mask[0];
 end else begin:branch
  localparam integer L=N/2,R=N-L;
  wire[L*W-1:0]left;wire[R*W-1:0]right;
  wire[$clog2(L+1)-1:0]lc;wire[$clog2(R+1)-1:0]rc;
  ot_hbm_idx_compact_tree #(.N(L),.W(W)) lhs(
   .mask(mask[L-1:0]),.words(words[L*W-1:0]),.packed_words(left),.count(lc));
  ot_hbm_idx_compact_tree #(.N(R),.W(W)) rhs(
   .mask(mask[N-1:L]),.words(words[N*W-1:L*W]),.packed_words(right),.count(rc));
  assign count=($clog2(N+1))'(lc)+($clog2(N+1))'(rc);
  assign packed_words={{R*W{1'b0}},left}|({{L*W{1'b0}},right} << (lc*W));
 end endgenerate
endmodule
`default_nettype wire
