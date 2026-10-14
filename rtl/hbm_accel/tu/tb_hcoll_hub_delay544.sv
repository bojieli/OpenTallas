`timescale 1ns/1ps
module tb_hcoll_hub_delay544;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rn=0,v=0;reg[543:0]data;
 wire rv;wire[543:0]out;reg[543:0]gold[0:5000];reg[5000:0]due=0;
 integer cycles=0,checked=0,sent=0;
 ot_hcoll_hub_delay544 #(.MUT(MUT))dut(.clk(clk),.rst_n(rn),.valid(v),.data(data),.reply_v(rv),.reply(out));
 always @(posedge clk)begin
  cycles=cycles+1;
  if(v)begin gold[cycles+35]=data;due[cycles+35]=1;sent=sent+1;end
  if(cycles>20&&rv!==due[cycles])$fatal(1,"HUB_DELAY FAIL native35epoch cycle=%0d",cycles);
  if(rv)begin if(out!==gold[cycles])$fatal(1,"HUB_DELAY FAIL full544 checked=%0d",checked);checked=checked+1;end
 end
 initial begin
  repeat(8)@(negedge clk);rn=1;repeat(12)@(negedge clk);
  for(integer n=0;n<4096;n=n+1)begin
   v=(n%11!=3&&n%17!=8);
   for(integer b=0;b<544;b=b+1)data[b]=((n*17+b*13)^(n>>4)^(b>>3))&1;
   @(negedge clk);
  end
  v=0;repeat(40)@(negedge clk);
  if(checked!=sent)$fatal(1,"HUB_DELAY FAIL response count");
  $display("HUB_DELAY PASS full544 replies=%0d cycles=%0d",checked,cycles);$finish;
 end
endmodule
