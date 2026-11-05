`timescale 1ns/1ps
`default_nettype none
// HBM-REFORM-B4 part 25: flat kport_q (kit face shell model) against the split composition (tile face shells), one clock, one random stimulus.
// Must hold: same set of K writes (sector -> data, each once, on the right PC); wbw_* edge for edge; wb_ready rises on the same edge; same wa
// values in order; no fault. Done lag is reported. K side: a registered partner, rdy seen by the skid 1 edge later, v at the pin 1 edge later.
module tb_wbq;
 parameter integer MUT=0,RMUT=0,SLOW=0,QUAD=0,NB=48;
 reg c=0;reg rst=0;always #5 c=~c;
 reg rv=0,rb=0,fb=0,fs=0;reg[15:0]re=0,fe=0;reg[11:0]rt=0;reg[31:0]rbase=0;reg[2311:0]wd=0;
 wire[15:0]v[0:1];wire[479:0]a[0:1];wire[4095:0]d[0:1];reg[15:0]rdy[0:1];reg[15:0]rdy1[0:1];reg[15:0]rdy2[0:1];reg[15:0]dn[0:1];
 wire rd[0:1];wire bv[0:1];wire f[0:1];wire[11:0]wa[0:1];wire[29:0]bb[0:1];wire[11:0]bt[0:1];
 ot_hbm_svc_wb_kport_q__fs u_ref(.stream_clk(c),.stream_rst_n(rst),.hbm_clk(c),.hbm_rst_n(rst),.stream_fifo_clk({4{c}}),.stk(2'd0),.quad(QUAD[0]),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),.wb_reserve_base(rbase),
  .wb_fill_start(fs),.wd(wd),.wb_ready(rd[0]),.wa(wa[0]),.wbw_v(bv[0]),.wbw_base(bb[0]),.wbw_total(bt[0]),.w_k_v(v[0]),.w_k_rdy(rdy[0]),.w_k_addr(a[0]),.w_k_wdata(d[0]),.w_k_wr_done(dn[0]),.fault(f[0]));
 ot_hbm_svc_wb_kport_q__p25fs #(.MUT(MUT),.RMUT(RMUT)) u_new(.stream_clk(c),.stream_rst_n(rst),.hbm_clk(c),.hbm_rst_n(rst),.stream_fifo_clk({4{c}}),.stk(2'd0),.quad(QUAD[0]),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),.wb_reserve_base(rbase),
  .wb_fill_start(fs),.wd(wd),.wb_ready(rd[1]),.wa(wa[1]),.wbw_v(bv[1]),.wbw_base(bb[1]),.wbw_total(bt[1]),.w_k_v(v[1]),.w_k_rdy(rdy[1]),.w_k_addr(a[1]),.w_k_wdata(d[1]),.w_k_wr_done(dn[1]),.fault(f[1]));
 // first fault report
 reg f0q=0,f1q=0;
 always @(posedge c)begin if(f[0]===1'b1&&!f0q)begin f0q<=1;$display("FAULT ref t=%0d",cyc);end if(f[1]===1'b1&&!f1q)begin f1q<=1;$display("FAULT new t=%0d",cyc);end end
 // scoreboard + K model
 bit [255:0] m[0:1][longint];int dup[0:1];int w[0:1];int badpc[0:1];int q[0:1][0:15];
 longint cyc=0;longint done_t[0:1][$];int wv[0:1][$];int nd[0:1];
 int sbad=0,fsbad=0;  // fsbad: wb_ready differs, or is low, on the edge the fill starts (it may fall later on the new form, done is later)
