`timescale 1ps/1fs
`default_nettype none
// One native wide group, three real producer classes assigned by the parent.
// New reserved posts may already be queued when a lease is acquired. Acquire
// requires no old VM response/commit obligations; release requires FULL drains.
// Ten bank credits belong to the held owner. They are never multiplied by source count.
// src_drained must include actual source/return/credit queues and commit tickets;
// vm_drained must include the actual destination queues and outstanding replies.
module ot_hbm_b2_peer_lease_owned #(parameter integer NSRC=3,MUT=0)(
 input wire [NSRC-1:0] cclk,input wire vclk,rst_n,
 input wire [NSRC-1:0] src_req,src_drained,vm_drained,vm_acquire_ready,
 output wire [NSRC-1:0] src_grant,src_drain_ack,
 output reg [NSRC-1:0] vm_grant,
 output wire fault
);
 reg [NSRC-1:0] req_r,req_n,idle_r,idle_n;
 (* async_reg="true" *)reg [NSRC-1:0] rq1,rq2,rn1,rn2,id1,id2,in1,in2;
 reg [NSRC-1:0] grant_n,ack_r,ack_n;
 wire [NSRC-1:0] grant_bus=(MUT==1)?{vm_grant[NSRC-2:0],vm_grant[NSRC-1]}:vm_grant;
 reg vf;wire [NSRC-1:0] cf;
 reg active,active_n;reg [$clog2(NSRC)-1:0] owner,last,owner_n,last_n;
 for(genvar s=0;s<NSRC;s=s+1)begin:source
  (* async_reg="true" *)reg g1,g2,gn1,gn2,a1,a2,an1,an2;reg sf;
  always @(posedge cclk[s] or negedge rst_n)if(!rst_n)begin
   req_r[s]<=0;req_n[s]<=1;idle_r[s]<=1;idle_n[s]<=0;
   g1<=0;g2<=0;gn1<=1;gn2<=1;a1<=1;a2<=1;an1<=0;an2<=0;sf<=0;
  end else begin
   req_r[s]<=src_req[s];req_n[s]<=~src_req[s];idle_r[s]<=src_drained[s];idle_n[s]<=~src_drained[s];
   g1<=grant_bus[s];g2<=g1;gn1<=grant_n[s];gn2<=gn1;
   a1<=ack_r[s];a2<=a1;an1<=ack_n[s];an2<=an1;
   // Transport rail disagreement refuses a transfer; local mutable mismatch is sticky.
   if(req_r[s]!=~req_n[s]||idle_r[s]!=~idle_n[s])sf<=1;
  end
  assign src_grant[s]=g2&&(g2==~gn2)&&!sf;
  assign src_drain_ack[s]=a2&&(a2==~an2)&&!sf;
  assign cf[s]=sf;
 end
 always @(posedge vclk or negedge rst_n)if(!rst_n)begin
  rq1<=0;rq2<=0;rn1<='1;rn2<='1;id1<='1;id2<='1;in1<=0;in2<=0;
  vm_grant<=0;grant_n<='1;ack_r<='1;ack_n<=0;active<=0;active_n<=1;owner<=0;owner_n<='1;last<=NSRC-1;last_n<=~($clog2(NSRC)'(NSRC-1));vf<=0;
 end else begin
  rq1<=req_r;rq2<=rq1;rn1<=req_n;rn2<=rn1;id1<=idle_r;id2<=id1;in1<=idle_n;in2<=in1;
  if(vm_grant!=~grant_n||ack_r!=~ack_n||active!=~active_n||owner!=~owner_n||last!=~last_n)begin
   vf<=1;vm_grant<=0;grant_n<='1;
  end else
  if(!vf&&rq2==~rn2&&id2==~in2)begin
   if(active)begin
    if(!rq2[owner]&&id2[owner]&&vm_drained[owner])begin
     vm_grant<=0;grant_n<='1;ack_r[owner]<=1;ack_n[owner]<=0;active<=0;active_n<=1;last<=owner;last_n<=~owner;
    end
   end else begin:choose
    integer pick,index;pick=-1;
    for(integer k=1;k<=NSRC;k=k+1)begin
     index=(int'(last)+k)%NSRC;
     if(pick<0&&rq2[index]&&vm_acquire_ready[index])pick=index;
    end
    if(pick>=0)begin
     owner<=pick;owner_n<=~($clog2(NSRC)'(pick));active<=1;active_n<=0;vm_grant<=NSRC'(1)<<pick;grant_n<=~(NSRC'(1)<<pick);ack_r[pick]<=0;ack_n[pick]<=1;
    end
   end
  end
 end
 assign fault=vf|(|cf);
endmodule
`default_nettype wire
