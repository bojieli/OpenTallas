`timescale 1ns/1ps
`default_nettype none
// Sized first by tools/hgi_dma_wide_landing_lane_model.py. No physical qualification claim.
// Initial producer credits DEPTH; no input ready. Credit returns ONLY on corrected read capture
// into an already-reserved finite prefetch slot. Two phase payload banks sustain one beat/cycle.
module ot_hgi_dma_wide_landing_lane #(parameter integer ENABLE=0,DEPTH=256,PREFETCH=8,MUT=0)(
 input wire clk,rst_n,in_v,input wire[17:0]in_sec,input wire[255:0]in_data,
 output wire out_v,input wire out_r,output wire[17:0]out_sec,output wire[255:0]out_data,
 output wire credit,output reg fault);
 localparam integer DW=$clog2(DEPTH),PW=$clog2(PREFETCH);
 (* keep=1,dont_touch=1 *) reg[DEPTH-1:0]allocated,allocated_n,published,published_n;
 (* keep=1,dont_touch=1 *) reg[17:0]meta[0:DEPTH-1],meta_n[0:DEPTH-1];
 (* keep=1,dont_touch=1 *) reg[19:0]wseq,wseq_n,ackseq,ackseq_n,rseq,rseq_n,retseq,retseq_n;
 (* keep=1,dont_touch=1 *) reg[8:0]live,live_n;
 (* keep=1,dont_touch=1 *) reg[PREFETCH-1:0]reserved,reserved_n,pv,pv_n;
 (* keep=1,dont_touch=1 *) reg[17:0]ps[0:PREFETCH-1],ps_n[0:PREFETCH-1];
 (* keep=1,dont_touch=1 *) reg[19:0]pt[0:PREFETCH-1],pt_n[0:PREFETCH-1];
 (* keep=1,dont_touch=1 *) reg[255:0]pd[0:PREFETCH-1],pd_n[0:PREFETCH-1];
 (* keep=1,dont_touch=1 *) reg[PW-1:0]ph,ph_n;
 (* keep=1,dont_touch=1 *) reg ov,ov_n,cq,cq_n;
 (* keep=1,dont_touch=1 *) reg[17:0]os,os_n;
 (* keep=1,dont_touch=1 *) reg[255:0]od,od_n;
 wire[1:0]bwr,bwd,brr,brd,bue,bfault;wire[39:0]bwtag,brtag;wire[511:0]brdata;wire[7:0]bce;
 wire[DW-1:0]wi=wseq[DW-1:0],ri=rseq[DW-1:0];wire[PW-1:0]pi=rseq[PW-1:0];
 wire badconfig=DEPTH<16||DEPTH>256||(DEPTH&(DEPTH-1))!=0||PREFETCH<8||PREFETCH>16||(PREFETCH&(PREFETCH-1))!=0;
 reg bad;integer x;
 always @*begin
  bad=badconfig||(allocated_n!==~allocated)||(published_n!==~published)||((published&~allocated)!=0)||
      (wseq_n!==~wseq)||(ackseq_n!==~ackseq)||(rseq_n!==~rseq)||(retseq_n!==~retseq)||(live_n!==~live)||
      (reserved_n!==~reserved)||(pv_n!==~pv)||((pv&~reserved)!=0)||(ph_n!==~ph)||(ov_n!==~ov)||(cq_n!==~cq);
  for(integer a=0;a<DEPTH;a=a+1)if(allocated[a]&&meta_n[a]!==~meta[a])bad=1;
  for(integer a=0;a<PREFETCH;a=a+1)begin
   if(reserved[a]&&(ps_n[a]!==~ps[a]||pt_n[a]!==~pt[a]))bad=1;
   if(pv[a]&&pd_n[a]!==~pd[a])bad=1;
  end
  if(ov&&(os_n!==~os||od_n!==~od))bad=1;
 end
 wire okay=(ENABLE!=0)&&!fault&&!bad&&!(|bfault);
 wire room=live<DEPTH&&!allocated[wi];
 wire wa=in_v&&okay&&room&&bwr[wseq[0]];
 wire rq=okay&&!reserved[pi]&&((MUT==2)?allocated[ri]:published[ri]);
 wire ra=rq&&brr[rseq[0]];
 wire pop=okay&&pv[ph]&&(!ov||out_r);
 assign out_v=okay&&ov;assign out_sec=os;assign out_data=od;
 assign credit=okay&&cq;
 genvar g;
 generate for(g=0;g<2;g=g+1)begin:phase
  ot_hgi_vm_wide_bank #(.ENABLE(ENABLE)) u_bank(.clk(clk),.rst_n(rst_n),
   .w_v(in_v&&okay&&room&&wseq[0]==g),.w_rdy(bwr[g]),.w_addr(8'(wi>>1)),.w_data(in_data),.w_mask(8'hff),.w_tag(wseq),
   .w_done(bwd[g]),.w_done_tag(bwtag[g*20+:20]),.r_v(rq&&rseq[0]==g),.r_rdy(brr[g]),.r_addr(8'(ri>>1)),.r_tag(rseq),
   .r_done(brd[g]),.r_done_tag(brtag[g*20+:20]),.r_data(brdata[g*256+:256]),.r_ce(bce[g*4+:4]),.r_ue(bue[g]),.fault(bfault[g]),
   .inj_v(1'b0),.inj_word(3'd0),.inj_mask(39'd0));
 end endgenerate
 wire wdany=|bwd,rdany=|brd;
 wire wp=bwd[1];wire rp=brd[1];
 wire[19:0]wt=bwtag[wp*20+:20],rt=brtag[rp*20+:20];
 wire ackok=wdany&&(bwd!=2'b11)&&wt==ackseq&&allocated[wt[DW-1:0]]&&!published[wt[DW-1:0]];
 wire retok=rdany&&(brd!=2'b11)&&rt==retseq&&reserved[rt[PW-1:0]]&&!pv[rt[PW-1:0]]&&pt[rt[PW-1:0]]==rt&&!bue[rp];
 wire capture=okay&&retok;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;allocated<=0;allocated_n<='1;published<=0;published_n<='1;
   wseq<=0;wseq_n<='1;ackseq<=0;ackseq_n<='1;rseq<=0;rseq_n<='1;retseq<=0;retseq_n<='1;live<=0;live_n<='1;
   reserved<=0;reserved_n<='1;pv<=0;pv_n<='1;ph<=0;ph_n<='1;ov<=0;ov_n<=1;cq<=0;cq_n<=1;
   os<=0;os_n<='1;od<=0;od_n<='1;
  end else begin
   cq<=0;cq_n<=1;
   if((ENABLE!=0)&&(bad||(|bfault)||(in_v&&(!okay||!room||!bwr[wseq[0]]))||(wdany&&!ackok)||(rdany&&!retok)))fault<=1;
   if(wa)begin
    allocated[wi]<=1;allocated_n[wi]<=0;meta[wi]<=in_sec;meta_n[wi]<=~in_sec;
    wseq<=wseq+20'd1;wseq_n<=~(wseq+20'd1);
   end
   if(okay&&ackok)begin
    published[wt[DW-1:0]]<=1;published_n[wt[DW-1:0]]<=0;ackseq<=ackseq+20'd1;ackseq_n<=~(ackseq+20'd1);
   end
   if(ra)begin
    reserved[pi]<=1;reserved_n[pi]<=0;ps[pi]<=meta[ri];ps_n[pi]<=meta_n[ri];pt[pi]<=rseq;pt_n[pi]<=~rseq;
    rseq<=rseq+20'd1;rseq_n<=~(rseq+20'd1);
   end
   if(capture)begin
    pd[rt[PW-1:0]]<=brdata[rp*256+:256];pd_n[rt[PW-1:0]]<=~brdata[rp*256+:256];pv[rt[PW-1:0]]<=1;pv_n[rt[PW-1:0]]<=0;
    allocated[rt[DW-1:0]]<=0;allocated_n[rt[DW-1:0]]<=1;published[rt[DW-1:0]]<=0;published_n[rt[DW-1:0]]<=1;
    retseq<=retseq+20'd1;retseq_n<=~(retseq+20'd1);cq<=1;cq_n<=0;
   end
   if((MUT==1)&&wa)begin cq<=1;cq_n<=0;end
   if(wa||capture)begin live<=live+9'(wa)-9'(capture);live_n<=~(live+9'(wa)-9'(capture));end
   if(pop)begin
    ov<=1;ov_n<=0;os<=ps[ph];os_n<=ps_n[ph];od<=(MUT==3)?(pd[ph]^256'd1):pd[ph];od_n<=~((MUT==3)?(pd[ph]^256'd1):pd[ph]);
    reserved[ph]<=0;reserved_n[ph]<=1;pv[ph]<=0;pv_n[ph]<=1;ph<=ph+PW'(1);ph_n<=~(ph+PW'(1));
   end else if(okay&&out_r)begin ov<=0;ov_n<=1;end
  end
 end
endmodule
`default_nettype wire
