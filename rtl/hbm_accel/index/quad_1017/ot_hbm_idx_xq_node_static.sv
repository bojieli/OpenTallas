`default_nettype none
// HBM d4g plan (b) IDX cross-quadrant score tree node (lane HBM-B-RTL2, 2026-10-17). One master for both levels of
// the registered merge tree that carries the 4 quadrant score lists to the stack-shared selector / top-k link:
//   level 1 (one per stack, between its two quadrants): {quarter 1 list, quarter 0 list} -> the stack's 16-lane group
//   level 2 (root, beside idx_sel):                      {stack 1 group, stack 0 group}   -> the selector in_line
// Every input lands in a pin flop and the output leaves a flop: 2 edges per node, fixed (the compiler's
// --score-chain counts them). Concatenation only (no arithmetic, no arbitration, no ready/credit).
// RESET: rst_n drives only ot_rst_relay; all node flops are reset (the lists carry valid bits).
// HBM-NSFIX 10-18: the relay has one region per <=256 node flops (4*WI flops: a_r, b_r, y), flop k on region
// k*RG/(4*WI), so no reset net carries more than ~256 loads (textbook high_fanout rule). Function and latency unchanged.
module ot_hbm_idx_xq_node_static #(parameter integer WI=297)(
 input wire clk,rst_n,
 input wire[WI-1:0]a,b,
 output reg[2*WI-1:0]y
);
 localparam integer NF=4*WI;
 localparam integer RG=(NF+255)/256;
 wire[RG-1:0]rst_c;
 ot_rst_relay #(.REGIONS(RG),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_c));
 reg[WI-1:0]a_r,b_r;
 genvar i;
 generate for(i=0;i<WI;i=i+1)begin:g_in
  always @(posedge clk or negedge rst_c[(i*RG)/NF]) if(!rst_c[(i*RG)/NF]) a_r[i]<=1'b0; else a_r[i]<=a[i];
  always @(posedge clk or negedge rst_c[((WI+i)*RG)/NF]) if(!rst_c[((WI+i)*RG)/NF]) b_r[i]<=1'b0; else b_r[i]<=b[i];
 end
 for(i=0;i<WI;i=i+1)begin:g_out
  always @(posedge clk or negedge rst_c[((2*WI+i)*RG)/NF]) if(!rst_c[((2*WI+i)*RG)/NF]) y[i]<=1'b0; else y[i]<=a_r[i];
  always @(posedge clk or negedge rst_c[((3*WI+i)*RG)/NF]) if(!rst_c[((3*WI+i)*RG)/NF]) y[WI+i]<=1'b0; else y[WI+i]<=b_r[i];
 end endgenerate
endmodule
`default_nettype wire
