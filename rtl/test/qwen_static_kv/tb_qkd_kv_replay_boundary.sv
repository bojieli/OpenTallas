`timescale 1ps/1fs
// Minimal real ABI join, one whole eight-sector block. Independent declared
// PC0 source-legal reservations precede first refresh. No PROFILE discovery.
// Actual controller/pcport/ECC + 4x8 front + dual-clock ring; PHY alone modeled.
module tb_qkd_kv_replay_boundary;
 reg hbm=0;always #512 hbm=~hbm;
 integer phase=137,mode=0,jitter=16;
 reg core=0;initial begin
  void'($value$plusargs("phase=%d",phase));
  #(phase);forever #416.667 core=~core;
 end
 reg reset=0,runreset=0;
 reg hw=0,hs=0,hstart=0,cw=0,cs=0,cstart=0;
 reg[5:0]ha=0,ca=0;reg[31:0]ht=0,ct=0;
 reg[63:0]hd=0;reg[32:0]cd=0;
 wire[63:0]hp;wire[32:0]cp;
 wire hc,haction,hdo,hfault,cc,caction,cdo,cfault;
 wire[31:0]hcycle,ccycle;
 qkd_kv_calendar_replay hprog(.ck(hbm),.rst_n(reset),.cfg_we(hw),.cfg_seal(hs),.cfg_addr(ha),.cfg_time(ht),.cfg_payload(hd),.start(hstart),.payload(hp),.configured(hc),.active(haction),.done(hdo),.fault(hfault),.cycle(hcycle));
 qkd_kv_calendar_replay #(.WIDTH(33)) cprog(.ck(core),.rst_n(reset),.cfg_we(cw),.cfg_seal(cs),.cfg_addr(ca),.cfg_time(ct),.cfg_payload(cd),.start(cstart),.payload(cp),.configured(cc),.active(caction),.done(cdo),.fault(cfault),.cycle(ccycle));
 wire[327:0]po;wire[293:0]co;wire[260:0]er;
 reg[288:0]pi=0;
 wire ctrl_fault,cv,cwe,cf,ic,ih,dc,dh;
 wire nominal_raw,nominal_corrected;wire[15:0]cal_epoch,actual_epoch;
 qkd_static_kv_return_calendar predictor(.pll_hbm(hbm),.hrst(runreset),
  .reserved_rd(hp[43]),.reserved_static_read(1'b0),.reservation_epoch(16'd7),
  .expected_raw_valid(nominal_raw),.compiled_hbm_put(nominal_corrected),.expected_return_epoch(cal_epoch));
 qkd_ctrl_pc_host_static #(.ELASTIC(1),.PROFILE(0)) controller(
  .pll_hbm(hbm),.hrst(runreset),.ck(core),.rsi(runreset),.pc(5'd0),.ci(319'd0),.co(co),
  .es(288'd0),.er(er),.po(po),.pi(pi),.ki(33'd0),.ko(),.fi(1'b0),.fo(ctrl_fault),
  .static_cmd_owner(runreset),.static_cmd(hp[42:0]),.reserved_rd(hp[43]),
  .reserved_static_col(hp[44]),.reserved_write_col(hp[45]),.static_epoch(16'd7),
  .expected_raw_valid(nominal_raw),.cfg_stack(2'd0),.es_context(318'd0),
  .es_expected_valid(1'b0),.es_expected_identity(61'd0),.es_expected_address(29'd0),
  .es_expected_pc(5'd0),.es_expected_stack(2'd0),.native_commit_valid(),.native_commit_identity(),
  .native_commit_address(),.corrected_epoch(actual_epoch),.completion_v(cv),.completion_we(cwe),
  .completion_fault(cf),.idle_core(ic),.idle_hbm(ih),.drain_fault_core(dc),.drain_fault_hbm(dh));
 wire[293:0]fc;wire[15:0]fe;wire put,freed,hold,ovf,gof,fi;
 wire[15:0]stall;wire[5:0]occ;
 qkd_kv_hbm_elastic_front front(.pll_hbm(hbm),.hrst(runreset),.co_in(co),.epoch_in(actual_epoch),
  .blk_go(hp[62]),.co_out(fc),.epoch_out(fe),.compiled_hbm_put(put),.blk_freed(freed),
  .hold(hold),.stall_edges(stall),.occupancy(occ),.idle(fi),.fault_overflow(ovf),.fault_go(gof));
 wire valid,rhf,rcf,rih,ric;wire[9:0]sector;wire[15:0]epoch;wire[5:0]layer;wire[255:0]payload;
 qkd_static_kv_return_slots ring(.pll_hbm(hbm),.hrst(runreset),.ck(core),.rsi(runreset),
  .controller_co(fc),.controller_epoch(fe),.compiled_hbm_put(put),
  .expected_put(cp[0]),.expected_sector(cp[10:1]),.expected_epoch(cp[26:11]),.expected_layer(cp[32:27]),
  .actual_valid(valid),.actual_sector(sector),.actual_epoch(epoch),.actual_layer(layer),
  .actual_data(payload),.fault_hbm(rhf),.fault_core(rcf),.idle_hbm(rih),.idle_core(ric));
 function automatic[255:0]data(input integer sec);
  for(integer i=0;i<8;i++)data[i*32+:32]=32'h7a31d980 ^ (sec*71+i*31);
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
 reg[18:0]rows[0:31];reg due[0:1023];reg[287:0]words[0:1023];
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
    if(rows[po[34:30]]!=67||sec!=reads||po[29])bad("PHY command identity");
    if(hcycle!=64+reads)bad($sformatf("PHY command edge c%0d expected%0d",hcycle,64+reads));
    // PO is observed after its launch edge; RL23 response is presented after
    // edge+23 and captured at edge+24. Preserve in-order PHY delivery.
    if(reads>0&&target<=last_due)target=last_due+1;
    if(mode==4&&reads==7)target+=32;
    last_due=target;due[target]=1;words[target]=encode(data(sec));reads++;
   end
   if(co[0])begin
    if(actual_epoch!=7||{co[11:9],co[7:1]}!=lands||co[281:26]!==data(lands))bad("corrected controller payload");lands++;
   end
   if(haction&&put !== (hcycle>=119&&hcycle<127))bad($sformatf("front release edge c%0d put%0d",hcycle,put));
   if(put)puts++;if(freed)frees++;if(occ>maxocc)maxocc=occ;
   if(ctrl_fault||cf||dc||dh||ovf||gof||rhf)bad("actual controller/front/ring sticky fault");
  end
 end
 integer last_due=0;
 always @(posedge core)begin
  #0.001;
  if(runreset&&valid)begin
   if(sector!=returns||epoch!=7||layer!=3||payload!==data(returns))bad("CORE exact payload/metadata");returns++;
  end
  if(runreset&&rcf)bad("CORE ring fault");
 end
 task automatic hword(input integer address,t,input[63:0]w);
  hw=1;ha=6'(address);ht=32'(t);hd=w;@(negedge hbm);
 endtask
 integer core_first;
 initial begin
  void'($value$plusargs("mode=%d",mode));void'($value$plusargs("jit=%d",jitter));
  for(integer i=0;i<1024;i++)begin due[i]=0;words[i]=0;end
  for(integer i=0;i<32;i++)rows[i]=0;
  repeat(4)@(negedge hbm);reset=1;repeat(4)@(negedge hbm);
  // Exact leaf origins: HBM edge index101; CORE edge index101.
  // Core expected stream starts at least160 HBM periods after HBM origin.
  core_first=$rtoi($ceil(((101.5*1024.0+160*1024.0)-(phase+416.667+101*833.334))/833.334));
  fork
   begin
    hword(0,10,(64'd8<<20)|(64'd67<<1)|1);
    hword(1,40,(64'd1<<31)|1);
    for(integer i=0;i<8;i++)hword(i+2,60+i+(mode==1?1:0),64'd1<<43);
    hword(10,115+(mode==2?-1:0),64'd1<<62);
    hw=0;hs=1;ht=300;@(negedge hbm);hs=0;
   end
   begin
    @(negedge core);
    for(integer i=0;i<8;i++)begin
     cw=1;ca=6'(i);ct=32'(core_first+i);
     cd={6'd3,16'd7,10'(i^(mode==3?1:0)),1'b1};@(negedge core);
    end
    cw=0;cs=1;ct=500;@(negedge core);cs=0;
   end
  join
  if(!hc||!cc)begin repeat(3)@(negedge hbm);if(!hc||!cc)$fatal(1,"boot not sealed");end
  // Start each domain at its predetermined edge, independently of results.
  fork
   begin wait(hedge==100);@(negedge hbm);runreset=1;hstart=1;@(negedge hbm);hstart=0;end
   begin
    // Last negative edge before external CORE start pin capture index100.
    #(phase+100*833.334-$realtime);#0.001;cstart=1;@(negedge core);cstart=0;
   end
  join
  repeat(450)@(negedge hbm);
  $display("MEASURE mode%0d phase%0d jit%0d reads%0d lands%0d puts%0d returns%0d frees%0d stall%0d maxocc%0d errors%0d corefirst%0d",mode,phase,jitter,reads,lands,puts,returns,frees,stall,maxocc,errors,core_first);
  if(reads!=8||lands!=8||puts!=8||returns!=8||frees!=1||stall||errors||hfault||cfault||!fi||!rih||!ric)$fatal(1,"BOUNDARY_FAIL");
  $display("PASS actual replay/controller/front/ring component one8-sector block; no production schedule/physical claim");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
