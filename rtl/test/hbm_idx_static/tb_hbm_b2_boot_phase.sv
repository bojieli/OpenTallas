`timescale 1ns/1ps
module tb_hbm_b2_boot_phase;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rn=0;wire tx,nw,ne;
 localparam integer WAIT=17,NW=2,NE=3;
 ot_hbm_b2_boot_phase #(.BOOT_WAIT(WAIT),.NW_AGE(NW),.NE_AGE(NE),.MUT(MUT)) dut(clk,rn,tx,nw,ne);
 reg[2:0]actual_route=0;
 always @(posedge clk)if(!rn)actual_route<=0;else actual_route<={actual_route[1:0],tx};
 integer c,ns=0,nns=0,nes=0;
 initial begin
  repeat(5)@(negedge clk);rn=1;
  for(c=1;c<80;c=c+1)begin
   @(posedge clk);#1;
   if(tx!==(c==WAIT))$fatal(1,"BOOT_TX_TIME got%0d cycle%0d",tx,c);
   if(nw!==(c==WAIT+NW)||ne!==(c==WAIT+NE))$fatal(1,"BOOT_RX_TIME cycle%0d",c);
   if(nw!==actual_route[NW-1]||ne!==actual_route[NE-1])$fatal(1,"BOOT_PATH_MISALIGN cycle%0d",c);
   ns+=tx;nns+=nw;nes+=ne;
  end
  if(ns!=1||nns!=1||nes!=1)$fatal(1,"BOOT_REPEAT");
  $display("B2_BOOT_PHASE PASS wait17 mirrorages2/3 onebroadcast, no token restart");$finish;
 end
endmodule
