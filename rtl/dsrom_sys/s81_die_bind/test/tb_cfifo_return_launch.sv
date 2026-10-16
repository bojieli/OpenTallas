`timescale 1ns/1ps
module tb_cfifo_return_launch;
 reg ck=0,rst=0;initial forever #5 ck=~ck;
 reg[65:0]ri=0;reg[1:0]st=0;reg[9:0]fault=0;reg av=0,bv=0;
 wire[69:0]cap,q;wire rs;
 dsfd_cfifo_return_control capture(.ck(ck),.rst(rst),.ri(ri),.st(st),.lane_fault(fault),.av(av),.bv(bv),.rs(rs),.rd(cap));
 dsfd_cfifo_return_launch70 dut(.ck(ck),.d(cap),.q(q));
 reg[69:0]expected;integer n=0,checks=0,bad=0;
 always @(posedge ck)begin
  expected=cap;#2;
  if(n>8)begin checks=checks+1;if(q!==expected)bad=bad+1;end
  #1;ri={$random,$random,$random};st=$random;av=n%3!=0;bv=(n%17==0)?!av:av;fault=(n%37==0)?10'b1000000010:0;n=n+1;
 end
 initial begin #23;rst=1;repeat(400)@(posedge ck);#4;
 if(bad==0&&checks>380)$display("CFIFO_RETURN_EDGE PASS checks=%0d added_edges=1 words_per_edge=1",checks);
 else begin $display("CFIFO_RETURN_EDGE FAIL checks=%0d bad=%0d",checks,bad);$fatal;end
 $finish;end
endmodule
