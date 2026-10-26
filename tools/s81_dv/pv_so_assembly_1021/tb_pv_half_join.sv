`timescale 1ns/1ps
module tb_pv_half_join;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,cv=0;
 reg[15:0]lf=5,pf=328;reg[561:0]lp=0,pp=0;
 wire ov,fault;wire[1:0]oq;wire[512:0]od;
 dsdv_pv_half_join dut(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.local_first(lf),.peer_first(pf),.local_pv(lp),.peer_pv(pp),.pv_v(ov),.pv_quarter(oq),.pv_d(od),.fault(fault));
 function automatic[512:0]word_(input integer i);
 reg[512:0]v;begin
 v=0;if(i%5==0)begin v[512]=1;v[93:92]=2'((i/40)/4);v[97:94]=4'(i/40);v[119:99]=777;v[91:72]=20'h92345;v[71:64]=8'((i%40)/5);end
 else for(integer h=0;h<16;h=h+1)v[32*h+:32]=32'h3f000000^32'(i*101+h*337);
 word_=v;end endfunction
 integer mut=0,n=0,cyc=0,last_input=-1;integer expected_cycle[0:639];reg collecting=0;
 always @(negedge clk)if(collecting)begin
  if(ov)begin
   if(n>=640 || od!==word_(n) || oq!==2'((n/40)/4))$fatal(1,"HALF_JOIN_DATA n%0d quarter%0d",n,oq);
   if(cyc!=expected_cycle[n])$fatal(1,"HALF_JOIN_AGE n%0d age%0d",n,cyc-expected_cycle[n]);
   n=n+1;
  end
 end
 task tick;@(negedge clk);#0.01;endtask
 initial begin
  if($value$plusargs("mut=%d",mut));repeat(4)tick();rst_n=1;repeat(3)tick();
  cv=1;if(mut==1)pf=100;tick();cv=0;collecting=(mut==0);
  for(cyc=1;cyc<655;cyc=cyc+1)begin
   lp=0;pp=0;
   if(cyc>=lf && cyc<lf+320)begin lp={48'd0,word_(cyc-lf),1'b1};expected_cycle[cyc-lf]=cyc;if(mut==2 && cyc==lf+17)lp[0]=0;if(mut==3 && cyc==lf+19)lp[514]=1;end
   if(cyc>=pf && cyc<pf+320)begin pp={48'd0,word_(320+cyc-pf),1'b1};expected_cycle[320+cyc-pf]=cyc;end
   tick();
  end
  collecting=0;
  if(mut==0)begin if(fault || n!=640)$fatal(1,"HALF_JOIN_COUNT n%0d fault%0d",n,fault);$display("HALF_JOIN_PASS records640 exact513 quarter4 booked-capture-edge");end
  else begin if(!fault)$fatal(1,"HALF_JOIN_NEGATIVE_ESCAPED %0d",mut);$display("HALF_JOIN_CAUGHT mut%0d",mut);end
  $finish;
 end
 initial begin #5000;$fatal(1,"HALF_JOIN_TIMEOUT");end
endmodule
