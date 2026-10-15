`timescale 1ns/1ps
// Persistent native controller component, including actual host CDC, pcport,
// raw PHY pin stage and ECC. Common-clock ABI proof only: production dual-clock
// insertion/phase and full compiled host program remain separate qualification.
module tb_static_return_controller_calendar;
 localparam CYCLES=2400,RL=23;
 integer core_phase_ps=137;real CORE_FIRST;
 reg core=0;initial begin void'($value$plusargs("phase=%d",core_phase_ps));
  CORE_FIRST=(core_phase_ps+416.667)/1000.0;
  #(core_phase_ps/1000.0);forever #0.416667 core=~core;end
 reg late_calendar;always @(posedge ck)late_calendar<=predicted_corrected;
 wire[293:0] observed_co={co[1][293:1],co[1][0]&&!(mode==7&&publish_ordinal==80)};
 reg expected_core_put=0;reg[9:0] expected_core_sector=0;
 reg[9:0] core_sector[0:10000];reg core_slots[0:10000];
 wire return_valid,return_hfault,return_cfault;wire[9:0] return_sector;
 wire[15:0] return_epoch;wire[5:0] return_layer;wire[255:0] return_data;
 integer core_edge=0,returned_count=0,publish_ordinal=0;
 qkd_static_kv_return_slots u_return(.pll_hbm(ck),.hrst(rst[1]),.ck(core),.rsi(rst[1]),
 .controller_co(observed_co),.controller_epoch(out_epoch[1] ^ (mode==6?16'd1:16'd0)),.compiled_hbm_put(mode==5?late_calendar:predicted_corrected),
 .expected_put(expected_core_put),.expected_sector(expected_core_sector),.expected_epoch(16'd7),.expected_layer(6'd3),
 .actual_valid(return_valid),.actual_sector(return_sector),.actual_epoch(return_epoch),.actual_layer(return_layer),
 .actual_data(return_data),.fault_hbm(return_hfault),.fault_core(return_cfault));
 initial for(integer c=0;c<=10000;c++)begin core_slots[c]=0;core_sector[c]=0;end
 // Future CORE commands are compiled from the predictor's fixed HBM edges,
 // never from actual controller_co, PHY return, publication or readiness.
 always @(posedge ck)if(rst[1]&&predicted_corrected)begin
  automatic real target=($realtime+1.024+2*0.833334-CORE_FIRST)/0.833334;
  automatic integer c=$rtoi($ceil(target));
  automatic integer o=publish_ordinal-256;
  automatic integer sec=publish_ordinal<256?publish_ordinal:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
  if(core_slots[c])$fatal(1,"compiled core slot collision");
  core_slots[c]=1;core_sector[c]=10'(sec);publish_ordinal++;
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
   if(return_epoch!=7||return_layer!=3||return_data!==data(67,return_sector))
    $fatal(1,"actual controller dual-clock return metadata/data");
   returned_count++;
  end
  if(rst[1]&&(return_hfault||return_cfault))$fatal(1,"actual controller dual-clock slot fault at core%0d",core_edge);
 end
 reg ck=0;always #0.512 ck=~ck;
 reg [1:0] rst=0;
 reg owner=0;reg [42:0] cmd=0;reg reserved=0,sr_reserved=0,wr_reserved=0;
 reg [287:0] es=0;reg [288:0] pi=0;
 wire [327:0] po[0:1];wire [293:0] co[0:1];wire [260:0] er[0:1];wire [1:0] fault,cv,cw,cf;
 wire predicted_raw,predicted_corrected;wire[15:0] predicted_epoch;
 qkd_static_kv_return_calendar u_calendar(.pll_hbm(ck),.hrst(rst[1]),
  .reserved_rd(reserved),.reserved_static_read(sr_read_reserved),.reservation_epoch(16'd7),
  .expected_raw_valid(predicted_raw),.compiled_hbm_put(predicted_corrected),
  .expected_return_epoch(predicted_epoch));
 integer predicted_count;
 reg slots[0:CYCLES-1],srslots[0:CYCLES-1],wrslots[0:CYCLES-1],rawslots[0:CYCLES-1];
 reg sr_read_reserved=0;reg rawslot=0;wire [15:0] out_epoch[0:1];
 genvar g;
 generate for(g=0;g<2;g++)begin:controllers
  qkd_ctrl_pc_host_static #(.PROFILE(g==0?1:0))dut(
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
 integer errors=0,mode=0,landed,hostreads,hostwrites,commits,reads;
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
  void'($value$plusargs("faultmode=%d",mode));
  for(integer phase=0;phase<2;phase++)begin
   rst=0;owner=0;cmd=0;reserved=0;es=0;pi=0;
   for(integer t=0;t<CYCLES+RL+1;t++)begin due[t]=0;word[t]=0;end
   for(integer t=0;t<CYCLES+9;t++)begin wdue[t]=0;wword[t]=0;end
   for(integer b=0;b<32;b++)openrow[b]=0;
   for(integer s=0;s<1024;s++)external_host_storage[s]=0;
   predicted_count=0;landed=0;hostreads=0;hostwrites=0;commits=0;reads=0;
   repeat(16)@(negedge ck);rst[phase]=1;
   for(integer t=0;t<CYCLES;t++)begin
    drive(t);
    if(phase==0)begin reserved=0;sr_reserved=0;wr_reserved=0;end
    else begin reserved=slots[t];sr_reserved=srslots[t];wr_reserved=wrslots[t];end
    sr_read_reserved=sr_reserved && t>=150;
    if(phase==1&&mode==1&&t>0)reserved=slots[t-1];
    if(phase==1&&mode==2&&t==1300)cmd[42:33]=10'd513;
    pi={word[t],due[t]};
    rawslot=phase==0?due[t]:rawslots[t];
    if(phase==0)rawslots[t]=due[t];
    if(phase==1&&mode==3&&t==400)pi[0]=0;
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
     else begin due[t+RL]=1;word[t+RL]=row==24427?external_host_storage[sec]:encode(data(row,sec));reads++;end
    end
    if(wdue[t])begin
     if(po[phase][327:40]!==wword[t])bad($sformatf("PHY write data phase%0d t%0d",phase,t));
     // The allowed off-chip memory model stores ACTUAL PHY write data. Host
     // readback cannot be supplied from an expected/golden data expression.
     external_host_storage[wsector[t]]=po[phase][327:40];
     if(phase==1&&mode==4)external_host_storage[wsector[t]]^=288'd3;
    end
    if(phase==1)begin
     // Calendar sees only compiler RD reservations; raw-return valid never
     // selects publication or shifts a later slot.
     if(predicted_raw !== rawslot)bad("predicted raw pin calendar");
     if(predicted_corrected !== co[phase][0])bad($sformatf("predicted co at t%0d want%0b got%0b",t,predicted_corrected,co[phase][0]));
     if(predicted_corrected)begin predicted_count++;if(predicted_epoch!=out_epoch[phase])bad("predicted epoch");end
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
    if(fault[phase]||cf[phase])bad($sformatf("controller sticky fault phase%0d t%0d",phase,t));
    @(negedge ck);
   end
   if(phase==0)begin slots[CYCLES-2]=0;slots[CYCLES-1]=0;srslots[CYCLES-2]=0;srslots[CYCLES-1]=0;wrslots[CYCLES-2]=0;wrslots[CYCLES-1]=0;end
   if((phase==1&&predicted_count!=512)||landed!=512||hostreads!=1||hostwrites!=1||commits!=2||reads!=513)
    bad($sformatf("counts phase%0d land%0d hostread%0d write%0d commit%0d rawread%0d",phase,landed,hostreads,hostwrites,commits,reads));
  end
  if(returned_count!=512)$fatal(1,"actual controller dual-clock return count%0d",returned_count);
  if(errors)begin $display("FAIL persistent staticKV host controller errors%0d mode%0d",errors,mode);$fatal(1);end
  $display("PASS sourcebound static return calendar controller K256 V256 hostNativeWriteRead bootCompletion2 rawPHYRL23 predictedCorrected32 dualClock512 productionPhaseNotQualified");$finish;
 end
endmodule
