`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_su_wsplit (HBM-NEXT-UNITS-SUDMA2 2026-10-19): split WRITE PHASE of one pinned SU store bank (next HBM die).
// One instance per store bank, at the bank's write pins (clk = the bank's register root clk_bank[n]).
// Why: each pinned bank has ONE write port, shared by the VM fill and the lane result. d4g serialises them per row
// (SU.VOP row II = (2k+1) nv512 + 2). The fill already alternates the two store-group halves edge by edge (fill
// command edge e writes the HI = 0 groups, e+1 the HI = 1 groups: 32 VM ports = one 512-word vector every 2 edges), so
// every bank has a free write slot every second edge while the fill streams. With wsplit = 1 (record-static), a
// DEFER bank (HI = 0) commits its lane result ONE edge later, from this register; an HI = 1 bank commits it at once.
// The compiler emits a vector every second edge with its lane-write edge W on a fill-HI0 edge: HI = 1 lane writes at
// W (fill is on HI0), HI = 0 lane writes at W + 1 (fill is on HI1) -> fill and lane results share the port with no
// collision and the row is bounded by the fill alone: II = 2 k nv512 (k per-row VM operands).
// wsplit = 0: pass-through (lw_v = lane_v, same edge, same address / data) = the d4g bank write bit for bit.
// Static schedule only: no queue, no ready, no arbitration. A collision is a FAULT in the slice (st_conflict, which
// sees lw_v), plus here: a fresh lane write and a deferred one on the same edge (only if wsplit toggles mid-record).
// WMUT (bench only, must FAIL): 1 deferral dropped (wsplit ignored); 2 the HI = 1 half deferred instead of HI = 0;
// 3 the deferred write takes the CURRENT edge's address (address capture dropped).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_su_wsplit #(parameter integer DEFER=1,RB=9,WMUT=0)(
 input wire clk,rst_n,
 input wire wsplit,
 input wire lane_v, input wire [RB-1:0] lane_a, input wire [31:0] lane_d,
 output wire lw_v, output wire [RB-1:0] lw_a, output wire [31:0] lw_d,
 output wire clash
);
 wire def=wsplit&&(WMUT!=1)&&((WMUT==2)?(DEFER==0):(DEFER!=0));
 reg dv; reg [RB-1:0] da; reg [31:0] dd;
 always @(posedge clk or negedge rst_n) if(!rst_n) dv<=1'b0; else dv<=def&&lane_v;
 always @(posedge clk) begin da<=lane_a; dd<=lane_d; end
 wire now=lane_v&&!def;
 assign lw_v=now||dv;
 assign lw_a=dv?((WMUT==3)?lane_a:da):lane_a;
 assign lw_d=dv?dd:lane_d;
 assign clash=now&&dv;
endmodule
`default_nettype wire
