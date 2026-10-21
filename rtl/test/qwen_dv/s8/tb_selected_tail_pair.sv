`timescale 1ns/1ps
// One real LM KC8/J3 tail at the two-station cut. No token, stream-age or full-programme claim.
module tb_selected_tail_pair;
reg ck=0;always #5 ck=~ck;
integer cycle=0,ed,po,rc,fd,bd,be,ba,br,si,ei;reg have,bhave;reg[1027:0]ew;reg[1023:0]bw;
reg rst_n=0;reg[115:0]cmd[0:1];reg[1027:0]rss[0:1],rsn[0:1];
reg[115:0]cfg_cmd[0:1];reg[511:0]exp_recv[0:2],exp_send[0:2];reg[255:0]exp_scale[0:2];
reg tw_we=0;reg[8:0]tw_addr=0;reg[1023:0]tw_data=0;
wire[513:0]nb[0:1];wire rv[0:1],rl[0:1],fault[0:1];wire[7:0]ri[0:1];wire[511:0]rd[0:1];
wire[8:0]left[0:1];integer nr=0,ns=0,halves=0;integer cfgshift=32;string path;
initial begin
 if($value$plusargs("CFGSHIFT=%d",cfgshift))begin end
 if(!$value$plusargs("FIX=%s",path))$fatal(1,"FIX required");
 $readmemh({path,"/cfg.hex"},cfg_cmd);$readmemh({path,"/receiver.hex"},exp_recv);$readmemh({path,"/sender.hex"},exp_send);$readmemh({path,"/scale.hex"},exp_scale);
 fd=$fopen({path,"/pair.ev"},"r");bd=$fopen({path,"/btab.ev"},"r");
 rc=$fscanf(fd,"%d %d %h\n",ed,po,ew);have=(rc==3);br=$fscanf(bd,"%d %d %h\n",be,ba,bw);bhave=(br==3);
 for(integer j=0;j<2;j=j+1)begin cmd[j]=0;rss[j]=0;rsn[j]=0;end
end
always @(negedge ck)begin
 rst_n=cycle>=8;tw_we=0;tw_addr=0;tw_data=0;
 for(integer j=0;j<2;j=j+1)begin cmd[j]=0;rss[j]=0;rsn[j]=0;end
 // Same post-enumeration SID values and SETID decode as the real parent.
 if(cycle==16)begin cmd[0]=116'h8f;cmd[1]=116'h9f;end
 // Actual W CMD dates + two edges per slice -> both local entries3298.
 // Explicit isolated retiming32edges earlier, preserving original command bits.
 if(cycle==3298-cfgshift)begin cmd[0]=cfg_cmd[0];cmd[1]=cfg_cmd[1];$display("CFG_INPUT cycle%0d original_local3298 advance%0d",cycle,cfgshift);end
 while(have && ed==cycle)begin
  si=(po-18)/2;
  if(po%2==0)rss[si]=rss[si]|ew;else rsn[si]=rsn[si]|ew;
  rc=$fscanf(fd,"%d %d %h\n",ed,po,ew);have=(rc==3);
 end
 if(have&&ed<cycle)$fatal(1,"stale event");
 if(bhave&&be==cycle)begin tw_we=1;tw_addr=ba;tw_data=bw;br=$fscanf(bd,"%d %d %h\n",be,ba,bw);bhave=(br==3);end
 cycle=cycle+1;
end
for(genvar s=0;s<2;s=s+1)begin:g_pair
 reg rs1=0,rst=0;always @(posedge ck or negedge rst_n)if(!rst_n)begin rs1<=0;rst<=0;end else begin rs1<=1;rst<=rs1;end
 reg[115:0]cq;reg[1027:0]sq,nq;reg[513:0]nbi;
 always @(posedge ck or negedge rst)if(!rst)begin cq<=0;sq<=0;nq<=0;nbi<=0;end else begin cq<=cmd[s];sq<=rss[s];nq<=rsn[s];nbi<=nb[1-s];end
 reg[3:0]sid;reg sid_ok;wire setid=cq[0]&&cq[3:1]==7;
 always @(posedge ck or negedge rst)if(!rst)begin sid<=0;sid_ok<=0;end else if(setid)begin sid<=cq[7:4];sid_ok<=1;end
 wire go=cq[0]&&sid_ok&&(cq[115:112]==sid||cq[115:112]==15)&&cq[3:1]!=7;
 wire cfg=go&&cq[3:1]==2;wire[28:0]c={cfg,cq[5:4],cq[6],cq[14:7],cq[23:15],cq[66:59]};
 wire bre;wire[8:0]bword;wire[255:0]bq;
 wire[1023:0]bt_rd;reg[1023:0]btcap;reg[1:0]b1,b2;
 for(genvar b=0;b<4;b=b+1)begin:g_bank
  // Exact mutable BTAB macro; receiver packets from real prelude, sender unused table stays untouched.
  ot_sram_1r1w_128x256_m1_r2c2 u_m(.clk(ck),.r_ce_in(bre&&bword[1:0]==b),.r_addr_in(bword[8:2]),.rd_out(bt_rd[256*b+:256]),
   .w_ce_in(tw_we&&(s==0)),.w_addr_in(tw_addr[8:2]),.wd_in(tw_data[256*b+:256]),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
 // Exact SRAM rd_out then btcap + bank t1/t2, both samples retained.
 always @(posedge ck)begin b1<=bword[1:0];b2<=b1;btcap<=bt_rd;end
 assign bq=btcap[256*b2+:256];
 tb_selected_tail_station #(.MUT(0),.PIN_IN(1),.BT_LAT(1)) u_stn(.ck_r({8{ck}}),.rst_n_r({8{rst}}),.cfg_r({8{c}}),
  .rs_s_lo(sq[511:0]),.rs_s_hi(sq[1025:514]),.rs_n_lo(nq[511:0]),.rs_n_hi(nq[1025:514]),
  .rs_s_c({8{sq[1027:1026],sq[513:512]}}),.rs_n_c({8{nq[1027:1026],nq[513:512]}}),
  .nb_d(nbi[511:0]),.nb_c({8{nbi[513:512]}}),.nb_od(nb[s][511:0]),.nb_oc(nb[s][513:512]),
  .bt_re(bre),.bt_word(bword),.bt_q(bq),.r_v(rv[s]),.r_idx(ri[s]),.r_last(rl[s]),.r_d(rd[s]),.fault(fault[s]));
 // Actual slice parent completion law; no forced busy-clear or fake padding.
 reg[8:0]stn_left;reg stn_snd;assign left[s]=stn_left;
 always @(posedge ck or negedge rst)if(!rst)begin stn_left<=0;stn_snd<=0;end else if(cfg)begin stn_left<={1'b0,cq[14:7]};stn_snd<=cq[5:4]==3;end else if(stn_left!=0&&(stn_snd?nb[s][512]:rv[s]))stn_left<=stn_left-1'b1;
 always @(posedge ck)begin
  if(cfg)$display("CFG_PARENT side%0d cycle%0d mode%0d nwords%0d kc%0d",s,cycle-1,cq[5:4],cq[14:7],cq[66:59]+1);
  if(u_stn.g_r[0].u_rg.cfg_final[6])begin #1;$display("CFG_READY side%0d cycle%0d nwords%0d word_last%0d",s,cycle-1,u_stn.g_r[0].u_rg.nwords,u_stn.g_r[0].u_rg.word_last);end
  if(sq[512]&&cycle<3295)$display("FIRST_NEAR_PARENT side%0d cycle%0d",s,cycle-1);
 end
end
always @(posedge ck)begin #2;
 for(integer j=0;j<2;j=j+1)begin
  if(rss[j][512])halves=halves+1;if(rss[j][1026])halves=halves+1;if(rsn[j][512])halves=halves+1;if(rsn[j][1026])halves=halves+1;
  if(cycle>50&&fault[j])$fatal(1,"SELECTED_TAIL_FAULT side%0d cycle%0d",j,cycle-1);
 end
 if(nb[1][512])begin
  if(ns>=3||nb[1][511:0]!==exp_send[ns])$fatal(1,"SENDER_NUMERIC_MISMATCH word%0d cycle%0d",ns,cycle-1);
  $display("SENDER_NB word%0d cycle%0d data%h",ns,cycle-1,nb[1][511:0]);ns=ns+1;
 end
 if(rv[0])begin
  if(nr>=3||rd[0]!==exp_recv[nr]||ri[0]!==nr||rl[0]!=(nr==2))$fatal(1,"RECEIVER_NUMERIC_MISMATCH word%0d idx%0d last%0d cycle%0d got%h want%h",nr,ri[0],rl[0],cycle-1,rd[0],exp_recv[nr]);
  $display("RECEIVER word%0d cycle%0d idx%0d last%0d data%h",nr,cycle-1,ri[0],rl[0],rd[0]);nr=nr+1;
 end
 if(cycle==3450)begin
  if(nr!=3||ns!=3||halves!=192||left[0]!=0||left[1]!=0)$fatal(1,"SELECTED_TAIL_NOT_DRAINED receiver%0d sender%0d halves%0d left%0d/%0d",nr,ns,halves,left[0],left[1]);
  $display("SELECTED_TAIL_PASS48_FP32 receiver3 sender3 halves192 KC8 J3 busy0/0 PIN_IN1 BT_LAT1 cfg_advance32 no_programme_age_claim");$finish;
 end
end
endmodule
