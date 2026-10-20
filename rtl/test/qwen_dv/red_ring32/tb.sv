`timescale 1ns/1ps
module check_ring #(parameter integer W=32,D=7,ID=0)(input wire ck,reset_i,input wire[15:0] cycle,output reg[15:0] checks=0);
 wire[W-1:0] d;wire[W-1:0] q;
 for(genvar b=0;b<W;b=b+1) assign d[b]=cycle[b%16] ^ cycle[(b+7)%16] ^ (b%3==0);
 qfd_dv_s5_red_ring32 #(.W(W),.D(D),.ID(ID)) dut(.*);
 reg[W-1:0] reference[0:D-1];integer warm=0;
 always @(posedge ck) begin
  reference[0]<=d;for(integer j=1;j<D;j=j+1) reference[j]<=reference[j-1];
  if(!reset_i) warm<=0;else warm<=warm+1;
 end
 always @(negedge ck) if(warm>D+8) begin
  if(q !== reference[D-1]) $fatal(1,"RING32_AGE W=%0d D=%0d cycle=%0d",W,D,cycle);
  checks<=checks+1;
 end
endmodule
module tb;
 reg ck=0,reset_i=0;always #5 ck=~ck;
 reg[15:0] cycle=0;wire[15:0] n[0:4];
 check_ring #(.W(283),.D(6),.ID(0)) a(ck,reset_i,cycle,n[0]);
 check_ring #(.W(26),.D(49),.ID(1)) b(ck,reset_i,cycle,n[1]);
 check_ring #(.W(32),.D(42),.ID(2)) c(ck,reset_i,cycle,n[2]);
 check_ring #(.W(32),.D(3),.ID(3)) d(ck,reset_i,cycle,n[3]);
 check_ring #(.W(1),.D(7),.ID(4)) e(ck,reset_i,cycle,n[4]);
 initial begin
  for(integer i=0;i<1200;i=i+1) begin
   @(negedge ck);cycle<=i;reset_i<=!(i<8 || (i>=600&&i<608));
  end
  @(negedge ck);for(integer j=0;j<5;j=j+1) if(n[j]<900) $fatal(1,"TOO_FEW_CHECKS");
  $display("RED_RING32 PASS 5 shapes two reset epochs");$finish;
 end
endmodule
