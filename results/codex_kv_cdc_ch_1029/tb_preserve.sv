`timescale 1ns/1ps
module coupon #(parameter MUT=0)(input clk,rst_n,issue,valid,output i_cr,o_v,output reg internal_use);
 (* keep=1 *) reg crq;
 (* keep=1 *) reg swv;
 (* keep=1 *) reg ov;
 wire dead_ov_alias=ov;
 assign i_cr=crq;
 assign o_v=ov;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin crq<=0;swv<=0;ov<=0;internal_use<=0;end
  else begin crq<=issue;swv<=MUT?~issue:issue;ov<=valid;internal_use<=swv;end
endmodule
module reference_coupon(input clk,rst_n,issue,valid,output i_cr,o_v,output reg internal_use);
 reg crq,swv,ov;
 assign i_cr=crq;assign o_v=ov;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin crq<=0;swv<=0;ov<=0;internal_use<=0;end
  else begin crq<=issue;swv<=issue;ov<=valid;internal_use<=swv;end
endmodule
module tb_preserve;
 parameter MUT=0;
 reg clk=0,rst_n=0,issue=0,valid=0;
 always #5 clk=~clk;
 wire cr,v,use_new,ref_cr,ref_v,use_ref;
 coupon #(.MUT(MUT)) d(clk,rst_n,issue,valid,cr,v,use_new);
 reference_coupon r(clk,rst_n,issue,valid,ref_cr,ref_v,use_ref);
 integer checked=0;
 initial begin
  repeat(3)@(negedge clk);
  rst_n=1;
  for(integer n=0;n<128;n++)begin
   @(negedge clk);issue=n[0]^n[2];valid=n[1]^n[3];
   if(n==53)rst_n=0;if(n==56)rst_n=1;
   #1;
   if({cr,v,use_new}!=={ref_cr,ref_v,use_ref})$fatal(1,"PRESERVE mutant/mismatch at %0d",n);
   checked++;
  end
  $display("PASS PRESERVE %0d edges zero-cycle credit/valid/internal consumer reset",checked);$finish;
 end
endmodule
