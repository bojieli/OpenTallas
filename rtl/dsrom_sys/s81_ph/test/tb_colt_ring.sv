`timescale 1ns/1ps
module tb_ring;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,push=0,pop=0;reg [511:0] wd=0;wire h0,h1,o0,o1;wire [511:0] d0,d1;
ot_s81ph_colt_fifo #(.RING(0)) base(clk,rst_n,push,wd,pop,h0,d0,o0);
ot_s81ph_colt_fifo #(.RING(1)) ring(clk,rst_n,push,wd,pop,h1,d1,o1);
integer i,j,seed=19,random_word,reads=0;
initial begin
 repeat(5) @(negedge clk);rst_n=1;
 for(i=0;i<100000;i=i+1) begin
  @(negedge clk);
  if(h0!==h1 || o0!==o1 || (h0 && d0!==d1)) $fatal(1,"COLT_RING FAIL i=%0d",i);
  if(h0 && pop) reads=reads+1;
  random_word=$random(seed);push=(random_word&7)<3;pop=((random_word>>4)&7)<4;
  if(i%1000<350) begin push=1;pop=0;end
  if(i%1000>=350 && i%1000<700) begin push=0;pop=1;end
  for(j=0;j<16;j=j+1) wd[j*32+:32]=$random(seed);
  if(i%17003==17002) begin rst_n=0;push=0;pop=0;end
  else rst_n=1;
 end
 $display("COLT_RING PASS cycles=100000 reads=%0d",reads);$finish;
end
endmodule
