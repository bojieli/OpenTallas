`timescale 1ns/1ps
// KVJ-A 10-17: the dispatcher successor composed with the ACTUAL 160 boot CDCs
// (32 front HAS_SEAL=0 + 128 controller HAS_SEAL=1) and qkd_static_kv_boot_observe,
// exactly as kv_static_boot_join.py joins them: sink_applied/sink_fault come from
// the observer, never from the bench. HBM side runs on its own clock (625:768).
// Every HBM sink word is scoreboarded (order, address, data, seal one edge after
// the controller's 32nd word, none for the front). setup_ready must rise.
// MUT=4 (no front_last, the pre-successor dispatcher) must never reach setup.
module tb_static_boot_dispatch_cdc;
 parameter integer MUT=0;
 reg ck=0,hck=0;always #0.625 ck=~ck;always #0.768 hck=~hck;
 reg rst=0,hrst=0;reg[142:0]pr=0;reg[3:0]target=1;reg ready=0,active=0;
 reg[15:0]epoch=77;reg[63:0]digest=0;reg[2:0]configured=0;
 wire lw,ww,ow;wire[8:0]la;wire[7:0]wa,ga,ca;wire[1:0]oa;wire[63:0]ld,wd,gd,cd;wire[31:0]od,lwe,fwe,flast;
 wire[127:0]cwe,clast;wire setup,fault;wire[7:0]code;wire[15:0]ie;wire[63:0]id;
 wire[159:0]applied_core,applied_hbm,fault_hbm,fault_leaf;wire obs_fault;
 qkd_static_kv_boot_dispatch #(.MUT(MUT))dut(.ck(ck),.rst_n(rst),.boot_pr(pr),.boot_image_target(target),.boot_image_ready(ready),
  .boot_image_fault(1'b0),.boot_image_epoch(epoch),.boot_image_digest(digest),.execution_active(active),.sink_applied(applied_core),
  .local_configured(configured),.sink_fault(obs_fault),.layer_we(lw),.layer_addr(la),.layer_data(ld),.writer_we(ww),.writer_addr(wa),
  .writer_data(wd),.ownership_we(ow),.ownership_addr(oa),.ownership_data(od),.landing_we(lwe),.front_we(fwe),.group_addr(ga),
  .group_data(gd),.controller_we(cwe),.controller_addr(ca),.controller_data(cd),.controller_last(clast),.front_last(flast),
  .setup_ready(setup),.fault(fault),.fault_code(code),.installed_epoch(ie),.installed_isa_digest(id));
 wire[159:0]swe,sseal;wire[8*160-1:0]saddr;wire[64*160-1:0]sdata;
 genvar g;
 generate for(g=0;g<160;g=g+1)begin:q
  if(g<32)begin:f
   qkd_static_kv_boot_cdc #(.HAS_SEAL(0))u(.ck(ck),.rst_n(rst),.hck(hck),.hrst_n(hrst),.cfg_we(fwe[g]),.cfg_addr(ga),.cfg_data(gd),
    .cfg_last(flast[g]),.sink_we(swe[g]),.sink_addr(saddr[8*g+:8]),.sink_data(sdata[64*g+:64]),.sink_seal(sseal[g]),
    .applied_hbm(applied_hbm[g]),.fault_core(fault_leaf[g]),.fault_hbm(fault_hbm[g]));
  end else begin:c
   qkd_static_kv_boot_cdc #(.HAS_SEAL(1))u(.ck(ck),.rst_n(rst),.hck(hck),.hrst_n(hrst),.cfg_we(cwe[g-32]),.cfg_addr(ca),.cfg_data(cd),
    .cfg_last(clast[g-32]),.sink_we(swe[g]),.sink_addr(saddr[8*g+:8]),.sink_data(sdata[64*g+:64]),.sink_seal(sseal[g]),
    .applied_hbm(applied_hbm[g]),.fault_core(fault_leaf[g]),.fault_hbm(fault_hbm[g]));
  end
 end endgenerate
 qkd_static_kv_boot_observe obs(.ck(ck),.rst_n(rst),.applied_hbm(applied_hbm),.fault_hbm(fault_hbm),.fault_leaf_core(fault_leaf),
  .applied_core(applied_core),.fault_core(obs_fault));
 function automatic[63:0]value(input integer t,input integer a);value=(t==3)?64'(a):64'h1234567800000000^(64'(t)<<32)^64'(a);endfunction
 // HBM-domain scoreboard
 integer cnt[0:159],seal_due[0:159],errors=0,words=0,seals=0,k;
 initial for(k=0;k<160;k=k+1)begin cnt[k]=0;seal_due[k]=0;end
 always @(posedge hck)begin #0.01;
  for(k=0;k<160;k=k+1)begin
   if(sseal[k])begin seals=seals+1;if(k<32||seal_due[k]!=1)errors=errors+1;end
   if(seal_due[k]>0)seal_due[k]=seal_due[k]-1;
   if(swe[k])begin
    words=words+1;
    if(k<32)begin
     if(saddr[8*k+:8]!==8'(cnt[k])||sdata[64*k+:64]!==value(5,6*k+cnt[k])||cnt[k]>5)errors=errors+1;
    end else begin
     if(saddr[8*k+:8]!==8'(cnt[k])||sdata[64*k+:64]!==value(6+(k-32)/32,32*((k-32)%32)+cnt[k])||cnt[k]>31)errors=errors+1;
     if(cnt[k]==31)seal_due[k]=1;
    end
    cnt[k]=cnt[k]+1;
   end
  end
 end
 integer t,a,n,e;
 task tick;begin @(posedge ck);#0.1;end endtask
 initial begin
  repeat(4)tick();@(negedge ck);rst=1;hrst=1;repeat(4)tick();
  for(t=1;t<=9;t=t+1)begin
   case(t)1:n=327;2:n=181;3:n=4;4,5:n=192;default:n=1024;endcase
   @(negedge ck);ready=0;target=4'(t);
   for(a=0;a<n;a=a+1)begin pr=0;pr[74]=1;pr[73:64]=10'(a);pr[63:0]=value(t,a);tick();@(negedge ck);end
   pr=0;tick();@(negedge ck);ready=1;digest=64'(t);tick();tick();if(fault)$fatal(1,"valid replay faulted %h",code);
  end
  @(negedge ck);ready=0;target=0;tick();@(negedge ck);ready=1;digest=64'h0123456789abcdef;configured=7;
  for(e=0;e<400&&!setup;e=e+1)tick();
  if(fault||obs_fault)$fatal(1,"CDC/observer fault code%h obs%0d",code,obs_fault);
  if(!setup)begin
   if(MUT==4)$fatal(1,"MUT4: setup never rose (front CDCs applied %0d/32)",$countones(applied_core[31:0]));
   $fatal(1,"FAIL setup_ready never rose applied %0d/160",$countones(applied_core));
  end
  if(MUT!=0)$fatal(1,"mutant escaped");
  repeat(20)tick();
  for(k=0;k<160;k=k+1)if(cnt[k]!=((k<32)?6:32))errors=errors+1;
  if(errors||seals!=128||words!=32*6+128*32)$fatal(1,"FAIL scoreboard errors%0d seals%0d words%0d",errors,seals,words);
  if(ie!=77||id!=64'h0123456789abcdef)$fatal(1,"installed epoch/digest");
  $display("PASS dispatcher+160 boot_cdc+observe: setup_ready after %0d core edges, %0d HBM sink words exact, 128 seals, 32 front applied without seal",e,words);
  $finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
