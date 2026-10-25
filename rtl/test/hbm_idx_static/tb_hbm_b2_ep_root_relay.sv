`timescale 1ns/1ps
module tb_hbm_b2_ep_root_relay;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rn=0;reg[614:0]rx=0;reg[631:0]tx=0;
 wire[614:0]ro;wire[631:0]to;
 ot_hbm_b2_ep_root_relay #(.MUT(MUT)) dut(clk,rn,rx,tx,ro,to);
 reg[614:0]er;reg[631:0]et;
 integer c,j;
 initial begin
  for(c=0;c<300;c=c+1)begin
   @(negedge clk);rn=(c>3&&!(c>=150&&c<=153));
   for(j=0;j<615;j=j+1)rx[j]=$urandom_range(0,1);
   for(j=0;j<632;j=j+1)tx[j]=$urandom_range(0,1);
   er=rx;et=tx;
   if(!rn)begin er[614:612]=0;et[613:612]=0;et[622]=0;et[624]=0;end
   @(posedge clk);#1;
   if(ro!==er||to!==et)$fatal(1,"EP_ROOT_RELAY mismatch cycle%0d MUT%0d",c,MUT);
  end
  $display("EP_ROOT_RELAY PASS 300 cycles 374100 bits MUT%0d",MUT);$finish;
 end
endmodule
