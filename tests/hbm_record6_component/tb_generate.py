"""Emit actual-source component wiring; generated testbench is never DUT RTL."""
import json

def emit(out,receipt,binding):
 # Same fixed 3:4 bridge source formula as native_su_calendar.py.
 # Command0 serial6011; phase-zero stream8015; hostlaunch7950/publication10.
 for q in range(4):
  commands=[int(v,16)for v in (out/f'q{q}/quarter.mem').read_text().split()]
  fields=[{}for _ in range(1024)];events=[]
  for e,w in enumerate(commands):
   for p in range(8):
    for kind,base,width,vbit,lag,local,owner in [('read',440,30,29,0,139,65),('write',128,39,38,4,163,73)]:
     c=w>>(base+p*width)&((1<<width)-1)
     if not(c>>vbit):continue
     n=e+lag;lg=8015+(4*n+6)//3+1;at=lg-7960
     depth=4+p%2 if kind=='read' else 3
     assert 0<=at<at+2+depth<1024
     fields[at][local]=fields[at].get(local,0)|(1<<p)
     fields[at+2+depth][owner]=fields[at+2+depth].get(owner,0)|(1<<p)
     events.append(dict(kind=kind,command=e,port=p,lg=lg,vm=lg+2+depth))
  words=[(0xc7a1<<240)|(i<<224)|sum(v<<sh for sh,v in f.items())for i,f in enumerate(fields)]
  # MAGIC_ROW is the real programme-target envelope, verified against source.
  (out/f'calendar{q}.mem').write_text(''.join(f'{v:064x}\n'for v in words))
  (out/f'calendar{q}.json').write_text(json.dumps(events,indent=2)+'\n')
 s=['''`timescale 1ns/1ps
module tb #(parameter integer STATION_MUT=0);
reg refclk=0;always #5 refclk=~refclk;
reg por_n=0;wire clk,stream,rs,rq;wire br,brfault;
hfd_ckgen cg(.refclk(refclk),.por_n(por_n),.pll_stream(stream),.pll_serial(clk),.por_serial(rq),.por_stream(rs));
reg reset_n=0;wire runrs=rs&&reset_n,runrq=rq&&reset_n;
wire[3:0] busy,valid,pfault,calrun;wire[2421:0] cmd[0:3],rawcmd[0:3];
ot_hbm_su_bridge_release_s rel(.clk_serial(clk),.rst_n(runrq),.prog_busy(busy[0]),.bridge_rst_n(br),.fault(brfault));
integer st=-1,qt=-1;
always @(posedge stream)if(rs)st=st+1;
always @(posedge clk)if(rq)qt=qt+1;
integer episode=0,mut=0;integer abort_mode=0;initial abort_mode=$test$plusargs("RESET_ABORT");reg launch=0;reg[3:0] we=0;
reg[15:0] cb[0:3];reg[6:0] cr[0:3];reg[255:0] cd[0:3];
wire[3:0] sfault[0:3];wire[16383:0] lanes_x;wire[511:0] lanes_v;
wire root_v;wire[31:0] root_x;wire station_fault;wire[9:0] cycle;
wire[10:0] capture_count,add_count;
wire station_start=valid[0] && edgeidx[0]==0;
wire[15:0] edgeidx[0:3];
wire[3:0] capmask=(cycle==64||cycle==176||cycle==288||cycle==400)?4'hf:4'h0;
wire[1:0] capgroup=(cycle-64)/112;
ot_hbm_r6_station41 #(.ENABLE(1),.MUT(STATION_MUT)) station(.clk(clk),.rst_n(runrq),.start(station_start),.episode_epoch(8'(episode+1)),.lane_x(lanes_x),.lane_v(lanes_v),.capture(capmask),.capture_group(capgroup),.root_v(root_v),.root_x(root_x),.fault(station_fault),.cycle(cycle),.capture_count(capture_count),.add_count(add_count));
reg[31:0] squares[0:2559],inputs[0:2559];
initial begin $readmemh("input0.mem",inputs,0,1279);$readmemh("input1.mem",inputs,1280,2559);$readmemh("square0.mem",squares,0,1279);$readmemh("square1.mem",squares,1280,2559);end
wire[31:0] gold[0:1];reg[31:0] goldmem[0:1];assign gold[0]=goldmem[0];assign gold[1]=goldmem[1];
wire[127:0] rfb;wire[35:0] rfbc;wire[255:0] rfd;
wire rsv,rfv,qfault;wire[31:0] rtag,rx;wire[3:0] wv;wire[31:0] wa;wire[127:0] wd;
ot_hbm_su_static_qcore #(.COLLPORT(1),.RF_LOCAL(1),.ROOT_OPERAND(1)) core(.clk_rf({64{clk}}),.clk_ctl(clk),.clk_red(clk),.rst_n(runrq),.rf_rd_cmd(cmd[0][127:74]),.red_cmd(cmd[0][73:0]),.rf_drain_cmd(cmd[0][166:165]),.slice_x(128'b0),.rf_wv(wv),.rf_wa(wa),.rf_wd(wd),.rf_bword(rfb),.rf_bcmd(rfbc),.rf_dsec(rfd),.red_sv(rsv),.red_tag(rtag),.red_x(rx),.red_rf_v(rfv),.rr_wv(1'b0),.rr_wa(5'b0),.rr_wd(256'b0),.sfu_x(32'b0),.root_operand({root_v&&(mut!=8),root_x}),.root_select((cmd[0][73]&&cmd[0][72:70]==0)&&(mut!=7)),.fault(qfault));
wire[40:0] up[0:14];wire[163:0] down[0:14];
ot_hbm_su_stree_leaf leaf(.clk(clk),.rst_n(runrq),.head_i({rfv,(mut==9 ? 8'd1 : rtag[7:0]),rx}),.up_o(up[0]),.dn_i(down[14]),.rf_wv(wv),.rf_wa(wa),.rf_wd(wd));
ot_hbm_su_stree_root treeroot(.clk(clk),.rst_n(runrq),.up0_i(up[14]),.up1_i(41'b0),.up2_i(41'b0),.up3_i(41'b0),.dn0_o(down[0]),.dn1_o(),.dn2_o(),.dn3_o());
''']
 # Preserve the exact selected direction master at each station.
 for i in range(14):
  upmaster=binding['instances'][f'stu_SW_{i:02d}']['master']
  am=binding['instances'][f'std_SW_{i:02d}a']['master']
  bm=binding['instances'][f'std_SW_{i:02d}b']['master']
  s.append(f'''wire[47:0] upwide{i};{upmaster} ur{i}(.ck(clk),.rs(runrq),.i({{7'b0,up[{i}]}}),.o(upwide{i}));assign up[{i+1}]=upwide{i}[40:0];
wire[135:0] da{i};wire[47:0] db{i};{am} dra{i}(.ck(clk),.rs(runrq),.i(down[{i}][135:0]),.o(da{i}));{bm} drb{i}(.ck(clk),.rs(runrq),.i({{20'b0,down[{i}][163:136]}}),.o(db{i}));assign down[{i+1}]={{db{i}[27:0],da{i}}};\n''')
 s.append('reg[95:0] adds[0:2561];initial $readmemh("adds.mem",adds);\n')
 ops=json.loads((out/'adds.json').read_text())
 for si in range(41):
  node=f'station.g_on.s{si}.u_node'if si<40 else'station.g_on.u_global'
  s.append(f'always @(posedge clk)if(runrq&&station.g_on.active)begin case(cycle)\n')
  for oi,o in enumerate(ops):
   if o['station']!=si:continue
   s.append(f'''{o['source_start']+3}:begin
 if(!{node}.ov||{{{node}.oa,{node}.ob}}!==adds[episode*1281+{oi}][95:32])$fatal(1,"ADD_INPUT_ID id={oi} station={si}");
 $display("ADD_IN id={oi} station={si} episode=%0d aborted=%0d cycle=%0d a=%h b=%h",episode,(abort_mode&&qt<6100),cycle,{node}.oa,{node}.ob);
end
''')
   s.append(f'''{o['source_done']}:begin
 if(!{node}.vy||{node}.y!==adds[episode*1281+{oi}][31:0]||{node}.err)$fatal(1,"ADD_OUTPUT_ID id={oi} station={si}");
 $display("ADD_OUT id={oi} station={si} episode=%0d aborted=%0d cycle=%0d y=%h",episode,(abort_mode&&qt<6100),cycle,{node}.y);
end
''')
  s.append('default:begin end endcase end\n')
 s.append('''integer roots=0,scalars=0,checked=0,fillcount=0,retired=0;integer startqt=0;integer abortfills=0;reg root_seen=0;
always @(posedge clk)begin
 if(station_start)begin startqt=qt;root_seen=0;end
 #0.001;
 if(runrq&&root_v&&!root_seen)begin root_seen=1;
  $display("ROOT episode=%0d age=%0d data=%h captures=%0d adds=%0d",episode,qt-startqt,root_x,capture_count,add_count);
  if(qt-startqt!=591)$fatal(1,"ROOT_AGE");
  if(root_x!==gold[episode]||capture_count!=1280||add_count!=1281)$fatal(1,"ROOT_NUMERIC");roots++;
 end
 if(runrq&&rsv)begin
  $display("SCALAR episode=%0d age=%0d tag=%h data=%h",episode,qt-startqt,rtag,rx);
  if(qt-startqt!=613)$fatal(1,"SCALAR_AGE");
  if(rx!==gold[episode]||rtag!=32'h100)$fatal(1,"SCALAR_IDENTITY");scalars++;
 end
end
''')
 s.append('''always @(posedge clk)if(runrq)begin
 if(|wv)begin
  $display("RF_PIN episode=%0d age=%0d v=%h addr=%h data=%h",episode,qt-startqt,wv,wa,wd);
  if(qt-startqt!=646||wv!=1||wa[7:0]!=0||wd[31:0]!==gold[episode])$fatal(1,"RF_WRITE_PIN_ID_AGE");
 end
 if(cmd[0][127])begin
  if(qt-startqt!=648||cmd[0][126:119]!=0)$fatal(1,"RF_CLASS5_ID_AGE");
  $display("RF_CLASS5 episode=%0d age=%0d",episode,qt-startqt);
 end
 if(cmd[0][166])begin
  if(qt-startqt!=650||cmd[0][165]!=1||cmd[0][151:136]!=4096||cmd[0][135:128]!=1)$fatal(1,"DRAIN_ID_AGE_MASK");
  $display("RF_DRAIN episode=%0d age=%0d",episode,qt-startqt);
 end
 #0.001;
 if(startqt>0&&qt-startqt==651&&core.rf_dsec[31:0]!==gold[episode])$fatal(1,"RF_DSEC_CAPTURE");
 if(s0_0.u_slice.su_w_done[0])begin
  $display("SERIAL_RETIRE episode=%0d age=%0d",episode,qt-startqt);
  if(qt-startqt!=670)$fatal(1,"SERIAL_NATIVE_DONE_AGE");retired++;
 end
end
''')
 for replica in range(6):
  s.append(f'''always @(posedge clk)begin #0.001;
 if(runrq&&startqt>0&&qt-startqt==647&&core.u_rf.g_bank[0].u_bank.g_replica[{replica}].v0!==gold[episode])$fatal(1,"RF_COHERENT_COMMIT replica={replica}");
end
''')
 for q in range(4):
  # Runtime mutations alter real boundary commands; immutable CP image checks
  # still compare raw producer output, so their failure is mechanistic.
  from su_arith_generate import FIELDS
  off={};pos=0
  for fn,fw in reversed(FIELDS):off[fn]=pos;pos+=fw
  raw=[int(v,16)for v in (out/f'q{q}/quarter.mem').read_text().split()]
  s.append(f'''reg[2421:0] applied{q};
assign cmd[{q}]=applied{q};
always @*begin
 applied{q}=rawcmd[{q}];
 if(mut==5 && (edgeidx[{q}]==144||edgeidx[{q}]==256||edgeidx[{q}]==368))applied{q}[2421:680]=1742'h{raw[32]>>680:x};
 if(mut==6 && edgeidx[{q}]>=40)applied{q}[{680+off['cp_m1']}+:3]=0;
 if(mut==10&&{q}==0)begin
  applied{q}[127:74]=0;
  if(edgeidx[{q}]==647)applied{q}[127:74]=54'h20000000000000;
 end
 if(mut==11&&{q}==0&&edgeidx[{q}]==650)applied{q}[135:128]=8'hff;
end
''')
  cfg=(out/f'q{q}/cols/config.mem').read_text().split();W=len(cfg)
  s.append(f'''reg[279:0] cfg{q}[0:{W-1}];reg[2421:0] expected{q}[0:671];integer n{q}=0;
ot_hbm_su_programme_pslice_c5 p{q}(.clk(clk),.rst_n(runrq),.cfg_we(we[{q}]),.cfg_bank(cb[{q}]),.cfg_row(cr[{q}]),.cfg_data(cd[{q}]),.start(launch),.length(16'd672),.busy(busy[{q}]),.valid(valid[{q}]),.done(),.fault(pfault[{q}]),.edge_index(edgeidx[{q}]),.command(rawcmd[{q}]));
always @(posedge clk)if(!runrq)n{q}=0;else if(valid[{q}])begin
 if(edgeidx[{q}]!=n{q}%672 || rawcmd[{q}]!==expected{q}[n{q}%672])$fatal(1,"PROGRAMME_Q{q}");n{q}++;
end
initial begin
 $readmemh("q{q}/cols/config.mem",cfg{q});$readmemh("q{q}/quarter.mem",expected{q});
 for(integer attempt=0;attempt<1+abort_mode;attempt++)begin wait(runrq);repeat(12)@(negedge clk);
 if(!(mut==14&&attempt==1))for(integer i=0;i<{W};i++)begin we[{q}]=1;cb[{q}]=cfg{q}[i][279:264];cr[{q}]=cfg{q}[i][262:256];cd[{q}]=cfg{q}[i][255:0];@(negedge clk);end we[{q}]=0;
 if(abort_mode&&attempt==0)@(negedge runrq);end
end
reg cv{q}=0,dv{q}=0,lv{q}=0;reg[11:0] ca{q}=0;reg[255:0] cdcal{q}=0;
wire acv{q},adv{q},alv{q};wire[7:0] act{q};wire[11:0] aca{q},adb{q};wire[255:0] acd{q};wire[12:0] adl{q};wire[15:0] adlp{q};wire tf{q},cf{q};wire[23:0] lr{q},lw{q},rslot{q},wslot{q};wire[7:0] rv{q},wv{q};
ot_hbm_host_cfg_leaf_sw hleaf{q}(.clk(stream),.rst_n(runrs),.cfg_v(cv{q}),.cfg_target(8'd{96+q}),.cfg_addr(ca{q}),.cfg_data(cdcal{q}),.desc_v(dv{q}),.desc_base(12'b0),.desc_limit(13'd1024),.desc_loops(16'd1),.launch_v(lv{q}),.a_cfg_v(acv{q}),.a_cfg_target(act{q}),.a_cfg_addr(aca{q}),.a_cfg_data(acd{q}),.a_desc_v(adv{q}),.a_desc_base(adb{q}),.a_desc_limit(adl{q}),.a_desc_loops(adlp{q}),.a_launch_v(alv{q}),.t_ready(14'b0),.t_active(14'b0),.t_fault(23'b0));
hfd_hgi_vm_calendar_f20 cal{q}(.clk(stream),.clk_cap(stream),.clk_mem(stream),.clk_tgt(stream),.rst_n(runrs),.tgt(8'd{96+q}),.cfg_v(acv{q}),.cfg_target(act{q}),.cfg_addr(aca{q}),.cfg_data(acd{q}),.desc_v(adv{q}),.desc_base(adb{q}),.desc_limit(adl{q}),.desc_loops(adlp{q}),.launch_v(alv{q}),.tgt_fault(tf{q}),.fault(cf{q}),.calendar_v(calrun[{q}]),.ordinal(),.lg_local_read(lr{q}),.lg_local_write(lw{q}),.rslot_v(rv{q}),.wslot_v(wv{q}),.rslot(rslot{q}),.wslot(wslot{q}));
reg[255:0] image{q}[0:1023];
initial begin
 $readmemh("calendar{q}.mem",image{q});
 for(integer attempt=0;attempt<1+abort_mode;attempt++)begin wait(runrs);repeat(20)@(negedge stream);
 for(integer i=0;i<1024;i++)begin cv{q}=1;ca{q}=i;cdcal{q}=image{q}[i];@(negedge stream);end cv{q}=0;
 if(abort_mode&&attempt==0)begin
  while(st<7800)@(negedge stream);dv{q}=1;@(negedge stream);dv{q}=0;while(st<7950)@(negedge stream);lv{q}=1;@(negedge stream);lv{q}=0;@(negedge runrs);
 end
 end
 for(integer e=0;e<2;e++)begin
  while(st<7800+12000*(e+abort_mode))@(negedge stream);
  if(!(mut==13&&e==1))begin dv{q}=1;@(negedge stream);dv{q}=0;end
  while(st<7950+12000*(e+abort_mode))@(negedge stream);lv{q}=1;@(negedge stream);lv{q}=0;
 end
end
''')
  s.append(f'''always @(posedge clk)if(runrq&&capmask[{q}])begin
 for(integer l=0;l<{128 if q in(0,2)else 32};l++)begin
  if(!lanes_v[{q*128}+l]||lanes_x[32*({q*128}+l)+:32]!==squares[episode*1280+capgroup*320+{(0,128,160,288)[q]}+l])$fatal(1,"LANE_CAPTURE_IDENTITY q={q} lane=%0d group=%0d",l,capgroup);
 end
 $display("SOURCE_CAPTURE q={q} group=%0d cycle=%0d",capgroup,cycle);
end
''')
  for g in range(4):
   s.append(f'''wire[33:0] rq{q}_{g};wire[561:0] wq{q}_{g};wire[513:0] rr{q}_{g};wire[1:0] dn{q}_{g};wire lf{q}_{g};
ot_hbm_su_static_pgslice_lg #(.QID({q}),.G({g}),.READ_RETURN(18),.WRITE_RETURN(15),.MLAT(4),.ALAT(3),.LEAF(1),.PIN_REG(1),.MULTIRATE(1),.COLLPORT(1),.RF_LOCAL(1)) s{q}_{g}(.pg_clk(stream),.clk_lane({{256{{clk}}}}),.clk_insert({{128{{clk}}}}),.rst_lane_n({{32{{runrq}}}}),.clk_bcast({{4{{clk}}}}),.rst_bcast_n({{4{{runrq}}}}),.clk_bank({{32{{clk}}}}),.clk_bank_macro({{192{{clk}}}}),.clk_ctl(clk),.clk_side({{6{{clk}}}}),.rst_n(runrq),.bridge_rst_n(br),.control(cmd[{q}][2421:680]),.vmr_cmd(cmd[{q}][{440+60*g}+:60]),.vmw_cmd(cmd[{q}][{128+78*g}+:78]),.rf_bword(rfb),.rf_bcmd(rfbc),.rf_dsec(rfd),.red_sel(12'b0),.inj_rd(2'b0),.inj_addr(160'b0),.dw_v(2'b0),.dw_row(18'b0),.dw_d(1024'b0),.fault(sfault[{q}][{g}]),.lg_fault(lf{q}_{g}),.lg_rq(rq{q}_{g}),.lg_wq(wq{q}_{g}),.lg_rr(rr{q}_{g}),.lg_w_done(dn{q}_{g}),.lg_read(lr{q}[{2*g}+:2]),.lg_write(lw{q}[{2*g}+:2]),.far_rq(34'b0),.far_wq(562'b0));
''')
   s.append(f'''always @(posedge clk)if(runrq)begin
 if(lf{q}_{g})$fatal(1,"NATIVE_LG_FAULT q={q} group={g}");
 if(s{q}_{g}.u_slice.fr_v[0])fillcount++;
 if(s{q}_{g}.u_slice.fr_v[1])fillcount++;
end
''')
   for n in range(32):
    L=16*g+n if n<16 else 64+16*g+n-16
    s.append(f'assign lanes_x[{32*(128*q+L)}+:32]=s{q}_{g}.u_slice.ro_x[{32*n}+:32];assign lanes_v[{128*q+L}]=s{q}_{g}.u_slice.ro_v[{n}];\n')
    inner=f's{q}_{g}.u_slice.g_lane[{n}].g_pr.u_lane.u_lane'
    if L<(128 if q in(0,2)else 32):
     ix=f"episode*1280+((cycle-32)/112)*320+{(0,128,160,288)[q]+L}"
     s.append(f'''always @(posedge clk)if(runrq)begin
 if({inner}.f_v)begin
  if((cycle-32)%112!=4 || {inner}.f_a!==24'(({q}<<14)|(((cycle-32)/112)<<7)|{L}))$fatal(1,"F0_SOURCE_AGE_ID q={q} lane={L} cycle=%0d",cycle);
 end
 if({inner}.x_v)begin
  if((cycle-32)%112!=10 || {inner}.x_a!==inputs[{ix}])$fatal(1,"X_SOURCE_AGE_DATA q={q} lane={L} cycle=%0d",cycle);
 end
 if({inner}.p_v)begin
  if((cycle-32)%112!=11 || {inner}.p_a!==inputs[{ix}])$fatal(1,"PRE_SOURCE_AGE_DATA q={q} lane={L} cycle=%0d",cycle);
 end
end
''')

     for valid,data,age,label in [('v1','P',15,'M1'),('v2','P2',19,'M2'),('v3','R',22,'AD'),('v4','S',22,'SFU_NONE'),('v5','T',26,'E1'),('v6','U',30,'E2'),('ro_v','ro_x',31,'OUT')]:
      s.append(f'''always @(posedge clk)if(runrq&&cycle>=32&&cycle<480&&(cycle-32)%112=={age})begin
 if(!{inner}.{valid}||{inner}.{data}!==squares[{ix}])$fatal(1,"{label}_SOURCE_AGE_DATA q={q} lane={L} cycle=%0d",cycle);
end
''')

   for h in range(2):
    p=2*g+h
    if q in (1,3)and p>=4:
     s.append(f'assign rr{q}_{g}[{257*h}+:257]=0;assign dn{q}_{g}[{h}]=0;\n');continue
    name=f'v{q}_{p}'
    s.append(f'''wire[16:0] {name}rq;wire[280:0] {name}wq;wire[256:0] {name}rr;wire {name}dn;
source_lane #(17,3,{1+p%2},0) {name}rl(stream,runrs,rq{q}_{g}[{17*h}+:17],{name}rq);
source_lane #(281,3,0,0) {name}wl(stream,runrs,wq{q}_{g}[{281*h}+:281],{name}wq);
source_lane #(257,{3-p%2},0,{1-p%2}) {name}ret(stream,runrs,{name}rr,rr{q}_{g}[{257*h}+:257]);
wire {name}ack;source_lane #(1,{3-p%2},0,{1-p%2}) {name}dl(stream,runrs,{name}dn,{name}ack);hbfd_pad #(.W(1),.N({1+p%2})) {name}dp(.ck(stream),.rs(runrs),.i({name}ack),.o(dn{q}_{g}[{h}]));
wire[17:0] {name}status;always @(posedge stream)if(runrs&&(|{name}status))$fatal(1,"NATIVE_BANK_STATUS q={q} bank={p} status=%h",{name}status);
reg[280:0] {name}hostw=0;reg[16:0] {name}hostr=0;wire[256:0] {name}hostrr;
wire {name}hosttime=(st%12000<7900)||(st%12000>=8900);
hfd_vms_bank_native_q0_faces {name}(.rq0({name}rq),.rr0({name}rr),.rq1({name}hostr),.rr1({name}hostrr),.rq2(17'b0),.rq3(17'b0),.rq4(17'b0),.wq0({name}wq),.wq_done0({name}dn),.wq1({name}hostw),.wq_done1(),.bid(3'd{p}),.sid(2'd{q}),.clk(stream),.clk_n(stream),.clk_s(stream),.clk_e(stream),.clk_w(stream),.clk_macro0(stream),.clk_macro1(stream),.clk_macro2(stream),.rst_n(runrs),.rslot_v({name}hosttime?{name}hostr[16]:rv{q}[{p}]),.rslot({name}hosttime?3'd1:rslot{q}[{3*p}+:3]),.wslot_v({name}hosttime?{name}hostw[280]:wv{q}[{p}]),.wslot({name}hosttime?3'd1:wslot{q}[{3*p}+:3]),.dq(281'b0),.kq(281'b0),.xq(276'b0),.xq2(276'b0),.pq(285'b0),.status({name}status));
''')
    events=[e for e in json.loads((out/f'calendar{q}.json').read_text()) if e['port']==p]
    for kind,bit in [('read',16),('write',280)]:
     matches=[e for e in events if e['kind']==kind]
     if matches:
      cases=[]
      for ev in matches:
       w=int((out/f'q{q}/quarter.mem').read_text().split()[ev['command']],16)
       sector=(w>>(440+30*p+13 if kind=='read'else 128+39*p+8))&65535
       cases.append(f"{ev['vm']} : if({name}{'rq'if kind=='read'else'wq'}[{15 if kind=='read'else 279}-:16]!=16'd{sector})$fatal(1,\"NATIVE_{kind.upper()}_SECTOR q={q} bank={p}\");")
      bus=f"{name}{'rq'if kind=='read'else'wq'}"
      s.append(f'''always @(posedge stream)if(runrs&&{bus}[{bit}])begin
 $display("NATIVE_PIN {kind} q={q} bank={p} st=%0d serial=%0d sector=%h",st,qt,{bus}[{15 if kind=='read'else 279}-:16]);
 case(st%12000)
 {chr(10).join(cases)}
 default:$fatal(1,"NATIVE_{kind.upper()}_PIN_AGE q={q} bank={p}");endcase
end
''')
    s.append(f'''always @(posedge stream)begin #0.001;if(runrs&&{name}dn)$display("NATIVE_BANK_DONE q={q} bank={p} st=%0d qt=%0d",st,qt);end
''')
    s.append('initial begin wait(runrs);\n')
    for ep in range(3):
     dataep=max(0,ep-1)
     packs=json.loads((out/f'preload{dataep}.json').read_text());packs=[r for r in packs if r['q']==q and r['bank']==p]
     s.append(f'if((abort_mode&&{ep}>=0)||(!abort_mode&&{ep}>0))begin\nwhile(st<{100}+12000*({ep}-1+abort_mode))@(negedge stream);\n')
     for row in packs:
      s.append(f"{name}hostw={{1'b1,16'd{row['sector']},256'h{row['value']},8'hff}};@(negedge stream);{name}hostw=0;repeat(12)@(negedge stream);\n")
     if q==0 and p==0:
      old=sum((0x3e800000+i)<<(32*i)for i in range(8))
      expected=(old&~0xffffffff)|int(receipt['gold'][dataep],16)
      s.append(f"{name}hostw={{1'b1,16'd4096,256'h{old:064x},8'hff}};@(negedge stream);{name}hostw=0;\nif({ep}>0)begin while(st<9000+12000*({ep}-1+abort_mode))@(negedge stream);{name}hostr={{1'b1,16'd4096}};@(negedge stream);{name}hostr=0;end\n")
     s.append('end\n')
    s.append('end\n')
    if q==0 and p==0:
     old=sum((0x3e800000+i)<<(32*i)for i in range(8))&~0xffffffff
     s.append(f'''always @(posedge stream)if(runrs&&{name}hostrr[256])begin
 if({name}hostrr[255:0]!=={{224'h{old>>32:056x},gold[episode]}})$fatal(1,"NATIVE_FULL_OLD_SECTOR");checked++;$display("NATIVE_FULL_SECTOR episode=%0d st=%0d data=%h",episode,st,{name}hostrr[255:0]);end
''')
 s.append('''initial begin
 $value$plusargs("MUT=%d",mut);$readmemh("gold.mem",goldmem);
 por_n=0;#100 por_n=1;wait(rq&&rs);reset_n=1;
 if(abort_mode)begin
  while(qt<6001)@(negedge clk);launch=1;@(negedge clk);launch=0;
  while(qt<6100)@(negedge clk);abortfills=fillcount;$display("RESET_ABORT qt=%0d stationcycle=%0d captures=%0d",qt,cycle,capture_count);reset_n=0;
  repeat(4)@(negedge clk);reset_n=1;$display("RESET_REINSTALL_RELEASE qt=%0d st=%0d",qt,st);
 end
 while(qt<6001+9000*abort_mode)@(negedge clk);launch=1;@(negedge clk);launch=0;
 while(st<9300+12000*abort_mode)@(negedge stream);
 if(roots!=1||scalars!=1||checked!=1)$fatal(1,"FIRST_EPISODE_INCOMPLETE");
 episode=1;
 while(qt<15001+9000*abort_mode)@(negedge clk);launch=1;@(negedge clk);launch=0;
 while(st<21300+12000*abort_mode)@(negedge stream);
 if(fillcount-abortfills!=320)$fatal(1,"NATIVE_FILL_COUNT");
 if(roots!=2||scalars!=2||checked!=2||retired!=2||station_fault||qfault||brfault||(|pfault))$fatal(1,"COMPONENT_FINAL");
''')
 for q in range(4):s.append(f'if((|sfault[{q}])||cf{q}||tf{q}||n{q}!=1344)$fatal(1,"Q{q}_FAULT");\n')
 s.append('''$display("R6_COMPONENT_PASS two_distinct_episodes native_full_sector");$finish;
end
always @(posedge stream)if(runrs&&st==19980+12000*abort_mode&&mut==13&&!calrun[0])$fatal(1,"DESCRIPTOR_REARM_IGNORED_LAUNCH");
always @(posedge clk)if(runrq&&mut==14&&abort_mode&&qt>15001&&(|pfault))$fatal(1,"RESET_WITHOUT_REINSTALL_PRODUCER_FAULT");
endmodule
module source_lane #(parameter W=1,N=3,PAD=0,SN=0)(input clk,rs,input[W-1:0] d,output[W-1:0] q);
wire[W-1:0] dp;if(PAD>0)hbfd_pad #(.W(W),.N(PAD)) pad(.ck(clk),.rs(rs),.i(d),.o(dp));else assign dp=d;
wire[623:0] v[0:N];assign v[0]={{(624-W){1'b0}},dp};
for(genvar i=0;i<N;i++)begin:G
if(SN&&i==0)hbfd_rly_624_SN r(.ck(clk),.rs(rs),.i(v[i]),.o(v[i+1]));else hbfd_rly_624_EW r(.ck(clk),.rs(rs),.i(v[i]),.o(v[i+1]));end
assign q=v[N][W-1:0];endmodule
''')
 (out/'tb.sv').write_text(''.join(s))
