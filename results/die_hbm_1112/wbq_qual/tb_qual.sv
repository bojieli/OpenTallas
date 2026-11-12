`timescale 1ps/1ps
`default_nettype none
// HBM-WBQ-QUAL-1 (DIE-HBM-100, 11-12): parent-in-the-loop qualification bench for the WBQ root S7 form.
// Two compositions of the REAL parent (ot_wbq_sw from reform_1105b, 16 K pin skids, 4 root slots, CDC FIFOs, SRAM macro models) run on the
// SAME random stimulus, on two free-running clocks (fifo_clk period TF ps, hbm_clk period TH ps, phase PH ps):
//   A = old root  (ot_wbq_root_g2 of reform_1105b: the form the wave builds now)
//   B = new root  (ROOT S7: CBREG/SSTOPREG/GREG parameters)
// MODE 0 (clean): chained blocks on alternating banks, zero gap and random gap, K stalls per SLOW; checks every K write against a golden
//   map (address -> data) built from the stimulus, no duplicate, no missing, no fault, stream pins and wa sequence equal A vs B, K outstanding
//   drained, done lag A vs B.
// MODE 1 (fault sweep): per case a reset, 2-3 chained blocks, one fault injected at a random fifo_clk time: F1 bad reserve pulse (stream
//   sticky), F2 corrupted wd sector word (stream sticky), F3 spurious K write-done (hbm sticky). Checks: fault raised and held, integrity of
//   every K write, root activity after the parent s_stop (cycles and lane events, per group), seam valids after h_stop, K writes after h_stop,
//   then a reset and a clean recovery block.
module tb_qual;
 // runtime plusargs (default in brackets): +TF=ps [1000] +TH=ps [1000] +PH=ps [137] +MODE=0|1 [0] +NCASE=n [20] +SLOW=0|1|2 [0] +QUAD=0|1 [0] +NB=n [4] +MAXTOT=n [1984]
 int TF=1000, TH=1000, PH=137, MODE=0, NCASE=20, NB=4, SLOW=0, QUAD=0;
 initial begin void'($value$plusargs("TF=%d",TF));void'($value$plusargs("TH=%d",TH));void'($value$plusargs("PH=%d",PH));void'($value$plusargs("MODE=%d",MODE));void'($value$plusargs("NCASE=%d",NCASE));void'($value$plusargs("SLOW=%d",SLOW));void'($value$plusargs("QUAD=%d",QUAD));void'($value$plusargs("NB=%d",NB)); end
 parameter integer HREG=2, GIN=0, CBREG=1, SSTOPREG=1, GREG=1, MUTCB=0, MUTSTOP=0, CRED=4, DCHK=1;
 int MAXTOT=1984;
 initial void'($value$plusargs("MAXTOT=%d",MAXTOT));
 reg fc=0,hc=0;
 initial begin #1; forever #(TF/2) fc=~fc; end
 initial begin #(PH+1); forever #(TH/2) hc=~hc; end
 reg srst_n=0,hrst_n=0;
 reg rv=0,rb=0,fb=0,fs=0;reg[15:0]re=0,fe=0;reg[11:0]rt=0;reg[31:0]rbase=0;reg[2311:0]wd=0;
 reg inj_rv=0,inj_rb=0;reg[11:0]inj_rt=0;
 wire w_rv=rv|inj_rv;wire w_rb=inj_rv?inj_rb:rb;wire[11:0]w_rt=inj_rv?inj_rt:rt;
 wire[15:0]kv[0:1];wire[479:0]ka[0:1];wire[4095:0]kd[0:1];reg[15:0]rdy[0:1];reg[15:0]dn[0:1];
 wire rd[0:1],bv[0:1],f[0:1],sst[0:1],hst[0:1],cpo[0:1],cps[0:1];wire[11:0]wa[0:1];wire[29:0]bb[0:1];wire[11:0]bt[0:1];
 wire[31:0]o_fw[0:1],o_fe[0:1],o_mr[0:1];wire[7:0]o_gv[0:1];
 genvar gi;
 generate for(gi=0;gi<2;gi=gi+1)begin:g_d
  qual_comp #(.NEWROOT(gi),.HREG(HREG),.GIN(GIN),.CBREG(CBREG),.SSTOPREG(SSTOPREG),.GREG(GREG),.MUTCB(MUTCB),.MUTSTOP(MUTSTOP),.CRED(CRED),.DCHK(DCHK)) u(
   .fifo_clk(fc),.hbm_clk(hc),.stream_rst_n(srst_n),.hbm_rst_n(hrst_n),.stk(2'd0),.quad(QUAD[0]!=0),
   .wb_reserve_v(w_rv),.wb_reserve_bank(w_rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(w_rt),.wb_reserve_base(rbase),
   .wb_fill_start(fs),.wd(wd),.wb_ready(rd[gi]),.wa(wa[gi]),.wbw_v(bv[gi]),.wbw_base(bb[gi]),.wbw_total(bt[gi]),
   .w_k_v(kv[gi]),.w_k_rdy(rdy[gi]),.w_k_addr(ka[gi]),.w_k_wdata(kd[gi]),.w_k_wr_done(dn[gi]),.fault(f[gi]),
   .s_stop(sst[gi]),.h_stop(hst[gi]),.copy_on(cpo[gi]),.copy_sel(cps[gi]),
   .obs_fillw(o_fw[gi]),.obs_fifowe(o_fe[gi]),.obs_memrd(o_mr[gi]),.obs_gv(o_gv[gi]));
 end endgenerate
 function automatic int pc4(input [3:0] v);pc4=int'(v[0])+int'(v[1])+int'(v[2])+int'(v[3]);endfunction
 function automatic [29:0] fold(input [28:0] o,input q);fold={o[28:6],q^o[10]^o[15],o[5:0]};endfunction
 function automatic int outst(input int u,input int p);
  if(u==0)outst=int'(g_d[0].u.u_sw.outstanding[p]);else outst=int'(g_d[1].u.u_sw.outstanding[p]);
 endfunction
 // ---------------- case state
 bit [255:0] gold[longint];
 bit seen[0:1][longint];
 int  q[0:1][0:15];
 int  w[0:1],corrupt[0:1],dup[0:1],afterh[0:1],gvpost[0:1];
 int  ev_cyc[0:1],ev_fw[0:1],ev_fe[0:1],ev_mr[0:1],ev_gmax[0:1];
 int  evg[0:1][0:7];
 int  nd[0:1];longint done_t[0:1][$];int wv[0:1][$];
 longint cstart_t[0:1][$];
 int  sbad=0,wbad=0,rdybad=0;
 int  fcyc=0;int ft_f[0:1]='{-1,-1};int fdl_hist[0:3][0:3];int fdl_max[0:3];initial for(int a=0;a<4;a++)begin fdl_max[a]=0;for(int b=0;b<4;b++)fdl_hist[a][b]=0;end
 int n_unclean_abs=0,n_fdiff=0,max_fdelta=0,n_f3abs_unraised=0;
 bit  fault_seen=0;
 reg  inj_dn_req=0;bit inj_dn_ok=0;int spur_pp=-1;bit arr[0:1];bit arr_clean[0:1];longint arr_t[0:1];longint hcyc=0;int n_a_clean[0:1],n_a_unclean[0:1],n_a_viol[0:1];
 initial begin for(int e=0;e<2;e++)begin n_a_clean[e]=0;n_a_unclean[e]=0;n_a_viol[e]=0;arr[e]=0;arr_clean[e]=0;arr_t[e]=0;end end
 bit chk_pend[0:1];
 // ---------------- K partner + monitors (hbm_clk), one shared random draw per edge
 bit [15:0] rrdy;bit [15:0] rdn;int u_i,p_i;longint ad_l;
 always @(posedge hc)begin
  rrdy=(SLOW==2)?16'hffff:(SLOW==1)?16'($urandom&$urandom&$urandom&$urandom):16'($urandom|$urandom);
  for(p_i=0;p_i<16;p_i++)rdn[p_i]=($urandom%((SLOW==1)?16:4)==0);
  for(u_i=0;u_i<2;u_i++)begin
   if(!hrst_n)begin
    rdy[u_i]<=0;dn[u_i]<=0;for(p_i=0;p_i<16;p_i++)q[u_i][p_i]=0;
   end else begin
    for(p_i=0;p_i<16;p_i++)begin
     if(kv[u_i][p_i]===1'b1&&rdy[u_i][p_i]===1'b1)begin
      ad_l=longint'(ka[u_i][30*p_i+:30]);
      if(!gold.exists(ad_l)||gold[ad_l]!==kd[u_i][256*p_i+:256])corrupt[u_i]=corrupt[u_i]+1;
      if(seen[u_i].exists(ad_l))dup[u_i]=dup[u_i]+1;
      seen[u_i][ad_l]=1;w[u_i]=w[u_i]+1;q[u_i][p_i]=q[u_i][p_i]+1;
      if(hst[u_i]===1'b1)afterh[u_i]=afterh[u_i]+1;
     end
    end
    dn[u_i]<=0;
    for(p_i=0;p_i<16;p_i++)if(q[u_i][p_i]>0&&rdn[p_i])begin dn[u_i][p_i]<=1;q[u_i][p_i]=q[u_i][p_i]-1;end
    rdy[u_i]<=rrdy;
    if(o_gv[u_i]!==8'b0&&hst[u_i]===1'b1)gvpost[u_i]=gvpost[u_i]+int'(|o_gv[u_i]);
   end
  end
  if(inj_dn_req)begin
   // spurious write-done on a PC where neither composition has anything outstanding (else it is absorbed as a real done):
   // wait on the request until such a PC exists
   int pp,k,found;pp=$urandom%16;found=-1;
   for(k=0;k<16;k++)begin
    if(found<0&&outst(0,(pp+k)%16)==0&&outst(1,(pp+k)%16)==0&&q[0][(pp+k)%16]==0&&q[1][(pp+k)%16]==0&&!dn[0][(pp+k)%16]&&!dn[1][(pp+k)%16])found=(pp+k)%16;
   end
   if(found>=0)begin for(u_i=0;u_i<2;u_i++)dn[u_i][found]<=1'b1;inj_dn_req=0;inj_dn_ok=1;spur_pp=found;arr[0]=0;arr[1]=0;end
  end
 end
 // rule (a): a K write-done with nothing outstanding (and no same-cycle push credit) must raise h_stop within 2 hbm_clk of its arrival
 initial begin chk_pend[0]=0;chk_pend[1]=0; end
 always @(posedge hc)begin
  hcyc<=hcyc+1;
  if(spur_pp>=0)begin
   for(int e=0;e<2;e++)begin
    bit dq;dq=(e==0)?g_d[0].u.u_sw.wr_done_q[spur_pp]:g_d[1].u.u_sw.wr_done_q[spur_pp];
    if(!arr[e]&&dq===1'b1)begin arr[e]=1;arr_t[e]=hcyc;arr_clean[e]=(outst(e,spur_pp)==0)&&(hst[e]!==1'b1);
     if(arr_clean[e])begin n_a_clean[e]++;chk_pend[e]=1;end else n_a_unclean[e]++;end
   end
  end
  for(int e=0;e<2;e++)if(chk_pend[e]&&hcyc>=arr_t[e]+2)begin
   chk_pend[e]=0;if(hst[e]!==1'b1)begin n_a_viol[e]++;if(n_a_viol[e]<=3)$display("RULE-A-VIOL dut %0d: done on PC %0d with nothing outstanding, no h_stop 2 hbm_clk after arrival",e,spur_pp);end
  end
 end
 // ---------------- stream-domain monitors (fifo_clk)
 int e,g_,l_;
 always @(posedge fc)begin
  fcyc<=fcyc+1;
  if(srst_n&&hrst_n)begin
   if(bv[0]!==bv[1]||(bv[0]&&(bb[0]!==bb[1]||bt[0]!==bt[1])))sbad=sbad+1;
   if(fs&&MODE==0&&(rd[0]!==1'b1||rd[1]!==1'b1))rdybad=rdybad+1;
   for(e=0;e<2;e++)begin
    if(wa[e]!==12'b0&&wa[e]!==12'bx)begin done_t[e].push_back($time);wv[e].push_back(int'(wa[e]));nd[e]=nd[e]+1;end
    if(sst[e]===1'b1)begin
     int tf_,te_,tm_;tf_=0;te_=0;tm_=0;
     for(g_=0;g_<8;g_++)begin
      int a_,b_,c_;a_=pc4(o_fw[e][4*g_+:4]);b_=pc4(o_fe[e][4*g_+:4]);c_=pc4(o_mr[e][4*g_+:4]);
      tf_+=a_;te_+=b_;tm_+=c_;evg[e][g_]=evg[e][g_]+a_+b_+c_;
      if(evg[e][g_]>ev_gmax[e])ev_gmax[e]=evg[e][g_];
     end
     ev_fw[e]=ev_fw[e]+tf_;ev_fe[e]=ev_fe[e]+te_;ev_mr[e]=ev_mr[e]+tm_;
     if(tf_+te_+tm_>0)ev_cyc[e]=ev_cyc[e]+1;
    end
    if(f[e]===1'b1||sst[e]===1'b1||hst[e]===1'b1)fault_seen=1;
    if(f[e]===1'b1&&ft_f[e]<0)ft_f[e]=fcyc;
   end
  end
 end
 reg cpo_q0=0,cpo_q1=0;int b2b[0:1],b2bflip[0:1];longint fall_t[0:1];
 initial begin b2b[0]=0;b2b[1]=0;b2bflip[0]=0;b2bflip[1]=0;fall_t[0]=-1;fall_t[1]=-1; end
 always @(posedge fc)begin cpo_q0<=cpo[0];cpo_q1<=cpo[1];
  if(!cpo[0]&&cpo_q0)fall_t[0]=$time;if(!cpo[1]&&cpo_q1)fall_t[1]=$time;
  for(int e=0;e<2;e++)if(cpo[e]&&!(e?cpo_q1:cpo_q0)&&fall_t[e]>=0&&($time-fall_t[e])<=3*TF)begin b2b[e]=b2b[e]+1;end
  if(cpo[0]&&!cpo_q0)cstart_t[0].push_back($time);if(cpo[1]&&!cpo_q1)cstart_t[1].push_back($time);end
 // ---------------- stimulus
 int cyc_inj=-1;int ftype=0;bit f2_done=0,inj_done=0;int ptot[0:3];
 task automatic clear_case();
  gold.delete();seen[0].delete();seen[1].delete();
  for(int u=0;u<2;u++)begin w[u]=0;corrupt[u]=0;dup[u]=0;afterh[u]=0;gvpost[u]=0;ev_cyc[u]=0;ev_fw[u]=0;ev_fe[u]=0;ev_mr[u]=0;ev_gmax[u]=0;nd[u]=0;
   done_t[u].delete();wv[u].delete();cstart_t[u].delete();for(int g=0;g<8;g++)evg[u][g]=0;end
  sbad=0;rdybad=0;fault_seen=0;f2_done=0;inj_done=0;spur_pp=-1;chk_pend[0]=0;chk_pend[1]=0;arr[0]=0;arr[1]=0;arr_clean[0]=0;arr_clean[1]=0;ft_f[0]=-1;ft_f[1]=-1;fcyc=0;
 endtask
 task automatic do_reset();
  srst_n=0;hrst_n=0;
  rv<=0;fs<=0;wd<=0;inj_rv<=0;
  #(10*TF+10*TH+$urandom%TF);
  srst_n=1;hrst_n=1;
  #(40*TF+30*TH);
  fault_seen=0;fcyc=0;
 endtask
 task automatic do_block(input bit b,input [15:0] ep,input [28:0] base_in,input [11:0] tot);
  integer o,k;reg [2311:0] wn;reg [28:0] base;
  begin
   // each block of a case lives in its own 61 M-sector region: no two blocks of one case share a sector address (a shared address makes the golden map ambiguous)
   base=29'(longint'(base_in)%61440000)+29'((ep%4)*61440000);
   @(posedge fc);rv<=1;rb<=b;re<=ep;rt<=tot;rbase<={3'b0,base};
   @(posedge fc);rv<=0;
   repeat(2)@(posedge fc);
   fb<=b;fe<=ep;repeat(5)@(posedge fc);fs<=1;@(posedge fc);fs<=0;
   for(o=0;o<tot;o=o+8)begin
    wn=0;
    for(k=0;k<8;k=k+1)if(o+k<tot)begin
     wn[289*k+:256]={8{$urandom}};
     wn[289*k+256+:32]={3'b0,base}+o+k;
     wn[289*k+288]=1;
     gold[longint'(fold(29'(base+o+k),QUAD[0]))]=wn[289*k+:256];
    end
    if(MODE==1&&ftype==2&&!f2_done&&cyc_inj>=0&&fcyc>=cyc_inj&&wn[288])begin wn[256+:32]=wn[256+:32]^32'h1;f2_done=1;end
    wd<=wn;@(posedge fc);
   end
   wd<=0;
  end
 endtask
 // ---------------- case driver
 int tots[0:13]='{1,7,8,9,31,32,33,63,64,256,640,1024,1984,77};
 int ncase_clean=0,nfail_clean=0;
 // aggregate stats
 longint agg_w0=0,agg_w1=0;int agg_cases=0;
 int bad_integrity=0,bad_nofault=0,bad_postcyc=0,bad_postwords=0,bad_hpost=0,bad_recov=0,bad_clean=0,bad_stream=0,bad_wv=0,bad_out=0,bad_done=0,bad_hold=0,bad_inj=0;
 int max_ev_cyc[0:1],max_ev_g[0:1],max_after[0:1],max_gvpost[0:1];int dw_min=1<<30,dw_max=-(1<<30);
 longint lag_sum=0;int lag_n=0,lag_max=-(1<<30),lag_min=1<<30;
 longint dur_sum[0:1];int dur_n[0:1];
 int n_absorb=0;int n_ft[0:3];int n_ftdet[0:3];
 int c,n,tt,want,ti,nblk,timeout;bit b;
 task automatic wait_done(input int cnt,input bit stop_on_fault);
  int t;t=0;
  while(!(nd[0]>=cnt&&nd[1]>=cnt)&&!(stop_on_fault&&fault_seen)&&t<60000)begin @(posedge fc);t=t+1;end
  if(t>=60000)timeout=1;
 endtask
 task automatic clean_check(input int expect_blocks,input string tag);
  int mism;int u;int k;
  mism=0;
  for(u=0;u<2;u++)begin
   foreach(gold[a])if(!seen[u].exists(a))mism++;
   if(corrupt[u]!=0||dup[u]!=0||mism!=0||w[u]!=gold.num())begin bad_clean=bad_clean+1;if(bad_clean<=5)$display("CLEAN-BAD %s case %0d dut %0d w %0d gold %0d corrupt %0d dup %0d missing %0d",tag,c,u,w[u],gold.num(),corrupt[u],dup[u],mism);end
   mism=0;
  end
  if(f[0]!==1'b0||f[1]!==1'b0||sst[0]!==1'b0||sst[1]!==1'b0||hst[0]!==1'b0||hst[1]!==1'b0)begin bad_hold=bad_hold+1;if(bad_hold<=5)$display("CLEAN-FAULT %s case %0d f %b %b",tag,c,f[0],f[1]);end
  if(sbad!=0||rdybad!=0)begin bad_stream=bad_stream+1;if(bad_stream<=5)$display("STREAM-BAD %s case %0d n %0d",tag,c,sbad);end
  if(nd[0]!=expect_blocks||nd[1]!=expect_blocks)begin bad_done=bad_done+1;if(bad_done<=5)$display("DONE-BAD %s case %0d nd %0d %0d want %0d",tag,c,nd[0],nd[1],expect_blocks);end
  begin int wb=0;for(k=0;k<nd[0]&&k<nd[1];k++)if(wv[0][k]!=wv[1][k])wb++;if(wb!=0)bad_wv=bad_wv+1;end
  for(u=0;u<2;u++)for(k=0;k<16;k++)if(outst(u,k)!=0||q[u][k]!=0)begin bad_out=bad_out+1;if(bad_out<=5)$display("OUTSTANDING-BAD %s case %0d dut %0d pc %0d sw %0d partner %0d",tag,c,u,k,outst(u,k),q[u][k]);end
  for(k=0;k<nd[0]&&k<nd[1];k++)begin longint lg;lg=longint'(done_t[1][k])-longint'(done_t[0][k]);lag_sum+=lg;lag_n++;if(lg>lag_max)lag_max=int'(lg);if(lg<lag_min)lag_min=int'(lg);end
  for(u=0;u<2;u++)for(k=0;k<nd[u]&&k<cstart_t[u].size();k++)begin dur_sum[u]+=longint'(done_t[u][k])-longint'(cstart_t[u][k]);dur_n[u]++;end
  agg_w0+=w[0];agg_w1+=w[1];
 endtask
 initial begin
  for(int u=0;u<2;u++)begin max_ev_cyc[u]=0;max_ev_g[u]=0;max_after[u]=0;max_gvpost[u]=0;dur_sum[u]=0;dur_n[u]=0;end
  for(int k=0;k<4;k++)begin n_ft[k]=0;n_ftdet[k]=0;end
  for(int u=0;u<2;u++)for(int p=0;p<16;p++)q[u][p]=0;
  for(int u=0;u<2;u++)begin rdy[u]=0;dn[u]=0;end
  #(5*TF);
  for(c=0;c<NCASE;c++)begin
   clear_case();timeout=0;
   do_reset();
   if(MODE==0)begin
    nblk=NB;
    for(n=0;n<nblk;n++)begin
     tt=(n<14&&c%3==0)?tots[n]:(1+$urandom%MAXTOT);
     want=n-1;if(want>0)wait_done(want,0);
     do_block(n[0],16'(n+1),29'(($urandom%100000)*2048+((tt>=128&&$urandom%4==0)?($urandom%2048):0)),12'(tt));
     if($urandom%3==0)repeat($urandom%300)@(posedge fc);
    end
    wait_done(nblk,0);
    repeat(60)@(posedge fc);repeat(60)@(posedge hc);
    clean_check(nblk,"clean");
    agg_cases++;
   end else begin
    // fault sweep: 3 chained blocks, one fault at a random fifo_clk time inside the expected busy window
    ftype=1+$urandom%3;nblk=3;
    begin int sumt;sumt=0;for(n=0;n<nblk;n++)begin ptot[n]=8+$urandom%MAXTOT;sumt+=ptot[n];end
     cyc_inj=$urandom%(60*nblk+sumt/3);end
    fork
     begin
      for(n=0;n<nblk&&!fault_seen;n++)begin
       want=n-1;if(want>0)wait_done(want,1);
       if(!fault_seen)do_block(n[0],16'(n+1),29'(($urandom%100000)*2048),12'(ptot[n]));
       if($urandom%3==0)repeat($urandom%100)@(posedge fc);
      end
     end
     begin
      while(fcyc<cyc_inj)@(posedge fc);
      if(ftype==1)begin @(posedge fc);inj_rv<=1;inj_rb<=$urandom;inj_rt<=0;@(posedge fc);inj_rv<=0;inj_done=1;end
      if(ftype==3)begin inj_dn_ok=0;inj_dn_req=1;begin int t;t=0;while(!inj_dn_ok&&t<400)begin @(posedge fc);t++;end end inj_done=inj_dn_ok;end
     end
    join
    if(ftype==2)begin int t;t=0;while(!f2_done&&!fault_seen&&t<200)begin @(posedge fc);t++;end end
    inj_done=(ftype==2)?f2_done:inj_done;
    if(inj_done)n_ft[ftype]++;
    wait_done(nblk,1);
    repeat(300)@(posedge fc);repeat(300)@(posedge hc);
    // verdicts for this case
    agg_cases++;
    for(int u=0;u<2;u++)begin
     if(corrupt[u]!=0||dup[u]!=0)begin bad_integrity=bad_integrity+1;if(bad_integrity<=5)$display("INTEGRITY-BAD case %0d dut %0d corrupt %0d dup %0d ft %0d",c,u,corrupt[u],dup[u],ftype);end
     if(ev_cyc[u]>max_ev_cyc[u])max_ev_cyc[u]=ev_cyc[u];
     if(ev_gmax[u]>max_ev_g[u])max_ev_g[u]=ev_gmax[u];
     if(afterh[u]>max_after[u])max_after[u]=afterh[u];
     if(gvpost[u]>max_gvpost[u])max_gvpost[u]=gvpost[u];
    end
    begin int lim;lim=(u_sst_lim());
     if(ev_cyc[0]!=0)begin bad_postcyc=bad_postcyc+1;end
     if(ev_cyc[1]>lim)begin bad_postcyc=bad_postcyc+1;if(bad_postcyc<=5)$display("POST-STOP-BAD case %0d ft %0d new cyc %0d fw %0d fe %0d mr %0d gmax %0d",c,ftype,ev_cyc[1],ev_fw[1],ev_fe[1],ev_mr[1],ev_gmax[1]);end
     if(ev_gmax[1]>12*lim)bad_postwords=bad_postwords+1;
    end
    if(afterh[1]>32||afterh[0]>32)begin bad_hpost=bad_hpost+1;end
    if(inj_done&&!fault_seen)begin bad_inj=bad_inj+1;if(bad_inj<=5)$display("INJECT-NOT-DETECTED case %0d ft %0d",c,ftype);end
    if(fault_seen)begin
     if(inj_done)n_ftdet[ftype]++;
     if((f[0]===1'b1)&&(f[1]===1'b1))begin
      int dl;dl=(ft_f[0]>ft_f[1])?ft_f[0]-ft_f[1]:ft_f[1]-ft_f[0];
      if(dl>max_fdelta)max_fdelta=dl;
      if(dl>fdl_max[ftype])fdl_max[ftype]=dl;fdl_hist[ftype][(dl==0)?0:(dl<=2)?1:(dl<=20)?2:3]++;
      if(dl>2&&!(ftype==3&&(!arr_clean[0]||!arr_clean[1])))begin n_fdiff=n_fdiff+1;bad_nofault=bad_nofault+1;if(bad_nofault<=5)$display("FAULT-DELTA-BAD case %0d ft %0d delta %0d",c,ftype,dl);end
     end else
     if(ftype==3&&(f[0]===1'b1)!=(f[1]===1'b1))begin
      // a spurious write-done is indistinguishable from a real one while a write is in flight on that PC; the two forms have different
      // in-flight timing (GREG +1), so one may absorb it. Accepted if the absorbing form shows no corrupt or duplicate K write (the run is cut at the other form's fault, so blocks may be unfinished).
      int ab;ab=(f[0]===1'b1)?1:0;
      begin n_absorb++;if(arr_clean[0]&&arr_clean[1]||!arr[0]||!arr[1])begin n_f3abs_unraised++;bad_nofault=bad_nofault+1;end else n_unclean_abs++;end if(corrupt[ab]!=0||dup[ab]!=0)begin bad_nofault=bad_nofault+1;$display("ABSORB-BAD case %0d corrupt %0d dup %0d",c,corrupt[ab],dup[ab]);end
     end else
     if(f[0]!==1'b1||f[1]!==1'b1)begin bad_nofault=bad_nofault+1;if(bad_nofault<=5)$display("FAULT-NOT-HELD case %0d ft %0d f %b %b sst %b %b hst %b %b",c,ftype,f[0],f[1],sst[0],sst[1],hst[0],hst[1]);end
    end
    w[0]=w[0];
    dw_min=(w[1]-w[0]<dw_min)?w[1]-w[0]:dw_min;dw_max=(w[1]-w[0]>dw_max)?w[1]-w[0]:dw_max;
    agg_w0+=w[0];agg_w1+=w[1];
    // recovery: reset, one clean block of random size on the same bank sequence
    clear_case();ftype=0;cyc_inj=-1;
    do_reset();
    tt=1+$urandom%200;
    do_block(1,16'd77,29'(($urandom%100000)*2048),12'(tt));
    wait_done(1,0);repeat(60)@(posedge fc);repeat(60)@(posedge hc);
    begin int bc;bc=bad_clean;clean_check(1,"recovery");if(bad_clean!=bc)bad_recov=bad_recov+1;end
   end
   if(timeout)begin bad_done=bad_done+1;$display("TIMEOUT case %0d",c);end
  end
  $display("QUAL cfg TF=%0d TH=%0d PH=%0d MODE=%0d NCASE=%0d SLOW=%0d QUAD=%0d HREG=%0d GIN=%0d CBREG=%0d SSTOPREG=%0d GREG=%0d MUTCB=%0d MUTSTOP=%0d",TF,TH,PH,MODE,NCASE,SLOW,QUAD,HREG,GIN,CBREG,SSTOPREG,GREG,MUTCB,MUTSTOP);
  $display("QUAL back-to-back copy starts (<=3 fifo_clk after the previous copy_on fell): old %0d new %0d",b2b[0],b2b[1]);
  $display("QUAL cases %0d writes old %0d new %0d done-lag(new-old, ps) min %0d max %0d mean %0d copy-dur mean old %0d new %0d (ps) dwrites(new-old) min %0d max %0d",
   agg_cases,agg_w0,agg_w1,(lag_n>0)?lag_min:0,(lag_n>0)?lag_max:0,(lag_n>0)?int'(lag_sum/lag_n):0,(dur_n[0]>0)?int'(dur_sum[0]/dur_n[0]):0,(dur_n[1]>0)?int'(dur_sum[1]/dur_n[1]):0,(MODE==1)?dw_min:0,(MODE==1)?dw_max:0);
  if(MODE==1)begin
   for(int a=1;a<4;a++)$display("QUAL first-raise delta F%0d (both forms raised): 0: %0d, 1-2: %0d, 3-20: %0d, >20: %0d, max %0d fifo_clk",a,fdl_hist[a][0],fdl_hist[a][1],fdl_hist[a][2],fdl_hist[a][3],fdl_max[a]);
   $display("QUAL RULING(2): fault raised by both forms, max first-raise delta %0d fifo_clk (limit 2), delta>2 cases %0d; F3 cases where one form never raised %0d",max_fdelta,n_fdiff,n_f3abs_unraised);
   $display("QUAL RULE(a) spurious done, nothing outstanding: arrivals clean old %0d new %0d, violations (no h_stop within 2 hbm_clk) old %0d new %0d; arrivals with a write outstanding (inherently indistinguishable, exempt) %0d %0d; unclean absorbs %0d",n_a_clean[0],n_a_clean[1],n_a_viol[0],n_a_viol[1],n_a_unclean[0],n_a_unclean[1],n_unclean_abs);
   $display("QUAL F3 spurious done absorbed by one form only (no corrupt/dup write): %0d",n_absorb);
   $display("QUAL fault types injected F1 %0d F2 %0d F3 %0d, fault raised F1 %0d F2 %0d F3 %0d",n_ft[1],n_ft[2],n_ft[3],n_ftdet[1],n_ftdet[2],n_ftdet[3]);
   $display("QUAL post-stop root activity: max cycles old %0d new %0d, max lane-events per group old %0d new %0d; seam valids after h_stop max old %0d new %0d; K writes after h_stop max old %0d new %0d",
    max_ev_cyc[0],max_ev_cyc[1],max_ev_g[0],max_ev_g[1],max_gvpost[0],max_gvpost[1],max_after[0],max_after[1]);
  end
  $display("QUAL bad: integrity %0d fault-not-held %0d post-stop-cycles %0d post-stop-words %0d k-after-hstop %0d recovery %0d inj-undetected %0d clean %0d stream %0d wa-seq %0d outstanding %0d done/timeout %0d fault-in-clean %0d",
   bad_integrity,bad_nofault,bad_postcyc,bad_postwords,bad_hpost,bad_recov,bad_inj,bad_clean,bad_stream,bad_wv,bad_out,bad_done,bad_hold);
  if(n_a_viol[0]+n_a_viol[1]!=0)bad_nofault=bad_nofault+n_a_viol[0]+n_a_viol[1];
  if(bad_integrity+bad_nofault+bad_postcyc+bad_postwords+bad_hpost+bad_recov+bad_inj+bad_clean+bad_stream+bad_wv+bad_out+bad_done+bad_hold==0)begin $display("QUAL PASS");$finish;end
  else begin $display("QUAL FAIL");$fatal(1,"QUAL FAIL");end
 end
 function automatic int u_sst_lim();u_sst_lim=(SSTOPREG!=0&&MUTSTOP==0)?1:0;endfunction
endmodule
`default_nettype wire
