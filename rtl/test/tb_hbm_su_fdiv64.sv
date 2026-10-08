`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,v=0;reg [31:0] a=0,b=0;
 wire [31:0] yg,y;wire vg,fg,vo,f;
 ot_hdc_fdiv gold(clk,rst,v,a,b,yg,vg,fg);
 ot_hdc_fdiv64 dut(clk,rst,v,a,b,y,vo,f);
 reg [33:0] hist[0:32];integer i,n,checked=0;
 always @(posedge clk) begin
  if(!rst) for(i=0;i<33;i=i+1)hist[i]<=0;
  else begin hist[0]<={vg,fg,yg};for(i=1;i<33;i=i+1)hist[i]<=hist[i-1];end
  #1;
  if(rst) begin
   if(vo!==hist[32][33])$fatal(1,"valid mismatch");
   if(vo) begin
    if({f,y}!==hist[32][32:0])$fatal(1,"result mismatch got %h expected %h",{f,y},hist[32][32:0]);
    checked=checked+1;
   end
  end
 end
 initial begin
  repeat(5)@(negedge clk);rst=1;
  for(n=0;n<3000;n=n+1)begin
   @(negedge clk);v=($urandom_range(0,7)!=0);a=$urandom;b=$urandom;
   if(n%17==0)b=0;if(n%19==0)a=32'h7fc01234;
   if(n%23==0)a=1;if(n%29==0)b=32'h7f7fffff;
   if(n==1001 || n==2000)rst=0;
   if(n==1004 || n==2004)rst=1;
  end
  @(negedge clk);v=0;repeat(75)@(negedge clk);
  $display("PASS comparisons=%0d latency=64 II=1 reset+bubbles+faults",checked);$finish;
 end
endmodule
