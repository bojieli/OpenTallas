`timescale 1ns/1ps
`default_nettype none
// Compiler-scheduled HGI ARGMAX fold over the actual native comparator stages.
// in_slot is the complete four-lane reservation. flush_slot is a compiled
// cycle (not endpoint feedback); publish_slot must be exactly flush+6.
// No ready, credit, variable flush or arrival-driven completion exists.
module ot_hgi_coll_argmax_static #(
 parameter integer MUT_TIE=0, MUT_SLOT_CHECK=0, MAX_GROUP=96
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
 reg [MAX_GROUP-1:0] seen;
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
  reg [MAX_GROUP-1:0] next_seen;
  if(!rst_n)begin
   active<=0;flushed<=0;group_q<=0;gbase_q<=0;rank_q<=0;
   observed<=0;seen<=0;out_v<=0;fault<=0;
  end else begin
   out_v<=publish_slot;
   if((MUT_SLOT_CHECK==0 && in_v!=in_slot) || raw_v!={3'b0,publish_slot})fault<=1;
   if(start)begin
    if(active || |in_v || flush_slot || publish_slot)fault<=1;
    if(!(cfg_g==1 || cfg_g==2 || cfg_g==4 || cfg_g==8 || cfg_g==96 || (MAX_GROUP>=192 && cfg_g==192)) ||
       {1'b0,cfg_gbase}+{1'b0,cfg_g}>9'd256)fault<=1;
    group_q<=cfg_g;gbase_q<=cfg_gbase;rank_q<=cfg_rank;
    observed<=0;seen<=0;active<=1;flushed<=0;
   end else begin
    count=0;next_seen=seen;
    for(integer l=0;l<4;l=l+1)if(in_v[l])begin
     count=count+1;src=int'(in_flit[l*545+528+:8])-int'(gbase_q);
     if(!active || flushed || !in_flit[l*545+544] || in_flit[l*545+512+:16]!=0 || src<0 || src>=int'(group_q) || src>=MAX_GROUP)fault<=1;
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

// HBM-GAPS-9 11-06 (q3_edge_arg pin-cycle form, DIE-HBM-81 13:37 ruling): same function as
// ot_hgi_coll_argmax_static, except the sticky fault output is one edge later (PIN CYCLES: fault +1,
// every other output exact). The duplicate-source check, which was a 4-lane chained lookup into
// next_seen (192:1) feeding fault, is split over two edges: edge 1 registers per lane the 8-bit
// source, a 'reached the dup check' bit, a snapshot of seen and the OR of every other fault term;
// edge 2 checks seen_q[src_l] | (src_k==src_l for an earlier lane k) in parallel. seen itself is
// updated exactly as before (seen | one-hot of every lane that reached the check).
// fault_fp(t) == fault_orig(t-1) for every t (proved: yosys equiv_induct + mutant, lock-step bench).
module ot_hgi_coll_argmax_static_fp #(
 parameter integer MUT_TIE=0, MUT_SLOT_CHECK=0, MAX_GROUP=96, MUT_FP=0
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
 reg [MAX_GROUP-1:0] seen;
 // stage-1 registers of the deferred fault terms
 reg set_q;
 reg [3:0] chk_q;
 reg [31:0] src_q;
 reg [MAX_GROUP-1:0] seen_q;
 wire [3:0] raw_v;
 wire [2179:0] raw_flit;
 ot_hgi_coll_amerge #(.MUT_TIE(MUT_TIE)) u_fold(
  .clk(clk),.rst_n(rst_n),.en(1'b1),.start(start),.rank(rank_q),
  .d_v(in_v),.d_f(in_flit),.ep_done(flush_slot),.o_v(raw_v),.o_f(raw_flit),.done_out());
 always @(posedge clk) out_flit<=raw_flit[0+:545];
 // stage 2: duplicate check, all lanes in parallel
 reg dup;
 always @* begin:dupchk
  dup=1'b0;
  for(integer l=0;l<4;l=l+1)if(chk_q[l])begin
   if(int'(src_q[l*8+:8])<MAX_GROUP && seen_q[src_q[l*8+:8]])dup=1'b1;
   for(integer k=0;k<l;k=k+1)
    if(chk_q[k] && src_q[k*8+:8]==src_q[l*8+:8] && (MUT_FP==0 || k!=0))dup=1'b1;
  end
 end
 always @(posedge clk or negedge rst_n)begin:control
  integer count,src;
  reg set;
  reg [3:0] chk;
  reg [31:0] srcv;
  reg [MAX_GROUP-1:0] next_seen;
  if(!rst_n)begin
   active<=0;flushed<=0;group_q<=0;gbase_q<=0;rank_q<=0;
   observed<=0;seen<=0;out_v<=0;fault<=0;
   set_q<=0;chk_q<=0;src_q<=0;seen_q<=0;
  end else begin
   set=1'b0;chk=4'b0;srcv=32'b0;
   out_v<=publish_slot;
   if((MUT_SLOT_CHECK==0 && in_v!=in_slot) || raw_v!={3'b0,publish_slot})set=1'b1;
   if(start)begin
    if(active || |in_v || flush_slot || publish_slot)set=1'b1;
    if(!(cfg_g==1 || cfg_g==2 || cfg_g==4 || cfg_g==8 || cfg_g==96 || (MAX_GROUP>=192 && cfg_g==192)) ||
       {1'b0,cfg_gbase}+{1'b0,cfg_g}>9'd256)set=1'b1;
    group_q<=cfg_g;gbase_q<=cfg_gbase;rank_q<=cfg_rank;
    observed<=0;seen<=0;active<=1;flushed<=0;
   end else begin
    count=0;next_seen=seen;
    for(integer l=0;l<4;l=l+1)if(in_v[l])begin
     count=count+1;src=int'(in_flit[l*545+528+:8])-int'(gbase_q);
     if(!active || flushed || !in_flit[l*545+544] || in_flit[l*545+512+:16]!=0 || src<0 || src>=int'(group_q) || src>=MAX_GROUP)set=1'b1;
     else begin
      chk[l]=1'b1;srcv[l*8+:8]=8'(src);
      next_seen[src]=1'b1;
     end
    end
    seen<=next_seen;observed<=observed+8'(count);
    if(int'(observed)+count>int'(group_q))set=1'b1;
    if(flush_slot)begin
     if(!active || flushed || int'(observed)+count!=int'(group_q))set=1'b1;
     flushed<=1;
    end
    if(publish_slot)begin
     if(!active || !flushed)set=1'b1;
     active<=0;
    end
   end
   set_q<=set;chk_q<=chk;src_q<=srcv;seen_q<=seen;
   if(set_q || dup)fault<=1'b1;
  end
 end
endmodule
`default_nettype wire
