`timescale 1ns/1ps
module tb_iss;
  reg ck=0; always #5 ck=~ck;
  reg rn=0, start_i=0, run_i=0, lr=0, rb=0, tr=0, mv=0; reg [15:0] off=0, per=0, mdl=0;
  wire i0,i1,i2,j0,j1,j2,d0,d1,d2,f0,f1,f2;
  ot_s81hd_static_issue_O u0 (ck,rn,start_i,run_i,off,per,mdl,lr,rb,tr,mv,i0,j0,d0,f0);
  `NEWMOD #(.DATE_SPLIT(1)) u1 (ck,rn,start_i,run_i,off,per,mdl,lr,rb,tr,mv,i1,j1,d1,f1);
  `NEWMOD #(.DATE_SPLIT(0)) u2 (ck,rn,start_i,run_i,off,per,mdl,lr,rb,tr,mv,i2,j2,d2,f2);
  integer cyc=0, seed, NC, mism=0, ndue=0, nfirst=0;
  always @(posedge ck) if (u1.first) nfirst=nfirst+1;
  initial begin if(!$value$plusargs("seed=%d",seed)) seed=1; if(!$value$plusargs("n=%d",NC)) NC=200000; end
  always @(negedge ck) begin
    cyc=cyc+1;
    if ({i0,j0,d0,f0,u0.next_date,u0.age} !== {i1,j1,d1,f1,u1.next_date,u1.age} || {i0,j0,d0,f0,u0.next_date} !== {i2,j2,d2,f2,u2.next_date}) begin mism=mism+1; if (mism<5) $display("MISMATCH cycle %0d", cyc); end
    if (d1) ndue=ndue+1;
    if ((cyc % 997) == 0) rn = 0; else if ((cyc % 997) == 3) rn = 1; else if (cyc == 3) rn = 1;
    if ((cyc % 997) == 2) begin off = $random(seed) & 31; per = ($random(seed) & 15) + (($random(seed)&7)==0 ? 0 : 1); mdl = $random(seed) & 31; if (($random(seed)&7)==0) off = 0; end
    start_i = ((cyc % 997) > 6 + ($random(seed) & 3)); run_i = (($random(seed) & 63) != 0);
    lr = $random(seed); rb = ($random(seed) & 3) == 0; tr = ($random(seed) & 7) == 0; mv = ($random(seed) & 7) == 0;
    if (cyc == NC) begin $display("ISS seed %0d cycles %0d mismatches %0d due %0d first %0d", seed, cyc, mism, ndue, nfirst);
      if (mism==0 && ndue>0 && nfirst>0) $display("ISS_PASS"); else $display("ISS_FAIL"); $finish; end
  end
endmodule
