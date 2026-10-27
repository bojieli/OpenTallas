`timescale 1ps/1ps
module tb_native_boot;
 reg clk=0;initial forever begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,av=0,wv=0;reg[11:0]aa=0;reg[31:0]wd=0;
 wire awr,wr,bv;wire[1:0]bres;wire cv,dv,lv,hfault;wire[7:0]target;wire[11:0]addr,base;wire[12:0]limit;wire[15:0]loops;wire[255:0]data;
 wire lcv,ldv,llv;wire[7:0]ltarget;wire[11:0]laddr,lbase;wire[12:0]llimit;wire[15:0]lloops;wire[255:0]ldata;wire[0:0]srdy,sact,sfault;
 wire ready,active,done,fault,jv;wire[216:0]job;wire[7:0]wsc;wire[5:0]pk5;wire pb5;
 wire rdone,rfault,rbusy;wire[172:0]dnw,dne;reg[270:0]unw=0,une=0;
 reg[216:0]gold[0:1];reg[280:0]entries[0:1];reg mut_data=0,mut_high=0;
 ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<224)) ingress(.clk(clk),.rst_n(rst_n),.s_awvalid(av),.s_awready(awr),.s_awaddr(aa),.s_wvalid(wv),.s_wready(wr),.s_wdata(wd),.s_wstrb(4'hf),.s_bvalid(bv),.s_bready(1'b1),.s_bresp(bres),.s_arvalid(1'b0),.s_arready(),.s_araddr(12'd0),.s_rvalid(),.s_rready(1'b1),.s_rdata(),.block_ready(srdy[0]),.program_active(sact[0]),.program_fault(sfault[0]),.cfg_v(cv),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(dv),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.launch_v(lv),.fault(hfault));
 ot_hbm_host_cfg_leaf2 #(.NT(1),.NF(1)) leaf(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(dv),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.launch_v(lv),.a_cfg_v(lcv),.a_cfg_target(ltarget),.a_cfg_addr(laddr),.a_cfg_data(ldata),.a_desc_v(ldv),.a_desc_base(lbase),.a_desc_limit(llimit),.a_desc_loops(lloops),.a_launch_v(llv),.b_cfg_v(),.b_cfg_target(),.b_cfg_addr(),.b_cfg_data(),.b_desc_v(),.b_desc_base(),.b_desc_limit(),.b_desc_loops(),.b_launch_v(),.t_ready(ready),.t_active(active),.t_fault(fault),.s_ready(srdy),.s_active(sact),.s_fault(sfault));
 ot_hnx_fused_host_program #(.TARGET(224),.DELIVERED_RESET(1)) programme(.clk(clk),.rst_n(rst_n),.cfg_v(lcv),.cfg_target(ltarget),.cfg_addr(laddr),.cfg_data(ldata),.desc_v(ldv),.desc_base(lbase),.desc_limit(llimit),.desc_loops(lloops),.launch_v(llv),.ready(ready),.active(active),.done(done),.fault(fault),.job_v(jv),.job(job),.wsc(wsc),.pk5(pk5),.pb5(pb5),.root_done(rdone),.root_fault(rfault),.root_busy(rbusy));
 ot_hnx_fused_hub_n4ext #(.DELIVERED_RESET(1)) root(.clk(clk),.rst_n(rst_n),.job_v(jv),.job(job),.done(rdone),.fault(rfault),.busy(rbusy),.wsc(wsc),.pk5(pk5),.pb5(pb5),.up_nw(unw),.up_ne(une),.down_nw(dnw),.down_ne(dne));
 wire disabled_load,disabled_start,disabled_commit;
 ot_hnx_fused_host_boot #(.TARGET(0)) disabled(.clk(clk),.rst_n(rst_n),.cfg_v(lcv),.cfg_target(ltarget),.cfg_addr(laddr),.cfg_data(ldata),.desc_v(ldv),.desc_base(lbase),.desc_limit(llimit),.desc_loops(lloops),.launch_v(llv),.load_v(disabled_load),.load_addr(),.load_entry(),.cfg_commit(disabled_commit),.cfg_calendar_bound(),.cfg_count(),.cfg_wsc(),.cfg_pk5(),.cfg_pb5(),.start(disabled_start),.provider_armed(1'b0),.provider_busy(1'b0),.provider_done(1'b0),.provider_fault(1'b0),.ready(),.active(),.fault());
 integer cc=0,start_edge=0,leaf_launch_edge=0,checks=0,errors=0,jobs=0,loads=0,traces=0,rootdones=0,progdone=0,scalars=0,finwait=0;reg measuring=0;
 always @(posedge clk)begin cc<=cc+1;if(programme.start)begin start_edge<=cc;if(measuring&&cc-leaf_launch_edge!=2)begin errors=errors+1;$display("START_CAPTURE_PHASE %0d",cc-leaf_launch_edge);end end if(llv)leaf_launch_edge<=cc;end
 always @(negedge clk)begin
  if(disabled_load||disabled_start||disabled_commit)$fatal(1,"unbound TARGET0 emitted traffic");
  if(measuring)begin
   checks=checks+1;
   if(hfault||fault)errors=errors+1;
   if(programme.load_v)begin if(programme.entry!==entries[loads%2]||programme.addr!==8'(loads%2))errors=errors+1;loads=loads+1;end
   if(jv)begin if(job!==gold[jobs%2]||cc-1-start_edge!=(jobs%2==0?10:310))begin errors=errors+1;$display("JOB_PHASE got%0d idx%0d",cc-1-start_edge,jobs);end jobs=jobs+1;end
   if(root.u_native.dec)begin if(root.u_native.jq!==gold[traces%2])errors=errors+1;traces=traces+1;end
   if(rdone)rootdones=rootdones+1;if(done)progdone=progdone+1;
  end
  #1;unw=0;une=0;
  // Control-only native SCRD/GO responder. No numerical leaf or VM model claim.
  if(dnw[172]&&dnw[171:169]==2)begin unw={1'b1,1'b0,2'b0,dnw[168:161],3'b0,256'd0};scalars=scalars+1;end
  if(dnw[172]&&dnw[171:169]==3)finwait=5;
  if(finwait>0)begin finwait=finwait-1;if(finwait==0)begin unw={15'b000000000000110,256'd0};une=unw;end end
 end
 task automatic tick;@(negedge clk);#2;endtask
 task automatic reset_all;begin rst_n=0;av=0;wv=0;measuring=0;repeat(5)tick;rst_n=1;repeat(80)tick;end endtask
 task automatic write32(input[11:0]a,input[31:0]d,input integer bad);
 begin
  tick;aa=a;wd=d;
  fork
   begin av=1;do @(posedge clk);while(!awr);tick;av=0;end
   begin wv=1;do @(posedge clk);while(!wr);tick;wv=0;end
  join
  while(!bv)tick;
  if(bres!==(bad?2'b10:2'b00))$fatal(1,"native host response mismatch a=%h response=%h",a,bres);
  tick;
 end endtask
 task automatic frame256(input[255:0]w);begin for(integer k=0;k<8;k=k+1)write32(12'hf24,w[k*32+:32],0);end endtask
 reg[255:0]hi,lo,config_word;
 initial begin
  $readmemh("actual_post_jobs.mem",gold);entries[0]={32'd200,32'd10,gold[0]};entries[1]={32'd500,32'd310,gold[1]};mut_data=$test$plusargs("MUT_DATA");mut_high=$test$plusargs("MUT_HIGH");
  reset_all();write32(12'hf30,1,1);repeat(8)tick;if(!hfault||jobs!=0)$fatal(1,"premature host launch escaped");
  reset_all();measuring=1;write32(12'hf20,224,0);
  for(integer row=0;row<2;row=row+1)begin lo=entries[row][255:0];hi={231'd0,entries[row][280:256]};if(row==0&&mut_data)lo=lo^256'd32;if(row==0&&mut_high)hi=hi^(256'd1<<100);frame256(lo);frame256(hi);end
  write32(12'hf20,(512<<8)|224,0);config_word=(256'(32'h46323137)<<32)|(256'd1<<24)|(256'd24<<9)|256'd2;frame256(config_word);
  write32(12'hf28,4<<12,0);write32(12'hf2c,1,0);repeat(16)tick;if(!ready||!srdy[0]||hfault||fault)$fatal(1,"native ready/status not validated");
  write32(12'hf30,1,0);repeat(530)tick;
  if(progdone!=1||jobs!=2||rootdones!=2)$fatal(1,"cold native completion missing jobs%0d root%0d programme%0d",jobs,rootdones,progdone);
  // Warm re-arm uses same installed programme: descriptor/launch only, no SRAM rewrite.
  write32(12'hf28,4<<12,0);write32(12'hf2c,1,0);repeat(16)tick;if(!ready)$fatal(1,"warm native ready missing");write32(12'hf30,1,0);repeat(530)tick;measuring=0;
  $display("NATIVE_BOOT_RESULT checks=%0d errors=%0d writes=%0d jobs=%0d traces=%0d root_done=%0d programme_done=%0d scalar_returns=%0d clock_ps=833",checks,errors,loads,jobs,traces,rootdones,progdone,scalars);
  if(errors||loads!=2||jobs!=4||traces!=4||rootdones!=4||progdone!=2||scalars!=72)$fatal(1,"NATIVE_BOOT FAIL");
  $display("NATIVE_BOOT PASS native ingress/leaf/target/twoSRAMprovider/root; current targetallocation and4rolecalendar unbound");$finish;
 end
endmodule
