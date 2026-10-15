`timescale 1ns/1ps
module tb_qfd_vm_su1024_t;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rtg=0,svc=0,p1=0,p2=0;
 reg[1023:0]sx=0,gold=0;wire[1023:0]so;
 ot_qfd_vm_su1024_t #(.MUT(MUT)) dut(.*);
 integer cycle,lane,checked=0,errors=0;reg ready=0;
 initial begin
  repeat(4)@(negedge clk);rtg=1;
  for(cycle=0;cycle<512;cycle=cycle+1)begin
   @(negedge clk);svc=(cycle%7!=2)&&(cycle%5!=1);
   for(lane=0;lane<32;lane=lane+1)sx[lane*32+:32]=(cycle<<8)|lane;
   @(posedge clk);if(p2)begin gold=sx;ready=1;end
   p2=p1;p1=svc;
   #1;if(ready)begin checked=checked+1;if(so!==gold)errors=errors+1;end
  end
  if(errors||checked<500)$fatal(1,"FAIL SU1024 errors=%0d checked=%0d",errors,checked);
  $display("PASS SU1024 checked=%0d original_two_epoch_enable exact_hclk",checked);$finish;
 end
endmodule
