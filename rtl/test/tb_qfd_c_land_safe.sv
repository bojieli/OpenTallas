`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg ck=0; always #5 ck=~ck;
 reg rst=0,ref_rst=0;
 reg [257:0] i=0;
 wire [1031:0] bank,ref_bank;
 wire [257:0] o,ref_o;
 wire [11:0] epo;
 wire [3:0] vld;
 qfd_c_land_safe_w #(.W(258)) w(ck,rst,i,bank);
 qfd_c_land_safe_r #(.W(258),.K(MUT?3:2)) r(ck,rst,bank,o);
 always @(posedge ck) ref_rst<=rst;
 qfd_c_land_w #(.W(258)) rw(ck,ref_rst,i,ref_bank,epo,vld);
 qfd_c_land_r #(.W(258)) rr(ck,ref_rst,ref_bank,epo,vld,ref_o);
 integer n,k,errors=0;
 initial begin
  for(n=0;n<2000;n=n+1) begin
   @(negedge ck);
   rst=(n>=8 && !(n>=500 && n<508) && !(n>=1500 && n<1510));
   for(k=0;k<258;k=k+1) i[k]=$random;
   @(posedge ck); #1;
   if(n>5 && o!==ref_o) begin
    errors=errors+1;
    if(errors<4) $display("SAFE_LAND_MISMATCH cycle=%0d",n);
   end
  end
  if(errors) $fatal(1,"SAFE_LAND_FAIL MUT%0d errors=%0d",MUT,errors);
  $display("SAFE_LAND_PASS MUT%0d",MUT); $finish;
 end
endmodule
