`timescale 1ns/1ps
module tb_qfd_xpf_release_guard;
 parameter integer MUT_EARLY=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,av=0,pv=0,issue=0;reg [71:0] ad=0;
 reg [11:0] ap=0,pp=0;reg [1:0] au=2,pu=2;
 wire ready,allow,release_p,fault;wire [71:0] pf;
 ot_qfd_xpf_release_guard #(.ARM_TO_WRITE_EDGES(16),.MUT_EARLY(MUT_EARLY)) d
 (.clk(clk),.rst_n(rst_n),.arm_v(av),.arm_descriptor(ad),.arm_pc(ap),.arm_unit(au),
 .arm_ready(ready),.producer_v(pv),.producer_pc(pp),.producer_unit(pu),
 .producer_requires_arm(1'b1),
 .producer_issue(issue),.producer_allow(allow),.xpf(pf),.released(release_p),.fault(fault));
 integer cyc=0,armed=-1,n,seen=0;
 always @(posedge clk)begin
  cyc=cyc+1;
  if(pf[0])begin armed=cyc;seen=seen+1;if(pf!==ad)$fatal(1,"descriptor mismatch");end
  if(issue&&(cyc-armed<16))$fatal(1,"producer issued before arm delivery: %0d edges",cyc-armed);
  if(fault)$fatal(1,"unexpected guard fault");
  if(cyc>3000)$fatal(1,"timeout");
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 initial begin
  repeat(3)tick();rst_n=1;
  for(n=0;n<40;n=n+1)begin
   ap=n;pp=n;pv=1;ad=72'h800112002010002001^(72'(n)<<1);av=1;#0.01;
   if(allow)$fatal(1,"arm arrival allowed simultaneous producer");
   tick();av=0;
   wait(allow);issue=1;tick();issue=0;
   if(!release_p)$fatal(1,"producer release pulse missing");
  end
  if(seen!=40)$fatal(1,"arm count %0d",seen);
  $display("PASS 40 real-width producer release guards,16-edge arm delivery separation");$finish;
 end
endmodule
