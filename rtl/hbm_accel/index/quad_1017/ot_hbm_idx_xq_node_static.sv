`default_nettype none
// HBM d4g plan (b) IDX cross-quadrant score tree node (lane HBM-B-RTL2, 2026-10-17). One master for both levels of
// the registered merge tree that carries the 4 quadrant score lists to the stack-shared selector / top-k link:
//   level 1 (one per stack, between its two quadrants): {quarter 1 list, quarter 0 list} -> the stack's 16-lane group
//   level 2 (root, beside idx_sel):                      {stack 1 group, stack 0 group}   -> the selector in_line
// Every input lands in a pin flop and the output leaves a flop: 2 edges per node, fixed (the compiler's
// --score-chain counts them). Concatenation only (no arithmetic, no arbitration, no ready/credit).
// RESET: rst_n drives only ot_rst_relay; all node flops are reset (the lists carry valid bits).
module ot_hbm_idx_xq_node_static #(parameter integer WI=297)(
 input wire clk,rst_n,
 input wire[WI-1:0]a,b,
 output reg[2*WI-1:0]y
);
 wire rst_c;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_c));
 reg[WI-1:0]a_r,b_r;
 always @(posedge clk or negedge rst_c)
  if(!rst_c)begin a_r<=0;b_r<=0;y<=0;end
  else begin a_r<=a;b_r<=b;y<={b_r,a_r};end
endmodule
`default_nettype wire
