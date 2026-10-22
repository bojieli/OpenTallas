`timescale 1ns/1ps
`default_nettype none
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// HBMb/HC-SFU 10-21 (PD-AUDIT (1)): registered, relayed 16 -> 1 OR of per-lane sticky-fault partials for the SFU core.
// Lane order follows the k10 perimeter floorplan: lanes 4q..4q+3 sit on side q (W, N, E, S), adjacent lanes ~475 um
// apart.  Stages (each one flop row, every hop planned <= ~405 um): s0 one flop per lane (at the lane), s1 one per
// adjacent lane pair (between the pair, <= ~240 um), s2 one per side (side midpoint, ~475/2 um from each pair flop),
// s3/s4 two relays per side toward the store/engine centre (~1 mm in thirds), then one OR into the caller's sticky
// fault.  Age: AGE = 5 edges from the partial to fault_any (diagnostic only; no data or schedule edge moves).
// Plus one local partial loc (store/engine-local checks) aged by the same 5 edges.  Reset: these are fault-valid bits
// (control), reset with the caller's regional rst_n; no payload is reset.
module ot_hgi_sfu_fault_tree(
 input wire clk,rst_n,
 input wire [15:0] lane_bad,
 input wire loc_bad,
 output wire fault_any
);
 (* keep=1,dont_touch=1 *) reg [15:0] s0;
 (* keep=1,dont_touch=1 *) reg [7:0] s1;
 (* keep=1,dont_touch=1 *) reg [3:0] s2,s3,s4;
 reg [4:0] loc_q;
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)begin s0<=0;s1<=0;s2<=0;s3<=0;s4<=0;loc_q<=0;end
  else begin
`ifdef OT_SFU_FTREE_MUT_DROP13
   s0<=lane_bad&~16'h2000;   // negative control: lane 13's partial never reaches the tree
`else
   s0<=lane_bad;
`endif
   for(integer p=0;p<8;p=p+1)s1[p]<=s0[2*p]|s0[2*p+1];
   for(integer q=0;q<4;q=q+1)s2[q]<=s1[2*q]|s1[2*q+1];
   s3<=s2;s4<=s3;
   loc_q<={loc_q[3:0],loc_bad};
  end
 assign fault_any=(|s4)|loc_q[4];
endmodule
`default_nettype wire
