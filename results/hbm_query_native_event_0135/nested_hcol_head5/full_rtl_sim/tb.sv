`timescale 1ns/1ps
module tb_hcol_regional_equiv;
 localparam QW=568, KW=544;
 reg ck0=0,ck1=0; always #5 ck0=~ck0; initial begin #2; forever #5 ck1=~ck1; end
 reg rst=0,qv=0; reg[QW-1:0] q=0; reg[KW-1:0] key=0; reg[31:0] hid=32'h07060504,cs=0; reg cf=0;
 wire[31:0] a,b; wire af,bf; wire[1:0] ao,bo;
 integer mut=0,seed=203211,checks=0,errors=0,cycles=0,nonzero=0,j,k;
 wire[QW-1:0] q1=(mut!=0)?(q ^ (568'b1 << 32)):q;
 ot_hidx_score_hcol #(.HALF(1),.DELIVERED_RESET(1)) gold(.clk_pair({ck1,ck0}),.rst_col(rst),.qv_b(qv),.q_b(q),.key(key),.hid4(hid),.cs_in(cs),.cf_in(cf),.cs_out(a),.cf_out(af),.prdy(ao));
 ot_hidx_score_hcol_regional_head5 #(.HALF(1),.DELIVERED_RESET(1)) dut(.clk_pair({ck1,ck0}),.rst_col(rst),.qv_b({qv,qv}),.q_b({q1[564:0],q[564:0]}),.key({key,key}),.hid4(hid),.cs_in(cs),.cf_in(cf),.cs_out(b),.cf_out(bf),.prdy(bo));
 always @(negedge ck0) begin
  cycles=cycles+1;
  if(cycles>220) begin checks=checks+1; if({a,af,ao}!=={b,bf,bo})begin errors=errors+1;if(errors<4)$display("MISMATCH cycle=%0d gold=%h/%b/%b gate=%h/%b/%b",cycles,a,af,ao,b,bf,bo);end
   if(a!=0)nonzero=nonzero+1;
  end
 end
 initial begin
  if($value$plusargs("MUT=%d",mut))begin end
  repeat(4)@(negedge ck0);rst=1;
  for(k=0;k<1400;k=k+1)begin
   @(negedge ck0);#1;
   qv=(k%32<12);q[567:560]=8'(4+k%4);
   for(j=0;j<16;j=j+1)q[48+32*j+:32]=$random(seed);
   q[47:16]=32'h7f7e7d7c;q[15:0]=16'h3f80;
   for(j=0;j<16;j=j+1)key[32*j+:32]=$random(seed);
   key[543:512]=32'h7c7d7e7f;
   cs=32'h3f800000;cf=(k%37==0);
   if(k==701)rst=0;if(k==705)rst=1;
  end
  @(negedge ck0);qv=0;repeat(220)@(negedge ck0);
  $display("HCOL_REGIONAL_EQ checks=%0d errors=%0d nonzero=%0d mutant=%0d",checks,errors,nonzero,mut);
  if(errors!=0 || checks<1200 || nonzero==0)$fatal(1,"HCOL_REGIONAL_EQ FAIL");
  $display("HCOL_REGIONAL_EQ PASS");$finish;
 end
endmodule
