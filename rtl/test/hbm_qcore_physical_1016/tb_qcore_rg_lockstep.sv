`timescale 1ns/1ps
`default_nettype none
// HBM-SU3 2026-10-17: qcore successor r5 ot_hbm_su_static_qcore_r5 (1 root, single-copy RF, selected read pipeline,
// pins first) in lockstep with the die's current qcore (66 roots), both at the die parameters COLLPORT 1, RF_LOCAL 1.
// Random traffic on every input every edge (RF reads all six classes, 4 relay writers + the COLL writer incl. same-bank
// conflicts, reducer commands from slice / RF / SFU operands), NRST reset phases.
// Checks: rf_bcmd, red_sv, red_tag, red_x, red_rf_v bit-exact (!==) at every edge; rf_bword word c / rf_dsec bit-exact on
// every edge whose class-c / class-5 read was valid 3 edges earlier (class 4 is issued valid every edge so the reducer's
// RF operand is always defined); fault equal, except a write-conflict fault may report exactly one edge later.
// MUT 256: an extra read stage (reads k+4) -> FAIL.
module tb_qcore_rg_lockstep;
 parameter integer MUT=0, NRST=4, EDGES=3000;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0, active=0;
 reg [53:0] rf_rd_cmd=0; reg [73:0] red_cmd=0; reg [1:0] rf_drain_cmd=0; reg [127:0] slice_x=0;
 reg [3:0] rf_wv=0; reg [31:0] rf_wa=0; reg [127:0] rf_wd=0; reg rr_wv=0; reg [4:0] rr_wa=0; reg [255:0] rr_wd=0; reg [31:0] sfu_x=0;
 integer i;
 always @(negedge clk) if(active) begin
  for(i=0;i<6;i=i+1) rf_rd_cmd[i*9+:9]={($urandom%3)==0,8'($urandom)};
  if(($urandom%4)==0) rf_rd_cmd[5*9+:3]=3'd0;            // mostly sector-aligned class-5 reads
  rf_rd_cmd[4*9+8]=1'b1;                                  // class 4 (reducer RF operand) always issued
  rf_drain_cmd=$urandom; slice_x={$urandom,$urandom,$urandom,$urandom}; sfu_x=$urandom;
  for(i=0;i<4;i=i+1) begin rf_wv[i]=($urandom%3)==0; rf_wa[i*8+:8]=$urandom; rf_wd[i*32+:32]=$urandom; end
  rr_wv=($urandom%5)==0; rr_wa=$urandom; for(i=0;i<8;i=i+1) rr_wd[i*32+:32]=$urandom;
  red_cmd={($urandom%6)==0,3'($urandom%5),10'($urandom),10'($urandom),10'($urandom),32'($urandom),1'($urandom),7'($urandom)};
 end else begin rf_rd_cmd=0; red_cmd=0; rf_drain_cmd=0; rf_wv=0; rr_wv=0; end
 wire [127:0] d_bw, r_bw; wire [35:0] d_bc, r_bc; wire [255:0] d_ds, r_ds; wire d_sv, r_sv, d_rv, r_rv, d_f, r_f;
 wire [31:0] d_tag, r_tag, d_x, r_x;
 ot_hbm_su_static_qcore_r5 #(.MUT(MUT),.COLLPORT(1),.RF_LOCAL(1)) dut(
  .clk_ctl(clk),.rst_n(rst_n),.rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),
  .rf_drain_cmd(rf_drain_cmd),.slice_x(slice_x),.rf_wv(rf_wv),.rf_wa(rf_wa),.rf_wd(rf_wd),.rf_bword(d_bw),.rf_bcmd(d_bc),
  .rf_dsec(d_ds),.red_sv(d_sv),.red_tag(d_tag),.red_x(d_x),.red_rf_v(d_rv),.rr_wv(rr_wv),.rr_wa(rr_wa),.rr_wd(rr_wd),
  .sfu_x(sfu_x),.fault(d_f));
 ot_hbm_su_static_qcore #(.MUT(0),.COLLPORT(1),.RF_LOCAL(1)) ref0(
  .clk_rf({64{clk}}),.clk_ctl(clk),.clk_red(clk),.rst_n(rst_n),.rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),
  .rf_drain_cmd(rf_drain_cmd),.slice_x(slice_x),.rf_wv(rf_wv),.rf_wa(rf_wa),.rf_wd(rf_wd),.rf_bword(r_bw),.rf_bcmd(r_bc),
  .rf_dsec(r_ds),.red_sv(r_sv),.red_tag(r_tag),.red_x(r_x),.red_rf_v(r_rv),.rr_wv(rr_wv),.rr_wa(rr_wa),.rr_wd(rr_wd),
  .sfu_x(sfu_x),.fault(r_f));
 integer checks=0, errors=0, cmp=0, lag=0, sv=0, fault_edges=0, wv=0; reg r_f_q=0;
 reg [5:0] vh [0:3];          // vh[d][c]: class c valid at the pin edge d edges before the current one
 always @(posedge clk) begin vh[3]<=vh[2]; vh[2]<=vh[1]; vh[1]<=vh[0];
  vh[0]<={rf_rd_cmd[5*9+8],rf_rd_cmd[4*9+8],rf_rd_cmd[3*9+8],rf_rd_cmd[2*9+8],rf_rd_cmd[1*9+8],rf_rd_cmd[0*9+8]}; end
 initial begin vh[0]=0; vh[1]=0; vh[2]=0; vh[3]=0; end
 always @(posedge clk) if(cmp) begin
  #1; checks=checks+1; sv=sv+r_sv; fault_edges=fault_edges+r_f;
  for(i=0;i<4;i=i+1) if(vh[3][i] && d_bw[32*i+:32]!==r_bw[32*i+:32]) begin errors=errors+1; if(errors<6) $display("RF WORD MISMATCH t=%0t class %0d %h/%h", $time, i, d_bw[32*i+:32], r_bw[32*i+:32]); end
  if(vh[3][5] && d_ds!==r_ds) begin errors=errors+1; if(errors<6) $display("DSEC MISMATCH t=%0t", $time); end
  wv=wv+vh[3][0]+vh[3][5];
  if({d_bc,d_sv,d_tag,d_x,d_rv}!=={r_bc,r_sv,r_tag,r_x,r_rv}) begin errors=errors+1;
   if(errors<6) $display("LOCKSTEP MISMATCH t=%0t bc %0d sv %b/%b x %h/%h", $time, d_bc!==r_bc, d_sv, r_sv, d_x, r_x); end
  if(d_f!==r_f) begin
   if(r_f===1'b1 && r_f_q===1'b0 && d_f===1'b0) lag=lag+1;              // conflict fault one edge later: allowed
   else begin errors=errors+1; if(errors<6) $display("FAULT MISMATCH t=%0t dut %b ref %b", $time, d_f, r_f); end
  end
  r_f_q=r_f;
 end
 integer k;
 initial begin
  for(k=0;k<NRST;k=k+1) begin
   rst_n=0; cmp=0; r_f_q=0; repeat(4) @(negedge clk); rst_n=1; repeat(2) @(negedge clk);
   cmp=1; active=1; repeat(k==0 ? 40 : EDGES) @(negedge clk);    // phase 0: short, fault-free window
   active=0; repeat(16) @(negedge clk);
  end
  if(errors==0 && checks>EDGES && sv>0 && wv>0) $display("QCORE_RG PASS checks=%0d scalars=%0d valid_reads=%0d fault_lags=%0d fault_edges=%0d", checks, sv, wv, lag, fault_edges);
  else $display("QCORE_RG FAIL errors=%0d checks=%0d scalars=%0d", errors, checks, sv);
  $finish;
 end
endmodule
`default_nettype wire
