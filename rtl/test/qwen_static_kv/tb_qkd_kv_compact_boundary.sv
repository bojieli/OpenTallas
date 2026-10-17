`timescale 1ps/1fs
// Actual compact mapped-calendar ABI join: source-constrained full512
// sectors per layer; persistent PC0 refresh/bank state. No PROFILE discovery.
// Actual controller/pcport/ECC + 4x8 front + dual-clock ring; PHY alone modeled.
module tb_qkd_kv_compact_boundary;
 parameter integer MUT=0;
 `include "params.svh"
 string image_dir;
 reg[255:0]himage[0:639],cimage[0:639];
 integer hexpected[0:18431],fexpected[0:18431],cexpected[0:18431];
 reg hbm=0;always #512 hbm=~hbm;
 integer phase=137,mode=0,jitter=16;
 reg core=0;initial begin
  void'($value$plusargs("phase=%d",phase));
  #(phase);forever #416.667 core=~core;
 end
 reg reset=0,runreset=0;
 reg hw=0,hs=0,hstart=0,cw=0,cs=0,cstart=0;
 reg[9:0]ha=0,ca=0;reg[255:0]hd=0,cd=0;
 wire hc,haction,hdo,hfault,cc,caction,cdo,cfault;
 wire[31:0]hcycle,ccycle;wire[42:0]hcmd;
 wire rdslot,srslot,wrslot,bgo,owner,cput;wire[9:0]csector;wire[15:0]sepoch,cepoch;wire[5:0]clayer;
 qkd_kv_compact_reader #(.FRAME(FRAME),.STAGES(NSTAGES),.MUT(MUT)) programme(
  .pll_hbm(hbm),.ck(core),.rst_n(reset),
  .h_we(hw),.h_seal(hs),.h_row(ha),.h_data(hd),.h_bytes(15'(HBYTES)),.h_stop(32'(HSTOP)),.h_start(hstart),
  .c_we(cw),.c_seal(cs),.c_row(ca),.c_data(cd),.c_bytes(15'(CBYTES)),.c_stop(32'(CSTOP)),.c_start(cstart),.epoch(16'd7),
  .configured_h(hc),.configured_c(cc),.active_h(haction),.active_c(caction),.done_h(hdo),.done_c(cdo),
  .fault_h(hfault),.fault_c(cfault),.cycle_h(hcycle),.cycle_c(ccycle),.static_cmd(hcmd),.static_cmd_owner(owner),
  .reserved_rd(rdslot),.reserved_static_col(srslot),.reserved_write_col(wrslot),.blk_go(bgo),.static_epoch(sepoch),
  .expected_put(cput),.expected_sector(csector),.expected_epoch(cepoch),.expected_layer(clayer));
 wire[327:0]po;wire[293:0]co;wire[260:0]er;
 reg[288:0]pi=0;
 wire ctrl_fault,cv,cwe,cf,ic,ih,dc,dh;
 wire nominal_raw,nominal_corrected;wire[15:0]cal_epoch,actual_epoch;
 qkd_static_kv_return_calendar predictor(.pll_hbm(hbm),.hrst(runreset),
  .reserved_rd(rdslot),.reserved_static_read(1'b0),.reservation_epoch(16'd7),
  .expected_raw_valid(nominal_raw),.compiled_hbm_put(nominal_corrected),.expected_return_epoch(cal_epoch));
 qkd_ctrl_pc_host_static #(.ELASTIC(1),.PROFILE(0)) controller(
  .pll_hbm(hbm),.hrst(runreset),.ck(core),.rsi(runreset),.pc(5'd0),.ci(319'd0),.co(co),
  .es(288'd0),.er(er),.po(po),.pi(pi),.ki(33'd0),.ko(),.fi(1'b0),.fo(ctrl_fault),
  .static_cmd_owner(owner),.static_cmd(hcmd),.reserved_rd(rdslot),
  .reserved_static_col(srslot),.reserved_write_col(wrslot),.static_epoch(sepoch),
  .expected_raw_valid(nominal_raw),.cfg_stack(2'd0),.es_context(318'd0),
  .es_expected_valid(1'b0),.es_expected_identity(61'd0),.es_expected_address(29'd0),
  .es_expected_pc(5'd0),.es_expected_stack(2'd0),.native_commit_valid(),.native_commit_identity(),
  .native_commit_address(),.corrected_epoch(actual_epoch),.completion_v(cv),.completion_we(cwe),
  .completion_fault(cf),.idle_core(ic),.idle_hbm(ih),.drain_fault_core(dc),.drain_fault_hbm(dh));
 wire[293:0]fc;wire[15:0]fe;wire put,freed,hold,ovf,gof,fi;
 wire[15:0]stall;wire[5:0]occ;
 qkd_kv_hbm_elastic_front front(.pll_hbm(hbm),.hrst(runreset),.co_in(co),.epoch_in(actual_epoch),
  .blk_go(bgo),.co_out(fc),.epoch_out(fe),.compiled_hbm_put(put),.blk_freed(freed),
  .hold(hold),.stall_edges(stall),.occupancy(occ),.idle(fi),.fault_overflow(ovf),.fault_go(gof));
 wire valid,rhf,rcf,rih,ric;wire[9:0]sector;wire[15:0]epoch;wire[5:0]layer;wire[255:0]payload;
 qkd_static_kv_return_slots ring(.pll_hbm(hbm),.hrst(runreset),.ck(core),.rsi(runreset),
  .controller_co(fc),.controller_epoch(fe),.compiled_hbm_put(put),
  .expected_put(cput),.expected_sector(csector),.expected_epoch(cepoch),.expected_layer(clayer),
  .actual_valid(valid),.actual_sector(sector),.actual_epoch(epoch),.actual_layer(layer),
  .actual_data(payload),.fault_hbm(rhf),.fault_core(rcf),.idle_hbm(rih),.idle_core(ric));
 function automatic integer sec_of(input integer n);
  integer o;begin o=n%512;sec_of=o<256?o:512+(((o-256)&8)<<4)+(((o-256)>>4)<<3)+((o-256)&7);end
 endfunction
 function automatic[255:0]data(input integer row,sec);
  for(integer i=0;i<8;i++)data[i*32+:32]=32'h7a31d980 ^ (row*65537+sec*71+i*31);
 endfunction
 function automatic[71:0]ecc(input[63:0]d);
  reg[71:0]c;integer j;begin
   c=0;j=0;for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin c[p-1]=d[j];j++;end
   for(integer k=0;k<7;k++)for(integer p=1;p<=71;p++)if((p&(1<<k))!=0)c[(1<<k)-1]^=c[p-1];
   c[71]=^c[70:0];ecc=c;
  end
 endfunction
 function automatic[287:0]encode(input[255:0]d);
  for(integer i=0;i<4;i++)encode[i*72+:72]=ecc(d[i*64+:64]);
 endfunction
 integer hedge=0,reads=0,lands=0,puts=0,returns=0,frees=0,errors=0,maxocc=0;
 reg[18:0]rows[0:31];reg due[0:HSTOP+2560];reg[287:0]words[0:HSTOP+2560];
 task automatic bad(input string message);
  if(errors<12)$display("BAD %s",message);errors++;
 endtask
 always @(negedge hbm)pi={words[hedge+1],due[hedge+1]};
 always @(posedge hbm)begin
  hedge++;
  #0.001;
  if(runreset)begin
   if(po[0]&&po[3:1]==1)rows[po[8:4]]=po[27:9];
   if(po[28])begin
    automatic integer sec=((po[34:30]>>2)<<7)|(po[39:35]<<2)|(po[34:30]&3);
    automatic integer extra=(reads*5+3)%(jitter+1);
    automatic integer target=hedge+24+extra;
    if(rows[po[34:30]]!=64+reads/512||sec!=sec_of(reads)||po[29])bad("PHY command identity");
    if(hcycle!=hexpected[reads]+4)bad($sformatf("PHY command edge c%0d expected%0d",hcycle,hexpected[reads]+4));
    // PO is observed after its launch edge; RL23 response is presented after
    // edge+23 and captured at edge+24. Preserve in-order PHY delivery.
    if(reads>0&&target<=last_due)target=last_due+1;
    if(mode==4&&reads==7)target+=32;
    last_due=target;due[target]=1;words[target]=encode(data(rows[po[34:30]],sec));reads++;
   end
   if(co[0])begin
    if(actual_epoch!=7||{co[11:9],co[7:1]}!=sec_of(lands)||co[17:12]!=lands/512||co[281:26]!==data(64+lands/512,sec_of(lands)))bad("corrected controller payload");lands++;
   end
   if(haction&&put !== (puts<NEVENTS&&hcycle==fexpected[puts]))bad($sformatf("front release edge c%0d put%0d next%0d",hcycle,put,fexpected[puts]));
   if(put)puts++;if(freed)frees++;if(occ>maxocc)maxocc=occ;
   if(ctrl_fault||cf||dc||dh||ovf||gof||rhf)bad("actual controller/front/ring sticky fault");
  end
 end
 integer last_due=0,core_checks=0;
 always @(posedge core)begin
  #0.001;
  if(runreset&&caction&&cput)begin
   if(ccycle!=cexpected[core_checks])bad("CORE programme slot cycle");core_checks++;
  end
  if(runreset&&valid)begin
   if(sector!=sec_of(returns)||epoch!=7||layer!=returns/512||payload!==data(64+returns/512,sec_of(returns)))bad("CORE exact payload/metadata");returns++;
  end
  if(runreset&&rcf)bad("CORE ring fault");
 end
 initial begin
  void'($value$plusargs("mode=%d",mode));void'($value$plusargs("jit=%d",jitter));
  if(!$value$plusargs("image=%s",image_dir))$fatal(1,"image required");
  $readmemh({image_dir,"/hbm.hex"},himage,0,HROWS-1);$readmemh({image_dir,"/core.hex"},cimage,0,CROWS-1);
  begin integer fd;
   fd=$fopen({image_dir,"/hbm_expected.mem"},"r");for(integer i=0;i<NEVENTS;i++)if($fscanf(fd,"%d\n",hexpected[i])!=1)$fatal(1,"hbm expected");$fclose(fd);
   fd=$fopen({image_dir,"/front_expected.mem"},"r");for(integer i=0;i<NEVENTS;i++)if($fscanf(fd,"%d\n",fexpected[i])!=1)$fatal(1,"front expected");$fclose(fd);
   fd=$fopen({image_dir,"/core_expected.mem"},"r");for(integer i=0;i<NEVENTS;i++)if($fscanf(fd,"%d\n",cexpected[i])!=1)$fatal(1,"core expected");$fclose(fd);
  end
  for(integer i=0;i<HSTOP+2561;i++)begin due[i]=0;words[i]=0;end
  for(integer i=0;i<32;i++)rows[i]=0;
  repeat(4)@(negedge hbm);reset=1;repeat(4)@(negedge hbm);
  fork
   begin
    for(integer i=0;i<HROWS;i++)begin hw=1;ha=10'(i);hd=himage[i];@(negedge hbm);end
    hw=0;hs=1;@(negedge hbm);hs=0;
   end
   begin
    @(negedge core);
    for(integer i=0;i<CROWS;i++)begin cw=1;ca=10'(i);cd=cimage[i];@(negedge core);end
    cw=0;cs=1;@(negedge core);cs=0;
   end
  join
  if(!hc||!cc)begin repeat(8)@(negedge hbm);if(!hc||!cc)$fatal(1,"boot not sealed");end
  // Start each domain at its predetermined edge, independently of results.
  fork
   begin wait(hedge==2048);@(negedge hbm);runreset=1;hstart=1;@(negedge hbm);hstart=0;end
   begin
    // Last negative edge before external CORE start pin capture index100.
    #(phase+2516*833.334-$realtime);#0.001;cstart=1;@(negedge core);cstart=0;
   end
  join
  repeat(HSTOP+100)@(negedge hbm);
  $display("MEASURE mode%0d phase%0d jit%0d reads%0d lands%0d puts%0d returns%0d frees%0d stall%0d maxocc%0d errors%0d",mode,phase,jitter,reads,lands,puts,returns,frees,stall,maxocc,errors);
  if(reads!=NEVENTS||lands!=NEVENTS||puts!=NEVENTS||returns!=NEVENTS||frees!=NEVENTS/8||stall||errors||hfault||cfault||!fi||!rih||!ric)$fatal(1,"BOUNDARY_FAIL");
  $display("PASS compact mapped-SRAM/source-resource controller/front/ring full512 read-only programme; native HOST/writer/consumer/physical join OPEN");$finish;
 end
 initial begin #(HSTOP*1024+10000000);$fatal(1,"timeout");end
endmodule
