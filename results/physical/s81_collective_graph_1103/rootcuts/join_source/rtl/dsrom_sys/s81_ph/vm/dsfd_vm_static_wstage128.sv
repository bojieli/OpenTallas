`timescale 1ns/1ps
// Compiler-indexed bank-local write storage. No queue head/tail, arbiter,
// credits, ready, or retry. Up to3 captures target distinct explicit slots.
// The compiler selects the exact drain edge/slot, visible combinationally to
// the receiving scatter input pins BEFORE that edge. CaptureE -> earliest
// scatter sampleE+1. Storage can be reused on the same edge it is drained.
module dsfd_vm_static_wstage128 #(parameter integer DEPTH=3)(
 input wire ck,rst_n,
 input wire [2:0] capture_v,input wire [5:0] capture_slot,
 input wire [41:0] capture_row,input wire [11:0] capture_mask,
 input wire [383:0] capture_data,input wire [23:0] capture_tag,
 input wire drain_v,input wire [1:0] drain_slot,
 output wire o_v,output reg [13:0] o_row,output reg [3:0] o_mask,
 output reg [127:0] o_data,output reg [7:0] o_tag,output reg fault
);
 reg [1:0] release_reset;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)release_reset<=0;else release_reset<={release_reset[0],1'b1};
 wire rn=release_reset[1];
 reg [DEPTH-1:0] valid,valid_n;reg bad;
 reg [13:0] rows[0:DEPTH-1];reg [3:0] masks[0:DEPTH-1];
 reg [127:0] words[0:DEPTH-1];reg [7:0] tags[0:DEPTH-1];
 assign o_v=drain_v && drain_slot<DEPTH && valid[drain_slot];
 always @*begin
  o_row=0;o_mask=0;o_data=0;o_tag=0;
  for(integer s=0;s<DEPTH;s=s+1)if(drain_slot==s)begin
   o_row=rows[s];o_mask=masks[s];o_data=words[s];o_tag=tags[s];
  end
 end
 always @*begin
  valid_n=valid;bad=0;
  if(drain_v)begin
   if(drain_slot>=DEPTH)bad=1;
   else begin if(!valid[drain_slot])bad=1;valid_n[drain_slot]=0;end
  end
  for(integer c=0;c<3;c=c+1)if(capture_v[c])begin
   if(capture_slot[2*c+:2]>=DEPTH)bad=1;
   else begin
    if(valid_n[capture_slot[2*c+:2]])bad=1;
    valid_n[capture_slot[2*c+:2]]=1;
   end
  end
 end
 always @(posedge ck or negedge rn)
  if(!rn)begin valid<=0;fault<=0;end
  else begin valid<=valid_n;fault<=fault|bad;end
 genvar g;
 generate for(g=0;g<DEPTH;g=g+1)begin:slot
  reg hit;reg [13:0] row_d;reg [3:0] mask_d;reg [127:0] word_d;reg [7:0] tag_d;
  always @*begin
   hit=0;row_d=0;mask_d=0;word_d=0;tag_d=0;
   for(integer c=0;c<3;c=c+1)if(capture_v[c] && capture_slot[2*c+:2]==g)begin
    hit=1;row_d=row_d|capture_row[14*c+:14];mask_d=mask_d|capture_mask[4*c+:4];
    word_d=word_d|capture_data[128*c+:128];tag_d=tag_d|capture_tag[8*c+:8];
   end
  end
  always @(posedge ck)if(hit)begin
   rows[g]<=row_d;masks[g]<=mask_d;words[g]<=word_d;
`ifdef OT_VM_WSTAGE_MUT_TAG
   tags[g]<=tag_d^8'h1;
`else
   tags[g]<=tag_d;
`endif
  end
 end endgenerate
 initial if(DEPTH<1 ||DEPTH>3)$error("scheduled write storage requires1..3slots");
endmodule
