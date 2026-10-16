`timescale 1ns/1fs
// Full population mechanism gate. 128 independent persistent actual controllers,
// each HOST native WR/readback then K256/V256 without resetting. Discovery is
// a separate executable whose frozen fixture is replayed by PROFILE0. Return
// calendar is reservation-only; production physical phases/source/token OPEN.
module qkd_paced_v_landing_return_cell #(parameter integer PC=0, STACK=0, DISCOVERY=0, HOST_DUAL=0)(output reg done=0, output wire [327:0] phy_command, output wire phy_clk,
 output wire landing_core,landing_rst,landing_put,landing_valid,
 output wire [9:0] landing_expected_sector,landing_sector,
 output wire [15:0] landing_epoch,output wire [5:0] landing_layer,
 output wire [255:0] landing_data);
 assign landing_core=core;assign landing_rst=rst;
 assign landing_valid=return_valid;assign landing_sector=return_sector;
 assign landing_epoch=return_epoch;assign landing_layer=return_layer;assign landing_data=return_data;
 reg ep1=0,ep2=0;reg [9:0] es1,es2;
 always @(posedge core)begin ep1<=expected_core_put;ep2<=ep1;es1<=expected_core_sector;es2<=es1;end
 assign landing_put=ep2;assign landing_expected_sector=es2;
 localparam CYCLES=6500,RL=23;
 // Source qkd_ctrl_pc_host_static: pc_q and dsel run throughout reset;
 // hr_q takes the release edge, then dcnt needs dtab[pc]+1 edges to hgo.
 // The first scheduler-active edge is max(dtab)+2. HOST requests start there.
 function automatic integer max_strap_delay();
  integer m,r,d;begin m=0;
   for(integer p=0;p<32;p++)begin r=(p*118)/32;d=r+((r+p)%2);if(d>m)m=d;end
   return m;
  end
 endfunction
 localparam integer MAX_STRAP=max_strap_delay(),PROGRAM_SHIFT=MAX_STRAP+2-100;
 string fixture_root; string fixture_file; integer fixture_fd;
 
 integer core_phase_ps=137;real CORE_FIRST;
 integer host_wr_core,host_rd_core;
 reg core=0;initial begin void'($value$plusargs("phase=%d",core_phase_ps));
  CORE_FIRST=(core_phase_ps+416.667)/1000.0;
  // Compile HOST request edges from the same source-bound HBM program, then
  // drive exactly one whole CORE cycle. No actual CDC/result event selects it.
  host_wr_core=$rtoi($ceil(((16+100+PROGRAM_SHIFT)*1.024-core_phase_ps/1000.0)/0.833334));
  host_rd_core=$rtoi($ceil(((16+160+PROGRAM_SHIFT)*1.024-core_phase_ps/1000.0)/0.833334));
  #(core_phase_ps/1000.0);forever #0.416667 core=~core;end
 real previous_core=-1,previous_hbm=-1;
 integer measured_core=0,measured_hbm=0;
 always @(posedge core)begin
  if(previous_core>=0 && (($realtime-previous_core)>0.833335 || ($realtime-previous_core)<0.833333))$fatal(1,"actual CORE period");
  if(measured_core==0 && ($realtime-CORE_FIRST>0.000001 || CORE_FIRST-$realtime>0.000001))$fatal(1,"actual CORE first phase");
  if(PC==0&&STACK==0&&measured_core==1)$display("CLOCK core period_ns%0.9f first_ns%0.9f",$realtime-previous_core,CORE_FIRST);
  measured_core++;previous_core=$realtime;
 end
 always @(posedge ck)begin
  if(previous_hbm>=0 && (($realtime-previous_hbm)>1.024001 || ($realtime-previous_hbm)<1.023999))$fatal(1,"actual HBM period");
  if(PC==0&&STACK==0&&measured_hbm==1)$display("CLOCK hbm period_ns%0.9f",$realtime-previous_hbm);
  measured_hbm++;previous_hbm=$realtime;
 end
 reg late_calendar;always @(posedge ck)late_calendar<=predicted_corrected;
 wire[293:0] observed_co={co[293:1],co[0]&&!(mode==7&&publish_ordinal==80)};
 reg expected_core_put=0;reg[9:0] expected_core_sector=0;
 reg[9:0] core_sector[0:12000];reg core_slots[0:12000];
 wire return_valid,return_hfault,return_cfault;wire[9:0] return_sector;
 wire[15:0] return_epoch;wire[5:0] return_layer;wire[255:0] return_data;
 integer core_edge=0,returned_count=0,publish_ordinal=0;
 qkd_static_kv_return_slots u_return(.pll_hbm(ck),.hrst(rst),.ck(core),.rsi(rst),
 .controller_co(observed_co),.controller_epoch(out_epoch ^ (mode==6?16'd1:16'd0)),.compiled_hbm_put(mode==5?late_calendar:predicted_corrected),
 .expected_put(expected_core_put),.expected_sector(expected_core_sector),.expected_epoch(16'd7),.expected_layer(6'd3),
 .actual_valid(return_valid),.actual_sector(return_sector),.actual_epoch(return_epoch),.actual_layer(return_layer),
 .actual_data(return_data),.fault_hbm(return_hfault),.fault_core(return_cfault));
 initial for(integer c=0;c<=12000;c++)begin core_slots[c]=0;core_sector[c]=0;end
 // Future CORE commands are compiled from the predictor's fixed HBM edges,
 // never from actual controller_co, PHY return, publication or readiness.
 always @(posedge ck)if(!DISCOVERY&&rst&&predicted_corrected)begin
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
  if(HOST_DUAL)begin
   es=0;
   if(rst&&core_edge==host_wr_core)es={1'b1,1'b1,5'd5,5'd7,19'd24427,data(24427,157),1'b1};
   if(rst&&core_edge==host_rd_core)es={1'b0,1'b0,5'd5,5'd7,19'd24427,256'b0,1'b1};
  end
 end
 always @(posedge core)begin
  core_edge++;
  #0.001;
  if(rst&&return_valid)begin
   if(return_epoch!=7||return_layer!=3||return_data!==data(67,return_sector))
    $fatal(1,"actual controller dual-clock return metadata/data");
   returned_count++;
  end
  if(HOST_DUAL&&rst)begin
   if(er[0])begin
    hostreads++;
    if(er[258:257]!=0||er[256:1]!==data(24427,157))bad("host native dual-clock read data");
   end
   if(cv)begin commits++;if(cw)commit_writes++;else commit_reads++;end
  end
  if(!DISCOVERY&&rst&&(return_hfault||return_cfault))$fatal(1,"actual controller dual-clock slot fault at core%0d",core_edge);
 end
 reg ck=0;always #0.512 ck=~ck;
 assign phy_clk=ck;assign phy_command=po;
 reg rst=0;
 reg owner=0;reg [42:0] cmd=0;reg reserved=0,sr_reserved=0,wr_reserved=0;
 reg [287:0] es=0;reg [288:0] pi=0;
 wire [327:0] po;wire [293:0] co;wire [260:0] er;wire fault,cv,cw,cf;
 wire predicted_raw,predicted_corrected;wire[15:0] predicted_epoch;
 qkd_static_kv_return_calendar u_calendar(.pll_hbm(ck),.hrst(rst),
  .reserved_rd(reserved),.reserved_static_read(sr_read_reserved),.reservation_epoch(16'd7),
  .expected_raw_valid(predicted_raw),.compiled_hbm_put(predicted_corrected),
  .expected_return_epoch(predicted_epoch));
 integer predicted_count;
 reg slots[0:CYCLES-1],srslots[0:CYCLES-1],wrslots[0:CYCLES-1],rawslots[0:CYCLES-1];
 reg sr_read_reserved=0;reg rawslot=0;wire [15:0] out_epoch;
 qkd_ctrl_pc_host_static #(.PROFILE(DISCOVERY?2:0))dut(
   .pll_hbm(ck),.hrst(rst),.ck(HOST_DUAL?core:ck),.rsi(rst),.pc(5'(PC)),.ci(319'b0),.co(co),
   .es(es),.er(er),.po(po),.pi(pi),.ki(33'b0),.ko(),.fi(1'b0),.fo(fault),
   .static_cmd_owner(owner),.static_cmd(cmd),.reserved_rd(reserved),.reserved_static_col(sr_reserved),.reserved_write_col(wr_reserved),
   .static_epoch(16'd7),.expected_raw_valid(DISCOVERY ? rawslot : predicted_raw),.cfg_stack(2'(STACK)),.es_context(318'b0),.es_expected_valid(1'b0),.es_expected_identity(61'b0),.es_expected_address(29'b0),.es_expected_pc(5'b0),.es_expected_stack(2'b0),.native_commit_valid(),.native_commit_identity(),.native_commit_address(),.corrected_epoch(out_epoch),.completion_v(cv),.completion_we(cw),.completion_fault(cf));

 function automatic [255:0] data(input integer row,sector);
  for(integer i=0;i<8;i++)data[32*i+:32]=32'h981ac500^32'(PC*8191+STACK*1048573)^32'(row*65537)^32'(sector*71+i*31);
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
 integer errors=0,mode=0,landed,hostreads,hostwrites,commits,commit_writes,commit_reads,reads;
 task automatic bad(input string message);
  if(errors<12)$display("BAD pc%0d stack%0d %s",PC,STACK,message);errors++;
 endtask
 task automatic drive(input integer edge_index);
  integer t;t=edge_index-PROGRAM_SHIFT;
  if(!HOST_DUAL)es=0;cmd=0;owner=t>=220;
  if(!HOST_DUAL&&t==100)es={1'b1,1'b1,5'd5,5'd7,19'd24427,data(24427,157),1'b1};
  if(!HOST_DUAL&&t==160)es={1'b0,1'b0,5'd5,5'd7,19'd24427,256'b0,1'b1};
  if(t==230)cmd={10'd0,2'b0,11'd256,19'd67,1'b1};
  if(t==300||t==1360)cmd={10'b0,2'd1,30'b0,1'b1};
  if(t==1300)cmd={10'd512,2'b0,11'd768,19'd67,1'b1};
 endtask
 initial begin
  if(!$value$plusargs("fixtures=%s",fixture_root))$fatal(1,"fixtures directory required");
  void'($value$plusargs("faultmode=%d",mode));
  for(integer phase=(DISCOVERY?0:1);phase<(DISCOVERY?1:2);phase++)begin
   fixture_file=$sformatf("%s/pc%02d_stack%0d.mem",fixture_root,PC,STACK);
   if(!DISCOVERY)begin
    fixture_fd=$fopen(fixture_file,"r");if(!fixture_fd)$fatal(1,"missing frozen fixture %s",fixture_file);
    for(integer t=0;t<CYCLES;t++)begin
     if($fscanf(fixture_fd,"%b %b %b %b\n",slots[t],srslots[t],wrslots[t],rawslots[t])!=4)$fatal(1,"short frozen fixture");
    end
    $fclose(fixture_fd);
   end
   rst=0;owner=0;cmd=0;reserved=0;es=0;pi=0;
   for(integer t=0;t<CYCLES+RL+1;t++)begin due[t]=0;word[t]=0;end
   for(integer t=0;t<CYCLES+9;t++)begin wdue[t]=0;wword[t]=0;end
   for(integer b=0;b<32;b++)openrow[b]=0;
   for(integer s=0;s<1024;s++)external_host_storage[s]=0;
   predicted_count=0;landed=0;hostreads=0;hostwrites=0;commits=0;commit_writes=0;commit_reads=0;reads=0;
   repeat(16)@(negedge ck);rst=1;
   for(integer t=0;t<CYCLES;t++)begin
    drive(t);
    // PROFILE2 intersects these advance-compiled request pins with actual
    // JEDEC legality. Only its frozen accepted slots enter PROFILE0 replay.
    if(phase==0)begin
     reserved=(t<1300+PROGRAM_SHIFT)||((t-(1300+PROGRAM_SHIFT))%7==0);
     sr_reserved=1;wr_reserved=1;
    end
    else begin reserved=slots[t];sr_reserved=srslots[t];wr_reserved=wrslots[t];end
    sr_read_reserved=sr_reserved && t>=150+PROGRAM_SHIFT && mode!=8;
    if(phase==1&&mode==1&&t>0)reserved=slots[t-1];
    if(phase==1&&mode==2&&t==1300+PROGRAM_SHIFT)cmd[42:33]=10'd513;
    pi={word[t],due[t]};
    rawslot=phase==0?due[t]:rawslots[t];
    if(phase==0)rawslots[t]=due[t];
    if(phase==1&&mode==3&&t==400+PROGRAM_SHIFT)pi[0]=0;
    @(posedge ck);
    // Wrapper has two RD reservation pin stages ahead of its actual core.
    if(phase==0&&t>=2)begin
     slots[t-2]=dut.u_ctl.core.on.rd_ok;
     srslots[t-2]=dut.u_ctl.core.on.s_go;
     wrslots[t-2]=dut.u_ctl.core.on.wr_ok;
    end
    if(po[0]&&po[3:1]==3'd1)openrow[po[8:4]]=po[27:9];
    if(po[28])begin
     automatic integer bank=po[34:30];
     automatic integer col=po[39:35];
     automatic integer sec=((bank>>2)<<7)|(col<<2)|(bank&3);
     automatic integer row=openrow[bank];
     if(po[29])begin wdue[t+5]=1;wword[t+5]=encode(data(row,sec));wsector[t+5]=sec;hostwrites++;end
     else begin due[t+RL]=1;word[t+RL]=row==24427?external_host_storage[sec]:encode(data(row,sec));reads++;end
    end
    if(wdue[t])begin
     if(po[327:40]!==wword[t])bad($sformatf("PHY write data phase%0d t%0d",phase,t));
     // The allowed off-chip memory model stores ACTUAL PHY write data. Host
     // readback cannot be supplied from an expected/golden data expression.
     external_host_storage[wsector[t]]=po[327:40];
     if(phase==1&&mode==4)external_host_storage[wsector[t]]^=288'd3;
    end
    if(phase==1)begin
     // Calendar sees only compiler RD reservations; raw-return valid never
     // selects publication or shifts a later slot.
     if(predicted_raw !== rawslot)bad("predicted raw pin calendar");
     if(predicted_corrected !== co[0])bad($sformatf("predicted co at t%0d want%0b got%0b",t,predicted_corrected,co[0]));
     if(predicted_corrected)begin predicted_count++;if(predicted_epoch!=out_epoch)bad("predicted epoch");end
    end
    if(co[0])begin
     automatic integer o=landed-256;
     automatic integer expected_sector=landed<256?landed:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
     automatic integer sec={co[11:9],co[7:1]};
     if(out_epoch!=7||sec!=expected_sector||co[281:26]!==data(67,expected_sector))bad($sformatf("KV row phase%0d index%0d sec%0d",phase,landed,sec));
     landed++;
    end
    if(!HOST_DUAL&&er[0])begin
     hostreads++;
     if(er[258:257]!=0||er[256:1]!==data(24427,157))bad("host native read data");
    end
    if(!HOST_DUAL&&cv)begin commits++;if(cw)commit_writes++;else commit_reads++;end
    if(fault||cf)bad($sformatf("controller sticky fault phase%0d t%0d",phase,t));
    @(negedge ck);
   end
   if(phase==0)begin slots[CYCLES-2]=0;slots[CYCLES-1]=0;srslots[CYCLES-2]=0;srslots[CYCLES-1]=0;wrslots[CYCLES-2]=0;wrslots[CYCLES-1]=0;end
   if(DISCOVERY)begin
    fixture_fd=$fopen(fixture_file,"w");
    for(integer t=0;t<CYCLES;t++)$fdisplay(fixture_fd,"%b %b %b %b",slots[t],srslots[t],wrslots[t],rawslots[t]);
    $fclose(fixture_fd);
   end
   if((phase==1&&predicted_count!=512)||landed!=512||hostreads!=1||hostwrites!=1||commits!=2||commit_writes!=1||commit_reads!=1||reads!=513)
    bad($sformatf("counts phase%0d land%0d hostread%0d write%0d commit%0d wr%0d rd%0d rawread%0d",phase,landed,hostreads,hostwrites,commits,commit_writes,commit_reads,reads));
  end
  if(!DISCOVERY&&returned_count!=512)$fatal(1,"actual controller dual-clock return count%0d",returned_count);
  if(errors)begin $display("FAIL persistent staticKV host controller errors%0d mode%0d",errors,mode);$fatal(1);end
  $display("PASS full128 cell pc%0d stack%0d discovery%0d K256 V256 hostNativeWriteRead bootCompletion2",PC,STACK,DISCOVERY);done=1;
 end
endmodule


// Actual 128 persistent controllers -> fixed return rings -> 32 physical
// seven-edge groups and 128 real macro functional models. Request calendars
// are compiled BEFORE execution from frozen reservations; never actual_valid.
module tb_static_paced_v_landing_full128;
 localparam integer DISCOVERY=0;
 wire [127:0] done,core,reset_n,put,av;
 wire [9:0] ps[0:127],asec[0:127];wire [15:0] ae[0:127];
 wire [5:0] al[0:127];wire [255:0] ad[0:127];
 integer basek[0:31],basev[0:31],phase=137,mode=0,edge_index=0,seen=0,errors=0;
 integer fd;string calendar_dir,filename;
 reg [31:0] rq=0,rv=0;reg [13:0] rt[0:31];
 wire [31:0] ov,kind,fault;wire [1023:0] od[0:31];wire [13:0] ot[0:31];
 wire [15:0] oe[0:31];wire [5:0] ol[0:31];
 reg arm=0;
 function automatic integer slotgroup(input integer g);
  case(g)4:return 0;5:return 1;0:return 2;1:return 3;2:return 4;3:return 5;6:return 6;7:return 7;endcase
 endfunction
 function automatic [13:0] kt(input integer i,s,g);
  return 14'(((i>>3)&15)*512+s*128+((i>>7)&1)*64+(i&7)*8+g);
 endfunction
 function automatic [13:0] vt(input integer i,s,g);
  return 14'(((i>>4)&15)*512+s*128+((i>>3)&1)*64+(i&7)*8+g);
 endfunction
 function automatic [9:0] sector(input [13:0] t,input bit v);
  return {v,1'b0,t[6],t[12:9],t[5:3]};
 endfunction
 function automatic [1023:0] expected_data(input integer n,input [13:0] t,input bit v);
  integer pc,sec;begin
   sec=sector(t,v);
   for(integer q=0;q<4;q++)begin
    pc=4*slotgroup(n%8)+q;
    for(integer i=0;i<8;i++)expected_data[256*q+32*i+:32]=32'h981ac500^32'(pc*8191+(n/8)*1048573)^32'(67*65537)^32'(sec*71+i*31);
   end
  end
 endfunction
 for(genvar p=0;p<128;p++)begin:pc
  wire [327:0] po;wire hclk;
  qkd_paced_v_landing_return_cell #(.PC(p%32),.STACK(p/32),.DISCOVERY(0),.HOST_DUAL(1))u_pc(
   .done(done[p]),.phy_command(po),.phy_clk(hclk),.landing_core(core[p]),.landing_rst(reset_n[p]),
   .landing_put(put[p]),.landing_valid(av[p]),.landing_expected_sector(ps[p]),.landing_sector(asec[p]),
   .landing_epoch(ae[p]),.landing_layer(al[p]),.landing_data(ad[p]));
 end
 for(genvar n=0;n<32;n++)begin:landing
  localparam integer S=n/8,G=n%8;
  localparam integer L=(G==4?0:G==5?1:G==0?2:G==1?3:G==2?4:G==3?5:G==6?6:7);
  wire [3:0] pp,vv;wire [39:0] eps,obs;wire [63:0] epoch;
  wire [23:0] layer;wire [1023:0] data;
  for(genvar q=0;q<4;q++)begin:quarter
   localparam integer P=S*32+4*L+q;
   assign pp[q]=put[P];assign vv[q]=av[P];assign eps[10*q+:10]=ps[P];assign obs[10*q+:10]=asec[P];
   assign epoch[16*q+:16]=ae[P];assign layer[6*q+:6]=al[P];assign data[256*q+:256]=ad[P];
  end
  qkd_static_kv_landing_physical_grp #(.STACK(S),.GROUP(G))u_landing(
   .ck(core[0]),.ck_pc({4{core[0]}}),.ck_req_rly({4{core[0]}}),.ck_rsp_rly({4{core[0]}}),.rst_n(reset_n[0]),
   .arm(arm),.epoch(16'd7),.layer(6'd3),.expected_put(pp),.expected_sector(eps),.actual_valid(vv),.actual_sector(obs),
   .actual_epoch(epoch),.actual_layer(layer),.actual_data(data),.req_valid(rq[n]),.req_t(rt[n]),.req_v(rv[n]),
   .req_epoch(16'd7 ^ ((mode==9&&n==0)?16'd1:16'd0)),.req_layer(6'd3),
   .rsp_valid(ov[n]),.rsp_data(od[n]),.rsp_t(ot[n]),.rsp_v(kind[n]),.rsp_epoch(oe[n]),.rsp_layer(ol[n]),.fault(fault[n]));
 end
 initial begin
  void'($value$plusargs("phase=%d",phase));void'($value$plusargs("faultmode=%d",mode));
  if(!$value$plusargs("landing_calendar=%s",calendar_dir))$fatal(1,"missing compiled landing calendar");
  filename=$sformatf("%s/p%0d.mem",calendar_dir,phase);fd=$fopen(filename,"r");
  if(!fd)$fatal(1,"missing calendar %s",filename);
  for(integer n=0;n<32;n++)begin
   if($fscanf(fd,"%d %d\n",basek[n],basev[n])!=2)$fatal(1,"short compiled calendar");
   rt[n]=0;
  end
  $fclose(fd);
  for(integer n=0;n<32;n++)if(basev[n]!=basev[8*((n/8)%2)]+128*((n/8)/2)+n%8)
   $fatal(1,"calendar violates actual shared pair source group%0d",n);
 end
 // Real canonical two-pair V issuer, including its 128-edge PV init
 // reservation. EXP input is a zero fixture in this KV-only component gate;
 // no arithmetic/PV/native whole-attention qualification is implied.
 wire [1:0] vreqlo,vreqhi,vdone,vfault;
 wire [13:0] vtag[0:1];wire [2:0] vslot[0:1];wire [15:0] vepoch[0:1];
 reg [1:0] vstart=0,vdone_seen=0;
 for(genvar pair=0;pair<2;pair++)begin:canonical_v
  reg lo_valid,hi_valid;reg [13:0] lo_tag,hi_tag;
  reg [15:0] lo_epoch,hi_epoch;reg [1023:0] lo_row,hi_row;
  reg [2:0] lo_slot,hi_slot;
  // Slot is source ordinal modulo8. Actual group ordinal tag t contains the
  // correct global pair traversal position, so slot=t[2:0].
  always @*begin
   lo_valid=0;hi_valid=0;lo_tag=0;hi_tag=0;lo_epoch=0;hi_epoch=0;
   lo_row=0;hi_row=0;lo_slot=0;hi_slot=0;
   for(integer n=0;n<32;n++)if(ov[n]&&kind[n])begin
    if(n/8==pair)begin lo_valid=1;lo_tag=ot[n];lo_epoch=oe[n];lo_row=od[n];lo_slot=ot[n][2:0];end
    if(n/8==pair+2)begin hi_valid=1;hi_tag=ot[n];hi_epoch=oe[n];hi_row=od[n];hi_slot=ot[n][2:0];end
   end
  end
  ot_qwen_tp8_vrow_static #(.PAIR(pair),.RETURN_LATENCY(8),.INIT_CYCLES(128))u_v(
   .clk(core[0]),.rst_n(reset_n[0]),.start(vstart[pair]),.context_len(14'd8192),.epoch(16'd7),
   .lo_req_valid(vreqlo[pair]),.hi_req_valid(vreqhi[pair]),.lo_req_ready(1'b1),.hi_req_ready(1'b1),
   .req_slot(vslot[pair]),.req_t(vtag[pair]),.req_epoch(vepoch[pair]),
   .lo_rsp_valid(lo_valid),.hi_rsp_valid(hi_valid),.lo_rsp_slot(lo_slot),.hi_rsp_slot(hi_slot),
   .lo_rsp_t(lo_tag),.hi_rsp_t(hi_tag),.lo_rsp_epoch(lo_epoch),.hi_rsp_epoch(hi_epoch),
   .lo_vrow(lo_row),.hi_vrow(hi_row),.lo_exp(64'b0),.hi_exp(64'b0),
   .out_valid(),.out_ready(1'b1),.out_vrow(),.out_exp(),.out_t(),.out_epoch(),.out_first(),.out_last(),
   .done(vdone[pair]),.fault(vfault[pair]));
 end
 always @(negedge core[0])begin
  arm=(edge_index==40);
  for(integer pair=0;pair<2;pair++)vstart[pair]=(edge_index==basev[8*pair]-129);
  for(integer n=0;n<32;n++)begin
   automatic integer k=edge_index-basek[n],v=edge_index-basev[n];
   rq[n]=0;rv[n]=0;
   if(k>=0&&k<256)begin rq[n]=1;rt[n]=kt(k,n/8,n%8);end
   if((vreqlo[(n/8)%2]||vreqhi[(n/8)%2])&&((vtag[(n/8)%2]>>7)&3)==n/8&&(vtag[(n/8)%2]&7)==n%8)begin
    rq[n]=1;rv[n]=1;rt[n]=vtag[(n/8)%2];
   end
   if(mode==10&&n==0&&rq[n])rt[n]^=14'd1;
  end
 end
 reg [31:0] exvalid[0:7],exkind[0:7];reg [13:0] ext[0:7][0:31];reg [1023:0] exdata[0:7][0:31];
 always @(posedge core[0])begin
  edge_index++;
  vdone_seen<=vdone_seen|vdone;
  if(!reset_n[0])for(integer d=0;d<8;d++)exvalid[d]<=0;
  else begin
   exvalid[0]<=rq;exkind[0]<=rv;
   for(integer n=0;n<32;n++)begin ext[0][n]<=rt[n];exdata[0][n]<=expected_data(n,rt[n],rv[n]);end
   for(integer d=1;d<8;d++)begin
    exvalid[d]<=exvalid[d-1];exkind[d]<=exkind[d-1];
    for(integer n=0;n<32;n++)begin ext[d][n]<=ext[d-1][n];exdata[d][n]<=exdata[d-1][n];end
   end
  end
  #0.000001;
  if(reset_n[0])begin
   if(ov!==exvalid[7])begin if(errors<4)$display("BAD landing valid edge%0d got%h expected%h",edge_index,ov,exvalid[7]);errors++;end
   if(|vfault)begin if(errors<4)$display("BAD actual V source fault edge%0d mask%h",edge_index,vfault);errors++;end
   if(|fault)begin if(errors<4)$display("BAD landing fault edge%0d mask%h",edge_index,fault);errors++;end
   for(integer n=0;n<32;n++)if(ov[n])begin
    seen++;
    if(od[n]!==exdata[7][n]||ot[n]!==ext[7][n]||kind[n]!==exkind[7][n]||oe[n]!=7||ol[n]!=3)begin
     if(errors<4)$display("BAD landing row edge%0d group%0d t%0d",edge_index,n,ot[n]);errors++;
    end
   end
  end
 end
 always @(done)if(&done)begin
  if(errors||seen!=16384||vdone_seen!=3)$fatal(1,"landing errors%0d rows%0d want16384",errors,seen);
  $display("PASS actual128 persistent controllers fixed returns mapped128SRAM physical32groups actual2Vissuers K8192 V8192 sevenedge exact phase%0d",phase);
  $finish;
 end
endmodule
