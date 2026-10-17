`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// SFU controller broadcast as a REGISTERED distribution tree (Claude hbm-group-B3, 2026-10-14).
//
// The quarter's controller broadcasts 1,022 dynamic bits (ld terms 480, o/i/row 72, ls/lvw 8, emit 1, pass 461) to 16
// lane mappers spread ~1.7 mm along the arithmetic grid; in the monolithic mapper every lane captured them itself at
// its edge 0 (audit 10-14: no registered broadcast tree, a single 1.7 mm hop).  The mapper's edge 0 is a PURE capture of
// common bits (only lane_j is per lane, and lane_j is captured beside it), so the capture can move to the tree: one
// ot_hgi_sfu_bcast_e0 node per four lanes holds edge 0 (controller -> node <= 500 um), and ot_hgi_sfu_lane_map_e123
// holds edges 1..3 of each lane (node -> mapper <= 500 um).  Same four registered edges from the controller output to
// the frozen body (BCAST1 / mapper4 / RET5 unchanged, nothing re-delayed), 2 x 500 um of registered reach, and 4 x
// 1,022 capture flops instead of 16 x 1,022 (-12,264 flops a quarter).  Cycle-identical to ot_hgi_sfu_lane_map.
module ot_hgi_sfu_bcast_e0 (
 input wire clk, rst_n,
 input wire [479:0] ld_terms,
 input wire [23:0] i_o_v, i_i_v, i_krow,
 input wire [3:0] i_ls, i_lvw,
 input wire i_emit,
 input wire [460:0] i_pass,
 output reg [479:0] e0_terms,
 output reg [23:0] e0_ov, e0_iv, e0_row,
 output reg [3:0] e0_ls, e0_lvw,
 output reg e0_emit,
 output reg [459:0] e0_pass,
 output reg e0_ld
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 always @(posedge clk) begin
  e0_terms<=ld_terms; e0_ov<=i_o_v; e0_iv<=i_i_v; e0_row<=i_krow; e0_ls<=i_ls; e0_lvw<=i_lvw; e0_pass<=i_pass[459:0];
  if(!f_rst) begin e0_emit<=1'b0; e0_ld<=1'b0; end
  else begin e0_emit<=i_emit; e0_ld<=i_pass[460]; end
 end
endmodule

// Lane mapper edges 1..3 behind a broadcast node (ot_hgi_sfu_lane_map with its edge-0 capture moved to the node).
module ot_hgi_sfu_lane_map_e123 #(parameter integer MUT_LANE=0, MUT_PASS=0) (   // MUT_PASS 1: pass one edge short (must FAIL)
 input wire clk, rst_n,
 input wire [3:0] lane_j,
 input wire [479:0] e0_terms,
 input wire [23:0] e0_ov, e0_iv, e0_row,
 input wire [3:0] e0_ls, e0_lvw,
 input wire e0_emit,
 input wire [459:0] e0_pass,
 input wire e0_ld,
 output reg [1199:0] o_ld_c,
 output reg [23:0] o_o_v, o_i_v, o_krow,
 output reg [3:0] o_ls, o_lvw,
 output reg o_emit,
 output wire [460:0] o_pass
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 reg [3:0] j0;                                   // captured on the node's edge 0 (lane_j may be a live input)
 reg emit1,emit2;
 reg [79:0] meta1,meta2;
 reg [3:1] ld_pipe;
 // pass: three more edges as a 2-slot ring + output register (written once, read once; no flop-to-flop data chain)
 reg [459:0] ps [0:1]; reg [1:0] poh; reg [459:0] pq;
 always @(posedge clk `OT_SFU_ARST(rst_n)) if(!rst_n) poh<=2'b01; else poh<={poh[0],poh[1]};
 always @(posedge clk) begin
  if(poh[0]) ps[0]<=e0_pass; if(poh[1]) ps[1]<=e0_pass;
  pq<=MUT_PASS ? e0_pass : (poh[0] ? ps[0] : 460'd0) | (poh[1] ? ps[1] : 460'd0);
 end
 assign o_pass={ld_pipe[3],pq};
 reg [23:0] term1[0:19],pair2[0:9];
 always @(posedge clk) begin
  j0<=lane_j ^ 4'(MUT_LANE);
  meta1<={24'(e0_ov + (24'(j0)>>e0_ls) - (24'd5>>e0_ls)),
          24'(e0_iv + (24'(j0)&((24'd1<<e0_ls)-1)) - (24'd5&((24'd1<<e0_ls)-1))),
          24'(e0_row + (24'(j0)>>e0_ls) - (24'd5>>e0_ls)),
          e0_ls,(e0_lvw<3 ? 4'd3 : e0_lvw)};
  meta2<=meta1;
  {o_o_v,o_i_v,o_krow,o_ls,o_lvw}<=meta2;
  for(integer s=0;s<5;s=s+1) begin
   for(integer k=0;k<4;k=k+1)
    term1[s*4+k]<=j0[k] ? e0_terms[(s*4+k)*24+:24] : 24'd0;
   pair2[s*2]<=term1[s*4]+term1[s*4+1];
   pair2[s*2+1]<=term1[s*4+2]+term1[s*4+3];
   o_ld_c[s*240+:240]<={216'd0,24'(pair2[s*2]+pair2[s*2+1])};
  end
  if(!f_rst) begin emit1<=0;emit2<=0;o_emit<=0;ld_pipe<=0;end
  else begin emit1<=e0_emit && (24'(j0)<(24'd1<<e0_lvw));emit2<=emit1;o_emit<=emit2;ld_pipe<={ld_pipe[2:1],e0_ld};end
 end
endmodule
`default_nettype wire
