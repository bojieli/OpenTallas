`ifndef SYNTHESIS
`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg wc=0,rc=0;always #5 wc=~wc;
 integer phase=0;
 initial begin if(!$value$plusargs("PHASE=%d",phase))phase=0;#(5+phase);rc=1;forever #5 rc=~rc;end
 reg rst=0;reg[257:0]i=0;
 wire[1031:0]b,qb;wire[43:0]v,qv;wire[257:0]direct_o,forward_o;
 qfd_c_land_safe_w #(.W(258))w(wc,rst,i,b,v);
 qfd_c_bank_forward_safe #(.W(258))f(wc,rst,b,v,qb,qv);
 qfd_c_land_safe_r #(.W(258))direct_r(rc,rst,b,v,direct_o);
 qfd_c_land_safe_r #(.W(258),.K(MUT?1:2))forward_r(rc,rst,qb,qv,forward_o);
 integer n=0,j,errors=0;
 always@(negedge wc)begin
  n=n+1;rst=(n>=12&&!(n>=300&&n<320)&&!(n>=700&&n<720));
  for(j=0;j<258;j=j+1)i[j]=$random;
 end
 always@(posedge rc)begin
  #0.1;
  if(n>5&&direct_o!==forward_o)begin errors=errors+1;if(errors<5)$display("FORWARD_MISMATCH n%0d phase%0d mut%0d",n,phase,MUT);end
  if(n>=1500)begin
   if(errors)$fatal(1,"BANK_FORWARD_FAIL MUT%0d PHASE%0d errors%0d",MUT,phase,errors);
   $display("BANK_FORWARD_PASS MUT%0d PHASE%0d",MUT,phase);$finish;
  end
 end
endmodule
`endif
