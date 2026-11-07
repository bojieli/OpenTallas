`timescale 1ns/1ps
module tb;
  reg clk=0; always #5 clk=~clk;
  reg [31:0] a=0,r0=0,r1=0,g0=0,g1=0,lk=0;
  integer cycle=0,bad=0;
  always_latch if(!clk) lk=(`MUT==1)?a:r0;
  always @(posedge clk)begin
    r0<=a;r1<=lk;g0<=a;g1<=g0;#1;
    if(cycle>4 && r1!==g1)bad++;
    if(cycle==10000)begin
      $display("N4_PHASE_RESULT MUT=%0d bad=%0d cycles=%0d",`MUT,bad,cycle);
      if((`MUT==0&&bad!=0)||(`MUT==1&&bad==0))$fatal(1,"phase or mutant failed");
      $finish;
    end
  end
  always @(negedge clk)begin a<=$urandom;cycle<=cycle+1;end
endmodule
