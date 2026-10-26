`timescale 1ps/1fs
// TOKSIM-HBM-smhbm 2026-10-19: tb_hbm_svg_rel_sm (HBM-SMBUDGET) re-composed EXACTLY as the GEN2e3 d4g die binds one SM
// (artifacts/hdie-d4/d4g_gen2e3/pb0/die.v svg_SW0 / vmks_SW0 / ctl_SW_p00..p03 / sm_SW0):
//   svg = ot_hbm_svc_sm_group_rel_id #(.ID_COHORT(1)) (ids_cohort = runs started, as hb_router_ids)
//   K ports -> ot_hbm_svc_vm_kshare_splitstrap #(.KRL1(1)) (sm strap 0; VM fill / WB windows idle)
//   -> 4 x ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(OREG 1,KREG 1,KRREG 1,RREG 1,WPAY 1,QREG 1) = the bound PC master
//   -> tb_svg_rel_dram_sparse (off-chip DRAM timing fixture, the only model)
//   SM = ot_hbm_accel_smh_attn #(.ENABLE_INT8(1)) (die parameter).  Everything else as tb_hbm_svg_rel_sm.
// HBM-SMBUDGET 2026-10-19 (coordinator decision 0jx): ONE d4g SM driven by its REAL relative HBM service, end to end:
//   host ingress word stream -> cp_svg collar (ot_static_run_target: 2,048-row programme window, run arg = layer)
//     -> svg = ot_hbm_svc_sm_group_rel_id (token-resident relative issuer + 2,048-word relocating programme feed, four-PC
//        producer, landing/cache SRAMs) -> 4 real controller leaves (ot_hbm_svc_native_sector_pipeline_leaves PCs 0-3)
//        -> DRAM command fixture (sparse copy, same timing checks)
//   ingress -> xc collar + extension calendar (ot_hbm_svc_sm_xcal_rel_t) in lockstep
//   SM = the d4g die SM master ot_hbm_accel_smh_attn: command = {xc.cmd_ext, svg.sm_command}, packet = svg.sm_packet,
//        kv_desc = xc.kv_desc.
// The bench only PLAYS three compiler-written event lists on fixed stream edges (never reacts to the DUT): +ING= the F20
// ingress words (programme rows, descriptor rows -- written ONCE -- then per layer one run descriptor per target + one
// global launch), +IDS= the router top-k broadcast {layer, ids} (C2), +XW= the SM x-store beats (the x-loader's job on the
// die; declared external stimulus), and +MEM= the HBM image (sector30 data pairs).  It prints every SM result row
// (R cycle row data), every programme go (G cycle base) and run end (D cycle), and stops on ANY fault: cp/xc collar,
// issuer (bad word, late or busy go slot = the static schedule would have stalled), feed / cache / producer, SM fault or
// schedule_fault (packet/command mismatch), DRAM command timing.  Results are checked bit for bit by smb_unit.py.
module tb_toksim_smhbm;
 parameter integer MAXI=8192, MAXX=65536, MAXD=64, NID=6;
 reg stream=0,hbm=0;initial forever begin #416.666 stream=1;#416.667 stream=0;end
 initial begin #173;forever #512 hbm=~hbm;end
 reg srst=0,hrst=0;
 // ---------------- event lists
 reg[351:0]ing_m[0:MAXI-1];reg[2095:0]xw_m[0:MAXX-1];reg[95:0]ids_m[0:MAXD-1];
 integer ni,nx,nd,nend,pi=0,px=0,pd=0;integer cyc=0;string fi,fx,fd,fm;
 reg cfg_v=0,desc_v=0,launch_v=0;reg[7:0]target=0;reg[11:0]addr=0,dbase=0;reg[255:0]data=0;reg[12:0]dlimit=0;reg[15:0]dloops=0;
 reg ids_v=0;reg[7:0]ids_layer=0;reg[9*NID-1:0]ids=0;
 reg xw_en=0;reg[6:0]xw_addr=0,xw_grp=0;reg[2047:0]xw_data=0;
 // ---------------- cp_svg collar -> svg
 wire a_we,b_we,run_v,cp_cfgd,cp_fault,cp_active;wire[10:0]a_addr;wire[7:0]b_addr,run_base;wire[255:0]a_data,b_data;
 wire[8:0]run_count;wire[7:0]run_arg;wire running,run_done,active,svg_fault;
 ot_static_run_target #(.AWA(11),.AWB(8),.RBW(8),.RCW(9),.TGT_PIN(1)) cp_svg(.clk(stream),.rst_n(srst),.tgt(8'd64),
  .cfg_v(cfg_v),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(desc_v),.desc_base(dbase),.desc_limit(dlimit),
  .desc_loops(dloops),.launch_v(launch_v),.tgt_active(running),.tgt_fault(svg_fault),.a_we(a_we),.a_addr(a_addr),.a_data(a_data),
  .b_we(b_we),.b_addr(b_addr),.b_data(b_data),.run_v(run_v),.run_base(run_base),.run_count(run_count),.run_arg(run_arg),
  .configured(cp_cfgd),.fault(cp_fault),.active(cp_active));
 wire[31:0]kv,krdy,kwe,kdone,rv_,rrdy;wire[959:0]ka;wire[127:0]kl,rb;wire[543:0]kt,rt;wire[8191:0]kw,rd;wire[1023:0]ks;
 wire[1098:0]packet;wire[82:0]command;
 reg[15:0]ids_cohort=0;always @(posedge stream)if(run_v)ids_cohort<=ids_cohort+16'd1;
 ot_hbm_svc_sm_group_rel_id #(.LBANKS(4),.NID(NID),.IDW(9),.PAW(11),.PREL(1),.DD(256),.ID_COHORT(1),.IMUT(`ifdef IMUT `IMUT `else 0 `endif),
  // HBM-SMXL: XSLOT = the descriptor's x-store slot base relocates every command's xaddr (die op_xb)
  .XSLOT(`ifdef XSLOT 1 `else 0 `endif),.OPEN_IL(`ifdef OPEN_IL 1 `else 0 `endif)) svg(
  .id_stack(2'd0),.id_sm(3'd0),
  .stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),.hbm_rst_n(hrst),.stream_bank_clk({2{stream}}),.hbm_fifo_clk({2{hbm}}),.hbm_pc_clk({4{hbm}}),
  .program_cfg_we(a_we),.program_cfg_addr(a_addr),.program_cfg_data(a_data),
  .desc_we(b_we),.desc_addr(b_addr),.desc_data(b_data),.run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_arg),
  .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.ids_cohort(ids_cohort),
  .running(running),.run_done(run_done),.program_active(active),.fault(svg_fault),
  .sm_packet(packet),.sm_command(command),.expected_request(),.lt0(),.lt1(),.lb0(),.lb1(),.fm(),
  .k_v(kv[3:0]),.k_rdy(krdy[3:0]),.k_addr(ka[119:0]),.k_len(kl[15:0]),.k_tag(kt[67:0]),.k_we(kwe[3:0]),
  .k_wdata(kw[1023:0]),.k_wstrb(ks[127:0]),.k_wr_done(kdone[3:0]),
  .kr_v(rv_[3:0]),.kr_rdy(rrdy[3:0]),.kr_tag(rt[67:0]),.kr_beat(rb[15:0]),.kr_data(rd[1023:0]));
 assign kv[31:4]=0;assign ka[959:120]=0;assign kl[127:16]=0;assign kt[543:68]=0;assign kwe[31:4]=0;assign kw[8191:1024]=0;
 assign ks[1023:128]=0;assign rrdy[31:4]={28{1'b1}};
 // ---------------- xc (extension calendar, own collar)
 wire[108:0]cmd_ext;wire[63:0]kv_desc;wire xc_done,xc_cfgd,xc_fault,xc_active;
 ot_hbm_svc_sm_xcal_rel_t #(.PAW(11),.PREL(1),.DD(256),.XSLOT(`ifdef XSLOT 1 `else 0 `endif),.MUT(`ifdef XMUT `XMUT `else 0 `endif)) xc(.clk(stream),.rst_n(srst),.tgt(8'd192),
  .cfg_v(cfg_v),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(desc_v),.desc_base(dbase),.desc_limit(dlimit),
  .desc_loops(dloops),.launch_v(launch_v),.cmd_ext(cmd_ext),.kv_desc(kv_desc),.done(xc_done),.configured(xc_cfgd),
  .fault(xc_fault),.active(xc_active));
 // ---------------- HBM: real controller leaves + DRAM command fixture
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire native_fault;
 // die composition: vmks (KRL1) + four bound h9b PC masters
 wire[3:0]c_kv,c_krdy,c_kwe,c_kdone,c_krv,c_krrdy;wire[119:0]c_ka;wire[15:0]c_kl,c_krb;wire[67:0]c_kt,c_krt;
 wire[1023:0]c_kw,c_krd;wire[127:0]c_ks;wire vmks_fault;wire[3:0]pcf;wire[23:0]ofs;
 wire[3:0]fill_v_u,fill_bank_u;wire[23:0]fill_slot_u;wire[63:0]fill_epoch_u;wire[1023:0]fill_data_u;wire[3:0]w_k_rdy_u,w_k_wr_done_u;
 ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0),.KRL1(1)) vmks(.hbm_clk(hbm),.hbm_rst_n(hrst),.stream_clk(stream),.stream_rst_n(srst),
  .sm_stream(3'd0),.sm_hbm(3'd0),
  .g_k_v(kv[3:0]),.g_k_rdy(krdy[3:0]),.g_k_addr(ka[119:0]),.g_k_len(kl[15:0]),.g_k_tag(kt[67:0]),.g_k_we(kwe[3:0]),
  .g_k_wdata(kw[1023:0]),.g_k_wstrb(ks[127:0]),.g_k_wr_done(kdone[3:0]),
  .g_kr_v(rv_[3:0]),.g_kr_rdy(rrdy[3:0]),.g_kr_tag(rt[67:0]),.g_kr_beat(rb[15:0]),.g_kr_data(rd[1023:0]),
  .c_k_v(c_kv),.c_k_rdy(c_krdy),.c_k_addr(c_ka),.c_k_len(c_kl),.c_k_tag(c_kt),.c_k_we(c_kwe),.c_k_wdata(c_kw),.c_k_wstrb(c_ks),
  .c_k_wr_done(c_kdone),.c_kr_v(c_krv),.c_kr_rdy(c_krrdy),.c_kr_tag(c_krt),.c_kr_beat(c_krb),.c_kr_data(c_krd),
  .vm_v(1'b0),.vm_bank(1'b0),.vm_epoch(16'd0),.vm_row(15'd0),.vm_col(4'd0),.wbw_v(1'b0),.wbw_base(30'd0),.wbw_total(12'd0),
  .w_k_v(4'd0),.w_k_rdy(w_k_rdy_u),.w_k_addr(120'd0),.w_k_wdata(1024'd0),.w_k_wr_done(w_k_wr_done_u),
  .fill_v(fill_v_u),.fill_bank(fill_bank_u),.fill_slot(fill_slot_u),.fill_epoch(fill_epoch_u),.fill_data(fill_data_u),.fault(vmks_fault));
 for(genvar p=0;p<4;p=p+1)begin:g_pc
  // refresh phases as tb_hbm_bw_pc4 H9B (HBM-BW): staggered per PC, die ot_hbm_pc_refresh_cfg reload class 118
  localparam integer RP=(p*118/32)%118;
  localparam integer RELOAD=118+RP+((RP+118+p)%2);
`ifdef TOKSIM_SAFE_PC
  // TOKSIM-HBM 10-19: successor PC controller (HBM-MC2 SAFE multi-row, claude/l2h-bw-safe-1019; port-identical to h9b +
  // kr_v_regions).  TOKSIM_MC3 = the HBM-MC3 physical structure (pure face captures, reset forest, local pc_id copies).
  // NOT bound in GEN2e3 die.v (release candidate controller).
`ifdef TOKSIM_MC3
  localparam integer MC3=1;
`else
  localparam integer MC3=0;
`endif
  wire[17:0]krvr_unused;
  ot_hbm_svc_pc_ctrl_leaf_cfg_safe #(.OREG(1),.KREG(1),.KRREG(1),.RREG(1),.WPAY(1),.PURE_FACE(MC3),.RST_FOREST(MC3),.PCID_LOCAL(MC3))
   ctl(.clk(hbm),.rst_n(hrst),.kr_v_regions(krvr_unused),
`else
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1),.KREG(1),.KRREG(1),.RREG(1),.WPAY(1),.QREG(1)) ctl(.clk(hbm),.rst_n(hrst),
`endif
   .pc_id(5'(p)),.refresh_reload(8'(RELOAD)),
   .k_v(c_kv[p]),.k_rdy(c_krdy[p]),.k_we(c_kwe[p]),.k_addr(c_ka[p*30+:30]),.k_len(c_kl[p*4+:4]),.k_tag(c_kt[p*17+:17]),
   .k_wdata(c_kw[p*256+:256]),.k_wstrb(c_ks[p*32+:32]),.kr_v(c_krv[p]),.kr_rdy(c_krrdy[p]),.kr_tag(c_krt[p*17+:17]),
   .kr_beat(c_krb[p*4+:4]),.kr_data(c_krd[p*256+:256]),.k_wr_done(c_kdone[p]),
   .row_v(row_v[p]),.row_op(row_op[p*3+:3]),.row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
   .col_v(col_v[p]),.col_we(col_we[p]),.col_bank(col_bank[p*5+:5]),.col_col(col_col[p*5+:5]),.col_data(col_data[p*256+:256]),
   .col_strb(col_strb[p*32+:32]),.dram_rvalid(dram_rvalid[p]),.dram_rdata(dram_rdata[p*256+:256]),.pc_fault(pcf[p]),
   .owner_fault_split(ofs[p*6+:6]));
 end
 assign row_v[31:4]=0;assign col_v[31:4]=0;assign col_we[31:4]=0;assign row_op[95:12]=0;assign row_bank[159:20]=0;
 assign row_row[607:76]=0;assign col_bank[159:20]=0;assign col_col[159:20]=0;assign col_data[8191:1024]=0;assign col_strb[1023:128]=0;
 assign native_fault=vmks_fault|(|pcf)|(|ofs);
 tb_svg_rel_dram_sparse dram(.clk(hbm),.rst_n(hrst),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),
  .col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 // ---------------- the d4g die SM master
 wire[42:0]request;wire sm_rv,sm_fault,sm_sfault;wire[11:0]rrow;wire[255:0]rdata;
`ifdef TOKSIM_I8W
 // HBM-QINT8B (10-20): + the opt-in WIDE INT8 front (ot_hbm_sm_i8w_front, command mode 3, 128 codes/edge)
 ot_hbm_accel_smh_attn #(.ENABLE_INT8(1),.INT8W(1)) sm(
`else
 ot_hbm_accel_smh_attn #(.ENABLE_INT8(1)) sm(
`endif.clk(stream),.rst_n(srst),.command({cmd_ext,command}),.kv_desc(kv_desc),.packet(packet),
  .request(request),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .rv(sm_rv),.rrow(rrow),.rdata(rdata),.fault(sm_fault),.schedule_fault(sm_sfault));
 // ---------------- checks / trace
`ifdef OT_SM_QSPLIT
 reg[1098:1088]s1v=0;always @(posedge stream)s1v<=svg.feed.s1_packet[1098:1088];
`else
 wire[1098:1088]s1v=svg.feed.s1_packet[1098:1088];
`endif
 integer nres=0,ngo=0,nrun=0,i8v_n=0;reg[1:0]cr_q=0;reg[3:0]br_q=0;reg[3:0]pr_q=0;
`ifdef PTRACE
 integer ap;always @(posedge hbm)if(hrst)for(ap=0;ap<4;ap=ap+1)if(row_v[ap])$display("A %0d %0d %0d %0d %0d",cyc,ap,row_op[ap*3+:3],row_bank[ap*5+:5],row_row[ap*19+:19]);
`endif
 always @(posedge hbm)if(hrst&&native_fault)begin $display("FAULT controller cycle %0d vmks %0d pc %b ofs %h",cyc,vmks_fault,pcf,ofs);$fatal(1,"native_fault");end
 always @(posedge stream)if(srst&&hrst)begin
  if(sm_rv)begin $display("R %0d %03h %064h",cyc,rrow,rdata);nres=nres+1;end
`ifdef TRACE
  if(ngo<=2&&(command!=0||svg.feed.programme[83]||svg.feed.programme[117]||packet[1098]))$display("T %0d cmd %h rd %0d/%0d/%0d ret %0d pkt %0d/%0d",cyc,command[39:0],svg.feed.programme[83],svg.feed.programme[106:101],svg.feed.programme[116:107],svg.feed.programme[117],packet[1098],packet[1097:1088]);
`endif
  if(svg.program_start_v)begin $display("G %0d %0d %0d",cyc,svg.program_start_base,svg.issuer.rc);ngo=ngo+1;end
  if(run_done)begin $display("D %0d",cyc);nrun=nrun+1;end
  if(svg.issuer.reserve_v)$display("V %0d %0d",cyc,svg.issuer.reserve_bank);
  if(svg.issuer.start_v)$display("S %0d %0d",cyc,svg.issuer.start_bank);
  if(svg.feed.cache_ready!=cr_q)$display("C %0d %b",cyc,svg.feed.cache_ready);
  if(svg.feed.block_ready!=br_q)$display("B %0d %b",cyc,svg.feed.block_ready);
  cr_q<=svg.feed.cache_ready;br_q<=svg.feed.block_ready;
`ifdef PTRACE
  // HBM-SMXL2 diagnostic only: raw landing-producer readiness (before the OPEN_IL cache mask) -> fetch law of the elastic side
  if(svg.feed.producer_ready!=pr_q)$display("P %0d %b",cyc,svg.feed.producer_ready);
  pr_q<=svg.feed.producer_ready;
`endif
  if(sm_sfault)begin $display("FAULT sm_schedule cycle %0d",cyc);$fatal(1,"sm schedule_fault");end
  if(sm_fault)begin $display("FAULT sm_arith cycle %0d",cyc);$fatal(1,"sm fault");end
  if(svg_fault)begin $display("FAULT svg cycle %0d issuer %0d feed %0d (desc %0d cdc %0d cache %0d prog %0d s1 %0d fl %0d i8 %0d)",cyc,svg.issuer.fault,svg.feed.fault,
   svg.feed.descriptor_fault,svg.feed.cdc_fault,svg.feed.cache_fault,svg.feed.programme_fault,svg.feed.feed_fault,svg.feed.inj_f,svg.feed.i8_f);
   $display("ISSUER rc %0d sq_n %0d gq_n %0d gh_at %0d go_busy %0d cache_ready %b block_ready %b a_v %0d p_v %0d st_v %0d s_blk %0d rd_q %0d",svg.issuer.rc,svg.issuer.sq_n,svg.issuer.gq_n,svg.issuer.gh_at,svg.issuer.go_busy,svg.issuer.cache_ready,svg.issuer.block_ready,svg.issuer.a_v,svg.issuer.p_v,svg.issuer.st_v,svg.issuer.s_blk,svg.issuer.rd_q);$fatal(1,"svg fault");end
  if(xc_fault)begin $display("FAULT xc cycle %0d",cyc);$fatal(1,"xc fault");end
  // HBM-QINT8: the svg S1 copy's INT8 view must equal the packet the SM front sees (valid every edge, tag when valid)
  // (reported, then fatal 4 edges later so a die fault the mismatch causes is reported first)
  // HBM-P4-SM (OT_SM_QSPLIT): the SM lands its inputs one cycle (R2-alt), so its front sees the svg view one edge later
  if(i8v_n==0&&(s1v[1098]!=sm.f_packet[1098]||(sm.f_packet[1098]&&s1v[1097:1088]!=sm.f_packet[1097:1088])))begin
   $display("I8VIEW mismatch cycle %0d svg %0d/%0d sm %0d/%0d",cyc,s1v[1098],s1v[1097:1088],sm.f_packet[1098],sm.f_packet[1097:1088]);i8v_n=1;end
  else if(i8v_n!=0)begin i8v_n=i8v_n+1;if(i8v_n==5)begin $display("FAULT i8view cycle %0d",cyc);$fatal(1,"i8 view");end end
  if(cp_fault)begin $display("FAULT cp_svg cycle %0d",cyc);$fatal(1,"cp fault");end
 end
 // event player: inputs change after the edge, sampled at the next one
 always @(posedge stream)if(srst&&hrst)begin
  cyc<=cyc+1;
  cfg_v<=0;desc_v<=0;launch_v<=0;ids_v<=0;xw_en<=0;
  if(pi<ni&&ing_m[pi][351:320]==32'(cyc))begin
   {cfg_v,desc_v,launch_v,target,addr,data,dbase,dlimit,dloops}<=ing_m[pi][319:0];pi<=pi+1;
  end else if(pi<ni&&ing_m[pi][351:320]<32'(cyc))begin $display("FAULT bench ingress order %0d",pi);$fatal(1,"bench");end
  if(px<nx&&xw_m[px][2095:2064]==32'(cyc))begin
   {xw_en,xw_addr,xw_grp,xw_data}<=xw_m[px][2062:0];px<=px+1;
  end
  if(pd<nd&&ids_m[pd][93:62]==32'(cyc))begin ids_v<=1;ids_layer<=ids_m[pd][61:54];ids<=ids_m[pd][53:0];pd<=pd+1;end
 end
 integer f,nm=0,code;reg[31:0]sa;reg[255:0]sd;
 initial begin
  if(!$value$plusargs("ING=%s",fi)||!$value$plusargs("XW=%s",fx)||!$value$plusargs("IDS=%s",fd)||!$value$plusargs("MEM=%s",fm)||
     !$value$plusargs("NI=%d",ni)||!$value$plusargs("NX=%d",nx)||!$value$plusargs("ND=%d",nd)||!$value$plusargs("END=%d",nend))$fatal(1,"plusargs");
  if(ni>MAXI||nx>MAXX||nd>MAXD)$fatal(1,"event list longer than the build");
  $readmemh(fi,ing_m,0,ni-1);$readmemh(fx,xw_m,0,nx-1);if(nd>0)$readmemh(fd,ids_m,0,nd-1);
  f=$fopen(fm,"r");if(f==0)$fatal(1,"MEM");
  while(!$feof(f))begin code=$fscanf(f,"%h %h\n",sa,sd);if(code==2)begin dram.mem[sa]=sd;nm=nm+1;end end
  $fclose(f);$display("MEM sectors=%0d",nm);
  repeat(4)@(negedge stream);srst=1;repeat(3)@(negedge hbm);hrst=1;
  wait(cyc>=nend);
  $display("DONE cycles=%0d results=%0d gos=%0d runs=%0d ing=%0d/%0d xw=%0d/%0d ids=%0d/%0d dram_reads=%0d",cyc,nres,ngo,nrun,pi,ni,px,nx,pd,nd,dram.reads);
  $finish;
 end
endmodule
