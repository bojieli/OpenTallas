`timescale 1ns/1ps
// MU-KV-CTL3 10-19: lockstep of the registered-timing variants as bound in the MU 3 qkd_kvs_ctl (the _mu wrappers):
// (1) qkd_static_kv_ownership_calendar_mu MU 1 PIPE=1 vs PIPE=0 fed with group_drained one edge later: every output
//     equal on every edge.  Episodes add RE-ARMING gos (later users' token starts inside the active window, MU 1).
//     Needs clean deadlines, re-arms, enter faults (code 3) and leave faults (code 4).
// (2) qkd_static_kv_boot_dispatch_mu MU 1 SRQ=2 vs SRQ=0 with MU target-1 images (471 words: GAP block 326..469, seal
//     470): every output equal on every edge except setup_ready; setup_ready(SRQ=2) == (original setup_ready of the
//     SRQ=0 instance two edges earlier) && !x_fault (the MU extension fault masks it unregistered, as before).
module tb_kv_ctl_mu3_lockstep;
 parameter integer EPIS=400,REPLAYS=40,SEED=11;
 reg ck=0;always #5 ck=~ck;
 integer seed=SEED,edges=0;
 // ---------------- (1) ownership ----------------
 reg orst=0,we=0,go=0,host=1,up=1;reg[1:0]addr=0;reg[31:0]data=0,gd=32'hffffffff,gd_d=32'hffffffff,gf=0;
 always @(posedge ck)gd_d<=gd;
 wire m0,v0,r0,a0,d0,c0,f0,m1,v1,r1,a1,d1,c1,f1;wire[31:0]cy0,cy1;wire[7:0]fc0,fc1;
 qkd_static_kv_ownership_calendar_mu #(.MUT(0),.MU(1),.PIPE(0)) o0(.ck(ck),.rst_n(orst),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),.go(go),
  .host_quiet(host),.upstream_quiet(up),.group_drained(gd_d),.group_fault(gf),.native_mode(m0),.ownership_valid(v0),.native_reserved(r0),
  .active(a0),.done(d0),.configured(c0),.cycle(cy0),.fault(f0),.fault_code(fc0));
 qkd_static_kv_ownership_calendar_mu #(.MUT(0),.MU(1),.PIPE(1)) o1(.ck(ck),.rst_n(orst),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),.go(go),
  .host_quiet(host),.upstream_quiet(up),.group_drained(gd),.group_fault(gf),.native_mode(m1),.ownership_valid(v1),.native_reserved(r1),
  .active(a1),.done(d1),.configured(c1),.cycle(cy1),.fault(f1),.fault_code(fc1));
 integer odiff=0,odone=0,oent=0,olea=0,omode=0,orearm=0;
 // ---------------- (2) boot dispatcher ----------------
 reg brst=0;reg[142:0]pr=0;reg[3:0]target=1;reg ready=0,sfault=0,active=0,kfault=0;
 reg[15:0]epoch=123;reg[63:0]digest=0;reg[159:0]applied=0;reg[2:0]configured=0;
 wire[431:0]oa,ob;wire[127:0]cwa,cwb,cla,clb;wire[7:0]caa,cab;wire[63:0]cda,cdb;wire[31:0]fla,flb;
 wire sra,srb,fa,fb;wire[7:0]fca,fcb;wire[15:0]iea,ieb;wire[63:0]ida,idb;
 qkd_static_kv_boot_dispatch_mu #(.MU(1),.SRQ(0)) b0(.ck(ck),.rst_n(brst),.boot_pr(pr),.boot_image_target(target),.boot_image_ready(ready),.boot_image_fault(sfault),
  .boot_image_epoch(epoch),.boot_image_digest(digest),.execution_active(active),.sink_applied(applied),.local_configured(configured),.sink_fault(kfault),
  .diecfg_sealed(1'b0),.diecfg_fault(1'b0),
  .layer_we(oa[0]),.layer_addr(oa[9:1]),.layer_data(oa[73:10]),.writer_we(oa[74]),.writer_addr(oa[82:75]),.writer_data(oa[146:83]),
  .ownership_we(oa[147]),.ownership_addr(oa[149:148]),.ownership_data(oa[181:150]),.landing_we(oa[213:182]),.front_we(oa[245:214]),
  .group_addr(oa[253:246]),.group_data(oa[317:254]),.controller_we(cwa),.controller_addr(caa),.controller_data(cda),.controller_last(cla),
  .front_last(fla),.setup_ready(sra),.fault(fa),.fault_code(fca),.installed_epoch(iea),.installed_isa_digest(ida));
 qkd_static_kv_boot_dispatch_mu #(.MU(1),.SRQ(2)) b2(.ck(ck),.rst_n(brst),.boot_pr(pr),.boot_image_target(target),.boot_image_ready(ready),.boot_image_fault(sfault),
  .boot_image_epoch(epoch),.boot_image_digest(digest),.execution_active(active),.sink_applied(applied),.local_configured(configured),.sink_fault(kfault),
  .diecfg_sealed(1'b0),.diecfg_fault(1'b0),
  .layer_we(ob[0]),.layer_addr(ob[9:1]),.layer_data(ob[73:10]),.writer_we(ob[74]),.writer_addr(ob[82:75]),.writer_data(ob[146:83]),
  .ownership_we(ob[147]),.ownership_addr(ob[149:148]),.ownership_data(ob[181:150]),.landing_we(ob[213:182]),.front_we(ob[245:214]),
  .group_addr(ob[253:246]),.group_data(ob[317:254]),.controller_we(cwb),.controller_addr(cab),.controller_data(cdb),.controller_last(clb),
  .front_last(flb),.setup_ready(srb),.fault(fb),.fault_code(fcb),.installed_epoch(ieb),.installed_isa_digest(idb));
 assign oa[431:318]=0;assign ob[431:318]=0;
 reg sra_1=0,sra_2=0;always @(posedge ck or negedge brst)if(!brst)begin sra_1<=0;sra_2<=0;end else begin sra_1<=b0.o_setup;sra_2<=sra_1;end
 wire srb_exp=sra_2&&!b2.x_fault;
 integer bdiff=0,srdiff=0,setups=0,sr_rise=0,sr_fall=0,bfaults=0;reg srb_prev=0;
 always @(negedge ck)begin
  edges=edges+1;
  if({m0,v0,r0,a0,d0,c0,f0,cy0,fc0}!=={m1,v1,r1,a1,d1,c1,f1,cy1,fc1})odiff=odiff+1;
  if(d0)odone=odone+1;if(m0)omode=omode+1;
  if(oa!==ob||cwa!==cwb||caa!==cab||cda!==cdb||cla!==clb||fla!==flb||fa!==fb||fca!==fcb||iea!==ieb||ida!==idb)bdiff=bdiff+1;
  if(srb!==srb_exp)srdiff=srdiff+1;
  if(sra)setups=setups+1;
  if(srb&&!srb_prev)sr_rise=sr_rise+1;if(!srb&&srb_prev)sr_fall=sr_fall+1;srb_prev=srb;
 end
 task tick;begin @(posedge ck);#1;end endtask
 function [31:0] rnd(input integer n);begin rnd=$unsigned($random(seed))%n;end endfunction
 // ---------------- ownership episodes ----------------
 task bootword(input[1:0]a,input[31:0]d);begin @(negedge ck);we=1;addr=a;data=d;tick();@(negedge ck);we=0;tick();end endtask
 task own_episode;integer e,l,dl,i,len,bit_;begin
  @(negedge ck);orst=0;we=0;go=0;host=1;up=1;gd=32'hffffffff;gf=0;repeat(2)tick();@(negedge ck);orst=1;tick();
  e=3+rnd(8);l=e+1+rnd(10);dl=l+1+rnd(10);
  if(rnd(16)==0)l=e;           // malformed (leave <= enter)
  bootword(0,e);bootword(1,l);bootword(2,dl);bootword(3,32'h514b564d);
  repeat(rnd(3))tick();
  @(negedge ck);go=1;tick();@(negedge ck);go=0;
  len=dl+4+rnd(2*dl);
  for(i=0;i<len;i=i+1)begin
   @(negedge ck);
   gd=32'hffffffff;host=1;up=1;go=0;
   if(i<len-dl-3&&rnd(6)==0)begin go=1;if(a0)orearm=orearm+1;end   // a later user's token start (re-arm, MU 1)
   if(rnd(5)==0)begin bit_=rnd(32);gd[bit_]=0;end
   if(rnd(40)==0)host=0;
   if(rnd(60)==0)up=0;
   if(rnd(300)==0)gf[rnd(32)]=1;
   tick();
  end
  if(fc0[3])oent=oent+1;if(fc0[4])olea=olea+1;
 end endtask
 // ---------------- boot replays ----------------
 function automatic integer wc(input integer t);case(t)1:wc=471;2:wc=181;3:wc=4;4,5:wc=192;default:wc=1024;endcase endfunction
 task gap;begin while(($random(seed)&3)==0)begin pr=0;tick();end end endtask
 task corrupt;begin case(rnd(6))0:pr[73:64]=$random(seed);1:epoch=epoch+1;2:active=1;3:pr[142]=1;4:sfault=1;5:kfault=1;endcase end endtask
 task boot_replay(input integer r);integer t,w,k;begin
  @(negedge ck);brst=0;pr=0;ready=0;sfault=0;active=0;kfault=0;applied=0;configured=0;epoch=100+r;tick();@(negedge ck);brst=1;tick();
  for(t=1;t<=10;t=t+1)begin
   @(negedge ck);ready=0;target=(t==10)?4'd0:4'(t);tick();
   if(t<10)for(w=0;w<wc(t);w=w+1)begin
    @(negedge ck);pr=0;pr[74]=1;pr[73:64]=10'(w);pr[63:0]={(t==3)?32'd0:$random(seed),$random(seed)};
    if(r%4==3&&rnd(256)==0)corrupt();
    tick();@(negedge ck);active=0;pr=0;gap();
   end
   @(negedge ck);pr=0;ready=1;digest={$random(seed),$random(seed)};tick();tick();
  end
  @(negedge ck);configured=7;applied=(r%5==4)?{$random(seed)}:{160{1'b1}};tick();tick();
  for(k=0;k<24;k=k+1)begin   // post-setup pin activity: ready / target / fault pulses, local drop
   @(negedge ck);
   case(rnd(8))0:ready=~ready;1:target=(target==0)?4'd1:4'd0;2:configured[rnd(3)]=~configured[rnd(3)];3:sfault=(k>18);default:;endcase
   tick();
  end
  if(fa)bfaults=bfaults+1;
 end endtask
 integer n;
 initial begin
  for(n=0;n<EPIS;n=n+1)own_episode();
  for(n=0;n<REPLAYS;n=n+1)boot_replay(n);
  if(odiff||bdiff||srdiff)$fatal(1,"FAIL lockstep own_diffs%0d boot_diffs%0d setup_ready_diffs%0d",odiff,bdiff,srdiff);
  if(orearm==0||odone==0||oent==0||olea==0||omode==0||setups==0||sr_rise==0||sr_fall==0||bfaults==0)
   $fatal(1,"FAIL weak stimulus rearms%0d done%0d enter_faults%0d leave_faults%0d mode%0d setups%0d rise%0d fall%0d bfaults%0d",orearm,odone,oent,olea,omode,setups,sr_rise,sr_fall,bfaults);
  $display("PASS KV_CTL_MU3_LOCKSTEP own_mu MU1 PIPE1==PIPE0(drain+1) episodes%0d rearms%0d done%0d enter_faults%0d leave_faults%0d; boot_mu MU1 SRQ2==SRQ0+2 (471-word t1) replays%0d setup_edges%0d rises%0d falls%0d faulted%0d edges%0d diffs0",
   EPIS,orearm,odone,oent,olea,REPLAYS,setups,sr_rise,sr_fall,bfaults,edges);
  $finish;
 end
endmodule
