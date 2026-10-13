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
//   records                : cmd_begin opens a record (its fetch is dispatched).  The record CLOSES on the first edge
//                            at which its final release (release_final rising, pulse or level) has been seen and
//                            every sink is drained: every beat of it has been sampled by the SM pins.
//   OVERLAP (round 4)      : the next record's cmd_begin may come while the previous record is still waiting for its
//                            release, its drain or its dispatch (at most ONE record behind the open one).  A closed
//                            record moves to `pend` with its own countdown pcnt (the edges left to its last SRAM write
//                            edge), so the 27-edge drain runs under the next record's HBM fetch instead of in series.
//   load_hold              : high while a second record is begun behind an unclosed one, or a closed record is not
//                            yet dispatched (pend), or a resident start is waiting.  The caller gates the producer's
//                            acceptance with it: NO beat of the next record is accepted, hence none reaches the SM
//                            pins, before the previous record's dispatch is taken.  So the x-store at a dispatch edge
//                            is exactly that record's image and the drain completes before the next write to the
//                            same x address.  (How long the dispatched op may still READ its x is the dispatcher's
//                            address-ring / serial rule, as before; this module bounds the hand-over only.)
//   dispatch_ok            : the dispatch condition of the oldest record, as a level.
//   start gate             : start_in is a level request with return-to-zero between commands.  start_out is a
//                            register; it rises on the last SRAM write edge (counter look-ahead), so the SM samples it
//                            on E0 + D + 1 (or two edges after a late release), and it falls when the SM takes it.
//                            Without an open or pending record (resident x) it rises when the store is drained.
//   fault (sticky)         : a start that claims committed (start_committed) while the join cannot fire; a third
//                            record begun; a beat sampled by the SM pins while a closed record is not yet dispatched
//                            (the caller ignored load_hold).  A fault blocks start_out.
// The op payload is held stable by the caller from start_in until start_taken; it does not pass through this module.
// MUT (bench only): 1 = counter reloads D - 1 (one pipeline stage short); 2 = the join ignores the drain (dispatch on
// the release / last ACK); 3 = the join ignores the release and the sink drained inputs; 4 = only the first beat of a
// run of consecutive beats reloads the counter (the later in-flight writes of the run are dropped from the count);
// 5 = load_hold stuck low and the early-beat fault off (the next record's beats may overtake the dispatch: the
// dispatched op would read the NEXT record's x).
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
 output reg start_out,output wire start_taken,output reg fault,
 output wire load_hold
);
 localparam integer DCFG=PIN_STAGES+FRONT_STAGES+HOP_STAGES*(NHOP-1)+TILE_STAGES;
 localparam integer DEFF=MUT==1?D-1:D;
 localparam integer CW=$clog2(D+1);
 initial if(D!=DCFG||D<2)$fatal(1,"ot_hbm_b2_xcommit: D %0d does not match the configured x-write pipeline %0d",D,DCFG);
 reg [CW-1:0] cnt,pcnt;reg rel_q,rel_d,armed,xw_q,pend;reg [1:0] nopen;
 wire xw_any=MUT==4?(|xw_en)&&!xw_q:|xw_en;
 wire [CW-1:0] cnt_n=xw_any?DEFF[CW-1:0]:(cnt!=0?cnt-1'b1:cnt);
 wire [CW-1:0] pcnt_n=pcnt!=0?pcnt-1'b1:pcnt;
 assign x_inflight=xw_any||cnt!=0;
 assign x_drained=!x_inflight;
 wire rel_ok=MUT==3?1'b1:rel_q;
 wire sink_ok=MUT==3?1'b1:&sink_drained;
 wire nodr=MUT==2;
 // the open record closes: every beat of it has been sampled by the SM pins
 wire closing=nopen!=0&&!pend&&rel_ok&&sink_ok;
 wire idle=nopen==0&&!pend&&!cmd_begin;   // resident x: no record begun (not even on this edge), none pending
 assign dispatch_ok=pend?(nodr||pcnt==0):(closing||(idle&&sink_ok))&&(nodr||x_drained);
 // look-ahead: the counter is zero after this edge, i.e. this edge is the last SRAM write edge of the oldest record
 wire join_n=pend?(nodr||pcnt_n==0):(closing||(idle&&sink_ok))&&(nodr||cnt_n==0);
 assign start_taken=start_out&&start_ready;
 assign load_hold=MUT==5?1'b0:(pend||start_out||nopen==2);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cnt<=0;pcnt<=0;xw_q<=0;rel_q<=0;rel_d<=0;armed<=1;start_out<=0;fault<=0;pend<=0;nopen<=0;end
  else begin
   cnt<=cnt_n;pcnt<=pcnt_n;xw_q<=|xw_en;rel_d<=release_final;
   // records: begun / closed.  The release is taken on its rising edge and only for a begun record.
   if(release_final&&!rel_d&&nopen!=0)rel_q<=1;
   if(closing)begin pend<=1;pcnt<=cnt_n;rel_q<=0;end
   nopen<=nopen+{1'b0,cmd_begin}-{1'b0,closing};
   if(cmd_begin&&nopen==2&&!closing)fault<=1;
   if(xw_any&&pend&&MUT!=5)fault<=1;
   if(!start_in)armed<=1;
   if(start_taken)begin start_out<=0;pend<=0;end
   else if(start_in&&armed&&!start_out&&!fault)begin
    if(join_n)begin start_out<=1;armed<=0;end
    else if(start_committed)fault<=1;
   end
  end
 end
endmodule
`default_nettype wire
