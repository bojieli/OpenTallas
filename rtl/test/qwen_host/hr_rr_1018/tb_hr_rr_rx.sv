`timescale 1ns/1ps
// NATIVE-FIX3/kvhr 10-18: qkd_host_rx_class_admission_rr (ot_rst_relay at the rst_n pin) vs the UNCHANGED
// qkd_host_rx_class_admission fed the pin reset with its release delayed by exactly 3 ck edges (assert immediate).
// Every output compared every cycle (4-state !==), including the reset windows. Release-latency check: the DUT core
// reset (u_dut.rst_q) must be low while the pin is low and rise on exactly the 3rd ck edge after the pin release.
// Stimulus = tb_irr_lockstep (KVJ-A8): epochs between random async resets alternate legal credited traffic and fully
// random words; traffic is driven straight after every release, so a core leaving reset early diverges.
// -DQKD_HR_RR_MUTANT: relay bypassed in the DUT -> must FAIL.
module tb_hr_rr_rx;
 parameter integer NCYC=100000, SEED=1018;
 reg ck=0,rst_n=0;reg[2:0]die_id=0;reg rx_v=0;reg[527:0]rx_d=0;
 reg native_reserved=1,ownership_valid=0,host_cr=0,ctrl_cr=0;reg[4:0]ing_crn=0;
 // reference reset: pin assert immediate, release 3 ck edges after the pin (the documented contract)
 reg[2:0]dly=0;always @(posedge ck or negedge rst_n)if(!rst_n)dly<=0;else dly<={dly[1:0],1'b1};
 wire rst_ref=dly[2];
 wire a_rx_cr,b_rx_cr,a_hv,b_hv,a_cv,b_cv,a_iv,b_iv,a_f,b_f,a_ao,b_ao,a_lq,b_lq,a_df,b_df;
 wire[511:0]a_hd,b_hd,a_cd,b_cd,a_id,b_id;wire[1:0]a_ic,b_ic;wire[23:0]a_cr,b_cr,a_pc,b_pc;
 qkd_host_rx_class_admission #(.MUT(0),.STRAPPED(1),.IR_REPL(1))ua(.ck(ck),.rst_n(rst_ref),.die_id(die_id),
  .rx_v(rx_v),.rx_d(rx_d),.rx_cr(a_rx_cr),.native_reserved(native_reserved),.ownership_valid(ownership_valid),
  .host_v(a_hv),.host_d(a_hd),.host_cr(host_cr),.ctrl_v(a_cv),.ctrl_d(a_cd),.ctrl_cr(ctrl_cr),
  .ing_v(a_iv),.ing_cls(a_ic),.ing_d(a_id),.ing_crn(ing_crn),.credit_return(a_cr),.peer_credit(a_pc),
  .fault(a_f),.admission_open(a_ao),.launch_quiet(a_lq),.deferred(a_df));
 qkd_host_rx_class_admission_rr #(.MUT(0),.STRAPPED(1),.IR_REPL(1))u_dut(.ck(ck),.rst_n(rst_n),.die_id(die_id),
  .rx_v(rx_v),.rx_d(rx_d),.rx_cr(b_rx_cr),.native_reserved(native_reserved),.ownership_valid(ownership_valid),
  .host_v(b_hv),.host_d(b_hd),.host_cr(host_cr),.ctrl_v(b_cv),.ctrl_d(b_cd),.ctrl_cr(ctrl_cr),
  .ing_v(b_iv),.ing_cls(b_ic),.ing_d(b_id),.ing_crn(ing_crn),.credit_return(b_cr),.peer_credit(b_pc),
  .fault(b_f),.admission_open(b_ao),.launch_quiet(b_lq),.deferred(b_df));
 wire[1600:0]va={a_rx_cr,a_hv,a_hd,a_cv,a_cd,a_iv,a_ic,a_id,a_cr,a_pc,a_f,a_ao,a_lq,a_df};
 wire[1600:0]vb={b_rx_cr,b_hv,b_hd,b_cv,b_cd,b_iv,b_ic,b_id,b_cr,b_pc,b_f,b_ao,b_lq,b_df};
 integer seed,cyc,mism=0,first_mism=-1,resets=0,ing_pops=0,host_pops=0,faults=0,legal=1,epoch_len=0;
 integer since=0,rel_chk=0,rel_err=0,first_rel_err=-1;
 integer s_h,s_c,s_i,o_h,o_c,o_i,k;
 reg[3:0]cls;reg[527:0]w;
 always @(posedge ck or negedge rst_n)if(!rst_n)since<=0;else if(since<1000)since<=since+1;
 task new_epoch;begin legal=($random(seed)&3)!=0;epoch_len=200+($random(seed)&16'h1ff);
  s_h=4;s_c=4;s_i=16;o_h=0;o_c=0;o_i=0;end endtask
 always #0.5 ck=~ck;
 initial begin
  seed=SEED;new_epoch;
  repeat(3)@(negedge ck);rst_n=1;
  for(cyc=0;cyc<NCYC;cyc=cyc+1)begin
   @(negedge ck);
   if(va!==vb)begin mism=mism+1;if(first_mism<0)first_mism=cyc;end
   rel_chk=rel_chk+1;
   if(u_dut.rst_q!==((rst_n&&since>=3)?1'b1:1'b0))begin rel_err=rel_err+1;if(first_rel_err<0)first_rel_err=cyc;end
   if(a_iv)ing_pops=ing_pops+1;if(a_hv)host_pops=host_pops+1;if(a_f)faults=faults+1;
   epoch_len=epoch_len-1;
   if(epoch_len<=0)begin rst_n=0;resets=resets+1;#0.2;
    if(u_dut.rst_q!==1'b0)begin rel_err=rel_err+1;if(first_rel_err<0)first_rel_err=cyc;end
    rst_n=1;new_epoch;end
   if(legal)begin
    s_h=s_h+a_cr[7:0];s_c=s_c+a_cr[15:8];s_i=s_i+a_cr[23:16];
    if(a_hv)o_h=o_h+1;if(a_cv)o_c=o_c+1;if(a_iv)o_i=o_i+1;
    die_id=0;
    native_reserved=(($random(seed)&7)==0)?~native_reserved:native_reserved;
    ownership_valid=(($random(seed)&15)==0)?~ownership_valid:ownership_valid;
    host_cr=(o_h>0)&&($random(seed)&1);if(host_cr)o_h=o_h-1;
    ctrl_cr=(o_c>0)&&($random(seed)&1);if(ctrl_cr)o_c=o_c-1;
    k=$random(seed)&7;if(k>o_i)k=o_i;ing_crn=k;o_i=o_i-k;
    w={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
       $random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
    cls=$random(seed)&7;rx_v=0;
    if(($random(seed)&3)!=0)begin
     if(cls<=1&&s_h>0)begin cls=0;s_h=s_h-1;rx_v=1;end
     else if(cls==5&&s_c>0)begin cls=1;s_c=s_c-1;rx_v=1;end
     else if(cls>=2&&cls<=4&&s_i>0)begin s_i=s_i-1;rx_v=1;end
     else if(cls==7)begin w[511:24]=0;w[7:0]=($random(seed)&255)%5;w[15:8]=($random(seed)&255)%5;w[23:16]=($random(seed)&255)%5;rx_v=1;end
     else if(s_i>0)begin cls=2+(($random(seed)&1));s_i=s_i-1;rx_v=1;end
    end
    w[527:524]=cls;w[523:512]=0;rx_d=w;
   end else begin
    die_id=$random(seed);rx_v=$random(seed);native_reserved=$random(seed);ownership_valid=$random(seed);
    host_cr=$random(seed);ctrl_cr=$random(seed);ing_crn=$random(seed);
    for(k=0;k<17;k=k+1)rx_d[k*32+:32]=$random(seed);
    if($random(seed)&1)rx_d[523:512]=0;
    if($random(seed)&1)rx_d[527:524]=($random(seed)&255)%5;
   end
  end
  $display("HR_RR_LOCKSTEP case=rx seed=%0d cycles=%0d resets=%0d host_pops=%0d ing_pops=%0d fault_cycles=%0d release_checks=%0d release_errs=%0d first_release_err=%0d mismatches=%0d first_mismatch=%0d %s",
   SEED,NCYC,resets,host_pops,ing_pops,faults,rel_chk,rel_err,first_rel_err,mism,first_mism,
   (mism==0&&rel_err==0&&resets>=10&&host_pops>=1000&&ing_pops>=1000)?"PASS":"FAIL");
  $finish;
 end
endmodule
