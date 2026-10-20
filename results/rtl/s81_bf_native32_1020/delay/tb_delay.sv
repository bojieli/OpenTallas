`timescale 1ns/1ps
module coupon #(parameter D=8)(input wire clk,rst_n,input wire[31:0] d,output reg done=0);
wire[31:0] q,gold;
ot_v41_bf_sram_delay #(.W(32),.D(D)) u(clk,rst_n,d,q);
ot_hdc_delay #(.W(32),.D(D)) ref_u(clk,rst_n,d,gold);
integer age=0,n=0;
always @(posedge clk) begin
 if(!rst_n) age=0; else age=age+1;
 #1;
 if(age>=D) begin
  if(q!==gold) $fatal(1,"DELAY DIFF D=%0d age=%0d q=%h gold=%h",D,age,q,gold);
  n=n+1;
 end
 if(n>300) done=1;
end
endmodule
module tb;
reg clk=0,rst_n=0;reg[31:0] d=0;wire[3:0] done;
always #5 clk=~clk;
coupon #(.D(3)) a(clk,rst_n,d,done[0]);
coupon #(.D(7)) b(clk,rst_n,d,done[1]);
coupon #(.D(8)) c(clk,rst_n,d,done[2]);
coupon #(.D(16)) e(clk,rst_n,d,done[3]);
initial begin
 for(integer i=0;i<650;i++) begin
  @(negedge clk); d=$urandom;rst_n=!(i<3 || i==97 || (i>=211 && i<217) || i==400);
 end
 if(!(&done)) $fatal(1,"COVERAGE");
 $display("PASS DELAY 4 shapes >300 comparisons each including repeated short/inflight reset");$finish;
end
endmodule
