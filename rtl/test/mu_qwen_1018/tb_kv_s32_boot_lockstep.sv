`timescale 1ns/1ps
// KV-CTL3 10-20 (fork S32-D2): qkd_static_kv_boot_dispatch_mu_s32 in lockstep with qkd_static_kv_boot_dispatch_mu (tile
// params MUT 0 DIECFG 1 NRST 43 LINKCFG 1 ESCFG 1 DIECAP 1 MU 1 WMUT 0 SRQ 2): EVERY output compared on EVERY edge.
// Episodes (reset between): full ordered boots (10, 1 (MU 471 words: GAP block + seal), 2..9, 11, 12, 13, ready edges,
// 0 = ISA) with legal data; each word / ready / epoch perturbed with small probability (wrong address, epoch, target,
// bad data fields for 3/11/12/13, execution_active, boot_pr[142], sink faults, mid-episode resets); plus chaos episodes
// of random words.  PASS: 'PASS KV_S32_BOOT_LOCKSTEP mismatches0 ...'; FAIL: 'FAIL KV_S32_BOOT_LOCKSTEP mismatches<n>'.
module tb_kv_s32_boot_lockstep;
 parameter integer EPIS=60,SEED=7;
 reg ck=0;always #5 ck=~ck;
 integer seed=SEED;
 reg rst_n=0;reg[142:0]pr=0;reg[3:0]tg=0;reg rdy=0,ifl=0,act=0,skf=0,dsl=0,dfl=0;reg[15:0]ep=16'h1234;reg[63:0]dg=0;
 reg[159:0]app=0;reg[2:0]lcf=0;
 `define BD_OUT(p) wire p``lw,p``ww,p``ow,p``dw,p``tx,p``rx,p``ew,p``sr,p``ft;wire[8:0]p``la;wire[63:0]p``ld,p``wd,p``gd,p``cd,p``dd,p``ed,p``id;\
  wire[7:0]p``wa,p``ga,p``ca,p``da,p``ea,p``fc;wire[1:0]p``oa;wire[31:0]p``od,p``lwe,p``fwe,p``fl,p``kd;wire[127:0]p``cw,p``cl;wire[5:0]p``ka;wire[15:0]p``ie;
 `BD_OUT(a_)
 `BD_OUT(b_)
 `define BD_CONN(p) (.ck(ck),.rst_n(rst_n),.boot_pr(pr),.boot_image_target(tg),.boot_image_ready(rdy),.boot_image_fault(ifl),\
  .boot_image_epoch(ep),.boot_image_digest(dg),.execution_active(act),.sink_applied(app),.local_configured(lcf),.sink_fault(skf),\
  .diecfg_sealed(dsl),.diecfg_fault(dfl),.layer_we(p``lw),.layer_addr(p``la),.layer_data(p``ld),.writer_we(p``ww),.writer_addr(p``wa),\
  .writer_data(p``wd),.ownership_we(p``ow),.ownership_addr(p``oa),.ownership_data(p``od),.landing_we(p``lwe),.front_we(p``fwe),\
  .group_addr(p``ga),.group_data(p``gd),.controller_we(p``cw),.controller_addr(p``ca),.controller_data(p``cd),.controller_last(p``cl),\
  .front_last(p``fl),.diecfg_we(p``dw),.diecfg_addr(p``da),.diecfg_data(p``dd),.link_cfg_tx_we(p``tx),.link_cfg_rx_we(p``rx),\
  .link_cfg_addr(p``ka),.link_cfg_data(p``kd),.es_cfg_we(p``ew),.es_cfg_addr(p``ea),.es_cfg_data(p``ed),.setup_ready(p``sr),\
  .fault(p``ft),.fault_code(p``fc),.installed_epoch(p``ie),.installed_isa_digest(p``id))
 qkd_static_kv_boot_dispatch_mu #(.MUT(0),.DIECFG(1),.NRST(43),.LINKCFG(1),.ESCFG(1),.DIECAP(1),.MU(1),.WMUT(0),.SRQ(2)) ref0 `BD_CONN(a_);
 qkd_static_kv_boot_dispatch_mu_s32 #(.MUT(0),.DIECFG(1),.NRST(43),.LINKCFG(1),.ESCFG(1),.DIECAP(1),.MU(1),.WMUT(0),.SRQ(2)) dut `BD_CONN(b_);
 wire[1199:0]va={a_lw,a_ww,a_ow,a_dw,a_tx,a_rx,a_ew,a_sr,a_ft,a_la,a_ld,a_wd,a_gd,a_cd,a_dd,a_ed,a_id,a_wa,a_ga,a_ca,a_da,a_ea,a_fc,a_oa,a_od,a_lwe,a_fwe,a_fl,a_kd,a_cw,a_cl,a_ka,a_ie};
 wire[1199:0]vb={b_lw,b_ww,b_ow,b_dw,b_tx,b_rx,b_ew,b_sr,b_ft,b_la,b_ld,b_wd,b_gd,b_cd,b_dd,b_ed,b_id,b_wa,b_ga,b_ca,b_da,b_ea,b_fc,b_oa,b_od,b_lwe,b_fwe,b_fl,b_kd,b_cw,b_cl,b_ka,b_ie};
 reg fprev=0,fok=0;integer dbg=0;
 integer mism=0,cyc=0,acts=0,faults=0,setups=0,cwh=0,lwh=0,fwh=0,flh=0,clh=0,gaps=0,boots=0;
 always @(posedge ck)begin
  #1;cyc=cyc+1;
  if(va!==vb)begin mism=mism+1;if(mism<=5)$display("MISMATCH cyc %0d diff %h",cyc,va^vb);end
  if(a_ft)faults=faults+1;
  if(a_ft&&!fprev&&dbg<12)begin dbg=dbg+1;$display("DBG fault cyc %0d epi %0d pe %0d fc %h tg %0d addr %0d",cyc,e,pe,a_fc,tg,pr[73:64]);end
  fprev=a_ft;if(a_sr)setups=setups+1;
  if(|a_cw)cwh=cwh+1;if(|a_lwe)lwh=lwh+1;if(|a_fwe)fwh=fwh+1;if(|a_fl)flh=flh+1;if(|a_cl)clh=clh+1;
  if(a_lw&&a_la>=326&&a_la<470)gaps=gaps+1;
 end
 function integer wc(input integer t);
  case(t)1:wc=471;2:wc=181;3:wc=4;4,5:wc=192;6,7,8,9:wc=1024;10:wc=32+43+2;11:wc=66;12:wc=1024;13:wc=8;default:wc=0;endcase
 endfunction
 integer pe;   // perturbation rate per mille
 function [63:0] wdata(input integer t,input integer a);
  reg[63:0]r;begin
   r={$random(seed),$random(seed)};
   if(t==3||t==11)r[63:32]=0;
   if(t==12)begin r[63:18]=0;r[17:16]=a[9:8];end
   if(t==13)begin r[63:62]=2'd1;r[61:24]=0;end
   if(t==1&&a<324)r[63:32]=0;
   if(($random(seed)&1023)<pe)r={$random(seed),$random(seed)};
   wdata=r;
  end
 endfunction
 task step;begin
  @(negedge ck);
  if(($random(seed)&4095)<pe/4)act=1;else act=0;
  if(($random(seed)&8191)<pe/8)pr[142]=1;else pr[142]=0;
  skf=(($random(seed)&16383)<pe/16);ifl=(($random(seed)&16383)<pe/16);dfl=(($random(seed)&16383)<pe/16);
  if(fok)begin app={160{1'b1}};lcf=3'b111;dsl=1;skf=0;ifl=0;dfl=0;end else begin
  app=(($random(seed)&3)==0)?{160{1'b1}}:{$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  lcf=(($random(seed)&3)==0)?3'b111:$random(seed);dsl=$random(seed);end
  if(($random(seed)&65535)<pe/16)begin rst_n=0;@(negedge ck);rst_n=1;end
 end endtask
 task word(input integer t,input integer a);begin
  step;pr[74]=1;tg=t;pr[73:64]=a;pr[63:0]=wdata(t,a);pr[141:75]={$random(seed),$random(seed),$random(seed)};
  if(($random(seed)&1023)<pe)pr[73:64]=$random(seed);
  if(($random(seed)&2047)<pe)tg=$random(seed);
  if(($random(seed)&2047)<pe)ep=ep^16'h1;
  step;pr[74]=0;acts=acts+1;
  if(($random(seed)&3)==0)step;
 end endtask
 task image(input integer t);integer a;begin
  for(a=0;a<wc(t);a=a+1)word(t,a);
  step;tg=t;rdy=1;step;rdy=0;step;
 end endtask
 integer e,k,o[0:13];
 initial begin
  if(!$value$plusargs("seed=%d",seed))seed=SEED;
  o[0]=10;o[1]=1;o[2]=2;o[3]=3;o[4]=4;o[5]=5;o[6]=6;o[7]=7;o[8]=8;o[9]=9;o[10]=11;o[11]=12;o[12]=13;
  for(e=0;e<EPIS;e=e+1)begin
   rst_n=0;rdy=0;pr=0;tg=0;act=0;ep=$random(seed);dg={$random(seed),$random(seed)};repeat(3)@(negedge ck);rst_n=1;
   pe=(e%3==0)?0:((e%3==1)?3:40);
   if(e%10==9)begin   // chaos: random words
    for(k=0;k<3000;k=k+1)begin step;pr[74]=$random(seed);tg=$random(seed);pr[73:64]=$random(seed);pr[63:0]={$random(seed),$random(seed)};
     rdy=(($random(seed)&63)==0);end
   end else begin
    for(k=0;k<13;k=k+1)image(o[k]);
    fok=1;step;tg=0;rdy=1;repeat(6)step;rdy=0;repeat(8)step;fok=0;boots=boots+1;
   end
  end
  if(mism==0&&cwh>0&&lwh>0&&fwh>0&&flh>0&&clh>0&&gaps>0&&setups>0)
   $display("PASS KV_S32_BOOT_LOCKSTEP mismatches0 cycles%0d words%0d boots%0d faultcyc%0d setupcyc%0d cw%0d cl%0d lw%0d fw%0d fl%0d gap%0d",cyc,acts,boots,faults,setups,cwh,clh,lwh,fwh,flh,gaps);
  else $display("FAIL KV_S32_BOOT_LOCKSTEP mismatches%0d cycles%0d words%0d boots%0d faultcyc%0d setupcyc%0d cw%0d cl%0d lw%0d fw%0d fl%0d gap%0d",mism,cyc,acts,boots,faults,setups,cwh,clh,lwh,fwh,flh,gaps);
  $finish;
 end
endmodule