int p,u;longint ad,ad6;
 always @(posedge c)begin
  cyc<=cyc+1;
  if(fs&&(rd[0]!==1'b1||rd[1]!==1'b1))fsbad=fsbad+1;
  if(bv[0]!==bv[1]||(bv[0]&&(bb[0]!==bb[1]||bt[0]!==bt[1])))sbad=sbad+1;
  for(u=0;u<2;u=u+1)begin
   if(wa[u]!=0&&wa[u]!==12'bx)begin done_t[u].push_back(cyc);wv[u].push_back(int'(wa[u]));nd[u]=nd[u]+1;end
   for(p=0;p<16;p=p+1)begin
    if(v[u][p]===1'b1&&rdy2[u][p])begin
     ad=longint'(a[u][30*p+:30]);
     if(m[u].exists(ad))dup[u]=dup[u]+1;
     m[u][ad]=d[u][256*p+:256];w[u]=w[u]+1;q[u][p]=q[u][p]+1;
     ad6=((ad>>7)<<6)|(ad&63);   // K address has the quadrant fold bit inserted at bit 6
     if(((ad6>>2)^(ad6>>6)^(ad6>>11))%16!=p||(((ad>>6)^(ad6>>10)^(ad6>>15)^QUAD)&1)!=0)badpc[u]=badpc[u]+1;
    end
   end
   dn[u]<=0;
   for(p=0;p<16;p=p+1)if(q[u][p]>0&&$urandom%((SLOW!=0)?16:4)==0)begin dn[u][p]<=1;q[u][p]=q[u][p]-1;end
   rdy2[u]<=rdy1[u];rdy1[u]<=rdy[u];
   rdy[u]<=(SLOW!=0)?($urandom&$urandom&$urandom&$urandom):($urandom|$urandom);
  end
 end
 task automatic fill(input bit b,input [15:0]e,input [28:0]base,input [11:0]tot);
  integer o,k;
  begin
   @(negedge c);rv=1;rb=b;re=e;rt=tot;rbase={3'b0,base};@(negedge c);rv=0;
   repeat(2)@(negedge c);
   fb=b;fe=e;repeat(5)@(negedge c);fs=1;@(negedge c);fs=0;
   for(o=0;o<tot;o=o+8)begin
    wd=0;
    for(k=0;k<8;k=k+1)if(o+k<tot)begin
     wd[289*k+:256]={8{$urandom}};
     wd[289*k+256+:32]={3'b0,base}+o+k;
     wd[289*k+288]=1;
    end
    @(negedge c);
   end
   wd=0;
  end
 endtask
 int tots[0:13]='{1,7,8,9,31,32,33,63,64,256,640,1024,1984,77};
 int n,tt,tot_sect=0,sent[0:1];int want;
 initial begin
  for(u=0;u<2;u=u+1)begin rdy[u]=0;rdy1[u]=0;rdy2[u]=0;dn[u]=0;dup[u]=0;w[u]=0;badpc[u]=0;nd[u]=0;for(p=0;p<16;p=p+1)q[u][p]=0;end
  sent[0]=0;sent[1]=0;
  repeat(10)@(negedge c);rst=1;repeat(40)@(negedge c);
  for(n=0;n<NB;n=n+1)begin
   tt=(n<14)?tots[n]:(1+$urandom%1984);
   tot_sect=tot_sect+tt;
   // a bank is free once both blocks reported done for it: at most one block outstanding per bank
   want=n-1;
   wait(nd[0]>=want&&nd[1]>=want);
   fill(n[0],16'(n+1),29'(($urandom%100000)*2048+((tt>=128&&$urandom%4==0)?($urandom%2048):0)),12'(tt));   // unaligned only for long blocks: a short one whose ends fold apart has negative span, which the flat block faults
   if($urandom%3==0)repeat($urandom%400)@(negedge c);
  end
  fork begin wait(nd[0]>=NB&&nd[1]>=NB);end begin repeat(NB*8000)@(negedge c);end join_any
  repeat(40)@(negedge c);
  begin
   int mism=0,only=0,lag_max=-99999,lag_sum=0,wvbad=0,riseb=0,lag;
   foreach(m[0][k])begin if(!m[1].exists(k))only++;else if(m[1][k]!==m[0][k])mism++;end
   foreach(m[1][k])if(!m[0].exists(k))only++;
   for(int i=0;i<nd[0]&&i<nd[1];i++)begin lag=int'(done_t[1][i]-done_t[0][i]);if(lag>lag_max)lag_max=lag;lag_sum+=lag;if(wv[0][i]!=wv[1][i])wvbad++;end
   riseb=fsbad;
   $display("WBQ sectors %0d writes ref %0d new %0d dup %0d %0d badpc %0d %0d mism %0d only %0d stream_bad %0d wv_bad %0d ready_bad %0d done %0d %0d lag max %0d mean %0d fault %b %b",
    tot_sect,w[0],w[1],dup[0],dup[1],badpc[0],badpc[1],mism,only,sbad,wvbad,riseb,nd[0],nd[1],lag_max,(nd[1]>0)?lag_sum/nd[1]:0,f[0],f[1]);
   if(w[0]==tot_sect&&w[1]==tot_sect&&badpc[0]==0&&badpc[1]==0&&mism==0&&only==0&&sbad==0&&wvbad==0&&riseb==0&&nd[0]==NB&&nd[1]==NB&&f[0]===1'b0&&f[1]===1'b0)begin $display("WBQ PASS");$finish;end
   else begin $display("WBQ FAIL");$fatal(1,"FAIL");end
  end
 end
endmodule
`default_nettype wire
