`timescale 1ns/1ps
module tb_land32;
 localparam W=512,C=(W+23)/24;
 reg ck=0,rsi=0;always #0.5 ck=~ck;
 reg[W-1:0] i=0;wire[4*W-1:0] ba,bb;wire[4*C-1:0] va,vb;wire[W-1:0] qa,qb,da,db;
 ot_qw_lw #(.W(W)) a(.ck(ck),.rsi(rsi),.i(i),.bank(ba),.vld(va));
 ot_qw_lw_n32 #(.W(W)) b(.ck(ck),.rsi(rsi),.i(i),.bank(bb),.vld(vb));
 ot_qw_lr #(.W(W)) ra(.ck(ck),.rsi(rsi),.bank(ba),.vld(va),.o(qa));
 ot_qw_lr_n32 #(.W(W)) rb(.ck(ck),.rsi(rsi),.bank(bb),.vld(vb),.o(qb));
 ot_qw_ring_delay #(.W(W),.D(10)) d0(.clk(ck),.rst_n(rsi),.d(i),.q(da));
 ot_qw_ring_delay_n32 #(.W(W),.D(10)) d1(.clk(ck),.rst_n(rsi),.d(i),.q(db));
 integer checks=0,mut=0;initial begin
  void'($value$plusargs("MUT=%d",mut));
  if(mut==1) force rb.g_c[0].g_a[0].roh=1;
  if(mut==2) force b.g_c[0].g_a[0].rq=0;
  if(mut==3) force d1.g_ring.g_c[0].p=1;
  for(integer c=0;c<5000;c=c+1) begin
   @(negedge ck);rsi=(c%777>=9);
   for(integer k=0;k<W;k=k+32)i[k+:32]=$urandom;
   @(posedge ck);#0.1;checks=checks+1;
   if(qa!==qb || da!==db || ba!==bb || va!==vb) $fatal(1,"LAND32_FAIL c=%0d mut=%0d",c,mut);
  end
  $display("LAND32_PASS checks=%0d mut=%0d",checks,mut);$finish;
 end
endmodule
