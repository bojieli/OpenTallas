`timescale 1ns/1ps
module control_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,re=0,we=0;wire rv,ce,fault,pending;wire[787:0]rd;integer i,j;
 ot_hbrom_xstore_protected #(.SP(3))dut(clk,rst,re,7'd0,we,7'd0,2'b11,2048'b0,rv,rd,ce,fault,pending);
 task tick;begin @(posedge clk);#1;end endtask
 initial begin
  for(i=0;i<35;i=i+1)begin
   rst=0;re=0;we=0;tick();@(negedge clk);rst=1;tick();@(negedge clk);
   if(i<3)dut.wv[i]=~dut.wv[i];
   else if(i<7)dut.rv[i-3]=~dut.rv[i-3];
   else if(i<14)dut.wa0[i-7]=~dut.wa0[i-7];
   else if(i<21)dut.wa1[i-14]=~dut.wa1[i-14];
   else if(i<28)dut.wa2[i-21]=~dut.wa2[i-21];
   else if(i<30)dut.wo0[i-28]=~dut.wo0[i-28];
   else if(i<32)dut.wo1[i-30]=~dut.wo1[i-30];
   else if(i<34)dut.wo2[i-32]=~dut.wo2[i-32];
   else dut.fault_q=~dut.fault_q;
   re=1;we=1;#1;
   if(!fault||rv)$fatal(1,"metadata fault escaped %0d",i);
   repeat(5)tick();
   if(!fault||rv)$fatal(1,"metadata fault not sticky %0d",i);
  end
  $display("PASS all35 new xstore metadata state bits failclosed");$finish;
 end
endmodule
