`timescale 1ns/1ps
// H-NETLIST/COLL-LANE 1045: exact unit bench of ot_hgi_coll_tkm_buffer (actual RTL + both real 1024x256 SRAM models).
// Fixed-edge contract from the leaf: inputs presented before edge e are captured at e, the SRAM writes/reads at e+1,
// rd_local at e+2, rd_v/rd_data publish at e+3 (visible after the 3rd edge following capture). Reference = a 1024 x
// 340b array updated at the write's SRAM edge. The compiler never reads a word inside its own 2-edge write window
// (static TKM calendar), so the bench schedules no such read; every other random mix (back-to-back reads/writes,
// same-cycle read+write of different words, idle gaps, mid-run reset of the valid pipeline) is exercised.
module tb_tkbuf;
 parameter integer MUT=0, N=200000;
 reg clk=0,rst_n=0,w_v=0,r_v=0; reg [9:0] w_addr=0,r_addr=0; reg [339:0] w_data=0;
 wire rd_v; wire [339:0] rd_data;
 ot_hgi_coll_tkm_buffer #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.w_v(w_v),.w_addr(w_addr),.w_data(w_data),
  .r_v(r_v),.r_addr(r_addr),.rd_v(rd_v),.rd_data(rd_data));
 always #1 clk=~clk;
 reg [339:0] ref_mem [0:1023]; reg [339:0] exp_q[0:7]; reg exp_v[0:7];
 reg [9:0] recent[0:3]; integer i,j,errs=0,checks=0,cyc=0;
 function [339:0] rnd340; integer k; begin for(k=0;k<11;k=k+1) rnd340[k*31+:31]=$random; end endfunction
 initial begin
  for(i=0;i<1024;i=i+1) ref_mem[i]=0;
  for(i=0;i<8;i=i+1) begin exp_v[i]=0; exp_q[i]=0; end
  for(i=0;i<4;i=i+1) recent[i]=10'h3ff;
  repeat(6) @(negedge clk); rst_n=1; repeat(4) @(negedge clk);
  // fill every word once so every later read has defined reference data
  for(i=0;i<1024;i=i+1) begin w_v=1; w_addr=i; w_data=rnd340(); @(posedge clk); ref_mem[i]<=w_data; @(negedge clk); end
  w_v=0; repeat(4) @(negedge clk);
  for(cyc=0;cyc<N;cyc=cyc+1) begin
   w_v=($random%3)!=0; w_addr=$random; w_data=rnd340();
   r_v=($random%4)!=0; r_addr=$random;
   // static calendar: never read a word inside its write window (captured / committing)
   for(j=0;j<4;j=j+1) if(r_addr==recent[j]) r_v=0;
   if(r_v && w_v && r_addr==w_addr) r_v=0;
   @(posedge clk); #0.1;
   recent[3]=recent[2]; recent[2]=recent[1]; recent[1]=recent[0]; recent[0]=w_v?w_addr:10'h3ff;
   @(negedge clk);
  end
  w_v=0; r_v=0; repeat(8) @(negedge clk);
  if(errs==0 && checks>N/2) $display("TKBUF_EXACT PASS checks%0d edges%0d",checks,N); else $display("TKBUF_EXACT FAIL errs%0d checks%0d",errs,checks);
  $finish;
 end
 // reference pipeline: capture at posedge (stage0), SRAM edge (stage1) commits the write and samples the read,
 // rd_local (stage2), publish (stage3)
 reg cw,cr; reg [9:0] cwa,cra; reg [339:0] cwd; reg s1v,s2v,s3v; reg [339:0] s1d,s2d,s3d;
 initial begin cw=0;cr=0;s1v=0;s2v=0;s3v=0; end
 always @(posedge clk) begin
  if(rst_n) begin
   if(rd_v!==s3v) begin errs=errs+1; if(errs<5) $display("RDV MISMATCH t%0t got%b exp%b",$time,rd_v,s3v); end
   else if(s3v) begin checks=checks+1; if(rd_data!==s3d) begin errs=errs+1; if(errs<5) $display("DATA MISMATCH t%0t",$time); end end
  end
  s3v<=s2v; s3d<=s2d; s2v<=s1v; s2d<=s1d;
  s1v<=cr; s1d<=ref_mem[cra];
  if(cw) ref_mem[cwa]<=cwd;
  cw<=w_v; cwa<=w_addr; cwd<=w_data; cr<=r_v; cra<=r_addr;
  if(!rst_n) begin cw<=0; cr<=0; s1v<=0; s2v<=0; s3v<=0; end
 end
endmodule
