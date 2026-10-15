`timescale 1ns/1ps
module tb_qfd_xpf_schedule_bank;
 parameter integer MUT_EARLY=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,cv=0,clear=0,seal=0;reg [2:0] ci=0;reg [91:0] cd=0;reg [3:0] cnt=4;
 reg [5:0] stage=0;reg mv=0,sv=0,mi=0,si=0;reg [11:0] mp=0,sp=0;
 wire ma,sa,ready,fault;wire [71:0] pf;
 ot_qfd_xpf_schedule_bank #(.ARM_TO_WRITE_EDGES(16),.MUT_EARLY(MUT_EARLY)) d
 (.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_index(ci),.cfg_data(cd),.cfg_clear(clear),
 .cfg_seal(seal),.cfg_count(cnt),.cfg_ready(ready),.stage(stage),
 .me_v(mv),.me_pc(mp),.me_issue(mi),.su_v(sv),.su_pc(sp),.su_issue(si),
 .me_allow(ma),.su_allow(sa),.xpf(pf),.fault(fault));
 reg [71:0] ds[0:3];integer cyc=0,seen=0,arm_cycle=0,e,k;
 always @(posedge clk)begin
  cyc=cyc+1;
  if(pf[0])begin
   if(pf!==ds[seen%4])$fatal(1,"descriptor order mismatch %0d",seen);
   seen=seen+1;arm_cycle=cyc;
  end
  if((mi||si)&&cyc-arm_cycle<16)$fatal(1,"unreleased producer");
  if(fault)$fatal(1,"bank fault");
  if(cyc>1000)$fatal(1,"timeout");
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 initial begin
  ds[0]=72'h800112002010002001;ds[1]=72'h800050002004018be1;
  ds[2]=72'h80040e002040002001;ds[3]=72'h8000d000200c01afe1;
  repeat(3)tick();rst_n=1;
  if(ma||sa)$fatal(1,"unconfigured producers allowed");
  // A prior-stage record can arm an operand whose consumer is in a later
  // stage. Here stage0 producerPC0 is the initial embedding's X producer.
  for(e=0;e<2;e=e+1)begin
   stage=e;clear=1;tick();clear=0;
   for(k=0;k<4;k=k+1)begin
    ci=k;cd={6'(e),(k==1?2'd1:2'd2),12'(k),ds[k]};cv=1;tick();cv=0;
   end
   seal=1;tick();seal=0;
   for(k=0;k<4;k=k+1)begin
    if(k==1)begin mv=1;mp=k;#0.01;wait(ma);mi=1;tick();mi=0;mv=0;end
    else begin sv=1;sp=k;#0.01;wait(sa);si=1;tick();si=0;sv=0;end
   end
  end
  if(seen!=8)$fatal(1,"arm count %0d",seen);
  $display("PASS explicit compiler bank 2 producer stages,8 full-width descriptor releases, unsealed issue refusal");$finish;
 end
endmodule
