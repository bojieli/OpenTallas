`timescale 1ns/1ps
`default_nettype none
// Tap the REAL static TOPK VM-write packet. Never reconstruct selections from scores or host IDs.
// One launch identity, one MoE TOPK, one aligned six-word write; no ready/credit/retry.
// GO_DELAY/CQ_DELAY/XRT are source-derived collar and VM return latencies, not timing waivers.
// cq is sampled in a face flop, checked at the compiler's W edge, then published from flops.
module ot_hbm_router_ids_static #(
 parameter integer XRT=2, GO_DELAY=1, CQ_DELAY=1
)(
 input wire clk,rst_n,
 input wire run_v,input wire[7:0]run_layer,
 input wire topk_go,input wire[155:0]topk_rec,
 input wire[337:0]cq,input wire[1:0]cq_seq,
 output reg ids_v,output reg[7:0]ids_layer,output reg[53:0]ids,
 output reg[15:0]ids_cohort,output reg fault
);
 // Payload flops need no reset; two face reset stages bound reset fanout.
 (* keep *) reg[1:0]reset_face;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)reset_face<=0;else reset_face<={reset_face[0],1'b1};
 wire rn=reset_face[1];
 reg rv,tg;reg[7:0]rl;reg[155:0]tr;reg[337:0]packet;reg[1:0]seq;
 always @(posedge clk)begin rl<=run_layer;tr<=topk_rec;packet[336:0]<=cq[336:0];seq<=cq_seq;end
 always @(posedge clk or negedge rn)
  if(!rn)begin rv<=0;tg<=0;packet[337]<=0;end
  else begin rv<=run_v;tg<=topk_go;packet[337]<=cq[337];end
 reg have_run,active,used;reg[7:0]layer;reg[15:0]cohort;
 reg[9:0]age,due;reg[31:0]address;
 wire router=tg&&tr[3:0]==6&&tr[24:5]==384&&tr[44:25]==1;
 // Engine header: S=G+3, F=S+2(ns-1)+9+XRT, W=F+7+4k+1.
 // For n=384, ns=48 for aligned A and 49 otherwise.
 wire[9:0]w_edge=10'(138+XRT+GO_DELAY+CQ_DELAY)+(tr[48:46]!=0?10'd2:10'd0);
 reg bad_ids;
 integer j;
 always @*begin
  bad_ids=0;
  for(integer k=0;k<6;k=k+1)begin
   if(packet[48+32*k+:32]>=384)bad_ids=1;
   if(k>0&&packet[48+32*k+:32]<=packet[48+32*(k-1)+:32])bad_ids=1;
  end
 end
 always @(posedge clk or negedge rn)begin
  if(!rn)begin have_run<=0;active<=0;used<=0;cohort<=0;age<=0;due<=0;ids_v<=0;fault<=0;end
  else begin
   ids_v<=0;
   if(rv)begin
    if(active)fault<=1;
    have_run<=1;used<=0;layer<=rl;cohort<=cohort+16'd1;
   end
   if(router)begin
    if(!have_run||rv||active||used||!tr[4]||tr[82]||tr[119]||tr[85:83]!=0)fault<=1;
    else begin
     active<=1;age<=0;due<=w_edge;address<={12'd0,tr[100:83],2'b0};used<=1;
    end
   end
   if(active)begin
    age<=age+10'd1;
    if(packet[337]&&age!=due)begin fault<=1;active<=0;end
    if(age==due)begin
     active<=0;
     if(!packet[337]||!packet[336]||packet[335:304]!=address||packet[47:16]!=32'h00ffffff||
        packet[15:0]!={14'h244,2'b0}||seq!=0||bad_ids)fault<=1;
     else begin
      ids_v<=1;ids_layer<=layer;ids_cohort<=cohort;
      for(j=0;j<6;j=j+1)ids[9*j+:9]<=packet[48+32*j+:9];
     end
    end
   end
  end
 end
endmodule
`default_nettype wire
