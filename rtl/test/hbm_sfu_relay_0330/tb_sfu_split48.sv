`timescale 1ns/1ps
module tb_sfu_split48 #(parameter integer R=23,MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=1;reg[623:0] data=0;
 wire[623:0] refq[0:R],gotq[0:R];
 assign refq[0]=data;assign gotq[0]=data;
 for(genvar n=0;n<R;n=n+1)begin:g
  hbfd_rly_624_EW reference(.ck(clk),.rs(rst_n),.i(refq[n]),.o(refq[n+1]));
  hbfd_rly_624_split48_candidate #(.MUT(n==0?MUT:0)) candidate
   (.ck(clk),.rs(rst_n),.i(gotq[n]),.o(gotq[n+1]));
 end
 integer checks=0;
 initial begin
  #1;rst_n=0;
  for(integer t=0;t<240;t=t+1)begin
   @(negedge clk);
   // Exercise assertion, release and live traffic. Golden input stamps are
   // external stimulus, with every one of 624 positions carrying varying data.
   if(t==4||t==103)rst_n=1;
   if(t==97)rst_n=0;
   for(integer b=0;b<624;b=b+1)data[b]=((t*19+b*11+(b/48)*7)>>(b%7))&1;
   @(posedge clk);#1;
   for(integer n=1;n<=R;n=n+1)begin
    if(gotq[n]!==refq[n])$fatal(1,"SPLIT48 mismatch t=%0d station=%0d R=%0d MUT=%0d",t,n,R,MUT);
    checks=checks+1;
   end
  end
  $display("SPLIT48 PASS R=%0d checks=%0d all624bits resetassert/release/cycle",R,checks);$finish;
 end
endmodule
