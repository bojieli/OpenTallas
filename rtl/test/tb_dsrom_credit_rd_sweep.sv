`timescale 1ns/1ps
// RD sweep of the W1 credit return node (046bf5026, ot_v41_retn_credit) against the
// unchanged RD64 reference (ot_v41_retn_w17w10). Bench only; no RTL module changed.
// Four-leaf tree, two levels, in both designs: leaves 0,1 -> na; leaves 2,3 -> nb; na,nb -> np -> consumer.
// The consumer pops every word and refunds a registered credit (ROOT-side capacity 128 as in W1).
// MODE 0: saturated, every leaf every cycle (the W1 fixture shape, four leaves).
// MODE 1: program-shaped rounds: each leaf emits ROUND rows back to back every PER cycles;
//         leaf j lags leaf 0 by j*SKEW cycles. Credit leaves send each row at max(schedule, ready);
//         reference leaves send exactly on schedule (no backpressure exists there).
// Drain: all rows sent on every leaf and no output word for 64 cycles on either tree.
// Exactness: per-row word count and 64-bit sum of {tag,data}, credit vs reference (skipped, and
// reported, if the reference overflows: the reference has no flow control).
module tb_dsrom_credit_rd_sweep #(
    parameter integer RD = 16, MODE = 0, ROWS = 256, ROUND = 8, PER = 40, SKEW = 0
);
 reg clk=0,rst_n=0; always #5 clk=~clk;
 localparam integer LIM = 65536;
 localparam [31:0] ONE = 32'h3f800000;
 reg  [3:0] lv=0, rlv=0; reg [31:0] lt[0:3], rlt[0:3];
 wire [3:0] lr;
 // credit tree
 wire av_,ae_,bv_,be_,ov,oe,ca,cb,cp,fa,fb,fp; wire [31:0] at_,ad_,bt_,bd_,ot,od;
 wire [31:0] pa0,pb0,st0,pa1,pb1,st1,pa2,pb2,st2;
 ot_v41_retn_credit #(.RD(RD),.OUTD(RD)) na(.clk(clk),.rst_n(rst_n),.a_v(lv[0]),.a_t(lt[0]),.a_d(ONE),.a_e(1'b0),
  .b_v(lv[1]),.b_t(lt[1]),.b_d(ONE),.b_e(1'b0),.a_ready(lr[0]),.b_ready(lr[1]),.a_credit(),.b_credit(),
  .o_credit(ca),.o_v(av_),.o_t(at_),.o_d(ad_),.o_e(ae_),.fault(fa),.quiet(),.peak_a(pa0),.peak_b(pb0),.credit_stalls(st0));
 ot_v41_retn_credit #(.RD(RD),.OUTD(RD)) nb(.clk(clk),.rst_n(rst_n),.a_v(lv[2]),.a_t(lt[2]),.a_d(ONE),.a_e(1'b0),
  .b_v(lv[3]),.b_t(lt[3]),.b_d(ONE),.b_e(1'b0),.a_ready(lr[2]),.b_ready(lr[3]),.a_credit(),.b_credit(),
  .o_credit(cb),.o_v(bv_),.o_t(bt_),.o_d(bd_),.o_e(be_),.fault(fb),.quiet(),.peak_a(pa1),.peak_b(pb1),.credit_stalls(st1));
 ot_v41_retn_credit #(.RD(RD),.OUTD(128)) np(.clk(clk),.rst_n(rst_n),.a_v(av_),.a_t(at_),.a_d(ad_),.a_e(ae_),
  .b_v(bv_),.b_t(bt_),.b_d(bd_),.b_e(be_),.a_ready(),.b_ready(),.a_credit(ca),.b_credit(cb),
  .o_credit(cp),.o_v(ov),.o_t(ot),.o_d(od),.o_e(oe),.fault(fp),.quiet(),.peak_a(pa2),.peak_b(pb2),.credit_stalls(st2));
 reg refund=0; always @(posedge clk) refund<=rst_n && ov; assign cp=refund;
 // reference tree
 wire rav,rae,rbv,rbe,rov,roe,rfa,rfb,rfp; wire [31:0] rat,rad,rbt,rbd,rot,rod;
 ot_v41_retn_w17w10 ra(.clk(clk),.rst_n(rst_n),.a_v(rlv[0]),.a_t(rlt[0]),.a_d(ONE),.a_e(1'b0),
  .b_v(rlv[1]),.b_t(rlt[1]),.b_d(ONE),.b_e(1'b0),.o_v(rav),.o_t(rat),.o_d(rad),.o_e(rae),.fault(rfa),.quiet());
 ot_v41_retn_w17w10 rb(.clk(clk),.rst_n(rst_n),.a_v(rlv[2]),.a_t(rlt[2]),.a_d(ONE),.a_e(1'b0),
  .b_v(rlv[3]),.b_t(rlt[3]),.b_d(ONE),.b_e(1'b0),.o_v(rbv),.o_t(rbt),.o_d(rbd),.o_e(rbe),.fault(rfb),.quiet());
 ot_v41_retn_w17w10 rp(.clk(clk),.rst_n(rst_n),.a_v(rav),.a_t(rat),.a_d(rad),.a_e(rae),
  .b_v(rbv),.b_t(rbt),.b_d(rbd),.b_e(rbe),.o_v(rov),.o_t(rot),.o_d(rod),.o_e(roe),.fault(rfp),.quiet());
 function [31:0] tag(input integer row,input integer lo); tag={3'd0,16'(row),5'(lo),3'd0,5'd4}; endfunction
 function integer sched(input integer i,input integer j);
  if (MODE==0) sched=i; else sched=(i/ROUND)*PER+(i%ROUND)+j*SKEW;
 endfunction
 integer cycle=0, last=0, rlast=0, words=0, rwords=0, i, j, lat_sum=0, lat_max=0, rfault=0;
 integer s[0:3], rs[0:3];
 reg [63:0] acc[0:ROWS-1], racc[0:ROWS-1]; integer cnt[0:ROWS-1], rcnt[0:ROWS-1], dn[0:ROWS-1], rdn[0:ROWS-1];
 initial begin
  for(i=0;i<ROWS;i=i+1) begin acc[i]=0;racc[i]=0;cnt[i]=0;rcnt[i]=0;dn[i]=0;rdn[i]=0; end
  for(j=0;j<4;j=j+1) begin s[j]=0; rs[j]=0; lt[j]=0; rlt[j]=0; end
 end
 always @(posedge clk) if(rst_n) begin
  cycle=cycle+1;
  for(j=0;j<4;j=j+1) begin if(lv[j] && lr[j]) s[j]=s[j]+1; if(rlv[j]) rs[j]=rs[j]+1; end
  if(ov) begin acc[ot[28:13]]=acc[ot[28:13]]+{ot,od}; cnt[ot[28:13]]=cnt[ot[28:13]]+1; dn[ot[28:13]]=cycle; words=words+1; last=cycle; end
  if(rov) begin racc[rot[28:13]]=racc[rot[28:13]]+{rot,rod}; rcnt[rot[28:13]]=rcnt[rot[28:13]]+1; rdn[rot[28:13]]=cycle; rwords=rwords+1; rlast=cycle; end
  if(fa||fb||fp) $fatal(1,"credit fault");
  if(rfa||rfb||rfp) rfault=1;
  if(s[0]==ROWS && s[1]==ROWS && s[2]==ROWS && s[3]==ROWS && rs[0]==ROWS && rs[3]==ROWS && cycle>last+64 && cycle>rlast+64) begin
   if(!rfault) for(i=0;i<ROWS;i=i+1) begin
    if(acc[i]!==racc[i] || cnt[i]!=rcnt[i]) $fatal(1,"row %0d differs credit cnt=%0d ref cnt=%0d",i,cnt[i],rcnt[i]);
    lat_sum=lat_sum+dn[i]-rdn[i]; if(dn[i]-rdn[i]>lat_max) lat_max=dn[i]-rdn[i];
   end
   $display("RESULT RD=%0d MODE=%0d ROUND=%0d PER=%0d SKEW=%0d rows=%0d words=%0d rwords=%0d credit_last=%0d reference_last=%0d reference_fault=%0d row_delay_sum=%0d row_delay_max=%0d peak_a=%0d peak_b=%0d parent_peak_a=%0d parent_peak_b=%0d stalls=%0d",
            RD,MODE,ROUND,PER,SKEW,ROWS,words,rwords,last,rlast,rfault,lat_sum,lat_max,(pa0>pa1?pa0:pa1),(pb0>pb1?pb0:pb1),pa2,pb2,st0+st1+st2);
   $finish;
  end
 end
 always @(negedge clk) if(rst_n) for(j=0;j<4;j=j+1) begin
  lv[j]=(s[j]<ROWS && sched(s[j],j)<=cycle); lt[j]=tag(s[j],j);
  rlv[j]=(rs[j]<ROWS && sched(rs[j],j)<=cycle); rlt[j]=tag(rs[j],j);
 end
 initial begin #22;rst_n=1;end
 initial begin repeat(LIM) @(posedge clk); $fatal(1,"did not drain"); end
endmodule
