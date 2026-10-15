`timescale 1ns/1ps
// HANDOFF 0az parent proof: HBM-backed KV boundary with VARIABLE PHY return
// latency. Actual persistent controller qkd_ctrl_pc_host_static (ELASTIC=1),
// actual pcport/landing ECC/tag queue, qkd_kv_hbm_elastic_front block buffer
// and the unchanged fixed dual-clock ring qkd_static_kv_return_slots.
// The off-chip HBM model stores ACTUAL PHY write data and returns reads in
// order at RL23 + a per-read random extra latency in [0,JIT] (production) or
// beyond it (exceptional modes). Every internal slot is compiled from the RD
// reservation calendar ONLY: blk_go = nominal corrected landing of the block's
// last sector + GO_DLY edges; core slots = the compiled release model. No
// actual arrival, ready or publication selects any internal slot.
// faultmode: 0 production (must PASS, zero stalls), 2 one read late beyond the
// window (hold observed, data intact at the front, then must report), 3
// historical wiring (ring fed from calendar + raw co) under jitter (must FAIL),
// 5 one read earlier than nominal (controller must fault), 6 PHY silent beyond
// watchdog (must fault). Compile-time: FRONT_MUT 1..3, CTRL_ELASTIC 0 (FAIL).
module tb_kv_hbm_elastic_boundary;
 parameter integer FRONT_MUT=0, CTRL_ELASTIC=1, NBLK=4, BLK=8;
 localparam CYCLES=2600,RL=23;
 integer JIT=16,GO_DLY=0,seed=1,late_sector=300,maxocc=0,blocks_go=0,blocks_freed=0,putcount=0,first_go=-1;
 integer jit_hist[0:63];
 integer core_phase_ps=137;real CORE_FIRST;
 reg core=0;initial begin void'($value$plusargs("phase=%d",core_phase_ps));
  CORE_FIRST=(core_phase_ps+416.667)/1000.0;
  #(core_phase_ps/1000.0);forever #0.416667 core=~core;end
 reg late_calendar;always @(posedge ck)late_calendar<=predicted_corrected;
 wire[293:0] observed_co={co[1][293:1],co[1][0]&&!(mode==107&&publish_ordinal==80)};
 reg expected_core_put=0;reg[9:0] expected_core_sector=0;
 reg[9:0] core_sector[0:10000];reg core_slots[0:10000];
 wire return_valid,return_hfault,return_cfault;wire[9:0] return_sector;
 wire[15:0] return_epoch;wire[5:0] return_layer;wire[255:0] return_data;
 integer core_edge=0,returned_count=0,publish_ordinal=0;
 integer core_fault_seen=0,front_ordinal=0,front_bad=0;
 wire expect_fail=(mode==2||mode==3||mode==5||mode==6||CTRL_ELASTIC==0||FRONT_MUT!=0);
 reg model_put=0;reg model_arr[0:CYCLES+400];reg go_arr[0:CYCLES+400];reg blk_go=0;
 wire[293:0] f_co;wire[15:0] f_epoch;wire f_put,f_freed,f_hold,f_ovf,f_gofault;wire[15:0] f_stall;wire[$clog2(NBLK*BLK):0] f_occ;
 qkd_kv_hbm_elastic_front #(.NBLK(NBLK),.BLK(BLK),.STRIDE(1),.MUT(FRONT_MUT)) u_front(.pll_hbm(ck),.hrst(rst[1]),
  .co_in(co[1]),.epoch_in(out_epoch[1]),.blk_go(blk_go),.co_out(f_co),.epoch_out(f_epoch),.compiled_hbm_put(f_put),
  .blk_freed(f_freed),.hold(f_hold),.stall_edges(f_stall),.occupancy(f_occ),.fault_overflow(f_ovf),.fault_go(f_gofault));
 qkd_static_kv_return_slots u_return(.pll_hbm(ck),.hrst(rst[1]),.ck(core),.rsi(rst[1]),
 .controller_co(mode==3?co[1]:f_co),.controller_epoch(mode==3?out_epoch[1]:f_epoch),.compiled_hbm_put(mode==3?predicted_corrected:f_put),
 .expected_put(expected_core_put),.expected_sector(expected_core_sector),.expected_epoch(16'd7),.expected_layer(6'd3),
 .actual_valid(return_valid),.actual_sector(return_sector),.actual_epoch(return_epoch),.actual_layer(return_layer),
 .actual_data(return_data),.fault_hbm(return_hfault),.fault_core(return_cfault));
 initial for(integer c=0;c<=10000;c++)begin core_slots[c]=0;core_sector[c]=0;end
 // Future CORE commands are compiled from the predictor's fixed HBM edges,
 // never from actual controller_co, PHY return, publication or readiness.
 always @(posedge ck)if(rst[1]&&(mode==3?predicted_corrected:model_put))begin
  automatic real target=($realtime+1.024+2*0.833334-CORE_FIRST)/0.833334;
  automatic integer c=$rtoi($ceil(target));
  automatic integer o=publish_ordinal-256;
  automatic integer sec=publish_ordinal<256?publish_ordinal:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
  if(core_slots[c])$fatal(1,"compiled core slot collision");
  core_slots[c]=1;core_sector[c]=10'(sec);
  if($test$plusargs("report_calendar"))$display("COMPILED_RETURN ordinal%0d sector%0d core%0d",publish_ordinal,sec,c);
  publish_ordinal++;
 end
 always @(negedge core)begin
  // First positive edge is index0. After a negative edge, core_edge points
  // at the next positive edge, which samples this fixed calendar pin.
  expected_core_put=core_slots[core_edge];expected_core_sector=core_sector[core_edge];
 end
 always @(posedge core)begin
  core_edge++;
  #0.001;
  if(rst[1]&&return_valid)begin
   if(return_epoch!=7||return_layer!=3||return_data!==data(67,return_sector))begin
    if(expect_fail)core_fault_seen=1;
    else $fatal(1,"actual controller dual-clock return metadata/data");
   end
   returned_count++;
  end
  if(rst[1]&&(return_hfault||return_cfault))begin
   if(expect_fail)core_fault_seen=1;
   else begin $display("FAIL dual-clock slot fault at core%0d",core_edge);$fatal(1);end
  end
 end
 reg ck=0;always #0.512 ck=~ck;
 reg [1:0] rst=0;
 reg owner=0;reg [42:0] cmd=0;reg reserved=0,sr_reserved=0,wr_reserved=0;
 reg [287:0] es=0;reg [288:0] pi=0;
 wire [327:0] po[0:1];wire [293:0] co[0:1];wire [260:0] er[0:1];wire [1:0] fault,cv,cw,cf;
 wire predicted_raw,predicted_corrected;wire[15:0] predicted_epoch;
 qkd_static_kv_return_calendar u_calendar(.pll_hbm(ck),.hrst(rst[1]),
  .reserved_rd(reserved),.reserved_static_read(mode==108?1'b0:sr_read_reserved),.reservation_epoch(16'd7),
  .expected_raw_valid(predicted_raw),.compiled_hbm_put(predicted_corrected),
  .expected_return_epoch(predicted_epoch));
 integer predicted_count;
 reg slots[0:CYCLES-1],srslots[0:CYCLES-1],wrslots[0:CYCLES-1],rawslots[0:CYCLES-1];
 reg sr_read_reserved=0;reg rawslot=0;wire [15:0] out_epoch[0:1];
 genvar g;
 generate for(g=0;g<2;g++)begin:controllers
  qkd_ctrl_pc_host_static #(.PROFILE(g==0?1:0),.ELASTIC(g==1?CTRL_ELASTIC:1))dut(
   .pll_hbm(ck),.hrst(rst[g]),.ck(ck),.rsi(rst[g]),.pc(5'd13),.ci(319'b0),.co(co[g]),
   .es(es),.er(er[g]),.po(po[g]),.pi(pi),.ki(33'b0),.ko(),.fi(1'b0),.fo(fault[g]),
   .static_cmd_owner(owner),.static_cmd(cmd),.reserved_rd(reserved),.reserved_static_col(sr_reserved),.reserved_write_col(wr_reserved),
   .static_epoch(16'd7),.expected_raw_valid(g==1 ? predicted_raw : rawslot),.cfg_stack(2'b0),.es_context(318'b0),.es_expected_valid(1'b0),.es_expected_identity(61'b0),.es_expected_address(29'b0),.es_expected_pc(5'b0),.es_expected_stack(2'b0),.native_commit_valid(),.native_commit_identity(),.native_commit_address(),.corrected_epoch(out_epoch[g]),.completion_v(cv[g]),.completion_we(cw[g]),.completion_fault(cf[g]));
 end endgenerate
 function automatic [255:0] data(input integer row,sector);
  for(integer i=0;i<8;i++)data[32*i+:32]=32'h981ac500^32'(row*65537)^32'(sector*71+i*31);
 endfunction
 function automatic [71:0] ecc(input [63:0] d);
  reg [71:0] c;integer j;begin
   c=0;j=0;for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin c[p-1]=d[j];j++;end
   for(integer k=0;k<7;k++)for(integer p=1;p<=71;p++)if((p&(1<<k))!=0)c[(1<<k)-1]^=c[p-1];
   c[71]=^c[70:0];ecc=c;
  end
 endfunction
 function automatic [287:0] encode(input [255:0] d);
  for(integer w=0;w<4;w++)encode[72*w+:72]=ecc(d[64*w+:64]);
 endfunction
 reg [18:0] openrow[0:31];
 reg due[0:CYCLES+RL];reg [287:0] word[0:CYCLES+RL];
 reg wdue[0:CYCLES+8];reg [287:0] wword[0:CYCLES+8];
 integer wsector[0:CYCLES+8];reg [287:0] external_host_storage[0:1023];
 integer errors=0,mode=0,landed,hostreads,hostwrites,commits,reads,last_arrival=0,model_free=0,ctrl_fault_seen=0;
 task automatic bad(input string message);
  if(errors<12)$display("BAD %s",message);errors++;
 endtask
 task automatic drive(input integer t);
  es=0;cmd=0;owner=t>=220;
  if(t==100)es={1'b1,1'b1,5'd5,5'd7,19'd24427,data(24427,157),1'b1};
  if(t==160)es={1'b0,1'b0,5'd5,5'd7,19'd24427,256'b0,1'b1};
  if(t==230)cmd={10'd0,2'b0,11'd256,19'd67,1'b1};
  if(t==300||t==1360)cmd={10'b0,2'd1,30'b0,1'b1};
  if(t==1300)cmd={10'd512,2'b0,11'd768,19'd67,1'b1};
 endtask
 initial begin
  void'($value$plusargs("faultmode=%d",mode));void'($value$plusargs("jit=%d",JIT));void'($value$plusargs("seed=%d",seed));
  void'($value$plusargs("late=%d",late_sector));
  GO_DLY=JIT+1;void'($value$plusargs("godly=%d",GO_DLY));
  void'($urandom(seed));for(integer i=0;i<64;i++)jit_hist[i]=0;
  for(integer phase=0;phase<2;phase++)begin
   rst=0;owner=0;cmd=0;reserved=0;es=0;pi=0;
   for(integer t=0;t<CYCLES+RL+1;t++)begin due[t]=0;word[t]=0;end
   for(integer t=0;t<CYCLES+9;t++)begin wdue[t]=0;wword[t]=0;end
   for(integer b=0;b<32;b++)openrow[b]=0;
   for(integer s=0;s<1024;s++)external_host_storage[s]=0;
   predicted_count=0;last_arrival=0;model_free=0;for(integer t=0;t<CYCLES+400;t++)begin model_arr[t]=0;go_arr[t]=0;end landed=0;hostreads=0;hostwrites=0;commits=0;reads=0;
   repeat(16)@(negedge ck);rst[phase]=1;
   for(integer t=0;t<CYCLES;t++)begin
    drive(t);
    if(phase==0)begin reserved=0;sr_reserved=0;wr_reserved=0;end
    else begin reserved=slots[t];sr_reserved=srslots[t];wr_reserved=wrslots[t];end
    sr_read_reserved=sr_reserved && t>=150;
    if(phase==1&&mode==101&&t>0)reserved=slots[t-1];
    if(phase==1&&mode==102&&t==1300)cmd[42:33]=10'd513;
    pi={word[t],due[t]};
    rawslot=phase==0?due[t]:rawslots[t];
    if(phase==0)rawslots[t]=due[t];
    blk_go=phase==1&&go_arr[t];if(blk_go)blocks_go++;
    @(posedge ck);
    // Wrapper has two RD reservation pin stages ahead of its actual core.
    if(phase==0&&t>=2)begin
     slots[t-2]=controllers[0].dut.u_ctl.core.on.legal_rd;
     srslots[t-2]=controllers[0].dut.u_ctl.core.on.legal_static;
     wrslots[t-2]=controllers[0].dut.u_ctl.core.on.legal_write;
    end
    if(po[phase][0]&&po[phase][3:1]==3'd1)openrow[po[phase][8:4]]=po[phase][27:9];
    if(po[phase][28])begin
     automatic integer bank=po[phase][34:30];
     automatic integer col=po[phase][39:35];
     automatic integer sec=((bank>>2)<<7)|(col<<2)|(bank&3);
     automatic integer row=openrow[bank];
     if(po[phase][29])begin wdue[t+5]=1;wword[t+5]=encode(data(row,sec));wsector[t+5]=sec;hostwrites++;end
     else begin
      automatic integer extra=0,a;
      if(phase==1)begin
       extra=$urandom_range(JIT,0);
       if(mode==2&&reads==late_sector)extra=JIT+40;
       if(mode==5&&reads==late_sector)extra=-1;
       if(mode==6&&reads==late_sector)extra=600;
      end
      a=t+RL+extra;if(phase==1&&a<=last_arrival)a=last_arrival+1;
      if(phase==1)begin last_arrival=a;if(a-t-RL>=0&&a-t-RL<64)jit_hist[a-t-RL]++;end
      if(a<CYCLES+RL)begin due[a]=1;word[a]=row==24427?external_host_storage[sec]:encode(data(row,sec));end
      reads++;
     end
    end
    if(wdue[t])begin
     if(po[phase][327:40]!==wword[t])bad($sformatf("PHY write data phase%0d t%0d",phase,t));
     // The allowed off-chip memory model stores ACTUAL PHY write data. Host
     // readback cannot be supplied from an expected/golden data expression.
     external_host_storage[wsector[t]]=po[phase][327:40];
     if(phase==1&&mode==104)external_host_storage[wsector[t]]^=288'd3;
    end
    if(phase==1)begin
     // Calendar sees only compiler RD reservations; raw-return valid never
     // selects publication or shifts a later slot.
     if(predicted_raw !== rawslot)bad("predicted raw pin calendar");
     // Nominal corrected landing (reservation calendar) schedules the block
     // release; actual co[0] may land later by up to the PHY window.
     if(predicted_corrected)begin
      predicted_count++;
      if(predicted_count%BLK==0)begin
       automatic integer tg=t+GO_DLY;
       go_arr[tg]=1;
       // compiled release model: start = max(go+1, previous block's last take)
       begin automatic integer st=(tg+1>model_free)?tg+1:model_free;
        for(integer i=0;i<BLK;i++)model_arr[st+1+i]=1;model_free=st+BLK;end
       if(first_go<0)first_go=tg;
      end
     end
     if(f_occ>maxocc)maxocc=f_occ;
     if(f_freed)blocks_freed++;
    end
    if(co[phase][0])begin
     automatic integer o=landed-256;
     automatic integer expected_sector=landed<256?landed:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
     automatic integer sec={co[phase][11:9],co[phase][7:1]};
     if(out_epoch[phase]!=7||sec!=expected_sector||co[phase][281:26]!==data(67,expected_sector))bad($sformatf("KV row phase%0d index%0d sec%0d",phase,landed,sec));
     landed++;
    end
    if(er[phase][0])begin
     hostreads++;
     if(er[phase][258:257]!=0||er[phase][256:1]!==data(24427,157))bad("host native read data");
    end
    if(cv[phase])commits++;
    if(fault[phase]||cf[phase])begin
     if(phase==1&&(mode==5||mode==6||CTRL_ELASTIC==0))ctrl_fault_seen=1;
     else bad($sformatf("controller sticky fault phase%0d t%0d",phase,t));
    end
    @(negedge ck);
    if(phase==1)begin
     if(f_put)begin
      // Front output = the block-released stream: exact sector order and data, independent of the ring/core.
      automatic integer o=front_ordinal-256;
      automatic integer es_=front_ordinal<256?front_ordinal:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
      if({f_co[11:9],f_co[7:1]}!=es_||f_co[281:26]!==data(67,es_)||f_epoch!=7)front_bad++;
      front_ordinal++;putcount++;
     end
     if(mode!=2&&mode!=3&&f_put!==model_arr[t])bad($sformatf("release not compile-time determined t%0d model%0b actual%0b",t,model_arr[t],f_put));
     model_put=model_arr[t];
     if(f_ovf||f_gofault)bad($sformatf("front overflow%0b go%0b t%0d",f_ovf,f_gofault,t));
    end
   end
   if(phase==0)begin slots[CYCLES-2]=0;slots[CYCLES-1]=0;srslots[CYCLES-2]=0;srslots[CYCLES-1]=0;wrslots[CYCLES-2]=0;wrslots[CYCLES-1]=0;end
   if((phase==1&&predicted_count!=512)||landed!=512||hostreads!=1||hostwrites!=1||commits!=2||reads!=513)
    bad($sformatf("counts phase%0d land%0d hostread%0d write%0d commit%0d rawread%0d",phase,landed,hostreads,hostwrites,commits,reads));
  end
  $display("MEASURE jit%0d godly%0d blk%0d nblk%0d maxocc%0d stall%0d go%0d freed%0d put%0d first_go%0d ctrlfault%0d corefault%0d errors%0d",
   JIT,GO_DLY,BLK,NBLK,maxocc,f_stall,blocks_go,blocks_freed,putcount,first_go,ctrl_fault_seen,core_fault_seen,errors);
  $display("FRONT ordinal%0d bad%0d",front_ordinal,front_bad);
  if(FRONT_MUT!=0)begin
   if(front_bad==0&&!core_fault_seen&&errors==0)begin $display("MUTANT_ESCAPED front MUT%0d mode%0d",FRONT_MUT,mode);$fatal(1);end
   $display("OBSERVED_FAIL front MUT%0d mode%0d frontbad%0d corefault%0d errors%0d",FRONT_MUT,mode,front_bad,core_fault_seen,errors);$fatal(1);
  end
  if(mode==5||mode==6||CTRL_ELASTIC==0)begin
   if(!ctrl_fault_seen)begin $display("MUTANT_ESCAPED controller accepted an out-of-window PHY return");$fatal(1);end
   $display("OBSERVED_FAIL controller PHY window mode%0d elastic%0d",mode,CTRL_ELASTIC);$fatal(1);
  end
  if(mode==3)begin
   if(!core_fault_seen)begin $display("MUTANT_ESCAPED historical fixed-calendar ring under variable PHY");$fatal(1);end
   $display("OBSERVED_FAIL historical fixed-calendar ring faults under variable PHY latency");$fatal(1);
  end
  if(mode==2)begin
   if(f_stall==0||putcount!=512||front_bad!=0||blocks_freed!=512/BLK||ctrl_fault_seen)begin
    $display("MUTANT_ESCAPED late block not held/emitted exactly stall%0d put%0d frontbad%0d",f_stall,putcount,front_bad);$fatal(1);end
   $display("OBSERVED_HOLD late block held %0d edges, 512 sectors emitted exact in order, corefault%0d (sequencer block pause required)",f_stall,core_fault_seen);$fatal(1);
  end
  if(front_bad)begin $display("FAIL front output bad%0d",front_bad);$fatal(1);end
  if(returned_count!=512)$fatal(1,"FAIL dual-clock return count%0d",returned_count);
  if(f_stall!=0||blocks_go!=512/BLK||blocks_freed!=512/BLK||putcount!=512)$fatal(1,"FAIL production stall%0d go%0d freed%0d put%0d",f_stall,blocks_go,blocks_freed,putcount);
  if(errors)begin $display("FAIL elastic KV boundary errors%0d mode%0d",errors,mode);$fatal(1);end
  $display("PASS 0az elastic KV-HBM boundary: actual controller ELASTIC + block front %0dx%0d + fixed return ring; PHY RL23+[0,%0d] in-order, 512 sectors exact, zero stalls, release compile-time determined, maxocc%0d",NBLK,BLK,JIT,maxocc);
  for(integer i=0;i<64;i++)if(jit_hist[i])$display("JIT_HIST extra%0d n%0d",i,jit_hist[i]);
  $finish;
 end
endmodule
