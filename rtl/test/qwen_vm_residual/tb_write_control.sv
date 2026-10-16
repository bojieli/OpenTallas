`timescale 1ns/1ps
module tb;
 parameter integer W=27;
 reg clk=0,rst_n=1,we=0;
 reg[W-1:0]d=0;
 wire qwe;wire[W-1:0]q;
 `DUT u_dut(.clk(clk),.rst_n(rst_n),.we(we),.d(d),.qwe(qwe),.q(q));
 reg[31:0]rng=32'h73a11a37;
 integer i,word_checks=0,async_checks=0;
 function[31:0]next;
  input[31:0]x;reg[31:0]y;
  begin y=x^(x<<13);y=y^(y>>17);next=y^(y<<5);end
 endfunction
 initial begin
  rst_n=0;#1;
  if(qwe!==1'b0)begin $display("FAIL initial asynchronous WE reset W=%0d",W);$fatal;end
  rst_n=1;#1;
  for(i=0;i<1024;i=i+1)begin
   clk=0;rng=next(rng);d=rng;we=(i%3!=0);rst_n=(i%29!=0);#1;
   if(!rst_n && qwe!==1'b0)begin $display("FAIL asynchronous WE reset W=%0d cycle=%0d",W,i);$fatal;end
   clk=1;#1;
   if(q!==d)begin $display("FAIL unconditional payload W=%0d cycle=%0d we=%b reset=%b",W,i,we,rst_n);$fatal;end
   if(qwe!==(rst_n ? we : 1'b0))begin $display("FAIL sampled WE W=%0d cycle=%0d",W,i);$fatal;end
   word_checks=word_checks+2;
   if(i%17==0)begin
    rst_n=0;#1;
    if(qwe!==1'b0 || q!==d)begin $display("FAIL asynchronous reset changed payload or missed WE W=%0d cycle=%0d",W,i);$fatal;end
    rst_n=1;#1;
    if(qwe!==1'b0 || q!==d)begin $display("FAIL reset release altered storage W=%0d cycle=%0d",W,i);$fatal;end
    async_checks=async_checks+2;
   end else #2;
  end
  $display("PASS write control W=%0d edges=1024 word_checks=%0d async_checks=%0d",W,word_checks,async_checks);$finish;
 end
endmodule
