`timescale 1ns/1ps
module tb_obs_delay;
 parameter integer D=20,MUT=0;
 reg clk=0;always begin #0.416 clk=1;#0.417 clk=0;end
 reg rst_n=1;reg[208:0]obs=0;reg q_v=0;reg[7:0]q_idx=0;reg[31:0]q_d=0;
 wire av,bv;wire[7:0]ai,bi;wire[31:0]ad,bd;
 localparam[511:0]MASK=512'h3ffff0000000000000000000000000000;
 ot_hbm_obs_leaf #(.N(209),.LID(4),.SYNC_MASK(MASK)) gold(
  .clk(clk),.rst_n(rst_n),.obs(obs),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),.r_v(av),.r_idx(ai),.r_d(ad));
 codex_obs_delay_candidate #(.D(D),.MUT(MUT),.SYNC_MASK(MASK)) dut(
  .clk(clk),.rst_n(rst_n),.obs(obs),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),.r_v(bv),.r_idx(bi),.r_d(bd));
 reg hv[0:64];reg[7:0]hi[0:64];reg[31:0]hd[0:64];integer he[0:64];
 integer epoch=0,clean=0,drive_age=0,steps=0,checks=0,packets=0,reset_checks=0;
 integer seed=32'h5721bb49;reg[208:0]seen_hi=0,seen_lo=0;reg[6:0]seen_live=0,seen_sticky=0;
 always @(negedge rst_n)begin
  epoch=epoch+1;clean=0;drive_age=0;
  #0.010;
  if(bv!==0)$fatal(1,"RESET_CANCEL D%0d MUT%0d",D,MUT);
  reset_checks=reset_checks+1;
 end
 always @(negedge clk)begin
  if(rst_n)begin
   drive_age=drive_age+1;
   for(integer k=0;k<209;k=k+1)obs[k]=($random(seed)&1)!=0;
   if(drive_age%31==0)obs=209'd1<<(drive_age%209);
   q_v=drive_age<=8 || drive_age%5==0;
   q_idx={(drive_age%17==0)?3'd3:3'd4,1'(drive_age/7),4'(drive_age%7)};
   q_d=$random(seed);
   seen_hi=seen_hi|obs;seen_lo=seen_lo|~obs;
  end else begin q_v=0;obs=0;end
 end
 always @(posedge clk)begin
  #0.002;steps=steps+1;
  for(integer j=64;j>0;j=j-1)begin hv[j]=hv[j-1];hi[j]=hi[j-1];hd[j]=hd[j-1];he[j]=he[j-1];end
  hv[0]=av;hi[0]=ai;hd[0]=ad;he[0]=epoch;
  if(!rst_n)clean=0;else clean=clean+1;
  if(rst_n && clean>D && he[D]==epoch)begin
   if(bv!==hv[D])$fatal(1,"VALID D%0d MUT%0d edge%0d clean%0d expected%b actual%b",D,MUT,steps,clean,hv[D],bv);
   checks=checks+1;
   if(bv)begin
    if({bi,bd}!=={hi[D],hd[D]})$fatal(1,"PACKET D%0d MUT%0d edge%0d idx%x/%x data%x/%x",D,MUT,steps,hi[D],bi,hd[D],bd);
    packets=packets+1;
    if(bi[7:5]==4 && bi[3:0]<7)begin
     if(bi[4])seen_sticky[bi[3:0]]=1;else seen_live[bi[3:0]]=1;
    end
   end
  end else if(bv!==0)$fatal(1,"EARLY_EPOCH_VALID D%0d MUT%0d edge%0d",D,MUT,steps);
 end
 initial begin
  for(integer j=0;j<=64;j=j+1)begin hv[j]=0;hi[j]=0;hd[j]=0;he[j]=-1;end
  #0.050;rst_n=0;repeat(5)@(negedge clk);rst_n=1;
  repeat(350)@(negedge clk);#0.020;rst_n=0;#0.833;rst_n=1;
  repeat(350)@(negedge clk);#0.100;rst_n=0;#0.416;rst_n=1;
  repeat(350)@(negedge clk);#0.050;rst_n=0;#0.080;rst_n=1;
  repeat(400)@(negedge clk);
  if(!(&seen_hi)||!(&seen_lo)||!(&seen_live)||!(&seen_sticky)||packets<150||reset_checks!=4)$fatal(1,"COVERAGE");
  $display("PASS OBS_DELAY D=%0d MUT=%0d edges=%0d qualified_checks=%0d packets=%0d obs_bits=209 q_bits=41 live_words=7 sticky_words=7 reset_checks=%0d period_ps=833 added_host_edges=%0d added_compute_edges=0 payload_FF=%0d reset_release_FF=%0d",D,MUT,steps,checks,packets,reset_checks,D,250*D,D);
  $finish;
 end
endmodule
