`timescale 1ps/1fs
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
module tb_hbm_svg_rel_sm;
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
 `ifdef SMB_SRAMFIFO
 ot_hbm_svc_sm_group_rel_sram_id #(.NATIVE_CACHE_SAFE(`ifdef SMB_NATIVE_CACHE_SAFE 1 `else 0 `endif),.ATTENTION(`ifdef SMB_ATTENTION 1 `else 0 `endif),.NATIVE_RETURN(`ifdef SMB_NATIVE_RETURN 1 `else 0 `endif),.RETURN_MUT(`ifdef SMB_RETURN_MUT `SMB_RETURN_MUT `else 0 `endif),.NATIVE_LANDING(`ifdef SMB_NATIVE_LANDING 1 `else 0 `endif),.FIFOMUT(`ifdef SMB_FIFOMUT `SMB_FIFOMUT `else 0 `endif),
 `else
 ot_hbm_svc_sm_group_rel_id #(
 `endif
.LBANKS(4),.NID(NID),.IDW(9),.PAW(11),.PREL(1),.DD(256),.IMUT(`ifdef IMUT `IMUT `else 0 `endif)) svg(
  `ifdef SMB_SRAMFIFO
  .return_pair_clk({4{stream}}),.return_local_clk({4{stream}}),.return_pair_hbm_clk({4{hbm}}),
  `endif
  .id_stack(2'd0),.id_sm(3'd0),
  .stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),.hbm_rst_n(hrst),.stream_bank_clk({2{stream}}),.hbm_fifo_clk({2{hbm}}),.hbm_pc_clk({4{hbm}}),
  .program_cfg_we(a_we),.program_cfg_addr(a_addr),.program_cfg_data(a_data),
  .desc_we(b_we),.desc_addr(b_addr),.desc_data(b_data),.run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_arg),
  .ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),
  .running(running),.run_done(run_done),.program_active(active),.fault(svg_fault),
  .sm_packet(packet),.sm_command(command),.expected_request(),.lt0(),.lt1(),.lb0(),.lb1(),.fm(),
  .k_v(kv[3:0]),.k_rdy(krdy[3:0]),.k_addr(ka[119:0]),.k_len(kl[15:0]),.k_tag(kt[67:0]),.k_we(kwe[3:0]),
  .k_wdata(kw[1023:0]),.k_wstrb(ks[127:0]),.k_wr_done(kdone[3:0]),
  .kr_v(rv_[3:0]),.kr_rdy(rrdy[3:0]),.kr_tag(rt[67:0]),.kr_beat(rb[15:0]),.kr_data(rd[1023:0]));
 assign kv[31:4]=0;assign ka[959:120]=0;assign kl[127:16]=0;assign kt[543:68]=0;assign kwe[31:4]=0;assign kw[8191:1024]=0;
 assign ks[1023:128]=0;assign rrdy[31:4]={28{1'b1}};
 // ---------------- xc (extension calendar, own collar)
 wire[108:0]cmd_ext;wire[63:0]kv_desc;wire xc_done,xc_cfgd,xc_fault,xc_active;
 `ifdef SMB_NATIVE_CACHE_SAFE
 ot_hbm_svc_sm_xcal_rel_cache2_t
 `else
 ot_hbm_svc_sm_xcal_rel_t
 `endif
 #(.PAW(11),.PREL(1),.DD(256),.MUT(`ifdef XMUT `XMUT `else 0 `endif)) xc(.clk(stream),.rst_n(srst),.tgt(8'd192),
  .cfg_v(cfg_v),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(desc_v),.desc_base(dbase),.desc_limit(dlimit),
  .desc_loops(dloops),.launch_v(launch_v),.cmd_ext(cmd_ext),.kv_desc(kv_desc),.done(xc_done),.configured(xc_cfgd),
  .fault(xc_fault),.active(xc_active));
 // ---------------- HBM: real controller leaves + DRAM command fixture
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire native_fault;
 ot_hbm_svc_native_sector_pipeline_leaves controller(.clk(hbm),.rst_n(hrst),.pc_clk({32{hbm}}),
  .k_tag(kt),.k_wdata(kw),.k_addr(ka),.kr_rdy(rrdy),.k_wstrb(ks),.k_we(kwe),.k_len(kl),.k_rdy(krdy),.kr_v(rv_),.kr_data(rd),.kr_beat(rb),
  .k_wr_done(kdone),.kr_tag(rt),.k_v(kv),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),
  .col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
 tb_svg_rel_dram_sparse dram(.clk(hbm),.rst_n(hrst),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),
  .col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 // ---------------- the d4g die SM master
 wire[42:0]request;wire sm_rv,sm_fault,sm_sfault;wire[11:0]rrow;wire[255:0]rdata;
 ot_hbm_accel_smh_attn sm(.clk(stream),.rst_n(srst),.command({cmd_ext,command}),.kv_desc(kv_desc),.packet(packet),
  .request(request),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .rv(sm_rv),.rrow(rrow),.rdata(rdata),.fault(sm_fault),.schedule_fault(sm_sfault));
 // ---------------- checks / trace
 integer nres=0,ngo=0,nrun=0;reg[1:0]cr_q=0;reg[3:0]br_q=0;
 always @(posedge hbm)if(hrst&&native_fault)begin $display("FAULT dram_aperture cycle %0d",cyc);$fatal(1,"native_fault");end
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
  if(sm_sfault)begin $display("FAULT sm_schedule cycle %0d",cyc);$fatal(1,"sm schedule_fault");end
  if(sm_fault)begin $display("FAULT sm_arith cycle %0d",cyc);$fatal(1,"sm fault");end
  if(svg_fault)begin $display("FAULT svg cycle %0d issuer %0d feed %0d (desc %0d cdc %0d cache %0d prog %0d s1 %0d fl %0d)",cyc,svg.issuer.fault,svg.feed.fault,
   svg.feed.descriptor_fault,svg.feed.cdc_fault,svg.feed.cache_fault,svg.feed.programme_fault,svg.feed.feed_fault,svg.feed.inj_f);
   $display("ISSUER rc %0d sq_n %0d gq_n %0d gh_at %0d go_busy %0d cache_ready %b block_ready %b a_v %0d p_v %0d st_v %0d s_blk %0d rd_q %0d",svg.issuer.rc,svg.issuer.sq_n,svg.issuer.gq_n,svg.issuer.gh_at,svg.issuer.go_busy,svg.issuer.cache_ready,svg.issuer.block_ready,svg.issuer.a_v,svg.issuer.p_v,svg.issuer.st_v,svg.issuer.s_blk,svg.issuer.rd_q);$fatal(1,"svg fault");end
  if(xc_fault)begin $display("FAULT xc cycle %0d",cyc);$fatal(1,"xc fault");end
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
