`timescale 1ns/1ps
module tb_hgi_coll_delivery_credit;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg[3:0] take=0,ret=0;wire[3:0]permit;wire fault;wire[31:0]credits;
 integer refc[0:3],outstanding[0:3];integer checked=0,blocked=0;
 reg[3:0] delay[0:159];
 ot_hgi_coll_delivery_credit #(.ENABLE(1),.MUT(MUT)) dut(
  .clk(clk),.rst_n(rst_n),.reserve(take),.credit_return(ret),.permit(permit),.fault(fault),.credits(credits));
 task reset;
  begin
   @(negedge clk);rst_n=0;take=0;ret=0;
   for(integer l=0;l<4;l=l+1)begin refc[l]=128;outstanding[l]=0;end
   for(integer t=0;t<160;t=t+1)delay[t]=0;
   repeat(2)@(negedge clk);rst_n=1;
  end
 endtask
 task check;
  begin
   for(integer l=0;l<4;l=l+1)begin
    refc[l]=refc[l]-integer'(take[l])+integer'(ret[l]);
    outstanding[l]=outstanding[l]+integer'(take[l])-integer'(ret[l]);
    if(refc[l]<0||refc[l]>128)$fatal(1,"reservation over capacity lane%0d",l);
   end
   @(posedge clk);#1;
   if(fault)$fatal(1,"unexpected fault");
   for(integer l=0;l<4;l=l+1)begin
    if(credits[l*8+:8]!==8'(refc[l]))$fatal(1,"credit count lane%0d",l);
    if(refc[l]+outstanding[l]!=128)$fatal(1,"conservation");
   end
   checked=checked+1;
  end
 endtask
 initial begin
  reset();
  // Sink deliberately unavailable for160 cycles: all128 credits are reserved
  // before the first return, then selection must stop despite in-flight data.
  for(integer t=0;t<450;t=t+1)begin
   @(negedge clk);ret=delay[t%160];take=permit;
   if(t>250)take=permit & 4'(t);
   if(take==0)blocked=blocked+1;
   delay[t%160]=take;
   check();
  end
  if(blocked==0)$fatal(1,"did not exercise finite backpressure");
  // One complementary-state error must stop every reservation immediately.
  @(negedge clk);take=0;ret=0;
  dut.inverse[0]=8'h00;
  #1;if(permit!=0)$fatal(1,"corrupt control still permits delivery");
  @(posedge clk);#1;if(!fault)$fatal(1,"control corruption not sticky");
  reset();
  @(negedge clk);ret=4'b0001;
  @(posedge clk);#1;if(!fault)$fatal(1,"extra acknowledgement accepted");
  $display("PASS delivery pre-reservation checked=%0d blocked=%0d; control corruption and extra ACK fail closed",checked,blocked);
  $finish;
 end
endmodule
