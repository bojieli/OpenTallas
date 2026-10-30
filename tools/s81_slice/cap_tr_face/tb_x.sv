`timescale 1ps/1fs
module tb_x;
reg clk=0; always #416.5 clk=~clk;
reg rst_n=0;reg[279:0]rt=0;
wire [2:0]ov,oe,ff;wire[31:0]ot[0:2],od[0:2];
gold_cap_tr a(.clk(clk),.rst_n(rst_n),.rt(rt),.o_v(ov[0]),.o_t(ot[0]),.o_d(od[0]),.o_e(oe[0]),.fault(ff[0]));
ot_s81sl_cap_tr b(.clk(clk),.rst_n(rst_n),.rt(rt),.o_v(ov[1]),.o_t(ot[1]),.o_d(od[1]),.o_e(oe[1]),.fault(ff[1]));
mut_cap_tr c(.clk(clk),.rst_n(rst_n),.rt(rt),.o_v(ov[2]),.o_t(ot[2]),.o_d(od[2]),.o_e(oe[2]),.fault(ff[2]));
integer k,j,mism=0,mut=0;
initial begin
 for(k=0;k<2000;k=k+1) begin
  @(negedge clk);rst_n=k%400>=80;rt=0;
  if(k%400>=120 && k%400<140)for(j=0;j<4;j=j+1)rt[70*j+69]=1'bx;
  @(posedge clk);#1;
  if({ov[0],oe[0],ff[0]} !== {ov[1],oe[1],ff[1]})begin mism=mism+1;if(mism<5)$display("X_MISM k=%0d f=%b/%b",k,ff[0],ff[1]);end
  if(ff[0]!==ff[2])mut=mut+1;
 end
 $display("CAP_TR_X cycles=%0d mism=%0d mutant=%0d",k,mism,mut);
 if(mism || mut==0)$fatal(1,"CAP_TR_X_FAIL");
 $display("CAP_TR_X_PASS");$finish;
end
endmodule
