`timescale 1ns/1ps
`default_nettype none
// Compiler-scheduled HGI ARGMAX fold over the actual native comparator stages.
// in_slot is the complete four-lane reservation. flush_slot is a compiled
// cycle (not endpoint feedback); publish_slot must be exactly flush+6.
// No ready, credit, variable flush or arrival-driven completion exists.
module ot_hgi_coll_argmax_static #(
 parameter integer MUT_TIE=0, MUT_SLOT_CHECK=0
)(
 input wire clk,rst_n,start,
 input wire [7:0] cfg_g,cfg_gbase,cfg_rank,
 input wire [3:0] in_slot,in_v,
 input wire [2179:0] in_flit,
 input wire flush_slot,publish_slot,
 output reg out_v,
 output reg [544:0] out_flit,
 output reg fault
);
 reg active,flushed;
 reg [7:0] group_q,gbase_q,rank_q;
 reg [7:0] observed;
 reg [95:0] seen;
 wire [3:0] raw_v;
 wire [2179:0] raw_flit;
 ot_hgi_coll_amerge #(.MUT_TIE(MUT_TIE)) u_fold(
  .clk(clk),.rst_n(rst_n),.en(1'b1),.start(start),.rank(rank_q),
  .d_v(in_v),.d_f(in_flit),.ep_done(flush_slot),.o_v(raw_v),.o_f(raw_flit),.done_out());
 // The output leaves a real pin register. Invalid schedules still publish at
 // their prescribed cycle; the sticky fault disqualifies their result.
 always @(posedge clk) out_flit<=raw_flit[0+:545];
 always @(posedge clk or negedge rst_n)begin:control
  integer count,src;
  reg [95:0] next_seen;
  if(!rst_n)begin
   active<=0;flushed<=0;group_q<=0;gbase_q<=0;rank_q<=0;
   observed<=0;seen<=0;out_v<=0;fault<=0;
  end else begin
   out_v<=publish_slot;
   if((MUT_SLOT_CHECK==0 && in_v!=in_slot) || raw_v!={3'b0,publish_slot})fault<=1;
   if(start)begin
    if(active || |in_v || flush_slot || publish_slot)fault<=1;
    if(!(cfg_g==1 || cfg_g==2 || cfg_g==4 || cfg_g==8 || cfg_g==96) ||
       {1'b0,cfg_gbase}+{1'b0,cfg_g}>9'd256)fault<=1;
    group_q<=cfg_g;gbase_q<=cfg_gbase;rank_q<=cfg_rank;
    observed<=0;seen<=0;active<=1;flushed<=0;
   end else begin
    count=0;next_seen=seen;
    for(integer l=0;l<4;l=l+1)if(in_v[l])begin
     count=count+1;src=int'(in_flit[l*545+528+:8])-int'(gbase_q);
     if(!active || flushed || !in_flit[l*545+544] || in_flit[l*545+512+:16]!=0 || src<0 || src>=int'(group_q) || src>=96)fault<=1;
     else begin
      if(next_seen[src])fault<=1;
      next_seen[src]=1'b1;
     end
    end
    seen<=next_seen;observed<=observed+8'(count);
    if(int'(observed)+count>int'(group_q))fault<=1;
    if(flush_slot)begin
     if(!active || flushed || int'(observed)+count!=int'(group_q))fault<=1;
     flushed<=1;
    end
    if(publish_slot)begin
     if(!active || !flushed)fault<=1;
     active<=0;
    end
   end
  end
 end
endmodule
`default_nettype wire
