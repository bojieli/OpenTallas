`timescale 1ns/1ps
// Host landing FIFO bench (HBMA-HOST 2026-10-17 rewrite; PINREG 0 and 1).
// Producer = endpoint face with FCR256 credits (one credit per landing pop).  Consumer = the exact rx handshake of
// ot_hbm_host_packet_static: rx_valid/rx_packet/rx_ready mirror pin flops, rx_take = rv_p && rxr_m, ready pulsed
// at most every other edge and only into an empty buffer; the buffer drains after a word-dependent stall.
// Lap 0 fills all 256 entries before draining (full FIFO, uninitialised real SRAM); lap 1 streams 256 words with
// producer and consumer concurrent (credit-limited).  Checks: every word in order exactly once, the head is stable
// while not taken, pops == words, count/fault/out_v at the end.
module tb_hbm_host_landing256;
 parameter integer PINREG=1;
 reg clk=0,rst_n=0,in_v=0,out_ready=0;reg[544:0]in_data=0;
 wire out_v,pop,fault;wire[511:0]out_data;
 integer checks=0,bad=0,got=0,lap,sent,credit=0,pops=0,cycles=0,stall=0,k;
 reg cons_en=0;
 // packet consumer model state
 reg rv_p=0,rxr_m=0,buf_v=0;reg[511:0]rp_p=0;
 reg[511:0]head_prev;reg head_seen=0;
 ot_hbm_host_landing256 #(.PINREG(PINREG)) dut(.*);
 function[511:0]word(input integer n);integer b;begin for(b=0;b<512;b=b+1)word[b]=((n*17+b*63)^(n>>(b%10)))&1;word[31:0]=n;end endfunction
 task tick;reg take,s_ov,s_or,s_pop,nready;reg[511:0]s_od;begin
  #0.416;
  // pre-edge samples
  s_ov=out_v;s_or=out_ready;s_pop=pop;s_od=out_data;take=rv_p&&rxr_m;
  if(s_ov&&!take)begin
   if(head_seen&&s_od!==head_prev)begin bad=bad+1;$display("head changed while held @%0d",cycles);end
   head_prev=s_od;head_seen=1;checks=checks+1;
  end
  nready=cons_en&&!s_or&&!buf_v&&!take;
  clk=1;#0.001;
  if(s_pop===1'b1)begin pops=pops+1;credit=credit+1;end
  if(rst_n&&fault!==1'b0)bad=bad+1;
  // consumer registers (as the packet's flops)
  if(take)begin
   checks=checks+1;
   if(rp_p!==word(got))begin bad=bad+1;$display("word %0d mismatch @%0d",got,cycles);end
   got=got+1;buf_v=1;stall=got%5;head_seen=0;
  end else if(buf_v)begin if(stall==0)buf_v=0;else stall=stall-1;end
  rv_p=s_ov;rxr_m=s_or;rp_p=s_od;out_ready=nready;
  #0.416;clk=0;cycles=cycles+1;end endtask
 task send(input integer n);begin in_v=1;in_data={33'd0,word(n)};end endtask
 initial begin
 repeat(4)tick;rst_n=1;tick;
 // lap 0: fill, then drain
 for(sent=0;sent<256;sent=sent+1)begin send(sent);tick;end
 in_v=0;repeat(4)tick;
 checks=checks+1;if(dut.count!==9'd256)begin bad=bad+1;$display("count %0d after fill",dut.count);end
 cons_en=1;k=0;while(got<256&&k<20000)begin tick;k=k+1;end
 repeat(8)tick;checks=checks+1;if(dut.count!==9'd0||out_v!==1'b0||pops!==256)begin bad=bad+1;$display("lap0 end count%0d pops%0d",dut.count,pops);end
 // lap 1: concurrent, credit-limited producer
 credit=256;sent=256;k=0;
 while(got<512&&k<40000)begin
  if(sent<512&&credit>0)begin send(sent);sent=sent+1;credit=credit-1;end else in_v=0;
  tick;k=k+1;
 end
 in_v=0;repeat(8)tick;
 checks=checks+1;if(dut.count!==9'd0||out_v!==1'b0||pops!==512)begin bad=bad+1;$display("lap1 end count%0d pops%0d",dut.count,pops);end
 if(bad==0&&got==512)$display("HBM_HOST_LANDING_PASS words%0d checks%0d cycles%0d pinreg%0d full256 concurrent256 packet_handshake_uninitialized_real_SRAM",got,checks,cycles,PINREG);
 else $display("HBM_HOST_LANDING_FAIL bad%0d words%0d checks%0d fault%h pinreg%0d",bad,got,checks,fault,PINREG);
 $finish;
 end
endmodule
