`timescale 1ns/1ps
// KV-GRP-CTL/MU5 10-19: qkd_static_kv_layer_programme_mus (stage/GAP tables in SRAM macros, registered event flags) in
// lockstep with qkd_static_kv_layer_programme_mu MU 1 (flop tables; the mu4 view's programme).  Same boot image words,
// same start stream; EVERY output of both compared on EVERY edge (incl. faults and fault codes).
//   mode A (aligned, 4 users concurrent): all roots / ends multiples of 4, gaps 0 or multiples of 4, user u starts on
//          cycles = u mod 4 -> the users' events never share an edge (no collision fault), so tokens run to completion
//          with random per-user / per-stage gaps and random start times.
//   mode C (one user at a time, random user ids): arbitrary roots >= 3 and gaps 0..6 (gap 1 / 2 / 3 exercise the
//          registered wait-expiry path, the stage-1 gap register and the per-row next-gap flags).
//   mode B (chaos): arbitrary roots / gaps, 4 users started at random (collisions, start-while-active, wrong digest /
//          epoch / position, late cfg writes, bad rows): fault behaviour must match too.
// PASS line: PASS KV_LPRG_MU5_LOCKSTEP ...; any difference: FAIL KV_LPRG_MU5_LOCKSTEP mismatches<n> ...
module tb_kv_lprg_mu5_lockstep;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,we=0,st=0,av=0,pa=0;reg[8:0]addr=0;reg[63:0]data=0,pdg=0;reg[15:0]pep=0,aep=0;
 reg[17:0]tok=0,pos=0;reg[1:0]gen=0;
 wire a_cg,a_kg,a_vg,a_ai,a_ar,a_ws,a_ls,a_ss,a_sd,a_q,a_cf,a_ac,a_dn,a_ft;wire[5:0]a_cs,a_st,a_ly;wire[15:0]a_ep;
 wire[17:0]a_tk,a_ps;wire[13:0]a_ct;wire[1:0]a_gn;wire[7:0]a_fc;wire[31:0]a_age,a_tc;
 wire b_cg,b_kg,b_vg,b_ai,b_ar,b_ws,b_ls,b_ss,b_sd,b_q,b_cf,b_ac,b_dn,b_ft;wire[5:0]b_cs,b_st,b_ly;wire[15:0]b_ep;
 wire[17:0]b_tk,b_ps;wire[13:0]b_ct;wire[1:0]b_gn;wire[7:0]b_fc;wire[31:0]b_age,b_tc;
 `define LPRG_CONN(p) (.ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),.start(st),.authority_valid(av),\
  .programme_authorized(pa),.programme_epoch(pep),.programme_digest(pdg),.authority_epoch(aep),.authority_token(tok),\
  .authority_position(pos),.authority_generation(gen),.ctrl_go(p``cg),.kgo(p``kg),.vgo(p``vg),.attention_issue(p``ai),\
  .attention_run(p``ar),.writer_start(p``ws),.link_start(p``ls),.stage_start(p``ss),.stage_done(p``sd),\
  .expected_upstream_quiet(p``q),.completed_stage(p``cs),.stage(p``st),.layer(p``ly),.epoch(p``ep),.token(p``tk),\
  .position(p``ps),.ctx_t(p``ct),.generation(p``gn),.configured(p``cf),.active(p``ac),.done(p``dn),.fault(p``ft),\
  .fault_code(p``fc),.age(p``age),.token_cycles(p``tc))
 qkd_static_kv_layer_programme_mu #(.MUT(0),.MU(1)) ref0 `LPRG_CONN(a_);
 qkd_static_kv_layer_programme_mus #(.MUT(0),.MU(1)) dut `LPRG_CONN(b_);
 wire[171:0]va={a_cg,a_kg,a_vg,a_ai,a_ar,a_ws,a_ls,a_ss,a_sd,a_q,a_cs,a_st,a_ly,a_ep,a_tk,a_ps,a_ct,a_gn,a_cf,a_ac,a_dn,a_ft,a_fc,a_age,a_tc};
 wire[171:0]vb={b_cg,b_kg,b_vg,b_ai,b_ar,b_ws,b_ls,b_ss,b_sd,b_q,b_cs,b_st,b_ly,b_ep,b_tk,b_ps,b_ct,b_gn,b_cf,b_ac,b_dn,b_ft,b_fc,b_age,b_tc};
 integer mism=0,cycles=0,events=0,stagesd=0,faults=0,faultsA=0,boots=0;integer toks[0:3];integer fcodes[0:7];
 integer gap1=0,gap2=0;
 always @(posedge ck)begin
  #0.1;
  cycles=cycles+1;
  if(va!==vb)begin
   mism=mism+1;
   if(mism<=5)$display("MISMATCH cyc %0d ref %h dut %h (ref fc %h dut fc %h stage %0d/%0d ep %h/%h)",cycles,va,vb,a_fc,b_fc,a_st,b_st,a_ep,b_ep);
  end
  if(a_ss|a_sd|a_cg|a_kg|a_vg|a_ai|a_ar|a_ws|a_ls)events=events+1;
  if(a_sd)stagesd=stagesd+1;
  if(a_dn&&!a_ft)toks[a_ep[1:0]]=toks[a_ep[1:0]]+1;
 end
 // ---- boot image ----
 reg[31:0]R[0:35][0:8];reg[31:0]G[0:3][0:35];reg[63:0]D;reg[15:0]E;
 integer s,w,u,j,k,mx;
 task tick;begin @(negedge ck);end endtask
 task make_rows(input integer mode);
  integer q,L;
  begin
   q=(mode==0)?4:1;
   for(s=0;s<36;s=s+1)begin
    L=(mode==0)?(2+$urandom%6):(1+$urandom%12);
    mx=0;
    for(w=0;w<7;w=w+1)begin
     if(mode==0)R[s][w]=4*(1+$urandom%L);else R[s][w]=3+$urandom%(4*L);
     if(w!=4&&R[s][w]>mx)mx=R[s][w];
    end
    // run >= issue + 4
    R[s][4]=R[s][3]+((mode==0)?4*(1+$urandom%3):(4+$urandom%6));if(R[s][4]>mx)mx=R[s][4];
    R[s][7]=mx+((mode==0)?4*(1+$urandom%3):(1+$urandom%6));               // quiet > words 0..6
    R[s][8]=R[s][7]+((mode==0)?4*(1+$urandom%4):(1+$urandom%8));          // end > words 0..7
   end
  end
 endtask
 task make_gaps(input integer mode);
  begin
   for(u=0;u<4;u=u+1)for(j=0;j<36;j=j+1)begin
    if(mode==0)G[u][j]=($urandom%3==0)?0:4*($urandom%3);
    else G[u][j]=($urandom%2==0)?0:($urandom%7);
    if(u==0&&mode==0&&$urandom%2==0)G[u][j]=0;
    if(G[u][j]==1)gap1=gap1+1;if(G[u][j]==2)gap2=gap2+1;
   end
  end
 endtask
 task wr(input[8:0]a,input[63:0]d);begin tick();we=1;addr=a;data=d;end endtask
 task boot(input integer corrupt);
  integer a;
  begin
   D={$urandom,$urandom};E=$urandom;
   for(s=0;s<36;s=s+1)for(w=0;w<9;w=w+1)wr(9*s+w,{32'd0,R[s][w]});
   wr(324,D);wr(325,{48'd0,E});
   for(u=0;u<4;u=u+1)for(j=0;j<36;j=j+1)wr(326+36*u+j,{32'd0,G[u][j]});
   wr(470,64'h514b564c59523336);
   tick();we=0;
   repeat(4)tick();
   boots=boots+1;
  end
 endtask
 task bad_boot;   // a corrupted image: one random word changed (row order, upper bits, seal, skipped address)
  integer a,n;
  begin
   D={$urandom,$urandom};E=$urandom;n=$urandom%471;
   for(a=0;a<471;a=a+1)begin
    if(a<324)data={32'd0,R[a/9][a%9]};else if(a==324)data=D;else if(a==325)data={48'd0,E};
    else if(a<470)data={32'd0,G[(a-326)/36][(a-326)%36]};else data=64'h514b564c59523336;
    if(a==n)begin
     case($urandom%4)0:data[63:32]=1;1:data[31:0]=2;2:data=data^64'h1;default:data[7:0]=data[7:0]+1;endcase
    end
    wr(a,data);
   end
   tick();we=0;repeat(4)tick();boots=boots+1;
  end
 endtask
 task reset;begin tick();rst_n=0;we=0;st=0;av=0;pa=0;repeat(4)tick();rst_n=1;repeat(3)tick();end endtask
 task start_user(input[1:0]uu,input integer bad);
  begin
   st=1;av=1;pa=1;pep=E;pdg=D;aep={$urandom%16384,uu};tok=$urandom;pos=$urandom%8192;gen=$urandom;
   if(bad==1)pdg[$urandom%64]^=1;if(bad==2)pep[$urandom%16]^=1;if(bad==3)pos=8192+$urandom%100;if(bad==4)av=0;
   if(bad==5)pa=0;
   tick();st=0;av=$urandom;pa=$urandom;pdg=$urandom;pep=$urandom;
  end
 endtask
 // mode A: users start on cycles = u mod 4 (absolute cycle count), only when inactive
 integer ep,t,T,nst;reg[1:0]uu;
 initial begin
  for(k=0;k<4;k=k+1)toks[k]=0;
  // ---------------- mode A ----------------
  for(ep=0;ep<40;ep=ep+1)begin
   reset();make_rows(0);make_gaps(0);boot(0);
   T=6000+$urandom%6000;
   for(t=0;t<T;t=t+1)begin
    // drive on negedge so that start is sampled at the next posedge; cycle number of that posedge = cycles+1
    uu=2'(cycles+1);
    if(!ref0.g_mu.c_act[uu]&&$urandom%40==0&&!a_ft)start_user(uu,0);else tick();
   end
   if(a_ft)faultsA=faultsA+1;
  end
  // ---------------- mode C ----------------
  for(ep=0;ep<40;ep=ep+1)begin
   reset();make_rows(1);make_gaps(1);boot(0);
   for(nst=0;nst<6;nst=nst+1)begin
    start_user($urandom,0);tick();tick();
    while(ref0.g_mu.c_act!=0&&!a_ft)tick();
    repeat($urandom%5)tick();
   end
   if(a_ft)faultsA=faultsA+1;
  end
  // ---------------- mode B ----------------
  for(ep=0;ep<60;ep=ep+1)begin
   reset();make_rows($urandom%2);make_gaps($urandom%2);
   if($urandom%5==0)bad_boot();else boot(0);
   T=1000+$urandom%5000;
   for(t=0;t<T;t=t+1)begin
    if($urandom%150==0)start_user($urandom,($urandom%6==0)?1+$urandom%5:0);
    else if($urandom%3000==0)wr($urandom,{$urandom,$urandom});
    else begin tick();we=0;end
   end
   if(a_ft)begin faults=faults+1;for(k=0;k<8;k=k+1)if(a_fc[k])fcodes[k]=fcodes[k]+1;end
  end
  repeat(4)tick();
  if(mism!=0||faultsA!=0||toks[0]<40||toks[1]<20||toks[2]<20||toks[3]<20||gap1==0||gap2==0||faults<10)
   $display("FAIL KV_LPRG_MU5_LOCKSTEP mismatches%0d faultsA%0d tokens %0d/%0d/%0d/%0d gap1 %0d gap2 %0d chaos_faults %0d",
    mism,faultsA,toks[0],toks[1],toks[2],toks[3],gap1,gap2,faults);
  else
   $display("PASS KV_LPRG_MU5_LOCKSTEP mismatches0 boots%0d cycles%0d events%0d stage_done%0d tokens %0d/%0d/%0d/%0d gap1 %0d gap2 %0d chaos_faults %0d (codes %0d %0d %0d %0d %0d)",
    boots,cycles,events,stagesd,toks[0],toks[1],toks[2],toks[3],gap1,gap2,faults,fcodes[0],fcodes[1],fcodes[2],fcodes[3],fcodes[4]);
  $finish;
 end
 initial for(k=0;k<8;k=k+1)fcodes[k]=0;
endmodule
