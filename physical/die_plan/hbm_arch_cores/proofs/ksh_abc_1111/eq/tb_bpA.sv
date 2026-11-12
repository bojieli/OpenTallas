`timescale 1ns/1ps
// HBM-CORES-B 11-11 form A under VM CDC FIFO back-pressure: gold (selrep RTL VM branch) and gate (OT_KSH_VMSTG stage),
// each fed by its own copy of the same response stream (a ring model: beats leave only when popped), same f_r sequence,
// same window commands (bank/epoch change only between windows, after the window's 64th pop, as take_cmd does).
// Checks: identical FIFO write sequence (content, order) and the tag fault on the same beat; no write while !f_r.
module tb_bpA;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg f_r=1,vm_phase=0,cm_bank=0;reg[15:0]cm_epoch=0;
 reg[276:0]q[0:262143];integer qn=0,hg=0,hu=0;   // shared beat list, per-model read heads
 wire g_cr,g_pop,g_wv,g_tb,u_cr,u_pop,u_wv,u_tb;wire[278:0]g_wd,u_wd;
 bpA_gold g(.hbm_clk(clk),.hrst_q(rst_n),.c_v(hg<qn),.vm_phase(vm_phase),.f_r(f_r),.d_r(1'b0),.cm_bank(cm_bank),.cm_epoch(cm_epoch),.c_d(q[hg]),
  .o_c_r(g_cr),.o_pop(g_pop),.o_wv(g_wv),.o_tbad(g_tb),.o_wd(g_wd));
 bpA_gate u(.hbm_clk(clk),.hrst_q(rst_n),.c_v(hu<qn),.vm_phase(vm_phase),.f_r(f_r),.d_r(1'b0),.cm_bank(cm_bank),.cm_epoch(cm_epoch),.c_d(q[hu]),
  .o_c_r(u_cr),.o_pop(u_pop),.o_wv(u_wv),.o_tbad(u_tb),.o_wd(u_wd));
 reg[279:0]gw[0:262143],uw[0:262143];integer gn=0,un=0,bad=0,cyc=0,ng=0,seed=7,pops=0,win=0,tb=0,stall=0;
 always @(posedge clk) if(rst_n)begin
  cyc<=cyc+1;
  if(g_wv)begin gw[gn]={g_tb,g_wd};gn=gn+1;if(g_tb)tb=tb+1;end
  if(u_wv)begin uw[un]={u_tb,u_wd};un=un+1;end
  if((g_wv||u_wv)&&!f_r)bad=bad+1;
  if(!f_r)stall=stall+1;
  if(g_pop)hg=hg+1;if(u_pop)hu=hu+1;
 end
 // compare write sequences as they appear
 always @(negedge clk) while(ng<gn&&ng<un)begin if(gw[ng]!==uw[ng])begin bad=bad+1;if(bad<5)$display("BP mismatch write %0d",ng);end ng=ng+1;end
 // stimulus: windows of 64 beats; beats appear in bursts; f_r random with long stalls
 integer i,b;reg[16:0]t;
 always @(negedge clk) if(rst_n)begin
  f_r<=(($random(seed)&7)!=0)&&!(cyc%997>900);
  if(qn<262000&&(($random(seed)&3)!=0)&&b<64)begin
   t={cm_bank,cm_epoch[11:0],4'($random(seed))};if(($random(seed)%50)==0)t[9]=~t[9];   // ~2% bad tags
   q[qn]={t,4'($random(seed)%5),{8{$random(seed)}}};qn=qn+1;b=b+1;
  end
 end
 // window control: open, wait until both models have popped the 64 beats of the window, close, change command
 initial begin
  b=0;repeat(4)@(posedge clk);rst_n=1;
  for(win=0;win<3000;win=win+1)begin
   @(negedge clk);vm_phase=1;
   wait(hg==qn&&hu==qn&&b==64);@(negedge clk);vm_phase=0;
   repeat(1+($random(seed)&7))@(negedge clk);
   cm_bank=$random(seed);cm_epoch=$random(seed);b=0;
  end
  repeat(50)@(posedge clk);
  $display("BP_A cycles %0d windows %0d beats %0d gold_writes %0d gate_writes %0d tag_faults %0d stall_cycles %0d mismatches %0d",cyc,win,qn,gn,un,tb,stall,bad+(gn!=un));
  $finish;
 end
endmodule
