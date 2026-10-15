`timescale 1ns/1ps
// Compiler-indexed bank-local write storage. No queue head/tail, arbiter,
// credits, ready, or retry. Up to3 captures target distinct explicit slots.
// The compiler selects the exact drain edge/slot. REGISTERED BOUNDARY (claude S81 VM F1, 2026-10-15, structural,
// +1 cycle; native pin rule: no combinational pin-to-pin arc): drain_v/drain_slot are pin registers at edge X, the
// output register loads the drained slot at X+1 (the receiving scatter samples at X+2). CaptureE -> earliest drain pin
// register E -> output register E+1. Storage can be reused on the edge it is read out.
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
 reg d_v;reg [1:0] d_slot;                       // drain pin registers (edge X)
 always @(posedge ck or negedge rn)if(!rn)d_v<=0;else d_v<=drain_v;
 always @(posedge ck)d_slot<=drain_slot;
 reg ov;assign o_v=ov;
 reg [13:0] row_q;reg [3:0] mask_q;reg [127:0] word_q;reg [7:0] tag_q;
 always @*begin
  row_q=0;mask_q=0;word_q=0;tag_q=0;
  for(integer s=0;s<DEPTH;s=s+1)if(d_slot==s)begin
   row_q=rows[s];mask_q=masks[s];word_q=words[s];tag_q=tags[s];
  end
 end
 always @(posedge ck)begin o_row<=row_q;o_mask<=mask_q;o_data<=word_q;o_tag<=tag_q;end   // output register X+1
 always @(posedge ck or negedge rn)if(!rn)ov<=0;else ov<=d_v && d_slot<DEPTH && valid[d_slot];
 always @*begin
  valid_n=valid;bad=0;
  if(d_v)begin
   if(d_slot>=DEPTH)bad=1;
   else begin if(!valid[d_slot])bad=1;valid_n[d_slot]=0;end
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
