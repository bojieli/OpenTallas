`timescale 1ns/1ps
// Minimum calendar component comparison. Encoded test words are mechanism
// stimuli, never an actual compiler deployment programme or timing authority.
module tb_syscal_lctx2;
 parameter integer NE=32,AW=$clog2(NE);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,cfg_we=0,start=0,start_seg=0,halt=0;
 reg[AW:0]cfg_addr=0;reg[31:0]cfg_data=0;
 wire av,bv,ar,br,af,bf;wire[2:0]ap,bp;wire[3:0]ak,bk;wire[4:0]ab,bb;
 integer i,j,n=0,events=0;
 ot_qwen_d2d_cal #(.NE(NE)) a(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start(start),.start_seg(start_seg),.halt(halt),.ev_v(av),.ev_port(ap),.ev_kind(ak),.ev_beat(ab),.running(ar),.fault(af));
 qfd_syscal_lctx2 #(.NE(NE)) b(.ck(ck),.rst_n({(3+2*(NE/16)){rst_n}}),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start(start),.start_seg(start_seg),.halt(halt),.ev_v(bv),.ev_port(bp),.ev_kind(bk),.ev_beat(bb),.running(br),.fault(bf));
 always @(posedge ck)begin #1;
   if({av,ap,ak,ab,ar,af} !== {bv,bp,bk,bb,br,bf}) $fatal(1,"CALENDAR_DIFF NE=%0d edge=%0d ref=%h actual=%h",NE,n,{av,ap,ak,ab,ar,af},{bv,bp,bk,bb,br,bf});
   n=n+1;if(av)events=events+1;
 end
 initial begin
  repeat(3)@(negedge ck);rst_n=1;
  // Initialize both segments, all table words, and the genuine base register.
  for(i=0;i<NE;i=i+1)begin
   @(negedge ck);cfg_we=1;cfg_addr=i;
   cfg_data=((i%7+1)<<18)|(((i==NE/2-1)||(i==NE-1))<<17)|(2<<14)|((i%4)<<10)|((i%8)<<5)|(i%3);
  end
  @(negedge ck);cfg_addr=NE;cfg_data=NE/2;
  @(negedge ck);cfg_we=0;
  repeat(3)@(negedge ck);
  for(j=0;j<8;j=j+1)begin
   start_seg=j%2;start=1;@(negedge ck);start=0;
   wait(!ar);repeat(3)@(negedge ck);
  end
  // Existing invalid-start/config/restart/halt priority is compared too.
  start=1;@(negedge ck);start=0;repeat(2)@(negedge ck);
  start=1;@(negedge ck);start=0;cfg_we=1;cfg_addr=0;
  @(negedge ck);cfg_we=0;halt=1;start=1;
  @(negedge ck);halt=0;start=0;repeat(3)@(negedge ck);
  rst_n=0;repeat(3)@(negedge ck);rst_n=1;repeat(3)@(negedge ck);
  $display("PASS CALENDAR_COMPONENT NE=%0d edges=%0d events=%0d same-edge segment/start/halt/reset comparison",NE,n,events);$finish;
 end
endmodule
