`timescale 1ns/1ps
module fp_tb;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,v=0;reg[31:0]a=0,b=0;wire[31:0]ya,yar,ym,ymr,seed;wire fa,far,fm,fmr;wire[63:0]yc,ycr,mc,mcr;
ot_s81dv_qadd_n32 #(.LAT(6),.NYC(2))ca(clk,rst_n,v,a,b,ya,fa,yc);
ot_s81dv_qadd_n32_n8ref #(.LAT(6),.NYC(2))ra(clk,rst_n,v,a,b,yar,far,ycr);
ot_s81dv_qmul_n32 #(.LAT(5),.NYC(2))cm(clk,rst_n,v,a,b,ym,fm,mc);
ot_s81dv_qmul_n32_n8ref #(.LAT(5),.NYC(2))rm(clk,rst_n,v,a,b,ymr,fmr,mcr);
ot_s81dv_seed_sub32 ss(.x(a),.y(seed));
integer checks=0;reg mutant;
initial begin
mutant=$test$plusargs("MUTANT");
repeat(8)@(negedge clk);rst_n=1;
for(integer c=0;c<12000;c=c+1)begin
 @(negedge clk);
 if(c>10)begin
  if({ya,fa,yc}!=={yar^(mutant?32'b1:32'b0),far,ycr})$fatal(1,"FP_N10_MISMATCH add cyc%0d",c);
  if({ym,fm,mc}!=={ymr,fmr,mcr})$fatal(1,"FP_N10_MISMATCH mul cyc%0d",c);
  if(seed!==32'h5f3759df-(a>>1))$fatal(1,"FP_N10_MISMATCH seed cyc%0d",c);
  checks++;
 end
 a=$urandom;b=$urandom;v=($urandom%4)!=0;
 if(c%997==0)rst_n=0;else if(c%997==4)rst_n=1;
end
$display("FP_N10_PASS checks%0d",checks);$finish;
end
endmodule
