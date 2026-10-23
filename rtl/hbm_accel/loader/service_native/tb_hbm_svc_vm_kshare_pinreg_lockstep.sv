`timescale 1ps/1ps
`default_nettype none
// STEWARD-HBMd/PINREG-KS 2026-10-23 (kshare r6): PINREG=0 (r5a) vs PINREG=1 (every data/valid input in one pin flop)
// side by side.  Each DUT has its own environment (ks_pr_env) driven by IDENTICAL stimulus: the same per-edge random
// stream (xorshift64, same seed, advanced every hbm / stream edge) for every back-pressure / send / gap decision, and the
// same transaction sequences (group reads + writes, VM windows, WB windows with their exact WB write lists).  Senders obey
// the K valid/ready rule (hold until v && rdy at one edge); the controller model answers reads IN ORDER (data = f(addr,
// beat)) and signals k_wr_done in order, so every per-class transaction stream is order-deterministic.
// Compared per lane, in order, DUT0 vs DUT1: c_k transfers (group / VM / WB classes), g_kr transfers, fills, g_k_wr_done
// and w_k_wr_done counts, fault.  Recorded: the minimum (= pipeline) latency of each path per DUT and the PINREG offset,
// and the streaming rate (group writes, all ready high) per DUT.  Params: KRL1, MUT1 (MUT of the PINREG=1 DUT; 9 = A/E
// ring depth 2 -> expect FAIL), GN (group requests per lane), NWIN (windows).  Exit: "PASS ..." else "FAIL ...".
module ks_pr_env #(parameter integer PINREG=0,KRL1=1,MUT=0,SM=3,GN=600,NWIN=9,NSTREAM=160,SEED=64'h9e3779b97f4a7c15)(
 input wire hbm_clk,stream_clk,hbm_rst_n,stream_rst_n,output reg done,output wire fault
);
 localparam integer KW=1+30+4+17+32+256, RW=17+4+256, FW=1+16+6+256;
 reg[3:0]g_k_v,g_k_we,g_kr_rdy,c_k_rdy,c_kr_v,c_k_wr_done,w_k_v;
 reg[119:0]g_k_addr,w_k_addr;reg[15:0]g_k_len,c_kr_beat;reg[67:0]g_k_tag,c_kr_tag;reg[1023:0]g_k_wdata,c_kr_data,w_k_wdata;
 reg[127:0]g_k_wstrb;
 wire[3:0]g_k_rdy,g_k_wr_done,g_kr_v,c_k_v,c_k_we,c_kr_rdy,w_k_rdy,w_k_wr_done,fill_v,fill_bank;
 wire[67:0]g_kr_tag,c_k_tag;wire[15:0]g_kr_beat,c_k_len;wire[1023:0]g_kr_data,c_k_wdata,fill_data;wire[119:0]c_k_addr;
 wire[127:0]c_k_wstrb;wire[23:0]fill_slot;wire[63:0]fill_epoch;
 reg vm_v,vm_bank;reg[15:0]vm_epoch;reg[14:0]vm_row;reg[3:0]vm_col;reg wbw_v;reg[29:0]wbw_base;reg[11:0]wbw_total;
 ot_hbm_svc_vm_kshare_splitstrap #(.MUT(MUT),.KRL1(KRL1),.PINREG(PINREG)) dut(.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.sm_stream(3'(SM)),.sm_hbm(3'(SM)),
  .g_k_v(g_k_v),.g_k_rdy(g_k_rdy),.g_k_addr(g_k_addr),.g_k_len(g_k_len),.g_k_tag(g_k_tag),.g_k_we(g_k_we),.g_k_wdata(g_k_wdata),
  .g_k_wstrb(g_k_wstrb),.g_k_wr_done(g_k_wr_done),.g_kr_v(g_kr_v),.g_kr_rdy(g_kr_rdy),.g_kr_tag(g_kr_tag),.g_kr_beat(g_kr_beat),
  .g_kr_data(g_kr_data),.c_k_v(c_k_v),.c_k_rdy(c_k_rdy),.c_k_addr(c_k_addr),.c_k_len(c_k_len),.c_k_tag(c_k_tag),.c_k_we(c_k_we),
  .c_k_wdata(c_k_wdata),.c_k_wstrb(c_k_wstrb),.c_k_wr_done(c_k_wr_done),.c_kr_v(c_kr_v),.c_kr_rdy(c_kr_rdy),.c_kr_tag(c_kr_tag),
  .c_kr_beat(c_kr_beat),.c_kr_data(c_kr_data),.vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),
  .wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),.w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata),
  .w_k_wr_done(w_k_wr_done),.fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),
  .fill_data(fill_data),.fault(fault));
 function automatic [63:0] mix(input [63:0] x);
  reg[63:0]z;begin z=x+64'h9e3779b97f4a7c15;z=(z^(z>>30))*64'hbf58476d1ce4e5b9;z=(z^(z>>27))*64'h94d049bb133111eb;mix=z^(z>>31);end
 endfunction
 function automatic [255:0] f(input [29:0] a,input [3:0] b);
  reg[255:0]r;integer i;begin for(i=0;i<4;i=i+1)r[64*i+:64]=mix({30'(a),4'(b),30'(i)});f=r;end
 endfunction
 function automatic [4:0] hsh(input [29:0] a);hsh=a[6:2]^a[11:7]^a[16:12];endfunction
 // group request i of lane l: requests < NSTREAM are single-beat writes (streaming phase), then 1/3 writes, 2/3 reads
 function automatic [KW-1:0] greq(input integer l,input integer i);
  reg[63:0]h;reg we;reg[29:0]a;reg[3:0]ln;reg[1:0]lo;reg[16:0]t;reg[31:0]st;reg[255:0]wd;
  begin
   h=mix({32'(l),32'(i)}^SEED);we=(i<NSTREAM)||(h[63:62]==2'd0);
   ln=we?4'd1:4'(1+h[61:60]);lo=2'(h[59:58]%(5-ln));
   a=30'(h[29:0]);a[1:0]=lo;a[6:2]=5'(4*SM+l)^a[11:7]^a[16:12];
   t={1'b1,1'b1,15'(i)};st=we?32'(h[57:26]|32'h1):32'd0;wd=we?f(a,4'(i)):256'd0;
   greq={we,a,ln,t,st,wd};
  end
 endfunction
 // ---------------------------------------------------------------- per-edge identical random streams
 reg[63:0]lf,ls;integer cyc;
 always @(posedge hbm_clk)begin lf<=hbm_rst_n?mix(lf):SEED;cyc<=hbm_rst_n?cyc+1:0;end
 always @(posedge stream_clk)ls<=stream_rst_n?mix(ls):~SEED;
 wire stream_ph=gi_min<NSTREAM;                 // streaming phase: every sender / ready high
 integer gi[0:3],gi_min,g_first[0:3],g_lastst[0:3];
 always @*begin gi_min=gi[0];if(gi[1]<gi_min)gi_min=gi[1];if(gi[2]<gi_min)gi_min=gi[2];if(gi[3]<gi_min)gi_min=gi[3];end
 // ---------------------------------------------------------------- records (per lane, in order)
 typedef logic[KW-1:0] kw_t;typedef logic[RW-1:0] rw_t;typedef logic[FW-1:0] fw_t;
 kw_t ck_grp[4][$],ck_vm[4][$],ck_wb[4][$];rw_t gkr[4][$];fw_t fil[4][$];
 integer t_gk[4][$],t_ckg[4][$],t_wk[4][$],t_ckw[4][$],t_ckrg[4][$],t_gkr[4][$],t_cwdg[4][$],t_gwd[4][$];
 longint t_ckrv[4][$],t_fil[4][$];
 integer n_gwd[0:3],n_wwd[0:3],n_gwr[0:3],n_grbeats[0:3],n_gkr[0:3],n_fill[0:3];
 // ---------------------------------------------------------------- WB write lists (filled by the window process)
 reg[29:0]wbq[4][$];integer wb_exp[0:3],vm_exp[0:3];reg[15:0]cur_epoch;
 // ---------------------------------------------------------------- group senders + responses
 always @(posedge hbm_clk)if(hbm_rst_n)begin:grp
  integer l;reg[KW-1:0]q;
  for(l=0;l<4;l=l+1)begin
   if(g_k_v[l]&&g_k_rdy[l])begin
    t_gk[l].push_back(cyc);if(gi[l]==0)g_first[l]=cyc;if(gi[l]==NSTREAM-1)g_lastst[l]=cyc;
    if(g_k_we[l])n_gwr[l]=n_gwr[l]+1;else n_grbeats[l]=n_grbeats[l]+g_k_len[4*l+:4];
    gi[l]=gi[l]+1;g_k_v[l]<=0;
   end
   if(!(g_k_v[l]&&!g_k_rdy[l])&&gi[l]<GN&&(stream_ph||lf[2*l+:2]==2'd0))begin
    q=greq(l,gi[l]);
    g_k_v[l]<=1;{g_k_we[l],g_k_addr[30*l+:30],g_k_len[4*l+:4],g_k_tag[17*l+:17],g_k_wstrb[32*l+:32],g_k_wdata[256*l+:256]}<=q;
   end
   g_kr_rdy[l]<=stream_ph||lf[8+2*l+:2]!=2'd0;
   if(g_kr_v[l]&&g_kr_rdy[l])begin
    gkr[l].push_back({g_kr_tag[17*l+:17],g_kr_beat[4*l+:4],g_kr_data[256*l+:256]});t_gkr[l].push_back(cyc);n_gkr[l]=n_gkr[l]+1;
   end
   if(g_k_wr_done[l])begin n_gwd[l]=n_gwd[l]+1;t_gwd[l].push_back(cyc);end
   if(w_k_wr_done[l])n_wwd[l]=n_wwd[l]+1;
  end
 end
 // ---------------------------------------------------------------- WB senders
 always @(posedge hbm_clk)if(hbm_rst_n)begin:wbs
  integer l;reg[29:0]a;
  for(l=0;l<4;l=l+1)begin
   if(w_k_v[l]&&w_k_rdy[l])begin t_wk[l].push_back(cyc);void'(wbq[l].pop_front());w_k_v[l]<=0;end
   // a transfer above popped the head (blocking), so wbq[0] is always the next write to offer
   if(!(w_k_v[l]&&!w_k_rdy[l])&&wbq[l].size()>0&&lf[16+2*l+:2]!=2'd3)begin
    a=wbq[l][0];
    w_k_v[l]<=1;w_k_addr[30*l+:30]<=a;w_k_wdata[256*l+:256]<=f(a,4'hb);
   end
  end
 end
 // ---------------------------------------------------------------- controller models (in order)
 reg[29:0]rqa[4][$];reg[3:0]rql[4][$];reg[16:0]rqt[4][$];reg rqc[4][$];   // reads: addr, len, tag, class (1 = group)
 reg wqc[4][$];                                                           // writes in order: class (1 = group)
 integer rbeat[0:3];reg[3:0]rdy_seen;
 wire[3:0]c_acc=(KRL1!=0)?rdy_seen:c_kr_rdy;
 always @(posedge hbm_clk)rdy_seen<=hbm_rst_n?c_kr_rdy:4'b0;
 always @(posedge hbm_clk)if(hbm_rst_n)begin:ctl
  integer l;reg[KW-1:0]q;reg grp;
  for(l=0;l<4;l=l+1)begin
   if(c_kr_v[l]&&c_acc[l])begin
    if(rqc[l][0])t_ckrg[l].push_back(cyc);else t_ckrv[l].push_back($time);
    rbeat[l]=rbeat[l]+1;
    if(rbeat[l]==rql[l][0])begin rbeat[l]=0;void'(rqa[l].pop_front());void'(rql[l].pop_front());void'(rqt[l].pop_front());void'(rqc[l].pop_front());end
    c_kr_v[l]<=0;
   end
   if(c_k_v[l]&&c_k_rdy[l])begin
    q={c_k_we[l],c_k_addr[30*l+:30],c_k_len[4*l+:4],c_k_tag[17*l+:17],c_k_wstrb[32*l+:32],c_k_wdata[256*l+:256]};
    grp=c_k_tag[17*l+16]&&c_k_tag[17*l+8+:8]!=8'd0;   // group tags {1,1,i}; VM tags bank 0; WB tags {1,8'd0,n}
    if(!c_k_tag[17*l+16])ck_vm[l].push_back(q);else if(grp)begin ck_grp[l].push_back(q);t_ckg[l].push_back(cyc);end
    else begin ck_wb[l].push_back(q);t_ckw[l].push_back(cyc);end
    if(c_k_we[l])wqc[l].push_back(grp);
    else begin rqa[l].push_back(c_k_addr[30*l+:30]);rql[l].push_back(c_k_len[4*l+:4]);rqt[l].push_back(c_k_tag[17*l+:17]);rqc[l].push_back(grp);end
   end
   c_k_rdy[l]<=(stream_ph||lf[24+2*l+:2]!=2'd0)&&rqa[l].size()<16&&wqc[l].size()<24;
   // in-order write completions, at most one per edge
   c_k_wr_done[l]<=0;
   if(wqc[l].size()>0&&(stream_ph||lf[32+l]))begin
    c_k_wr_done[l]<=1;if(wqc[l][0])t_cwdg[l].push_back(cyc+1);void'(wqc[l].pop_front());
   end
   // present the next beat of the head read (in order), random gaps
   if(!(c_kr_v[l]&&!c_acc[l])&&rqa[l].size()>0&&(stream_ph||lf[40+2*l+:2]!=2'd0))begin
    c_kr_v[l]<=1;c_kr_tag[17*l+:17]<=rqt[l][0];c_kr_beat[4*l+:4]<=4'(rbeat[l]);
    c_kr_data[256*l+:256]<=f(rqa[l][0]+30'(rbeat[l]),4'(rbeat[l]));
   end
  end
 end
 // the head read may have just been popped (blocking) in the same edge: the presenter above reads the new head, and a
 // transferred beat leaves rbeat pointing at the next beat, so the beat sequence is in order either way.
 always @(posedge stream_clk)if(stream_rst_n)begin:fl
  integer l;
  for(l=0;l<4;l=l+1)if(fill_v[l])begin
   fil[l].push_back({fill_bank[l],fill_epoch[16*l+:16],fill_slot[6*l+:6],fill_data[256*l+:256]});t_fil[l].push_back($time);
   n_fill[l]=n_fill[l]+1;
  end
 end
 // ---------------------------------------------------------------- windows (stream side), then drain
 integer w,l,t,s,ok;reg[29:0]b;reg[11:0]tot;reg[63:0]h;
 initial begin
  done=0;g_k_v=0;g_k_we=0;g_k_addr=0;g_k_len=0;g_k_tag=0;g_k_wdata=0;g_k_wstrb=0;g_kr_rdy=0;c_k_rdy=0;c_kr_v=0;c_kr_tag=0;
  c_kr_beat=0;c_kr_data=0;c_k_wr_done=0;w_k_v=0;w_k_addr=0;w_k_wdata=0;rdy_seen=0;
  vm_v=0;vm_bank=0;vm_epoch=0;vm_row=0;vm_col=0;wbw_v=0;wbw_base=0;wbw_total=0;cyc=0;lf=SEED;ls=~SEED;
  for(l=0;l<4;l=l+1)begin gi[l]=0;n_gwd[l]=0;n_wwd[l]=0;n_gwr[l]=0;n_grbeats[l]=0;n_gkr[l]=0;n_fill[l]=0;rbeat[l]=0;
   wb_exp[l]=0;vm_exp[l]=0;g_first[l]=0;g_lastst[l]=0;end
  @(posedge stream_rst_n);
  t=0;while(stream_ph&&t<100000)begin @(posedge stream_clk);t=t+1;end
  for(w=0;w<NWIN;w=w+1)begin
   repeat(20+ls[7:0])@(posedge stream_clk);
   @(negedge stream_clk);
   h=mix(64'(w)^SEED);
   if(w%3!=1)begin   // VM window (w%3==2: VM and WB on consecutive stream edges, VM has priority)
    vm_v=1;vm_bank=0;vm_epoch=16'h200+16'(w);vm_row=15'(h[14:0]);vm_col=4'(h[18:15]);
    for(l=0;l<4;l=l+1)vm_exp[l]=vm_exp[l]+64;
    @(negedge stream_clk);vm_v=0;
   end
   if(w%3!=0)begin   // WB window: exact per-lane write list (sectors of [base, base+total) with hash 4*SM+l, ascending)
    b=30'(h[49:30]);tot=12'(1+h[59:52]+h[61:60]*12'd256);
    for(s=0;s<tot;s=s+1)if(hsh(b+30'(s))>=5'(4*SM)&&hsh(b+30'(s))<5'(4*SM+4))begin
     wbq[hsh(b+30'(s))-5'(4*SM)].push_back(b+30'(s));wb_exp[hsh(b+30'(s))-5'(4*SM)]+=1;
    end
    wbw_v=1;wbw_base=b;wbw_total=tot;
    @(negedge stream_clk);wbw_v=0;
   end
   t=0;ok=0;
   while(!ok&&t<400000)begin
    @(posedge stream_clk);t=t+1;ok=1;
    for(l=0;l<4;l=l+1)if(n_fill[l]!=vm_exp[l]||n_wwd[l]!=wb_exp[l])ok=0;
   end
   if(!ok)$display("ENV PINREG=%0d window %0d timed out",PINREG,w);
  end
  t=0;ok=0;
  while(!ok&&t<400000)begin
   @(posedge stream_clk);t=t+1;ok=1;
   for(l=0;l<4;l=l+1)if(gi[l]!=GN||n_gkr[l]!=n_grbeats[l]||n_gwd[l]!=n_gwr[l])ok=0;
  end
  if(!ok)$display("ENV PINREG=%0d drain timed out",PINREG);
  repeat(50)@(posedge stream_clk);
  done=1;
 end
endmodule

module tb_hbm_svc_vm_kshare_pinreg_lockstep;
 parameter integer KRL1=1, MUT1=0, GN=600, NWIN=9;
 localparam integer NSTREAM_TB=160;
 integer HBM_HALF=512, STR_HALF=417;
 reg hbm_clk=0,stream_clk=0,hbm_rst_n=0,stream_rst_n=0;
 always #(HBM_HALF) hbm_clk=~hbm_clk;
 always #(STR_HALF) stream_clk=~stream_clk;
 wire done0,done1,fault0,fault1;
 ks_pr_env #(.PINREG(0),.KRL1(KRL1),.MUT(0),.GN(GN),.NWIN(NWIN)) e0(.hbm_clk(hbm_clk),.stream_clk(stream_clk),
  .hbm_rst_n(hbm_rst_n),.stream_rst_n(stream_rst_n),.done(done0),.fault(fault0));
 ks_pr_env #(.PINREG(1),.KRL1(KRL1),.MUT(MUT1),.GN(GN),.NWIN(NWIN)) e1(.hbm_clk(hbm_clk),.stream_clk(stream_clk),
  .hbm_rst_n(hbm_rst_n),.stream_rst_n(stream_rst_n),.done(done1),.fault(fault1));
 integer errors=0,l,i,n,fseen0=0,fseen1=0;
 always @(posedge stream_clk)begin if(fault0)fseen0=1;if(fault1)fseen1=1;end
 `define CMPQ(NAME,STR) \
  if(e0.NAME[l].size()!=e1.NAME[l].size())begin errors+=1;$display("MISMATCH lane %0d %s size %0d vs %0d",l,STR,e0.NAME[l].size(),e1.NAME[l].size());end \
  else for(i=0;i<e0.NAME[l].size();i=i+1)if(e0.NAME[l][i]!==e1.NAME[l][i])begin errors+=1;if(errors<20)$display("MISMATCH lane %0d %s #%0d",l,STR,i);end
 // minimum latency of a path: pairs the k-th source event with the k-th destination event (order preserved)
 function automatic integer minlat(input integer src[$],input integer dst[$]);
  integer k,m;begin m=1<<30;for(k=0;k<src.size()&&k<dst.size();k=k+1)if(dst[k]-src[k]<m)m=dst[k]-src[k];minlat=m;end
 endfunction
 function automatic longint minlat_t(input longint src[$],input longint dst[$]);
  integer k;longint m;begin m=64'd1<<40;for(k=0;k<src.size()&&k<dst.size();k=k+1)if(dst[k]-src[k]<m)m=dst[k]-src[k];minlat_t=m;end
 endfunction
 integer a0,a1,m0[0:4],m1[0:4];longint v0,v1;
 initial begin
  if($value$plusargs("HBM_HALF=%d",HBM_HALF));if($value$plusargs("STR_HALF=%d",STR_HALF));
  #(20000);hbm_rst_n=1;stream_rst_n=1;
  fork
   begin wait(done0&&done1); end
   begin #(64'd400_000_000);$display("FAIL timeout done0=%b done1=%b",done0,done1);$finish; end
  join_any
  for(l=0;l<4;l=l+1)begin
   `CMPQ(ck_grp,"ck_grp")
   `CMPQ(ck_vm,"ck_vm")
   `CMPQ(ck_wb,"ck_wb")
   `CMPQ(gkr,"gkr")
   `CMPQ(fil,"fil")
   if(e0.n_gwd[l]!=e1.n_gwd[l]||e0.n_wwd[l]!=e1.n_wwd[l])begin errors+=1;$display("MISMATCH lane %0d wr_done g %0d/%0d w %0d/%0d",l,e0.n_gwd[l],e1.n_gwd[l],e0.n_wwd[l],e1.n_wwd[l]);end
   if(e0.ck_grp[l].size()!=GN||e0.n_fill[l]!=e0.vm_exp[l]||e0.n_wwd[l]!=e0.wb_exp[l]||e0.n_gwd[l]!=e0.n_gwr[l])begin
    errors+=1;$display("INCOMPLETE lane %0d grp %0d/%0d fills %0d/%0d wbdone %0d/%0d gwdone %0d/%0d",l,e0.ck_grp[l].size(),GN,
     e0.n_fill[l],e0.vm_exp[l],e0.n_wwd[l],e0.wb_exp[l],e0.n_gwd[l],e0.n_gwr[l]);end
   $display("LANE %0d grp_req %0d vm_req %0d wb_wr %0d gkr_beats %0d fills %0d g_wr_done %0d w_wr_done %0d",l,e0.ck_grp[l].size(),
    e0.ck_vm[l].size(),e0.ck_wb[l].size(),e0.gkr[l].size(),e0.fil[l].size(),e0.n_gwd[l],e0.n_wwd[l]);
  end
  if(fseen0||fseen1)begin errors+=1;$display("FAULT dut0=%0d dut1=%0d",fseen0,fseen1);end
  // latencies (hbm edges; VM beat -> fill in ps), lane minimum over all lanes
  for(n=0;n<5;n=n+1)begin m0[n]=1<<30;m1[n]=1<<30;end
  v0=64'd1<<40;v1=64'd1<<40;
  for(l=0;l<4;l=l+1)begin
   a0=minlat(e0.t_gk[l],e0.t_ckg[l]);a1=minlat(e1.t_gk[l],e1.t_ckg[l]);if(a0<m0[0])m0[0]=a0;if(a1<m1[0])m1[0]=a1;
   a0=minlat(e0.t_wk[l],e0.t_ckw[l]);a1=minlat(e1.t_wk[l],e1.t_ckw[l]);if(a0<m0[1])m0[1]=a0;if(a1<m1[1])m1[1]=a1;
   a0=minlat(e0.t_ckrg[l],e0.t_gkr[l]);a1=minlat(e1.t_ckrg[l],e1.t_gkr[l]);if(a0<m0[2])m0[2]=a0;if(a1<m1[2])m1[2]=a1;
   a0=minlat(e0.t_cwdg[l],e0.t_gwd[l]);a1=minlat(e1.t_cwdg[l],e1.t_gwd[l]);if(a0<m0[3])m0[3]=a0;if(a1<m1[3])m1[3]=a1;
   a0=e0.g_lastst[l]-e0.g_first[l];a1=e1.g_lastst[l]-e1.g_first[l];if(a0<m0[4])m0[4]=a0;if(a1<m1[4])m1[4]=a1;
   if(minlat_t(e0.t_ckrv[l],e0.t_fil[l])<v0)v0=minlat_t(e0.t_ckrv[l],e0.t_fil[l]);
   if(minlat_t(e1.t_ckrv[l],e1.t_fil[l])<v1)v1=minlat_t(e1.t_ckrv[l],e1.t_fil[l]);
  end
  $display("LATENCY group_req g_k->c_k (hbm edges, min) PINREG0=%0d PINREG1=%0d offset=%0d",m0[0],m1[0],m1[0]-m0[0]);
  $display("LATENCY wb_write w_k->c_k (hbm edges, min) PINREG0=%0d PINREG1=%0d offset=%0d",m0[1],m1[1],m1[1]-m0[1]);
  $display("LATENCY response c_kr->g_kr (hbm edges, min) PINREG0=%0d PINREG1=%0d offset=%0d",m0[2],m1[2],m1[2]-m0[2]);
  $display("LATENCY wr_done c_k_wr_done->g_k_wr_done (hbm edges, min) PINREG0=%0d PINREG1=%0d offset=%0d",m0[3],m1[3],m1[3]-m0[3]);
  $display("LATENCY vm_beat c_kr->fill (ps, min, CDC) PINREG0=%0d PINREG1=%0d offset=%0d (hbm period %0d)",v0,v1,v1-v0,2*HBM_HALF);
  $display("STREAM %0d back-to-back group writes per lane took (edges, min over lanes) PINREG0=%0d PINREG1=%0d (II=1 -> %0d)",
   NSTREAM_TB,m0[4],m1[4],NSTREAM_TB-1);
  if(m1[4]!=NSTREAM_TB-1||m0[4]!=NSTREAM_TB-1)begin errors+=1;$display("II mismatch");end
  if(errors==0)$display("PASS tb_hbm_svc_vm_kshare_pinreg_lockstep KRL1=%0d MUT1=%0d GN=%0d NWIN=%0d hbm_half=%0d str_half=%0d",KRL1,MUT1,GN,NWIN,HBM_HALF,STR_HALF);
  else $display("FAIL tb_hbm_svc_vm_kshare_pinreg_lockstep KRL1=%0d MUT1=%0d errors=%0d",KRL1,MUT1,errors);
  $finish;
 end
endmodule
`default_nettype wire
