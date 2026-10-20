`timescale 1ns/1ps
module tb_s3_acc14_exhaustive;
 reg[13:0]a;reg[4:0]b;wire[13:0]y;wire low_carry;
 ot_hidx_s3_acc14 u(.a(a),.b(b),.mut(1'b0),.y(y),.low_carry(low_carry));
 wire over=(|a[13:10])||(a[9]&&((|a[8:0])||(|b)))||((&a[8:5])&&low_carry&&(|y[4:0]));
 integer checks=0;
 initial begin
  for(integer ai=0;ai<16384;ai=ai+1)for(integer bi=0;bi<32;bi=bi+1)begin
   a=14'(ai);b=5'(bi);#1;
   if(y!==14'(ai+bi)||over!==((ai+bi)>512))
    $fatal(1,"S3_ACC_EXHAUSTIVE_FAIL a%0d b%0d sum%0d over%b",ai,bi,y,over);
   checks=checks+1;
  end
  $display("S3_ACC_EXHAUSTIVE_PASS states%0d sum14_modulo_and_exact_hazard",checks);$finish;
 end
endmodule
