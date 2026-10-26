`timescale 1ns/1ps
module tb_qkh_recip_leaf;
 parameter integer MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,v=0;
 reg [31:0] x=0;
 wire [31:0] a,b;
 wire av,bv,af,bf;
 ot_qwen_nearhbm_recip_p ref0 (.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(a),.vo(av),.fault(af));
 ot_qkh_recip_leaf dut (.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(b),.vo(bv),.fault(bf));
 reg [31:0] aq0,aq1;
 reg av0=0,av1=0,af0=0,af1=0;
 always @(posedge clk) begin aq0<=a;aq1<=aq0;av0<=av;av1<=av0;af0<=af;af1<=af0;end
 integer n=0,count=0,err=0;
 reg [31:0] rng=32'h12345678;
 always @(negedge clk) begin
  n=n+1;
  if(n==8)rst_n=1;
  if(n>20 && n<2020) begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   v=(n%5!=0);x={1'b0,8'h7f,rng[22:0]};x[30:23]=127+rng[6:0]%16;
  end else v=0;
  if(n>100) begin
   if(bv!==av1 || bf!==af1)err=err+1;
   if(bv) begin count=count+1;if((b^(MUT?32'h1:32'h0))!==aq1)err=err+1;end
  end
  if(n==2120) begin
   $display("RECIP_EQ count=%0d err=%0d",count,err);
   if(err || count<1400)$fatal(1,"reciprocal mismatch");$finish;
  end
 end
endmodule
