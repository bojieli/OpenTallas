`timescale 1ns/1ps
// Minimum production PIPE0 reservation gate, two finite SQ and CQ relays,
// engine IB4 with exact one/N response amplification and finite sequencer sink.
module tb_qwen_native_elastic_collective;
 parameter integer AG=1, NWORDS=64, NF=2;
 reg ck=0, ckd=0, rst_n=0, go=0;
 always #0.416667 ck=~ck; always #0.555556 ckd=~ckd;
 wire [546:0] sq[0:NF];wire scr[0:NF];
 wire [516:0] cq[0:NF];wire ccr[0:NF];wire sf[NF-1:0],cf[NF-1:0];
 reg iv=0;reg[545:0] id=0;assign sq[0]={iv,id};
 genvar j;
 generate for(j=0;j<NF;j=j+1)begin:g
  ot_qwen_native_elastic_relay #(.W(546),.DEPTH(4),.OCRED(4),.ENABLE(1)) s(
   .clk(ckd),.rst_n(rst_n),.i_v(sq[j][546]),.i_d(sq[j][545:0]),.i_cr(scr[j]),
   .o_v(sq[j+1][546]),.o_d(sq[j+1][545:0]),.o_cr(scr[j+1]),.fault(sf[j]));
  ot_qwen_native_elastic_relay #(.W(516),.DEPTH(4),.OCRED(4),.ENABLE(1)) c(
   .clk(ckd),.rst_n(rst_n),.i_v(cq[j][516]),.i_d(cq[j][515:0]),.i_cr(ccr[j]),
   .o_v(cq[j+1][516]),.o_d(cq[j+1][515:0]),.o_cr(ccr[j+1]),.fault(cf[j]));
 end endgenerate
 wire ev;wire[545:0] ed;reg ecr=0, rv=0;reg[515:0] rd=0;wire fk,fd;
 ot_qwen_die_coll_xfifo #(.PIPE(0)) native(
  .ck(ck),.ckd(ckd),.rst_n(rst_n),.i_seq_coll_v(sq[NF][546]),.i_seq_coll(sq[NF][545:0]),.i_seq_coll_cr(scr[NF]),
  .o_seq_coll_v(ev),.o_seq_coll(ed),.o_seq_coll_cr(ecr),.i_coll_seq_v(rv),.i_coll_seq(rd),
  .o_coll_seq_v(cq[0][516]),.o_coll_seq(cq[0][515:0]),.o_coll_seq_cr(ccr[0]),.fault_ck(fk),.fault_ckd(fd));
 reg take=0;wire ov,sinkfault;wire[515:0] od;
 ot_link_credit_rx #(.W(516),.DEPTH(4),.WFREE(1)) sink(
  .clk(ckd),.rst_n(rst_n),.l_valid(cq[NF][516]),.l_data(cq[NF][515:0]),.l_credit(ccr[NF]),
  .o_valid(ov),.o_data(od),.o_ready(take),.fault(sinkfault));
 // Minimal legal engine: input depth4, returns its input credit on dequeue,
 // emits exactly AG?4:1 output beats per input without output backpressure.
 reg[545:0] ib[0:3];integer wp=0,rp=0,count=0,left=0;reg[515:0] active=0;
 wire pop=go && count>0 && left==0;
 always @(posedge ck)begin
  ecr<=0;rv<=0;
  if(go)begin
   if(ev)begin if(count==4 && !pop)$fatal(1,"engine IB overflow");ib[wp]<=ed;wp=(wp+1)%4;end
   if(pop)begin active<=ib[rp][515:0];rp=(rp+1)%4;left<=AG?4:1;ecr<=1;end
   else if(left>0)begin rv<=1;rd<=active;left<=left-1;end
   count=count+ev-pop;
  end
 end
 integer cycle=0,sent=0,credits=4,received=0,first=-1,last=-1,firstcr=-1;
 always @(negedge ckd)take=go && cycle%31>10;
 always @(posedge ckd)begin
  cycle=cycle+1;
  if(cycle>200+NWORDS*200)$fatal(1,"deadlock sent=%0d received=%0d",sent,received);
  if(go)begin
   if(iv)begin if(first<0)first=cycle;last=cycle;sent=sent+1;end
   if(scr[0])begin credits=credits+1;if(firstcr<0)firstcr=cycle;end
   if(sent<NWORDS && credits>0)begin iv<=1;id<=sent;id[513]<=AG;credits=credits-1;end else iv<=0;
   if(ov && take)begin
    if(od[31:0]!==received/(AG?4:1))$fatal(1,"response order at%0d data%0d",received,od[31:0]);
    received=received+1;
   end
   if(fk || fd || sinkfault)$fatal(1,"native/sink fault");
  end
 end
 initial begin
  repeat(20)@(negedge ckd);rst_n=1;repeat(20)@(negedge ckd);go=1;
  wait(received==NWORDS*(AG?4:1));repeat(30)@(negedge ckd);
  if(sent!=NWORDS || fk || fd || sinkfault || sf[0] || sf[NF-1] || cf[0] || cf[NF-1])$fatal(1,"final fault");
  $display("PASS native_elastic_collective AG=%0d SQrelays=%0d CQrelays=%0d sent=%0d received=%0d firstcredit=%0d launch_window=%0d",AG,NF,NF,sent,received,firstcr-first,last-first+1);$finish;
 end
endmodule
