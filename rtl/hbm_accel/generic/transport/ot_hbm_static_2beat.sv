`timescale 1ns/1ps
`default_nettype none
// Fixed-calendar transport. Source accepts only slot0, period2. Every DATA
// event/valid in CONTROL_MASK and correlated CTL event in SIDE_CONTROL_MASK
// MUST be0 on slot1. Payload may change there. The spare high-beat MSB carries
// a sticky phase fault; RX clears all DATA/CTL valid bits on fault.
// Start is one boot-only aligned broadcast after both wavefront resets release.
// Repeated start faults and is ignored for phase; never bind per-token launch.
// DATA and correlated SIDE paths must each have exactly LINK_STAGES channel
// registers (pad the short path). End-to-end age=LINK_STAGES+2 edges, II2.
// HOLD_MASK/SIDE_HOLD_MASK identify persistent control/status: reset0,
// update on completion and hold between words; never phaseguard these levels.
// No ready/arbitration/queue, feedback scheduling, or reset on payload flops.
module ot_hbm_static_2beat_tx #(
 parameter integer W=3749,B=1875,S=1,
 parameter [W-1:0] CONTROL_MASK={W{1'b0}},HOLD_MASK={W{1'b0}},
 parameter [S-1:0] SIDE_CONTROL_MASK={S{1'b1}},SIDE_HOLD_MASK={S{1'b0}},
 parameter integer MUT=0
)(input wire clk,rst_n,start,input wire[W-1:0] d,input wire[S-1:0] side_d,
 output reg[B-1:0] beat,output reg[S-1:0] side_beat,
 output reg fault,output wire slot0);
 localparam integer HI=W-B,PAD=B-HI-1;
 initial begin
  if(W<=B||W>=2*B)$fatal(1,"2beat requires B<W<2B; spare high-beat fault bit");
  if(CONTROL_MASK==0)$fatal(1,"explicit nonzero CONTROL_MASK required");
  if((CONTROL_MASK&HOLD_MASK)!=0||(SIDE_CONTROL_MASK&SIDE_HOLD_MASK)!=0)$fatal(1,"pulse/held masks overlap");
 end
 reg running,phase;
 reg[HI-1:0] high_q;
 wire bad_phase=phase&&((|(d&CONTROL_MASK))||(|(side_d&SIDE_CONTROL_MASK)));
 assign slot0=running&&!phase;
 always @(posedge clk)begin
  if(!rst_n)begin running<=0;phase<=0;fault<=0;end
  else if(start&&!running)begin running<=1;phase<=0;end
  else if(running)begin phase<=~phase;if(bad_phase||start)fault<=1;end
 end
 always @(posedge clk)if(running)begin
  if(!phase)begin high_q<=d[W-1:B];beat<=d[B-1:0];side_beat<=side_d;end
  else begin
   beat<={{(B-HI){1'b0}},high_q} ^ (MUT==1?{{(B-3){1'b0}},3'b100}:{B{1'b0}});
   // Every surplus high-beat slot is functional: registered copies of
   // the first beat, checked by RX. No constant padding on NE wires.
   for(integer j=0;j<PAD;j=j+1)beat[HI+j]<=beat[j] ^ ((MUT==2&&j==0)?1'b1:1'b0);
   beat[B-1]<=fault||bad_phase;
  end
 end
endmodule

module ot_hbm_static_2beat_rx #(
 parameter integer W=3749,B=1875,S=1,LINK_STAGES=0,
 parameter [W-1:0] CONTROL_MASK={W{1'b0}},HOLD_MASK={W{1'b0}},
 parameter [S-1:0] SIDE_CONTROL_MASK={S{1'b1}},SIDE_HOLD_MASK={S{1'b0}},
 parameter integer MUT=0
)(input wire clk,rst_n,start,input wire[B-1:0] beat,input wire[S-1:0] side_beat,
 output wire[W-1:0] q,output wire[S-1:0] side_q,output reg fault);
 localparam integer HI=W-B,PAD=B-HI-1,CW=$clog2(LINK_STAGES+2);
 initial begin
  if(W<=B||W>=2*B||LINK_STAGES<0)$fatal(1,"invalid 2beat width/channel depth");
  if(CONTROL_MASK==0)$fatal(1,"explicit nonzero CONTROL_MASK required");
  if((CONTROL_MASK&HOLD_MASK)!=0||(SIDE_CONTROL_MASK&SIDE_HOLD_MASK)!=0)$fatal(1,"pulse/held masks overlap");
 end
 reg running,phase,have_low;
 reg[CW-1:0] warmup;
 reg[B-1:0] low_q;
 reg[W-1:0] data_q,control_q,held_q;
 reg[S-1:0] side_data_q,side_control_q,side_held_q;
 wire[W-1:0] complete_word={beat[HI-1:0],low_q};
 wire duplicate_bad;
 if(PAD>0)begin:g_duplicate
  assign duplicate_bad=|(beat[HI+:PAD]^low_q[0+:PAD]);
 end else begin:g_no_duplicate assign duplicate_bad=1'b0;end
 wire complete_fault=beat[B-1]||duplicate_bad;
 wire active=running&&warmup==0;
 assign q=(data_q&~(CONTROL_MASK|HOLD_MASK))|control_q|held_q;
 assign side_q=(side_data_q&~(SIDE_CONTROL_MASK|SIDE_HOLD_MASK))|side_control_q|side_held_q;
 always @(posedge clk)begin
  if(!rst_n)begin running<=0;phase<=0;have_low<=0;warmup<=0;control_q<=0;side_control_q<=0;held_q<=0;side_held_q<=0;fault<=0;end
  else if(start&&!running)begin running<=1;phase<=1'(LINK_STAGES%2);have_low<=0;warmup<=CW'(LINK_STAGES+1);control_q<=0;side_control_q<=0;held_q<=0;side_held_q<=0;end
  else if(running)begin
   if(start)fault<=1;
   phase<=~phase;
   if(warmup!=0)warmup<=warmup-1'b1;
   else begin
    if(phase)begin
     have_low<=1;
     if(MUT!=3)begin control_q<=0;side_control_q<=0;end
    end
    if(!phase&&have_low)begin
     if(complete_fault)fault<=1;
     held_q<=complete_word&HOLD_MASK;
     side_held_q<=side_beat&SIDE_HOLD_MASK;
     control_q<=fault||complete_fault||start?{W{1'b0}}:(complete_word&CONTROL_MASK);
     side_control_q<=fault||complete_fault||start?{S{1'b0}}:(side_beat&SIDE_CONTROL_MASK);
    end
   end
  end
 end
 always @(posedge clk)if(active)begin
  if((MUT==2)?!phase:phase)begin if(MUT!=1)low_q<=beat;end
  if(!phase&&have_low)begin data_q<=complete_word;side_data_q<=side_beat;end
 end
endmodule
`default_nettype wire
