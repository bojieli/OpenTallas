`timescale 1ns/1ps
module tb_y;
 reg clk=0;always #1 clk=~clk;
 reg rst=0,yacc=0,req=0;
 reg[2815:0] data;
 wire[2815:0] a,b;
 wire fa,fb;
 integer cyc=0,occ=0,pushes=0,pops=0,checks=0,err=0;
 wire rb=req;
`ifdef MUT_Y
 wire rv=req ^ (cyc==75);
`else
 wire rv=req;
`endif
 ot_s81_hc_crooty_y #(.FIFO_SLICE(0)) u_a(.sk(clk),.srs(rst),.y_s(data),.yacc(yacc),.p_req(rb),.p_y(a),.p_flt(fa));
 ot_s81_hc_crooty_y #(.FIFO_SLICE(256)) u_b(.sk(clk),.srs(rst),.y_s(data),.yacc(yacc),.p_req(rv),.p_y(b),.p_flt(fb));
 initial begin
  data='0;repeat(5)@(negedge clk);rst=1;
  for(cyc=0;cyc<600;cyc=cyc+1)begin
   @(negedge clk);
   if(cyc>20)begin
    checks=checks+1;
    if(a!==b||fa!==fb)begin err=err+1; if(err<4)$display("YM mismatch cyc=%0d",cyc);end
   end
   yacc=0;req=0;
   if(cyc>8 && cyc<540)begin
    if(occ<14 && ((cyc%37<14)||(cyc%7==0)))begin yacc=1;occ=occ+1;pushes=pushes+1;end
    if(occ>3 && ((cyc%37>17)||(cyc%7==0)))begin req=1;occ=occ-1;pops=pops+1;end
   end else if(cyc>=540 && occ>0)begin req=1;occ=occ-1;pops=pops+1;end
   for(integer k=0;k<88;k=k+1)data[k*32+:32]=$urandom;
  end
  $display("YM checks=%0d pushes=%0d pops=%0d err=%0d",checks,pushes,pops,err);
  if(err||fa||fb)$fatal(1,"YM FAIL");$display("YM PASS");$finish;
 end
endmodule
