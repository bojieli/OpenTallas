`timescale 1ns/1ps
// NATIVE-FIX3/kvhr 10-18: qkd_host_tx_class_rr (ot_rst_relay at the rst_n pin) vs the UNCHANGED qkd_host_tx_class fed
// the pin reset with its release delayed by exactly 3 ck edges (assert immediate). Every output compared every cycle
// (4-state !==), including the reset windows. Release-latency check: the DUT core reset (u_dut.rst_q) must be low
// while the pin is low and rise on exactly the 3rd ck edge after the pin release. Epochs between random async resets
// alternate legal credited traffic (HOST/CTRL/ING sources hold 4 credits each, peer and physical credits returned
// for every send, class-credit returns, IRQ toggles) and fully random inputs; traffic is driven straight after every
// release, so a core leaving reset early diverges. -DQKD_HR_RR_MUTANT: relay bypassed in the DUT -> must FAIL.
module tb_hr_rr_tx;
 parameter integer NCYC=100000, SEED=1018;
 reg ck=0,rst_n=0;
 reg host_v=0,ctrl_v=0,ing_v=0,irq=0,tx_cr=0;reg[511:0]host_d=0,ctrl_d=0;reg[63:0]ing_d=0;
 reg[23:0]credit_return=0,peer_credit=0;
 reg[2:0]dly=0;always @(posedge ck or negedge rst_n)if(!rst_n)dly<=0;else dly<={dly[1:0],1'b1};
 wire rst_ref=dly[2];
 wire a_hc,b_hc,a_cc,b_cc,a_ic,b_ic,a_tv,b_tv,a_f,b_f;wire[527:0]a_td,b_td;
 qkd_host_tx_class #(.MUT(0))ua(.ck(ck),.rst_n(rst_ref),.host_v(host_v),.host_d(host_d),.host_cr(a_hc),
  .ctrl_v(ctrl_v),.ctrl_d(ctrl_d),.ctrl_cr(a_cc),.ing_v(ing_v),.ing_d(ing_d),.ing_cr(a_ic),
  .credit_return(credit_return),.peer_credit(peer_credit),.irq(irq),.tx_v(a_tv),.tx_d(a_td),.tx_cr(tx_cr),.fault(a_f));
 qkd_host_tx_class_rr #(.MUT(0))u_dut(.ck(ck),.rst_n(rst_n),.host_v(host_v),.host_d(host_d),.host_cr(b_hc),
  .ctrl_v(ctrl_v),.ctrl_d(ctrl_d),.ctrl_cr(b_cc),.ing_v(ing_v),.ing_d(ing_d),.ing_cr(b_ic),
  .credit_return(credit_return),.peer_credit(peer_credit),.irq(irq),.tx_v(b_tv),.tx_d(b_td),.tx_cr(tx_cr),.fault(b_f));
 wire[532:0]va={a_hc,a_cc,a_ic,a_tv,a_td,a_f},vb={b_hc,b_cc,b_ic,b_tv,b_td,b_f};
 integer seed,cyc,mism=0,first_mism=-1,resets=0,app_tx=0,all_tx=0,faults=0,legal=1,epoch_len=0;
 integer since=0,rel_chk=0,rel_err=0,first_rel_err=-1;
 integer s_h,s_c,s_i,o_p[0:2],o_phys,k,cl;
 always @(posedge ck or negedge rst_n)if(!rst_n)since<=0;else if(since<1000)since<=since+1;
 task new_epoch;begin legal=($random(seed)&3)!=0;epoch_len=200+($random(seed)&16'h1ff);
  s_h=4;s_c=4;s_i=4;o_p[0]=0;o_p[1]=0;o_p[2]=0;o_phys=0;end endtask
 always #0.5 ck=~ck;
 initial begin
  seed=SEED;new_epoch;
  repeat(3)@(negedge ck);rst_n=1;
  for(cyc=0;cyc<NCYC;cyc=cyc+1)begin
   @(negedge ck);
   if(va!==vb)begin mism=mism+1;if(first_mism<0)first_mism=cyc;end
   rel_chk=rel_chk+1;
   if(u_dut.rst_q!==((rst_n&&since>=3)?1'b1:1'b0))begin rel_err=rel_err+1;if(first_rel_err<0)first_rel_err=cyc;end
   if(a_tv)all_tx=all_tx+1;if(a_tv&&a_td[527:524]<=5&&a_td[527:524]!=4)app_tx=app_tx+1;if(a_f)faults=faults+1;
   epoch_len=epoch_len-1;
   if(epoch_len<=0)begin rst_n=0;resets=resets+1;#0.2;
    if(u_dut.rst_q!==1'b0)begin rel_err=rel_err+1;if(first_rel_err<0)first_rel_err=cyc;end
    rst_n=1;new_epoch;end
   for(k=0;k<16;k=k+1)begin host_d[k*32+:32]=$random(seed);ctrl_d[k*32+:32]=$random(seed);end
   ing_d={$random(seed),$random(seed)};
   if(legal)begin
    // source credits back on *_cr; peer credits back for every application send; physical credit for every send
    if(a_hc)s_h=s_h+1;if(a_cc)s_c=s_c+1;if(a_ic)s_i=s_i+1;
    if(a_tv)begin o_phys=o_phys+1;cl=a_td[527:524];
     if(cl==0)o_p[0]=o_p[0]+1;else if(cl==1)o_p[1]=o_p[1]+1;else if(cl==5)o_p[2]=o_p[2]+1;end
    host_v=(s_h>0)&&(($random(seed)&3)==0);if(host_v)s_h=s_h-1;
    ctrl_v=(s_c>0)&&(($random(seed)&3)==0);if(ctrl_v)s_c=s_c-1;
    ing_v=(s_i>0)&&(($random(seed)&3)==0);if(ing_v)s_i=s_i-1;
    tx_cr=(o_phys>0)&&($random(seed)&1);if(tx_cr)o_phys=o_phys-1;
    peer_credit=0;
    for(k=0;k<3;k=k+1)if(o_p[k]>0&&($random(seed)&1))begin peer_credit[k*8+:8]=1;o_p[k]=o_p[k]-1;end
    credit_return=(($random(seed)&15)==0)?{8'($random(seed)&3),8'($random(seed)&3),8'($random(seed)&3)}:24'd0;
    if(($random(seed)&63)==0)irq=~irq;
   end else begin
    host_v=$random(seed);ctrl_v=$random(seed);ing_v=$random(seed);irq=$random(seed);tx_cr=$random(seed);
    credit_return=$random(seed);peer_credit=$random(seed);
   end
  end
  $display("HR_RR_LOCKSTEP case=tx seed=%0d cycles=%0d resets=%0d app_tx=%0d all_tx=%0d fault_cycles=%0d release_checks=%0d release_errs=%0d first_release_err=%0d mismatches=%0d first_mismatch=%0d %s",
   SEED,NCYC,resets,app_tx,all_tx,faults,rel_chk,rel_err,first_rel_err,mism,first_mism,
   (mism==0&&rel_err==0&&resets>=10&&app_tx>=1000)?"PASS":"FAIL");
  $finish;
 end
endmodule
