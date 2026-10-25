`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,v=0,legal=0;always #5 clk=~clk;
reg[4:0]tag=0;reg[575:0]qb=0;
wire[16:0]s0,s1,c0,c1;
for(genvar b=0;b<17;b=b+1)begin:g
 ot_s81eng_token_bit #(.BIT(b),.CAPTURE_FIRST(0)) r(clk,rst_n,v,legal,tag,qb,s0[b],c0[b]);
 ot_s81eng_token_bit #(.BIT(b),.CAPTURE_FIRST(1)) d(clk,rst_n,v,legal,tag,qb,s1[b],c1[b]);
end
integer seed=1,cycle=0,checks=0;
initial begin
 if($value$plusargs("SEED=%d",seed))begin end
 repeat(4)@(negedge clk);rst_n=1;
 for(cycle=0;cycle<100000;cycle=cycle+1)begin
  @(negedge clk);
  if(cycle>4)begin checks=checks+1;if({s0,c0}!=={s1,c1})$fatal(1,"DIFF cycle%0d sel%h/%h cid%h/%h",cycle,s0,s1,c0,c1);end
  if(cycle%8191==8190)rst_n=0;else if(cycle%8191==3)rst_n=1;
  v=(cycle%37<32)?1:($random(seed)&1);legal=(cycle%41<32)?1:($random(seed)&1);
  tag=(cycle%37<32)?(cycle%32):$random(seed);
  for(integer k=0;k<18;k=k+1)qb[k*32+:32]=$random(seed);
 end
 $display("PASS TMAP exact ALL 34 outputs %0d cycles",checks);$finish;
end
endmodule
