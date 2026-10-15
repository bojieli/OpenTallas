`timescale 1ns/1ps
module tb_qfd_xpf_static_schedule;
 parameter integer MUT_LATE=0,MUT_ISSUE=0,TEST_FAULT_TIMELINE=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,cv=0,clear=0,seal=0,start=0,stop=0;
 reg [2:0] ci=0;reg [187:0] cd=0;reg [3:0] cnt=2;
 reg mi=0,si=0;reg [11:0] mp=0,sp=0;
 wire [71:0] pf;wire fault;
 ot_qfd_xpf_static_schedule #(.ARM_TRANSPORT_EDGES(13),.MUT_LATE(MUT_LATE)) d
 (.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_index(ci),.cfg_data(cd),.cfg_clear(clear),
 .cfg_seal(seal),.cfg_count(cnt),.start(start),.stop(stop),.stage(6'd0),
 .cp_issue(1'b0),.cp_pc(12'd0),.me_issue(mi),.me_pc(mp),.su_issue(si),.su_pc(sp),.xpf(pf),.fault(fault));
 reg [71:0] pipe[0:12];integer j,c,arrived=-100,seen=0;
 always @(posedge clk)begin
  pipe[0]<=pf;for(j=1;j<13;j=j+1)pipe[j]<=pipe[j-1];
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 initial begin
  for(j=0;j<13;j=j+1)pipe[j]=0;
  repeat(3)tick();rst_n=1;clear=1;tick();clear=0;
  // The producer may issue BEFORE the arm: its first write is later and
  // immutable. Control must schedule the arm rather than stall that issue.
  ci=0;cd={32'd30,32'd2,32'd14,6'd0,2'd2,12'd0,72'h800112002010002001};cv=1;tick();
  ci=1;cd={32'd70,32'd40,32'd54,6'd0,2'd1,12'd11,72'h800050002004018be1};tick();cv=0;
  seal=1;tick();seal=0;start=1;tick();start=0;
  for(c=0;c<75;c=c+1)begin
   si=(c==(MUT_ISSUE!=0?3:2));sp=0;mi=(c==40);mp=11;
   tick();
   if(pipe[12][0])begin arrived=c;seen=seen+1;end
   if(c==30||c==70)begin
    if(c-arrived<3)$fatal(1,"static producer write lacks completed arm delivery");
   end
   if(fault&&!TEST_FAULT_TIMELINE)$fatal(1,"static schedule fault cycle %0d",c);
  end
  si=0;mi=0;stop=1;tick();stop=0;
  if(fault!==(TEST_FAULT_TIMELINE!=0)||seen!=2)$fatal(1,"completion/count fault");
  $display("PASS fixed-cycle arms13-hop transport,2 producers issue without stalls,3-edge first-write separation");$finish;
 end
endmodule
