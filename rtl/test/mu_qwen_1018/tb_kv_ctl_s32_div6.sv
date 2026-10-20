`timescale 1ns/1ps
module tb_kv_ctl_s32_div6;
 reg[9:0]a;
 wire[4:0]q;
 qkd_kv_ctl_s32_div6 dut(.a(a),.q(q));
 initial begin
  for(integer n=0;n<1024;n=n+1)begin
   a=10'(n); #1;
   if(q!==5'(n/6))$fatal(1,"FAIL KV_CTL_DIV6 a=%0d got=%0d expected=%0d",n,q,5'(n/6));
  end
  $display("PASS KV_CTL_DIV6 all1024 unsigned inputs");$finish;
 end
endmodule
