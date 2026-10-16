`timescale 1ns/1ps
module tb;
 parameter RG=6, WG=3;
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg rslot_v,wslot_v; reg [2:0] rslot; reg [3:0] wslot; reg [RG*17-1:0] rq; reg [WG*281-1:0] wq; reg [280:0] dq,kq; reg [275:0] xq,xq2; reg [284:0] pq;
 wire [RG*257-1:0] rr0,rr1; wire [WG-1:0] wd0,wd1; wire a0,a1,b0,b1,c0,c1,e0,e1; wire [275:0] eg0,eg1; wire [265:0] pr0,pr1; wire [17:0] st0,st1;
 old_strap #(.RG(RG),.WG(WG)) u0(.clk(clk),.rst_n(rst_n),.bid(3'd2),.sid(2'd3),.rslot_v(rslot_v),.rslot(rslot),.wslot_v(wslot_v),.wslot(wslot),.rq(rq),.rr(rr0),.wq(wq),.wq_done(wd0),.dq(dq),.dq_done(a0),.kq(kq),.kq_done(b0),.xq(xq),.xq_done(c0),.xq2(xq2),.xq2_done(e0),.eg(eg0),.pq(pq),.pr(pr0),.status(st0));
 ot_vms_bank_static_strap #(.RG(RG),.WG(WG)) u1(.clk(clk),.rst_n(rst_n),.bid(3'd2),.sid(2'd3),.rslot_v(rslot_v),.rslot(rslot),.wslot_v(wslot_v),.wslot(wslot),.rq(rq),.rr(rr1),.wq(wq),.wq_done(wd1),.dq(dq),.dq_done(a1),.kq(kq),.kq_done(b1),.xq(xq),.xq_done(c1),.xq2(xq2),.xq2_done(e1),.eg(eg1),.pq(pq),.pr(pr1),.status(st1));
 function [1023:0] r1k; integer i; begin for(i=0;i<32;i=i+1) r1k[i*32+:32]=$urandom; end endfunction
 integer cyc, bad=0, wr=0; reg [9:0] row;
 initial begin
  {rslot_v,wslot_v,rslot,wslot,rq,wq,dq,kq,xq,xq2,pq}=0;
  repeat(5) @(negedge clk); rst_n=1; repeat(5) @(negedge clk);
  for(cyc=0;cyc<40000;cyc=cyc+1) begin
   @(negedge clk);
   // garbage payload everywhere; valids random but sparse; sectors legal half the time
   rq=r1k(); wq=r1k(); dq=r1k(); kq=r1k(); xq=r1k(); xq2=r1k(); pq=r1k();
   for(integer g=0;g<WG;g=g+1) begin wq[g*281+280]=($urandom%8==0); if($urandom%2) wq[g*281+264+:16]={1'b0,2'd3,10'($urandom),3'd2}; end
   dq[280]=($urandom%8==0); if($urandom%2) dq[264+:16]={1'b0,2'd3,10'($urandom),3'd2};
   kq[280]=($urandom%8==0); if($urandom%2) kq[264+:16]={1'b0,2'd3,10'($urandom),3'd2};
   xq[275]=($urandom%8==0); xq2[275]=($urandom%8==0); pq[284]=($urandom%6==0);
   rslot_v=$urandom%2; wslot_v=$urandom%2; rslot=$urandom%(RG+1); wslot=$urandom%(WG+5);
   if (u0.s1w_v) wr=wr+1;
   if ({rr0,wd0,a0,b0,c0,e0,eg0,pr0,st0}!=={rr1,wd1,a1,b1,c1,e1,eg1,pr1,st1}) begin bad=bad+1; if(bad<5) $display("MISMATCH cyc=%0d eg %0d rr %0d pr %0d st %0d",cyc,eg0!==eg1,rr0!==rr1,pr0!==pr1,st0!==st1); end
  end
  $display("EQUIV cycles=40000 writes=%0d mismatches=%0d", wr, bad); $finish;
 end
endmodule
