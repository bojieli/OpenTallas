`timescale 1ns/1ps
// MU-KV-BOOT 10-19 (Qwen ROM 4 users): the real KV boot path loads the compiler-emitted MU layer image into the
// multi-context layer programme inside the qkd_kvs_ctl _mu parent, then 4 users run their stages per the GAP table.
//   DUT  qkd_kvs_ctl from rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu.sv (u_boot =
//        qkd_static_kv_boot_dispatch_mu MU 1, u_lprg = qkd_static_kv_layer_programme_mu MU 1).  The image goes in as
//        the HOST loader replay does (boot_pr word stream, target 1, then boot_image_ready); no bench-side preload.
//   +IMG=<hex> +NW=<words>  the boot image (results/rtl/mu_qwen_1018/kvboot/target1.hex, 471 words; mutants below)
//   +STARTS=<txt>            "cycle user token" (kv_static_programme --mu-from: mu_calendar frame, two frames)
//   +EVENTS=<txt>            "cycle user stage mask" the compiler's expected KV programme events (mu_calendar
//                            kv_event_list; mask bit 0 stage_start, 1..8 ctrl_go kgo vgo attention_issue attention_run
//                            writer_start link_start expected_quiet, 9 stage_done; bit 8 is a level, not compared)
//   Checks, every edge: no layer programme / dispatcher fault; every pulse of the DUT equals the compiler's event list
//   (cycle, kinds, user = epoch[1:0], stage / completed_stage); user 0 in lockstep with the original single-user
//   qkd_static_kv_layer_programme (bench reference, given only user 0's starts and the single-user image) on every
//   pulse and its metadata; every user's every token completes 36 stages.
module tb_mu_kv_boot;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0;
 reg[142:0]pr=0;reg[3:0]target=0;reg ready=0;
 reg st=0;reg[81:0]auth=0;reg[58:0]cht=0;reg[1:0]chg=0;
 qkd_kvs_ctl dut(.ck(ck),.rst_n(rst_n),.boot__boot_pr(pr),.boot__boot_image_target(target),.boot__boot_image_ready(ready),
  .boot__boot_image_fault(1'b0),.boot__boot_image_epoch(16'h0b0b),.boot__boot_image_digest(64'd0),.d2d__svc(174'd0),
  .por_n(1'b1),.st(st),.auth(auth),.cht(cht),.chg(chg));
 // single-user reference (user 0 only)
 reg rwe=0;reg[8:0]ra=0;reg[63:0]rd=0;reg rst_ref=0;
 wire r_cg,r_kg,r_vg,r_ai,r_ar,r_ws,r_ls,r_ss,r_sd,r_q,r_cf,r_ac,r_dn,r_ft;wire[5:0]r_cs,r_st,r_ly;wire[15:0]r_ep;
 wire[17:0]r_tk,r_ps;wire[13:0]r_ct;wire[1:0]r_gn;wire[7:0]r_fc;wire[31:0]r_age,r_tc;
 qkd_static_kv_layer_programme u_ref(.ck(ck),.rst_n(rst_n),.cfg_we(rwe),.cfg_addr(ra),.cfg_data(rd),.start(st&&cht[44:43]==0),
  .authority_valid(auth[0]),.programme_authorized(auth[1]),.programme_epoch(auth[17:2]),.programme_digest(auth[81:18]),
  .authority_epoch(cht[58:43]),.authority_token(cht[36:19]),.authority_position({5'd0,cht[18:6]}),.authority_generation(chg),
  .ctrl_go(r_cg),.kgo(r_kg),.vgo(r_vg),.attention_issue(r_ai),.attention_run(r_ar),.writer_start(r_ws),.link_start(r_ls),
  .stage_start(r_ss),.stage_done(r_sd),.expected_upstream_quiet(r_q),.completed_stage(r_cs),.stage(r_st),.layer(r_ly),
  .epoch(r_ep),.token(r_tk),.position(r_ps),.ctx_t(r_ct),.generation(r_gn),.configured(r_cf),.active(r_ac),.done(r_dn),
  .fault(r_ft),.fault_code(r_fc),.age(r_age),.token_cycles(r_tc));
 wire[9:0]m_mu={dut.w_lprg__stage_done,1'b0,dut.w_lprg__link_start,dut.w_lprg__writer_start,dut.w_lprg__attention_run,
  dut.w_lprg__attention_issue,dut.w_lprg__vgo,dut.w_lprg__kgo,dut.w_lprg__ctrl_go,dut.w_lprg__stage_start};
 wire[9:0]m_ref={r_sd,1'b0,r_ls,r_ws,r_ar,r_ai,r_vg,r_kg,r_cg,r_ss};
 reg[63:0]img[0:511];integer nw;
 integer NS,NE;reg[31:0]s_c[0:63];reg[1:0]s_u[0:63];reg[7:0]s_k[0:63];
 reg[31:0]e_c[0:8191];reg[1:0]e_u[0:8191];reg[5:0]e_s[0:8191];reg[9:0]e_m[0:8191];
 integer cyc=0,base,i,a,ei=0,si=0,nev=0,ndone=0,nlock=0,fd,r,c,u,s,k,m;
 reg[1023:0]fn;
 task tick;begin @(posedge ck);#0.1;end endtask
 task fail(input [8*96-1:0]why);begin
  $display("FAIL MU_KV_BOOT: %0s cyc %0d (rel %0d) mu mask %03h ref mask %03h epoch %h lprg fault %02h boot fault %02h",
   why,cyc,cyc-base,m_mu,m_ref,dut.w_lprg__epoch,dut.w_lprg__fault_code,dut.w_boot__fault_code);$finish;end endtask
 always @(posedge ck)cyc<=cyc+1;
 initial begin
  if(!$value$plusargs("IMG=%s",fn))$fatal(1,"+IMG");$readmemh(fn,img);
  if(!$value$plusargs("NW=%d",nw))nw=471;
  if(!$value$plusargs("STARTS=%s",fn))$fatal(1,"+STARTS");
  fd=$fopen(fn,"r");NS=0;while($fscanf(fd,"%d %d %d\n",c,u,k)==3)begin s_c[NS]=c;s_u[NS]=u[1:0];s_k[NS]=k[7:0];NS=NS+1;end $fclose(fd);
  if(!$value$plusargs("EVENTS=%s",fn))$fatal(1,"+EVENTS");
  fd=$fopen(fn,"r");NE=0;
  while($fscanf(fd,"%d %d %d %d\n",c,u,s,m)==4)if((m&~32'h100)!=0)begin e_c[NE]=c;e_u[NE]=u[1:0];e_s[NE]=s[5:0];e_m[NE]=m[9:0]&~10'h100;NE=NE+1;end
  $fclose(fd);
  repeat(4)tick();rst_n=1;repeat(4)tick();
  // ---- boot: target 1 through the dispatcher (HOST loader replay order), the reference gets the single-user form ----
  target=1;
  for(a=0;a<nw;a=a+1)begin pr=0;pr[74]=1;pr[73:64]=10'(a);pr[63:0]=img[a];tick();end
  pr=0;tick();ready=1;tick();tick();
  for(a=0;a<327;a=a+1)begin rwe=1;ra=9'(a);rd=(a==326)?64'h514b564c59523336:img[a];tick();end
  rwe=0;repeat(4)tick();
  if(dut.w_boot__fault||dut.w_lprg__fault||!dut.w_lprg__configured)begin
   $display("FAIL MU_KV_BOOT: layer programme not configured by the boot path (configured %0d, lprg fault %02h, dispatcher fault %02h)",
    dut.w_lprg__configured,dut.w_lprg__fault_code,dut.w_boot__fault_code);$finish;end
  if(!r_cf)$fatal(1,"reference not configured");
  $display("boot: %0d words through qkd_static_kv_boot_dispatch_mu, layer programme configured, GAP[1][1] %0d",nw,img[326+36+1]);
  auth={img[324],img[325][15:0],1'b1,1'b1};
  base=cyc+10;
  // ---- run: drive every start one cycle before its compiled start cycle; compare every edge ----
  while(ei<NE||si<NS||cyc<base+e_c[NE-1]+50)begin
   @(negedge ck);
   st=0;
   if(si<NS&&cyc==base+s_c[si]-1)begin
    st=1;cht=0;cht[58:43]={6'd0,s_k[si],s_u[si]};cht[36:19]=18'(1000*s_u[si]+s_k[si]);cht[18:6]=13'(100+16*s_u[si]+s_k[si]);
    chg=2'(s_k[si]);si=si+1;
   end
   @(posedge ck);#0.1;
   if(dut.w_lprg__fault||dut.w_boot__fault)fail("layer programme / dispatcher fault");
   if(r_ft)fail("reference fault");
   // user 0 == the single-user original
   if(m_ref!=((m_mu!=0&&dut.w_lprg__epoch[1:0]==0)?m_mu:10'd0))fail("user 0 differs from MU 0 (pulses)");
   if(m_ref!=0)begin
    if({dut.w_lprg__epoch,dut.w_lprg__token,dut.w_lprg__position,dut.w_lprg__stage,dut.w_lprg__layer,dut.w_lprg__completed_stage,
        dut.w_lprg__ctx_t,dut.w_lprg__generation}!=={r_ep,r_tk,r_ps,r_st,r_ly,r_cs,r_ct,r_gn})fail("user 0 differs from MU 0 (metadata)");
    nlock=nlock+1;
   end
   // the compiler's event list
   if(ei<NE&&cyc-base==e_c[ei]+1)begin
    if(m_mu!=e_m[ei])fail("event kinds differ from the compiled list");
    if(dut.w_lprg__epoch[1:0]!=e_u[ei])fail("event user (epoch[1:0]) differs from the compiled list");
    if(e_m[ei][8:0]!=0&&dut.w_lprg__stage!=e_s[ei])fail("event stage differs from the compiled list");
    if(e_m[ei][8:0]==0&&dut.w_lprg__completed_stage!=e_s[ei])fail("completed stage differs from the compiled list");
    if(dut.w_lprg__done)ndone=ndone+1;
    ei=ei+1;nev=nev+1;
   end else if(m_mu!=0)fail("pulse not in the compiled list");
  end
  if(ndone!=NS)fail("not every token completed 36 stages");
  $display("PASS MU_KV_BOOT: %0d-word MU image through the boot dispatcher; %0d starts (4 users, 2 frames), %0d event edges equal the compiled list, %0d tokens done, user 0 == MU 0 on %0d edges, no fault",
   nw,NS,nev,ndone,nlock);
  $finish;
 end
endmodule
