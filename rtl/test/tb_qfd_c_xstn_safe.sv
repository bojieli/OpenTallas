`ifndef SYNTHESIS
`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst=0,r0=0,r1=0;reg[2:0]sidx=0;reg[515:0]d=0;
 wire[515:0]a,ra;wire[507:0]t,rt;
 wire[515:0]candidate_d=MUT?(d^516'h2):d;
 qfd_c_xstn_safe dut(ck,rst,sidx,candidate_d,a,t);
 always@(posedge ck)begin r0<=rst;r1<=r0;end
 qfd_c_xstn refdut(ck,r1,sidx,d,ra,rt);
 integer n,j,errors=0;
 initial begin
  for(n=0;n<6000;n=n+1)begin
   @(negedge ck);
   rst=(n>=12&&!(n>=900&&n<920)&&!(n>=3000&&n<3030));
   sidx=(n/97)%8;
   for(j=0;j<516;j=j+1)d[j]=$random;
   d[0]=(n%64==0);
   // Exercise both tagged line choices, nonmatching words, and every sx.
   d[511:508]=n%3?{1'b1,3'(n%8)}:0;
   d[515:512]=n%5?{1'b1,3'((n+3)%8)}:0;
   @(posedge ck);#1;
   if(n>5&&(a!==ra||t!==rt))begin errors=errors+1;if(errors<5)$display("SAFE_XSTN_MISMATCH n%0d",n);end
  end
  if(errors)$fatal(1,"SAFE_XSTN_FAIL MUT%0d errors%0d",MUT,errors);
  $display("SAFE_XSTN_PASS MUT%0d",MUT);$finish;
 end
endmodule
`endif
