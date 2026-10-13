`timescale 1ns/1ps
`default_nettype none
// ot_hbm_b2_xcommit: SM x-store COMMIT / DRAIN tracker and dispatcher join for the native VM8 PIPE1 sink.
//
// The sink's tap ACK proves only that the SM xw pins sampled a beat.  Inside ot_hbm_accel_smh the beat then moves
// through a fixed-latency, back-pressure-free register pipeline to the x-store SRAM write edge.  With E0 = the clock
// edge at which the SM pin flop (front_n wl) samples xw_en, the write edge of the slowest branch is E0 + D, with
//   D = PIN_STAGES   (front_n wl, wm, w0)                                                     3
//     + FRONT_STAGES (tile row 1 under OT_SMH_FC_HIER: fx, xl, relay 1, relay 2, M, O)        6   (tile row 0: a, m, o = 3)
//     + HOP_STAGES * (NHOP - 1)  (tile pass-through bl, bm, bm4, bout; NHOP = NC / 2)         12
//     + TILE_STAGES  (pt_w bk1, xs bk, leaf we0, we1, wce_q, macro pin register wce2)         6
//     = 27 for the selected native SM (NC 8, RMAX 4096, REQCR 1, TAGW 16; CG + FC_HIER + HIER + XLK).
// The x-store macro is read-before-write (a same-edge read returns the old word), so the first edge at which the
// committed word can be observed is E0 + D + 1: that one edge is the read hazard margin, and it is exactly the edge
// at which the SM samples start_out below (no other slack).
//
//   x_inflight / x_drained : a saturating down-counter reloaded with D by every xw_en (any SM); x_inflight is high from
//                            the cycle a beat is at the SM pins until the SRAM write edge of that beat has passed.
//   join                   : per command; cmd_begin clears it, release_final (the VM8 root's final lease / traffic
//                            release, pulse or level, seen strictly after cmd_begin) sets it.
//   dispatch_ok            : release seen && every sink drained && x_drained.
//   start gate             : start_in is a level request with return-to-zero between commands.  start_out is a
//                            register; it rises on the last SRAM write edge (counter look-ahead), so the SM samples it
//                            on E0 + D + 1, and it falls when the SM takes it (start_out && start_ready).
//   fault (sticky)         : a start that claims committed (start_committed) while the join cannot fire, or a
//                            cmd_begin while a gated start is still waiting for the SM.  A fault blocks start_out.
// The op payload is held stable by the caller from start_in until start_taken; it does not pass through this module.
// MUT (bench only): 1 = counter reloads D - 1; 2 = the join ignores x_drained; 3 = the join ignores the release and
// the sink drained inputs.
module ot_hbm_b2_xcommit #(
 parameter integer NSM=8,
 parameter integer NSINK=1,
 parameter integer PIN_STAGES=3,
 parameter integer FRONT_STAGES=6,
 parameter integer HOP_STAGES=4,
 parameter integer NHOP=4,
 parameter integer TILE_STAGES=6,
 parameter integer D=27,
 parameter integer MUT=0
)(
 input wire clk,rst_n,
 input wire [NSM-1:0] xw_en,
 input wire [NSINK-1:0] sink_drained,
 input wire cmd_begin,release_final,
 input wire start_in,start_committed,start_ready,
 output wire x_inflight,x_drained,dispatch_ok,
 output reg start_out,output wire start_taken,output reg fault
);
 localparam integer DCFG=PIN_STAGES+FRONT_STAGES+HOP_STAGES*(NHOP-1)+TILE_STAGES;
 localparam integer DEFF=MUT==1?D-1:D;
 localparam integer CW=$clog2(D+1);
 initial if(D!=DCFG||D<2)$fatal(1,"ot_hbm_b2_xcommit: D %0d does not match the configured x-write pipeline %0d",D,DCFG);
 reg [CW-1:0] cnt;reg rel_q,armed;
 wire xw_any=|xw_en;
 wire [CW-1:0] cnt_n=xw_any?DEFF[CW-1:0]:(cnt!=0?cnt-1'b1:cnt);
 assign x_inflight=xw_any||cnt!=0;
 assign x_drained=!x_inflight;
 wire rel_ok=MUT==3?1'b1:rel_q;
 wire sink_ok=MUT==3?1'b1:&sink_drained;
 assign dispatch_ok=rel_ok&&sink_ok&&(MUT==2?1'b1:x_drained);
 // look-ahead: the counter is zero after this edge, i.e. this edge is the last SRAM write edge
 wire join_n=rel_ok&&sink_ok&&(MUT==2?1'b1:cnt_n==0);
 assign start_taken=start_out&&start_ready;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cnt<=0;rel_q<=0;armed<=1;start_out<=0;fault<=0;end
  else begin
   cnt<=cnt_n;
   if(cmd_begin)rel_q<=0;else if(release_final)rel_q<=1;
   if(!start_in)armed<=1;
   if(start_taken)start_out<=0;
   else if(start_in&&armed&&!start_out&&!fault)begin
    if(join_n&&!cmd_begin)begin start_out<=1;armed<=0;end
    else if(start_committed)fault<=1;
   end
   if(cmd_begin&&start_out&&!start_taken)fault<=1;
  end
 end
endmodule
`default_nettype wire
