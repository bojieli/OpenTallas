`timescale 1ns/1ps
module tb_tkm_return;
 parameter integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,v=0,busy=0,done=0,fault=0;reg[39:0]a=0;reg[15:0]m=0;reg[511:0]d=0;
 wire ov,ob,od,of;wire[39:0]oa;wire[15:0]om;wire[511:0]data;
 ot_hbm_tkm_return #(.MUT(MUT)) dut(clk,rst_n,v,busy,done,fault,a,m,d,ov,ob,od,of,oa,om,data);
 reg[571:0]q[0:1];reg[571:0]expected;integer checks=0;
 initial begin q[0]=0;q[1]=0;repeat(4)@(negedge clk);rst_n=1;
  for(integer i=0;i<256;i=i+1)begin
   busy=(i%13)<9;v=(i%7)<3;done=i%17==0;fault=i%41==0;
   a=40'(i*16);m=16'hffff>>i%8;for(integer k=0;k<16;k=k+1)d[32*k+:32]=32'(i*37+k);
   @(posedge clk);q[1]=q[0];q[0]={busy,v,done,fault,a,m,d};expected=q[1];#0.01;
   if({ob,ov,od,of}!==expected[571:568])$fatal(1,"TKM_RETURN control edge mismatch i=%0d",i);
   if(ov&&{oa,om,data}!==expected[567:0])$fatal(1,"TKM_RETURN data/valid mismatch i=%0d",i);
   checks++;@(negedge clk);
  end
  $display("TKM_RETURN PASS checks=%0d coherent data+busy+done+fault age2",checks);$finish;
 end
endmodule
