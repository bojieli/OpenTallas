`timescale 1ns/1ps
module tb_hbm_cxijq_safe;
 parameter integer MUT=0, SD=0;
 reg clk=0;always #0.55 clk=~clk;
 reg rst=0;reg [31:0]j0,j1;reg[1023:0]a,b,c,d;reg sf,ic;
 wire[1023:0]l0,l1,s0,s1;wire lf,sfout;
 ot_hbm_su_static_cxport_ij_q #(.SD(SD)) legacy(clk,rst,j0,j1,a,b,c,d,l0,l1,sf,ic,lf);
 ot_hbm_su_static_cxport_ij_q #(.SD(SD),.SAFE_GATHER(1),.MUT(MUT)) safe(clk,rst,j0,j1,a,b,c,d,s0,s1,sf,ic,sfout);
 integer checks=0,errs=0,age=0;
 always @(negedge clk) begin
  j0=$urandom;j1=$urandom;sf=$urandom;ic=$urandom;
  for(integer i=0;i<32;i=i+1)begin a[i*32+:32]=$urandom;b[i*32+:32]=$urandom;c[i*32+:32]=$urandom;d[i*32+:32]=$urandom;end
 end
 always @(posedge clk)begin
  if(!rst)age=0;else age=age+1;
  #0.01;
  if(age>SD+15)begin checks=checks+1;if({l0,l1,lf}!=={s0,s1,sfout})begin errs=errs+1;if(errs<4)$display("MISMATCH age=%0d",age);end end
 end
 initial begin
  for(integer epoch=0;epoch<9;epoch=epoch+1)begin
   rst=0;repeat(4+epoch)@(negedge clk);#0.1;rst=1;repeat(1500)@(negedge clk);
  end
  $display("CXIJQ_SAFE %s checks=%0d errors=%0d SD=%0d MUT=%0d",errs?"FAIL":"PASS",checks,errs,SD,MUT);
  if(errs)$fatal(1,"CXIJQ_SAFE FAIL");$finish;
 end
endmodule
