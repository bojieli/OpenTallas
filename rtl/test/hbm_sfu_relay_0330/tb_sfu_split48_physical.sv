`timescale 1ns/1ps
module tb_sfu_split48_physical #(parameter integer R=23,MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=1;reg[623:0] data=0;
 wire[623:0] refq[0:R],gotq[0:R];
 assign refq[0]=data;assign gotq[0]=data;
 for(genvar n=0;n<R;n=n+1)begin:g
  hbfd_rly_624_EW reference(.ck(clk),.rs(rst_n),.i(refq[n]),.o(refq[n+1]));
  wire[623:0]mapped_input=(MUT==3 && n==0)?{gotq[n][623:96],gotq[n][47:0],gotq[n][95:48]}:gotq[n];
  hbfd_rly_624_split48_physical_candidate candidate(.ck_payload0(clk),.ck_payload1(clk),.ck_payload2(clk),.ck_payload3(clk),.ck_payload4(clk),.ck_payload5(clk),.ck_payload6(clk),.ck_payload7(((MUT==1)?1'b0:clk)),.ck_payload8(clk),.ck_payload9(clk),.ck_payload10(clk),.ck_payload11(clk),.ck_payload12(clk),.ck_reset((MUT==2)?1'b0:clk),.rs(rst_n),.i(mapped_input),.o(gotq[n+1]));
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
    if(gotq[n]!==refq[n])$fatal(1,"SPLIT48_PHYSICAL_ABI mismatch t=%0d station=%0d R=%0d MUT=%0d",t,n,R,MUT);
    checks=checks+1;
   end
  end
  $display("SPLIT48_PHYSICAL_ABI PASS R=%0d checks=%0d all624bits resetassert/release/cycle",R,checks);$finish;
 end
endmodule
