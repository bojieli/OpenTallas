`timescale 1ns/1ps
module tb_sfustore_if;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rv=0,wv=0;
 reg [8:0] ra=0,wa=0;
 reg [31:0] wd=0;
 wire [31:0] gold,got[0:4];
 ot_hbm_su_sfustore_hw_bank refb(.clk(clk),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.read_data(gold),.write_v(wv),.write_addr(wa),.write_data(wd));
 for(genvar m=0;m<5;m=m+1)begin:g
  ot_hbm_su_sfustore_hw_bank_if #(.MUT_IF(m)) u(.clk(clk),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.read_data(got[m]),.write_v(wv),.write_addr(wa),.write_data(wd));
 end
 integer checks=0,errors=0,mutdiff[1:4];reg [31:0] seed=32'h6842a15b;
 task step(input bit rn,input bit r,input [8:0] a,input bit w,input [8:0] b,input [31:0] d);
  @(negedge clk);rst_n=rn;rv=r;ra=a;wv=w;wa=b;wd=d;
  @(posedge clk);#1;
  checks=checks+1;
  if(gold!==got[0])begin errors=errors+1;if(errors<8)$display("MISMATCH edge=%0d gold=%h got=%h",checks,gold,got[0]);end
  for(integer m=1;m<5;m=m+1)if(gold!==got[m])mutdiff[m]=mutdiff[m]+1;
 endtask
 initial begin
  for(integer m=1;m<5;m=m+1)mutdiff[m]=0;
  for(integer i=0;i<8;i=i+1)step(0,0,0,0,0,0);
  for(integer i=0;i<512;i=i+1)step(1,0,0,1,9'(i),32'(i)*32'h9e3779b9^32'hbd615a7c);
  for(integer i=0;i<8;i=i+1)step(1,0,0,0,0,0);
  for(integer i=0;i<512;i=i+1)step(1,1,9'(i),0,0,0);
  for(integer i=0;i<8;i=i+1)step(0,0,0,0,9'd263,32'hdeadbeef);
  for(integer i=0;i<512;i=i+1)step(1,1,9'(i),0,0,0);
  for(integer i=0;i<5000;i=i+1)begin
   seed={seed[30:0],seed[31]^seed[21]^seed[1]^seed[0]};
   step(1,seed[0],seed[9:1],seed[10],seed[19:11],seed^32'(i));
  end
  // Simultaneous read/write and held enables exercise read-before-write ordering.
  for(integer i=0;i<128;i=i+1)step(1,1,9'(i),1,9'(i),32'(i)^32'h12345678);
  for(integer i=0;i<16;i=i+1)step(1,1,9'(i),0,0,0);
  $display("SFUSTORE_IF checks=%0d errors=%0d mask=%0d data=%0d addr=%0d reset=%0d",checks,errors,mutdiff[1],mutdiff[2],mutdiff[3],mutdiff[4]);
  if(errors || !mutdiff[1] || !mutdiff[2] || !mutdiff[3] || !mutdiff[4])$fatal(1,"SFUSTORE_IF FAIL");
  $display("SFUSTORE_IF PASS");$finish;
 end
endmodule
