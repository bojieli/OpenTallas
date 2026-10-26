`timescale 1ns/1ps
// RBH-SFUS 10-18: lockstep of the hard tile ot_hbm_su_static_sfustore_hw (one root, relay reset, qid strap pin, per-lane ports) against today's
// ot_hbm_su_static_sfustore (HARD=0, every clk_bank/clk_bank_macro on the same clock), on identical random traffic.
//  - vi_q (all 16 lanes) must equal ref vi_q delayed by ONE edge outside the reset windows (r2 read capture: n+3);
//  - dut.fault must equal ref.fault delayed by ONE edge (the flop-first identity check, n+2 instead of n+1);
//  - traffic: random reads/writes on all lanes, legal addresses (lane id, QID, all 512 rows) with rare illegal ones
//    (each check field, only in the 400 edges before each reset), +RESETS mid-run resets (traffic stops 4 edges before assert and resumes 4 edges after release,
//    the relay's +3 release).
// MUT (DUT): 1 lane n^1 read data, 2 write row bits swapped, 3 lane n^1 check bits, 4 read capture dropped,
// 5 lanes 8..15 bit-swapped qid replica -- each must FAIL.
module tb_hbm_su_sfustore_hw #(parameter integer MUT=0, QID=1);
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [15:0] vi_re=0,kv_we=0; reg [383:0] vi_addr=0,kv_waddr=0; reg [511:0] kv_wdata=0;
 wire [511:0] q_ref,q_dut; wire f_ref,f_dut;
 ot_hbm_su_static_sfustore #(.QID(QID),.MUT(0)) u_ref(.clk(clk),.rst_n(rst_n),.clk_bank({16{clk}}),
  .clk_bank_macro({16{clk}}),.vi_re(vi_re),.vi_addr(vi_addr),.vi_q(q_ref),.kv_we(kv_we),.kv_waddr(kv_waddr),
  .kv_wdata(kv_wdata),.fault(f_ref));
 ot_hbm_su_static_sfustore_hw #(.MUT(MUT)) u_dut(.clk(clk),.rst_n(rst_n),.qid(2'(QID)),
  .l00_vi_re(vi_re[0]),.l00_vi_addr(vi_addr[0+:24]),.l00_vi_q(q_dut[0+:32]),.l00_kv_we(kv_we[0]),.l00_kv_waddr(kv_waddr[0+:24]),.l00_kv_wdata(kv_wdata[0+:32]),
  .l01_vi_re(vi_re[1]),.l01_vi_addr(vi_addr[24+:24]),.l01_vi_q(q_dut[32+:32]),.l01_kv_we(kv_we[1]),.l01_kv_waddr(kv_waddr[24+:24]),.l01_kv_wdata(kv_wdata[32+:32]),
  .l02_vi_re(vi_re[2]),.l02_vi_addr(vi_addr[48+:24]),.l02_vi_q(q_dut[64+:32]),.l02_kv_we(kv_we[2]),.l02_kv_waddr(kv_waddr[48+:24]),.l02_kv_wdata(kv_wdata[64+:32]),
  .l03_vi_re(vi_re[3]),.l03_vi_addr(vi_addr[72+:24]),.l03_vi_q(q_dut[96+:32]),.l03_kv_we(kv_we[3]),.l03_kv_waddr(kv_waddr[72+:24]),.l03_kv_wdata(kv_wdata[96+:32]),
  .l04_vi_re(vi_re[4]),.l04_vi_addr(vi_addr[96+:24]),.l04_vi_q(q_dut[128+:32]),.l04_kv_we(kv_we[4]),.l04_kv_waddr(kv_waddr[96+:24]),.l04_kv_wdata(kv_wdata[128+:32]),
  .l05_vi_re(vi_re[5]),.l05_vi_addr(vi_addr[120+:24]),.l05_vi_q(q_dut[160+:32]),.l05_kv_we(kv_we[5]),.l05_kv_waddr(kv_waddr[120+:24]),.l05_kv_wdata(kv_wdata[160+:32]),
  .l06_vi_re(vi_re[6]),.l06_vi_addr(vi_addr[144+:24]),.l06_vi_q(q_dut[192+:32]),.l06_kv_we(kv_we[6]),.l06_kv_waddr(kv_waddr[144+:24]),.l06_kv_wdata(kv_wdata[192+:32]),
  .l07_vi_re(vi_re[7]),.l07_vi_addr(vi_addr[168+:24]),.l07_vi_q(q_dut[224+:32]),.l07_kv_we(kv_we[7]),.l07_kv_waddr(kv_waddr[168+:24]),.l07_kv_wdata(kv_wdata[224+:32]),
  .l08_vi_re(vi_re[8]),.l08_vi_addr(vi_addr[192+:24]),.l08_vi_q(q_dut[256+:32]),.l08_kv_we(kv_we[8]),.l08_kv_waddr(kv_waddr[192+:24]),.l08_kv_wdata(kv_wdata[256+:32]),
  .l09_vi_re(vi_re[9]),.l09_vi_addr(vi_addr[216+:24]),.l09_vi_q(q_dut[288+:32]),.l09_kv_we(kv_we[9]),.l09_kv_waddr(kv_waddr[216+:24]),.l09_kv_wdata(kv_wdata[288+:32]),
  .l10_vi_re(vi_re[10]),.l10_vi_addr(vi_addr[240+:24]),.l10_vi_q(q_dut[320+:32]),.l10_kv_we(kv_we[10]),.l10_kv_waddr(kv_waddr[240+:24]),.l10_kv_wdata(kv_wdata[320+:32]),
  .l11_vi_re(vi_re[11]),.l11_vi_addr(vi_addr[264+:24]),.l11_vi_q(q_dut[352+:32]),.l11_kv_we(kv_we[11]),.l11_kv_waddr(kv_waddr[264+:24]),.l11_kv_wdata(kv_wdata[352+:32]),
  .l12_vi_re(vi_re[12]),.l12_vi_addr(vi_addr[288+:24]),.l12_vi_q(q_dut[384+:32]),.l12_kv_we(kv_we[12]),.l12_kv_waddr(kv_waddr[288+:24]),.l12_kv_wdata(kv_wdata[384+:32]),
  .l13_vi_re(vi_re[13]),.l13_vi_addr(vi_addr[312+:24]),.l13_vi_q(q_dut[416+:32]),.l13_kv_we(kv_we[13]),.l13_kv_waddr(kv_waddr[312+:24]),.l13_kv_wdata(kv_wdata[416+:32]),
  .l14_vi_re(vi_re[14]),.l14_vi_addr(vi_addr[336+:24]),.l14_vi_q(q_dut[448+:32]),.l14_kv_we(kv_we[14]),.l14_kv_waddr(kv_waddr[336+:24]),.l14_kv_wdata(kv_wdata[448+:32]),
  .l15_vi_re(vi_re[15]),.l15_vi_addr(vi_addr[360+:24]),.l15_vi_q(q_dut[480+:32]),.l15_kv_we(kv_we[15]),.l15_kv_waddr(kv_waddr[360+:24]),.l15_kv_wdata(kv_wdata[480+:32]),
  .fault(f_dut));
 integer seed=1, cycles=24000, nresets=6, errors=0, checks=0, qchecks=0, fchecks=0, faults_seen=0, rd=0, wr=0, bad_issued=0;
 integer quiet=0;            // edges since the last reset release (traffic + compare need >= 4)
 reg f_ref_d=0; reg [511:0] q_ref_d=0;
 always @(posedge clk) q_ref_d<=q_ref;
 integer rises=0;
 always @(posedge clk) begin if(f_ref&&!f_ref_d) rises=rises+1; f_ref_d<=f_ref; end
 function automatic [23:0] legal(input integer lane, input integer row);
  legal=lane | (QID<<14) | ((row&127)<<7) | ((row>>7)<<16);
 endfunction
 function automatic [23:0] mk(input integer lane, input integer allow_bad);
  integer row, k, b; reg [23:0] a;
  row=$urandom%512; a=legal(lane,row);
  if(allow_bad!=0 && $urandom%4000==0) begin
   k=$urandom%4; bad_issued=bad_issued+1;
   case(k) 0: b=18+$urandom%6; 1: b=14+$urandom%2; 2: b=4+$urandom%3; default: b=$urandom%4; endcase
   a[b]=~a[b];
  end
  mk=a;
 endfunction
 // compare just before each rising edge
 always @(negedge clk) if(rst_n && quiet>=4) begin
  qchecks=qchecks+1;
  if(q_dut!==q_ref_d) begin errors=errors+1; if(errors<6) $display("SFUSTORE_HW MISMATCH vi_q t=%0t ref_d=%h dut=%h",$time,q_ref_d,q_dut); end
  fchecks=fchecks+1;
  if(f_dut!==f_ref_d) begin errors=errors+1; if(errors<6) $display("SFUSTORE_HW MISMATCH fault t=%0t ref_d=%b dut=%b",$time,f_ref_d,f_dut); end
  if(f_ref) faults_seen=faults_seen+1;
 end
 integer next_reset, bad_ok;
 initial begin
  if($value$plusargs("SEED=%d",seed)) ; if($value$plusargs("CYCLES=%d",cycles)) ; if($value$plusargs("RESETS=%d",nresets)) ;
  void'($urandom(seed));
  repeat(4) @(posedge clk); @(negedge clk); rst_n=1; quiet=0;
  next_reset=cycles/(nresets+1);
  for(integer c=0;c<cycles;c=c+1) begin
   @(posedge clk); #1; quiet=quiet+1;
   if(nresets>0 && c==next_reset) begin
    vi_re=0; kv_we=0; repeat(4) @(posedge clk); #1; rst_n=0; repeat(3) @(posedge clk); #1; rst_n=1; quiet=0;
    next_reset=next_reset+cycles/(nresets+1);
   end
   // illegal addresses only in the last 400 edges before each reset / the end: the sticky fault rises, is compared, and
   // the reset clears it, so most compared edges see fault low
   bad_ok=((next_reset-c)<400 && next_reset>c) || (cycles-c)<400;
   if(quiet>=4 && c<cycles-8) begin
    for(integer n=0;n<16;n=n+1) begin
     vi_re[n]=($urandom%3)!=0; kv_we[n]=($urandom%3)==0;
     vi_addr[24*n+:24]=mk(n,bad_ok); kv_waddr[24*n+:24]=mk(n,bad_ok); kv_wdata[32*n+:32]=$urandom;
     rd=rd+vi_re[n]; wr=wr+kv_we[n];
    end
   end else begin vi_re=0; kv_we=0; end
  end
  repeat(6) @(posedge clk);
  $display("SFUSTORE_HW checks vi_q=%0d fault=%0d reads=%0d writes=%0d illegal=%0d fault_edges=%0d fault_rises=%0d errors=%0d MUT=%0d",
           qchecks,fchecks,rd,wr,bad_issued,faults_seen,rises,errors,MUT);
  if(errors!=0) $fatal(1,"SFUSTORE_HW LOCKSTEP FAIL errors=%0d",errors);
  if(rises<3||rd<1000||wr<1000) $fatal(1,"SFUSTORE_HW LOCKSTEP FAIL weak stimulus");
  $display("SFUSTORE_HW LOCKSTEP PASS checks=%0d",qchecks+fchecks);
  $finish;
 end
endmodule
