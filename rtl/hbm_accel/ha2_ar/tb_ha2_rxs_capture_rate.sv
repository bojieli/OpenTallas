`timescale 1ns/1ps
// Smallest full-shape receiver: both 544-bit lanes, real 64-deep macro models.
// Continuous input plus returned output credits checks actual first-send latency and II.
module tb_ha2_rxs_capture_rate;
 localparam W=544,INJ=2,N=128;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[1:0] av=0,credit=0;
 reg[1087:0] data=0;reg[31:0] tag=0;
 wire[1:0] sv,rv;wire[1087:0] sd;wire[31:0] rt;wire quiet,fault;
 integer got[0:1],first=-1,last=-1,cycle;
 function automatic[W-1:0] row(input integer i,k);
  for(integer j=0;j<W/32;j=j+1)row[j*32+:32]=32'h73425180^(i<<24)^(k<<8)^j;
 endfunction
 ot_ha2_truecredit_receiver_s #(.W(W),.INJ(INJ),.AW(6),.TAGW(16),.CRD(8)) rx
 (.clk(clk),.rst_n(rst_n),.arrival_v(av),.receiver_ready(credit),.arrival_data(data),.arrival_tag(tag),
 .send_v(sv),.return_v(rv),.send_data(sd),.return_tag(rt),.quiet(quiet),.fault(fault));
 initial begin
  got[0]=0;got[1]=0;
  repeat(4)@(negedge clk);rst_n=1;
  for(cycle=0;cycle<N+80;cycle=cycle+1)begin
   @(negedge clk);av=(cycle<N)?2'b11:0;credit=sv;
   for(integer i=0;i<INJ;i=i+1)begin data[i*W+:W]=row(i,cycle);tag[i*16+:16]=16'(cycle);end
   @(posedge clk);#1;
   if(fault)$fatal(1,"CAPTURE_RATE_FAULT cycle=%0d",cycle);
   for(integer i=0;i<INJ;i=i+1)if(sv[i])begin
    if(sd[i*W+:W]!==row(i,got[i]) || rt[i*16+:16]!==16'(got[i]) || !rv[i])$fatal(1,"CAPTURE_RATE_DATA lane=%0d row=%0d",i,got[i]);
    if(i==0)begin
     if(first<0)first=cycle;
     if(last>=0 && cycle!=last+1)$fatal(1,"CAPTURE_RATE_BUBBLE cycle=%0d last=%0d",cycle,last);
     last=cycle;
    end
    got[i]=got[i]+1;
   end
   if(got[0]==N && got[1]==N && quiet)begin
    $display("HA2_CAPTURE_RATE_PASS rows=%0d lanes=2 width=544 first_send_cycle=%0d last_send_cycle=%0d ii=1",N,first,last);$finish;
   end
  end
  $fatal(1,"CAPTURE_RATE_TIMEOUT %0d/%0d",got[0],got[1]);
 end
endmodule
