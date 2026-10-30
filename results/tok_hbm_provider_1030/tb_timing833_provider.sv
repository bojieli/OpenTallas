`timescale 1ns/1ps
`default_nettype none
module tb_timing833_provider;
 reg clk=0,rst_n=0;always begin #0.416 clk=1;#0.417 clk=0;end
 // Fixturestrap106 exercises existing native target ports; not an additional
 // productiontarget allocation or overlap with the realSTOREtarget.
 reg[7:0]tgt=106,cfg_target=106;reg cfg_v=0,desc_v=0,launch_v=0;
 reg[11:0]cfg_addr=0,desc_base=0;reg[12:0]desc_limit=15;reg[15:0]desc_loops=1;reg[255:0]cfg_data=0;
 wire begin_v,begin_bank;wire[15:0]begin_epoch;wire[14:0]begin_row;wire[3:0]begin_col;
 wire[15:0]fill_v,fill_bank;wire[95:0]fill_slot;wire[255:0]fill_epoch;wire[4095:0]fill_data;
 reg release_v_i=0,release_buffer_i=0;reg[15:0]release_epoch_i=0;
 wire configured,cp_active,busy_o,fault_o,load_done_o;wire[31:0]cycle;wire[280:0]vm_dq;wire[15:0]block_ready;wire[7:0]leaf_fault;
 wire[307:0]cmd;wire shared_cmd_v,load_v,store_v,collar_fault,dispatch_fault,load_busy,load_fault;
 wire store_busy,store_fault,store_done;wire[135:0]store_rq;wire[2055:0]store_rr;
 wire wr_reserve,wr_bank,wr_fill_bank,wr_fill_start,wb_ready,wb_fault;wire[15:0]wr_epoch,wr_fill_epoch;wire[11:0]wr_sectors,wa;wire[31:0]wr_base;wire[2311:0]wd;
 wire wbw_v;wire[29:0]wbw_base;wire[11:0]wbw_total;
 wire[3:0]wbw_copy_v;wire[119:0]wbw_copy_base;wire[47:0]wbw_copy_total;
 wire[15:0]wk_v,wk_ready,wk_done;wire[479:0]wk_addr;wire[4095:0]wk_data;
 integer store_cmds=0,store_completions=0,physical_WR=0;
 assign busy_o=load_busy|store_busy;assign fault_o=load_fault|store_fault|dispatch_fault|collar_fault|wb_fault;
 ot_hgi_dma_back_cp_collar cp(.clk(clk),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.tgt_active(busy_o),.tgt_fault(fault_o),.cmd_v(shared_cmd_v),.cmd(cmd),.cycle(cycle),.configured(configured),.fault(collar_fault),.active(cp_active));
 ot_hbm_static_dma_cmd_dispatch dispatch(.clk(clk),.rst_n(rst_n),.cmd_v_i(shared_cmd_v),.cmd_i(cmd),.busy_i(busy_o),.backend_fault_i(load_fault|store_fault|wb_fault),.load_v_o(load_v),.store_v_o(store_v),.fault_o(dispatch_fault));
 ot_hbm_static_load_cmd_provider_quad #(.SOURCE_QUAD(2))dut(.clk(clk),.rst_n(rst_n),.cmd_v(load_v),.cmd(cmd),.cycle(cycle),.command_fault_i(collar_fault|dispatch_fault),
 .begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),.begin_row(begin_row),.begin_col(begin_col),.fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),.release_v_i(release_v_i),.release_buffer_i(release_buffer_i),.release_epoch_i(release_epoch_i),.vm_dq_done_i(vm_dq_done_i),.vm_fault_i(vm_fault_i),.dated_step_o(),.admit_o(),.vm_dq(vm_dq),.block_ready(block_ready),.leaf_fault(leaf_fault),.busy_o(load_busy),.fault_o(load_fault),.load_done_o(load_done_o));
 ot_hgi_dma_back_static_vp4_banks_rs #(.RR_RT(80))back(.clk(clk),.rst_ctl_n(rst_n),.rst_bank_n({8{rst_n}}),.stk(2'd2),.clk_bank({8{clk}}),.cycle(cycle),.mv_v(store_v),.mv(cmd[290:64]),.issue_at(cmd[31:0]),.drain_at(cmd[63:32]),.mv_wb_bank(cmd[291]),.mv_wb_epoch(cmd[307:292]),.mv_src(),.mv_done(store_done),.mv_fault(store_fault),.quiet(),.busy(store_busy),.rq(store_rq),.rr(store_rr),.wb_reserve_v(wr_reserve),.wb_reserve_bank(wr_bank),.wb_fill_bank(wr_fill_bank),.wb_reserve_epoch(wr_epoch),.wb_fill_epoch(wr_fill_epoch),.wb_reserve_sectors(wr_sectors),.wb_reserve_base(wr_base),.wb_fill_start(wr_fill_start),.wb_ready(wb_ready),.wd(wd),.wa(wa));
 ot_hbm_svc_wb_kport_q #(.WOPEN(0),.MUT(0))wb(.stream_clk(clk),.stream_rst_n(rst_n),.hbm_clk(clk),.hbm_rst_n(rst_n),.stream_fifo_clk({4{clk}}),.stk(2'd2),.quad(1'b0),.wb_reserve_v(wr_reserve),.wb_reserve_bank(wr_bank),.wb_fill_bank(wr_fill_bank),.wb_reserve_epoch(wr_epoch),.wb_fill_epoch(wr_fill_epoch),.wb_reserve_sectors(wr_sectors),.wb_reserve_base(wr_base),.wb_fill_start(wr_fill_start),.wd(wd),.wb_ready(wb_ready),.wa(wa),.wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),.w_k_v(wk_v),.w_k_rdy(wk_ready),.w_k_addr(wk_addr),.w_k_wdata(wk_data),.w_k_wr_done(wk_done),.fault(wb_fault));
 ot_hbm_svc_wbw_copy #(.NS(4))wbcopy(.stream_clk(clk),.stream_rst_n(rst_n),.wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),.o_wbw_v(wbw_copy_v),.o_wbw_base(wbw_copy_base),.o_wbw_total(wbw_copy_total));
 always @(posedge clk)if(rst_n)begin if(store_v)store_cmds=store_cmds+1;if(store_done)store_completions=store_completions+1;end
 reg[226:0]descs[0:13];reg[31:0]steps[0:13];reg[280:0]expected[0:2687];
 integer cyc=0,sent=0,got=0,latency=-1,phase,b,g,s,w,di,wordno,mut_epoch=0,mut_deadline=0,mut_slot=0,mut_bank=0,mut_late=0;
 integer sent_cycle[0:2687];integer first_step=-1,last_step=-1,first_packet=-1,last_packet=-1,cmds=0;
 integer at_date,issue_date,drain_date,final_drain;
 integer vm_latency=-1,read_latency=-1,vm_acks=0,load_dones=0,read_sent=0,read_got=0,first_fault=-1,first_dq_capture=-1,first_bank_ack=-1;
 integer dq_sent[0:31],dq_got[0:31],dq_cycle[0:31][0:1023];
 integer read_cycle[0:2687];integer read_j,read_bank,k,resp;
 wire[8991:0]bank_dq;
 wire demux_fault;
 wire[31:0]native_done;
 // Actual native geography: SID0=SW(flat0..7),SID1=SE(flat8..15),
 // SID2=NW(flat16..23),SID3=NE(flat24..31). These are not NW-first qids.
 wire geo_SW_bank0_done=native_done[0];
 wire geo_SE_bank0_done=native_done[8];
 wire geo_NW_bank0_done=native_done[16];
 wire geo_NE_bank0_done=native_done[24];
 wire[17:0]vm_status[0:31];
 wire[31:0]vm_dq_done_i,vm_fault_i;
 reg[31:0]ack_delay[0:23];
 reg[16:0]rq0_bank[0:31];wire[256:0]rr0_bank[0:31];wire[256:0]store_rr_native[0:7];
 ot_hbm_static_load_vm_dq_demux demux(.packet_i(vm_dq),.bank_dq_o(bank_dq),.fault_o(demux_fault));
 assign vm_dq_done_i=mut_late!=0?ack_delay[23]:native_done;
 for(genvar bankidx=0;bankidx<32;bankidx=bankidx+1)begin:VM
  wire[256:0]rr1_local;
 if(bankidx/8==2)begin:RETURN
 assign store_rr_native[bankidx%8]=rr1_local;
 reg[256:0]delay[0:71];
 always @(posedge clk)begin delay[0]<=rst_n?rr1_local:257'd0;for(integer z=1;z<72;z=z+1)delay[z]<=rst_n?delay[z-1]:257'd0;end
 assign store_rr[(bankidx%8)*257+:257]=delay[71];
 end
 wire[280:0]incoming=bank_dq[bankidx*281+:281]^((mut_bank!=0&&bank_dq[bankidx*281+280])?(281'd1<<264):281'd0);
  assign vm_fault_i[bankidx]=vm_status[bankidx][17]|vm_status[bankidx][16];
  hfd_vms_bank_native_q0_faces bank(
   .rq0(rq0_bank[bankidx]),.rr0(rr0_bank[bankidx]),.rq1(bankidx/8==2?store_rq[(bankidx%8)*17+:17]:17'd0),.rr1(rr1_local),.rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
   .wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.bid(3'(bankidx%8)),.sid(2'(bankidx/8)),
   .clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),
   .rslot_v(rq0_bank[bankidx][16]|(bankidx/8==2&&store_rq[(bankidx%8)*17+16])),.rslot(bankidx/8==2&&store_rq[(bankidx%8)*17+16]?3'd1:3'd0),.wslot_v(bank_dq[bankidx*281+280]),.wslot(mut_slot!=0?3'd5:3'd6),
   .dq(incoming),.dq_done(native_done[bankidx]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(vm_status[bankidx]));
 end
 always @(posedge clk)begin
  if(!rst_n)begin for(integer delayidx=0;delayidx<24;delayidx=delayidx+1)ack_delay[delayidx]<=0;end
  else begin ack_delay[0]<=native_done;for(integer delayidx=1;delayidx<24;delayidx=delayidx+1)ack_delay[delayidx]<=ack_delay[delayidx-1];end
 end


 wire cal_v,cal_active,cal_done,cal_fault,cal_configured,cal_target_fault;wire[31:0]cal_ordinal;
 wire[88:0]cal_payload;
 assign begin_v=cal_v&&cal_payload[0];assign begin_bank=cal_payload[1];assign begin_epoch=cal_payload[17:2];assign begin_row=cal_payload[84:70];assign begin_col=cal_payload[88:85];assign vm_fill_v=cal_v&&cal_payload[52];
 integer cal_begin_count=0,cal_fill_count=0,cal_done_count=0;reg[255:0]cal_entry;
 hfd_hgi_vm_calendar_f20_role #(.W(89))cal(.clk(clk),.clk_cap(clk),.clk_mem(clk),.clk_tgt(clk),.rst_n(rst_n),.tgt(8'd58),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_configured(cal_configured),.tgt_fault(cal_target_fault),.calendar_v(cal_v),.active(cal_active),.done(cal_done),.fault(cal_fault),.ordinal(cal_ordinal),.payload(cal_payload));
 always @(posedge clk)if(rst_n)begin
 if(cal_fault||cal_target_fault)$fatal(1,"VMFC_CALENDAR_FAULT");
 if(begin_v)begin cal_begin_count=cal_begin_count+1;$display("VMFC_BEGIN edge=%0d epoch=%0d buffer=%0d row=%0d col=%0d",cyc,begin_epoch,begin_bank,begin_row,begin_col);end
 if(vm_fill_v)begin cal_fill_count=cal_fill_count+1;$display("VMFC_FILL edge=%0d epoch=%0d buffer=%0d row=%0d col=%0d",cyc,cal_payload[69:54],cal_payload[53],cal_payload[84:70],cal_payload[88:85]);end
 if(cal_done)cal_done_count=cal_done_count+1;
 end

 // Actual selected NW source service: four groups, sixteen PC controllers.
 // All selected clocks are pll_stream[0], reproduced at833ps phase0.
 wire vm_fill_v;reg ref_v=0;reg[255:0]ref_data=0;reg[255:0]timing_boot_data[0:0];
 wire[127:0]reload;wire pc_rst_n,ref_ready,ref_active,ref_fault;
 wire[3:0]vmks_fault;wire[15:0]pc_fault;
 integer fill_start,wait_edges,dram_reads=0,fill_count=0,refresh_count=0;
 ot_hbm_pc_refresh_cfg #(.NPC(16),.RMIN(144),.RMAX(252))refcfg(.clk(clk),.rst_n(rst_n),.clk_hbm(clk),.rst_hbm_n(rst_n),.tgt(8'd127),
 .cfg_v(ref_v),.cfg_target(8'd127),.cfg_addr(12'h800),.cfg_data(ref_data),.refresh_reload(reload),.pc_rst_n(pc_rst_n),.ready(ref_ready),.active(ref_active),.fault(ref_fault));
 wire[15:0]ckv,ckrdy,ckwe,ckdone,crv,crrdy;
 wire[479:0]cka;wire[63:0]cklen,crbeat;wire[271:0]cktag,crtag;
 wire[4095:0]ckdata,crdata;wire[511:0]ckstrb;
 wire[4095:0]phy_write_data;wire[511:0]phy_write_strb;wire[15:0]row_v,col_v,col_we;wire[47:0]row_op;wire[79:0]row_bank,col_bank,col_col;wire[303:0]row_row;
 reg[15:0]dram_rvalid=0;reg[255:0]dram_rdata[0:15];
 for(genvar vg=0;vg<4;vg=vg+1)begin:GROUP
 wire[3:0]fv,fb;wire[23:0]fs;wire[63:0]fe;wire[1023:0]fd;
 ot_hbm_svc_vm_kshare_splitstrap #(.KRL1(1),.MUT(0))vmks(
 .hbm_clk(clk),.hbm_rst_n(rst_n),.stream_clk(clk),.stream_rst_n(rst_n),.sm_stream(3'(vg)),.sm_hbm(3'(vg)),
 .g_k_v(4'd0),.g_k_rdy(),.g_k_addr(120'd0),.g_k_len(16'd0),.g_k_tag(68'd0),.g_k_we(4'd0),.g_k_wdata(1024'd0),.g_k_wstrb(128'd0),.g_k_wr_done(),
 .g_kr_v(),.g_kr_rdy(4'hf),.g_kr_tag(),.g_kr_beat(),.g_kr_data(),
 .c_k_v(ckv[vg*4+:4]),.c_k_rdy(ckrdy[vg*4+:4]),.c_k_addr(cka[vg*120+:120]),.c_k_len(cklen[vg*16+:16]),.c_k_tag(cktag[vg*68+:68]),
 .c_k_we(ckwe[vg*4+:4]),.c_k_wdata(ckdata[vg*1024+:1024]),.c_k_wstrb(ckstrb[vg*128+:128]),.c_k_wr_done(ckdone[vg*4+:4]),
 .c_kr_v(crv[vg*4+:4]),.c_kr_rdy(crrdy[vg*4+:4]),.c_kr_tag(crtag[vg*68+:68]),.c_kr_beat(crbeat[vg*16+:16]),.c_kr_data(crdata[vg*1024+:1024]),
 .vm_v(vm_fill_v),.vm_bank(cal_payload[53]),.vm_epoch(cal_payload[69:54]),.vm_row(cal_payload[84:70]),.vm_col(cal_payload[88:85]),
 .wbw_v(wbw_copy_v[vg]),.wbw_base(wbw_copy_base[vg*30+:30]),.wbw_total(wbw_copy_total[vg*12+:12]),.w_k_v(wk_v[vg*4+:4]),.w_k_rdy(wk_ready[vg*4+:4]),.w_k_addr(wk_addr[vg*120+:120]),.w_k_wdata(wk_data[vg*1024+:1024]),.w_k_wr_done(wk_done[vg*4+:4]),
 .fill_v(fv),.fill_bank(fb),.fill_slot(fs),.fill_epoch(fe),.fill_data(fd),.fault(vmks_fault[vg]));
 for(genvar lane=0;lane<4;lane=lane+1)begin:PC
 localparam integer P=vg*4+lane;
 localparam integer FI=2*(P%8)+(P/8);
 assign fill_v[FI]=fv[lane];assign fill_bank[FI]=fb[lane];assign fill_slot[FI*6+:6]=fs[lane*6+:6];assign fill_epoch[FI*16+:16]=fe[lane*16+:16];assign fill_data[FI*256+:256]=fd[lane*256+:256];
 ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.TIMING_833(1),.OREG(1),.KREG(1),.KRREG(1),.RREG(1),.WPAY(1),.QREG(1))ctl(
 .clk(clk),.rst_n(pc_rst_n),.pc_id(5'(P)),.refresh_reload(reload[P*8+:8]),
 .k_v(ckv[P]),.k_rdy(ckrdy[P]),.k_we(ckwe[P]),.k_addr(cka[P*30+:30]),.k_len(cklen[P*4+:4]),.k_tag(cktag[P*17+:17]),.k_wdata(ckdata[P*256+:256]),.k_wstrb(ckstrb[P*32+:32]),.k_wr_done(ckdone[P]),
 .kr_v(crv[P]),.kr_rdy(crrdy[P]),.kr_tag(crtag[P*17+:17]),.kr_beat(crbeat[P*4+:4]),.kr_data(crdata[P*256+:256]),
 .row_v(row_v[P]),.row_op(row_op[P*3+:3]),.row_bank(row_bank[P*5+:5]),.row_row(row_row[P*19+:19]),
 .col_v(col_v[P]),.col_we(col_we[P]),.col_bank(col_bank[P*5+:5]),.col_col(col_col[P*5+:5]),.col_data(phy_write_data[P*256+:256]),.col_strb(phy_write_strb[P*32+:32]),
 .dram_rvalid(dram_rvalid[P]),.dram_rdata(dram_rdata[P]),.pc_fault(pc_fault[P]),.owner_fault_split());
 end end
 // External memory pins only. No controller ready/credit or delivery fill is
 // driven by the fixture. Read return delay16edges=13.328ns; source-model CL12.5ns.
 reg opened[0:15][0:31];integer physical_row[0:15][0:31],act_at[0:15][0:31],pre_at[0:15][0:31],ref_until[0:15][0:31];
 integer last_rd_bank[0:15][0:31],last_wr_bank[0:15][0:31];
 integer last_act_pc[0:15],last_act_bg[0:15][0:3],last_col_pc[0:15],last_col_bg[0:15][0:3],last_rd_pc[0:15],last_wr_pc[0:15],last_ref_pc[0:15];
 integer last_row_pair[0:7],last_col_pair[0:7],act_history[0:15][0:3];
 integer ns_ACT=0,ns_PRE=0,ns_REF=0,ns_RD=0,ns_WR=0;
 task ns_min(input integer gap,required_ps,input string label,input integer pcno);
 if(gap*833<required_ps)$fatal(1,"LOCAL_NS_%s edge=%0d pc=%0d observed_ps=%0d required_ps=%0d",label,cyc,pcno,gap*833,required_ps);
 endtask
 reg[28:0]due_read[0:15];reg[255:0]due_data[0:15][0:28];
 function automatic[29:0]inverse(input integer pc,bank,row,col);
 reg[29:0]sec;begin sec=(row<<15)|((((bank>>2)^(row>>2))&7)<<12)|(col<<7)|((bank^row)&3);sec|=(pc^((sec>>7)&31)^((sec>>12)&31))<<2;inverse=sec;end endfunction
 always @(posedge clk)begin:PHY
 integer pp,bb,op,rr,sec,slotno,jj;
 if(rst_n)begin
 if(ref_fault||(|pc_fault)||(|vmks_fault))$fatal(1,"NATIVE_PHY_FAULT cycle=%0d ref=%b pc=%h vmks=%h",cyc,ref_fault,pc_fault,vmks_fault);
 for(pp=0;pp<16;pp=pp+1)begin
 if(fill_v[pp])fill_count=fill_count+1;
 dram_rvalid[pp]<=due_read[pp][28];dram_rdata[pp]<=due_data[pp][28];due_read[pp]<=due_read[pp]<<1;
 for(jj=1;jj<29;jj=jj+1)due_data[pp][jj]<=due_data[pp][jj-1];
 if(row_v[pp])begin
 ns_min(cyc-last_row_pair[pp/2],1024,"ROW_CA",pp);last_row_pair[pp/2]=cyc;
 bb=integer'(row_bank[pp*5+:5]);op=integer'(row_op[pp*3+:3]);rr=integer'(row_row[pp*19+:19]);
 if(op==1)begin
 ns_min(cyc-pre_at[pp][bb],16250,"RP_ACT",pp);ns_min(cyc-last_ref_pc[pp],8000,"RREFD_ACT",pp);
 ns_min(cyc-last_act_pc[pp],2500,"RRDS",pp);ns_min(cyc-last_act_bg[pp][bb%4],3125,"RRDL",pp);ns_min(cyc-act_history[pp][0],15000,"FAW",pp);
 for(integer z=0;z<3;z=z+1)act_history[pp][z]=act_history[pp][z+1];act_history[pp][3]=cyc;last_act_pc[pp]=cyc;last_act_bg[pp][bb%4]=cyc;ns_ACT=ns_ACT+1;
 if(opened[pp][bb]||cyc-pre_at[pp][bb]<16||cyc<ref_until[pp][bb])$fatal(1,"PHY_ACT_TIMING");
 opened[pp][bb]=1;physical_row[pp][bb]=rr;act_at[pp][bb]=cyc;
 end else if(op==0)begin
 ns_min(cyc-act_at[pp][bb],28125,"RAS_PRE",pp);ns_min(cyc-last_rd_bank[pp][bb],5625,"RTP_PRE",pp);ns_min(cyc-last_wr_bank[pp][bb],27899,"WRR_PRE",pp);ns_PRE=ns_PRE+1;
 if(opened[pp][bb]&&cyc-act_at[pp][bb]<28)$fatal(1,"PHY_PRE_TIMING");opened[pp][bb]=0;pre_at[pp][bb]=cyc;
 end else if(op==6)begin
 ns_min(cyc-pre_at[pp][bb],16250,"RP_REF",pp);ns_min(cyc-last_act_pc[pp],8000,"ACT_RREFD",pp);ns_min(cyc-last_ref_pc[pp],8000,"RREFD_REF",pp);
 last_ref_pc[pp]=cyc;ns_REF=ns_REF+1;
 if(opened[pp][bb]||cyc-pre_at[pp][bb]<16||cyc<ref_until[pp][bb])$fatal(1,"PHY_REF_TIMING");ref_until[pp][bb]=cyc+241;refresh_count=refresh_count+1;
 end else if(op!=5)$fatal(1,"PHY_ROW_OPCODE %0d",op);
 end
 if(col_v[pp])begin
 ns_min(cyc-last_col_pair[pp/2],512,"COL_CA",pp);last_col_pair[pp/2]=cyc;
 ns_min(cyc-last_col_pc[pp],1024,"CCDS",pp);last_col_pc[pp]=cyc;
 bb=integer'(col_bank[pp*5+:5]);
 ns_min(cyc-last_col_bg[pp][bb%4],2560,"CCDL",pp);last_col_bg[pp][bb%4]=cyc;
 if(col_we[pp])begin
 ns_min(cyc-act_at[pp][bb],9375,"RCD_WR",pp);ns_min(cyc-last_rd_pc[pp],9948,"RTW",pp);last_wr_pc[pp]=cyc;last_wr_bank[pp][bb]=cyc;ns_WR=ns_WR+1;
 end else begin
 ns_min(cyc-act_at[pp][bb],19375,"RCD_RD",pp);ns_min(cyc-last_wr_pc[pp],13524,"WTR",pp);last_rd_pc[pp]=cyc;last_rd_bank[pp][bb]=cyc;ns_RD=ns_RD+1;
 end
 if(!opened[pp][bb]||cyc-act_at[pp][bb]<(col_we[pp]?10:19)||cyc<ref_until[pp][bb])$fatal(1,"PHY_RD_TIMING");
 sec=integer'(inverse(pp,bb,physical_row[pp][bb],integer'(col_col[pp*5+:5])));
 if(col_we[pp])begin
 slotno=((sec>>7)<<6)|(sec&63);slotno=slotno-32'h100000;
 if(slotno<0||slotno>=8||phy_write_strb[pp*32+:32]!=32'hffffffff||phy_write_data[pp*256+:256]!==expected[phase*896+516+slotno][263:8])$fatal(1,"ACTUAL_PHY_STORE_DATA sector=%h ordinalidx=%0d",sec,slotno);physical_WR=physical_WR+1;
 end else begin
 if((sec>>15)!=20752||((sec>>8)&15)!=0)$fatal(1,"PHY_WRONG_WINDOW sec=%h",sec);
 slotno=4*((((sec>>7)&1)<<3)|((sec>>12)&7))+(sec&3);
 for(jj=0;jj<8;jj=jj+1)due_data[pp][0][jj*32+:32]<=payload(phase,pp%8,pp/8,slotno,jj);
 due_read[pp][0]<=1;dram_reads=dram_reads+1;end
 end
 end end end

 reg[307:0]command;reg[339:0]entry;reg[15:0]epoch;reg ebank;
 function automatic[31:0]payload(input integer ph,l,grp,slotno,wordidx);
 payload=32'h3e800000+32'(ph)*32'h01000000+32'(l)*32'h10000+32'(grp)*32'h1000+32'(slotno)*8+32'(wordidx);
 endfunction
 task tick;begin @(negedge clk);end endtask
 task write_word(input[11:0]address,input[255:0]data);
 begin cfg_addr=address;cfg_data=data;cfg_v=1;tick();cfg_v=0;tick();end endtask
 always @(posedge clk)begin
 cyc=cyc+1;
 if(rst_n)for(integer nb=0;nb<32;nb=nb+1)if(bank_dq[nb*281+280])begin
  if(first_dq_capture<0)first_dq_capture=cyc;
  dq_cycle[nb][dq_sent[nb]]=cyc;dq_sent[nb]=dq_sent[nb]+1;
 end
 if(rst_n&&dut.dated_step)begin
 if(first_step<0)first_step=cyc;last_step=cyc;sent_cycle[sent]=cyc;sent=sent+1;
 end
 if(rst_n&&dut.admit)begin cmds=cmds+1;
 $display("CP_CMD index=%0d edge=%0d nativecycle=%0d issue_at=%0d drain_at=%0d n=%0d",cmds,cyc,cycle,dut.cmd[31:0],dut.cmd[63:32],dut.move[226:206]);end
 #0.1;
 if(rst_n)begin
 if(fault_o||(|leaf_fault)||demux_fault)begin
  if(mut_slot==0&&mut_bank==0&&mut_late==0)$fatal(1,"VM_PROVIDER_UNEXPECTED_FAULT edge=%0d phase=%0d nativecycle=%0d fault=%b vm_fault=%h leaf=%h",cyc,phase,cycle,fault_o,vm_fault_i,leaf_fault);
  if(first_fault<0)first_fault=cyc;
  if(cyc>=first_fault+8)$fatal(1,"VM_PROVIDER_FAULT first=%0d edge=%0d slot=%0d bank=%0d late=%0d actual_native_acks=%0d load_done=%0d vm_fault=%h",first_fault,cyc,mut_slot,mut_bank,mut_late,vm_acks,load_dones,vm_fault_i);
 end
 if(load_done_o)begin
  if(mut_slot!=0||mut_bank!=0||mut_late!=0)$fatal(1,"VM_MUTANT_COMPLETED");
  load_dones=load_dones+1;
  $display("VM_LOAD_DONE index=%0d edge=%0d cycle_post=%0d drain_at=%0d",load_dones,cyc,cycle,dut.drain_at);
 end
 for(integer nb=0;nb<32;nb=nb+1)if(native_done[nb])begin
  if(first_bank_ack<0)first_bank_ack=cyc;
  if(dq_got[nb]>=dq_sent[nb])$fatal(1,"VM_UNSOLICITED_NATIVE_ACK bank=%0d",nb);
  if(vm_latency<0)vm_latency=cyc-dq_cycle[nb][dq_got[nb]];
  if(cyc-dq_cycle[nb][dq_got[nb]]!=vm_latency)$fatal(1,"VM_ACK_DATE bank=%0d actual=%0d expected=%0d",nb,cyc-dq_cycle[nb][dq_got[nb]],vm_latency);
  dq_got[nb]=dq_got[nb]+1;vm_acks=vm_acks+1;
 end
 resp=0;
 for(integer nb=0;nb<32;nb=nb+1)if(rr0_bank[nb][256])begin
  resp=resp+1;
  if(nb!=integer'({expected[read_got][278:277],expected[read_got][266:264]}))$fatal(1,"VM_READBACK_GEOGRAPHY actualflat=%0d expectedSID=%0d expectedbank=%0d",nb,expected[read_got][278:277],expected[read_got][266:264]);
  if(read_got>=read_sent||rr0_bank[nb][255:0]!==expected[read_got][263:8])$fatal(1,"VM_READBACK_DATA bank=%0d got=%0d sent=%0d actual=%h expected=%h",nb,read_got,read_sent,rr0_bank[nb],expected[read_got][263:8]);
  if(read_latency<0)read_latency=cyc-read_cycle[read_got];
  if(cyc-read_cycle[read_got]!=read_latency)$fatal(1,"VM_READBACK_DATE");
  read_got=read_got+1;
 end
 if(resp>1)$fatal(1,"VM_READBACK_COLLISION");
 if(vm_dq[280])begin
 if(got>=sent||vm_dq!==expected[got])$fatal(1,"CP_PROVIDER_DATA got=%0d sent=%0d actual=%h expected=%h",got,sent,vm_dq,expected[got]);
 if(latency<0)latency=cyc-sent_cycle[got];
 if(cyc-sent_cycle[got]!=latency)$fatal(1,"CP_PROVIDER_DATE actual=%0d expect=%0d",cyc-sent_cycle[got],latency);
 if(first_packet<0)first_packet=cyc;last_packet=cyc;got=got+1;
 end end end
 initial begin
 for(k=0;k<32;k=k+1)begin rq0_bank[k]=0;dq_sent[k]=0;dq_got[k]=0;end
 $readmemh("fixture_desc.mem",descs);$readmemh("fixture_steps.mem",steps);$readmemh("fixture_expected.mem",expected);
 if($value$plusargs("MUT_SLOT=%d",mut_slot))begin end
 if($value$plusargs("MUT_BANK=%d",mut_bank))begin end
 if($value$plusargs("MUT_LATE=%d",mut_late))begin end
 if($value$plusargs("MUT_EPOCH=%d",mut_epoch))begin end
 if($value$plusargs("MUT_DEADLINE=%d",mut_deadline))begin end
 for(integer pairidx=0;pairidx<8;pairidx=pairidx+1)begin last_row_pair[pairidx]=-100000;last_col_pair[pairidx]=-100000;end
 for(integer p=0;p<16;p=p+1)begin
 last_act_pc[p]=-100000;last_col_pc[p]=-100000;last_rd_pc[p]=-100000;last_wr_pc[p]=-100000;last_ref_pc[p]=-100000;
 for(integer bg=0;bg<4;bg=bg+1)begin last_act_bg[p][bg]=-100000;last_col_bg[p][bg]=-100000;act_history[p][bg]=-100000;end
 dram_rvalid[p]=0;dram_rdata[p]=0;due_read[p]=0;
 for(integer bb=0;bb<32;bb=bb+1)begin last_rd_bank[p][bb]=-100000;last_wr_bank[p][bb]=-100000;opened[p][bb]=0;pre_at[p][bb]=-1000;act_at[p][bb]=-1000;ref_until[p][bb]=0;end
 end
 repeat(32)tick();rst_n=1;repeat(16)tick();
 $readmemh("timing_boot.mem",timing_boot_data);ref_data=timing_boot_data[0];
 ref_v=1;tick();ref_v=0;
 while(!ref_ready)tick();repeat(16)tick();
 for(phase=0;phase<3;phase=phase+1)begin
 epoch=16'(7+phase);ebank=phase==2;
 // Actual existing VMFC target58 F20 programme, no directbegin/fill pin drive.
 cfg_target=58;desc_limit=18;
 for(integer ci=0;ci<18;ci=ci+1)begin
 cal_entry=0;cal_entry[255:240]=16'hc7a1;cal_entry[239:224]=16'(ci);
 if(ci==0)begin cal_entry[0]=1;cal_entry[1]=ebank;cal_entry[17:2]=epoch;cal_entry[84:70]=15'd20752;end
 if(ci==16)begin cal_entry[52]=1;cal_entry[53]=ebank;cal_entry[69:54]=epoch;cal_entry[84:70]=15'd20752;end
 write_word(12'(ci),cal_entry);
 end
 repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(40)tick();
 if(!cal_configured)$fatal(1,"VMFC_NOT_CONFIGURED");
 fill_start=cyc;launch_v=1;tick();launch_v=0;
 // Host preparation: a high old buffer fullness bit is not a newepoch receipt.
 // Observe this nativeROLE's FILL event (16edgesafter itsBEGIN) before ownedready.
 while(cal_fill_count<phase+1)tick();
 wait_edges=0;
 while((block_ready & (ebank?16'haaaa:16'h5555)) != (ebank?16'haaaa:16'h5555))begin
 tick();wait_edges=wait_edges+1;if(wait_edges>20000)$fatal(1,"PHY_FILL_TIMEOUT ready=%h faults=%h/%h",block_ready,pc_fault,vmks_fault);
 end
 $display("NATIVE_PHY_FILL phase=%0d first=%0d ready=%0d edges=%0d RD=%0d fills=%0d REF=%0d",phase,fill_start,cyc,cyc-fill_start,dram_reads,fill_count,refresh_count);
 repeat(16)tick();
 if(cal_begin_count!=phase+1||cal_fill_count!=phase+1||cal_done_count!=phase+1||cal_active)$fatal(1,"VMFC_EVENT_CONSERVATION");
 cfg_target=106;desc_limit=15;
 for(b=0;b<8;b=b+1)if(!block_ready[b*2+integer'(ebank)])$fatal(1,"CP_PROVIDER_FILL_READY");
 at_date=32;
 for(di=0;di<14;di=di+1)begin
 issue_date=at_date+8;drain_date=issue_date+integer'(steps[di])+20;
 if(mut_deadline!=0&&phase==0&&di==0)drain_date=issue_date+integer'(steps[di])-1;
 command=0;command[31:0]=32'(issue_date);command[63:32]=32'(drain_date);command[290:64]=descs[di];command[291]=ebank;command[307:292]=epoch;
 if(mut_epoch!=0&&phase==0&&di==0)command[307:292]=epoch+1;
 entry={command,32'(at_date)};
 write_word(12'h800+12'(di*2),entry[255:0]);write_word(12'h801+12'(di*2),{172'd0,entry[339:256]});
 at_date=drain_date+8;
 end
 // Same onecollar page nowdispatchesoneactual64word STORE after14LOADs.
 issue_date=at_date+8;drain_date=issue_date+112;
 command=0;command[31:0]=32'(issue_date);command[63:32]=32'(drain_date);
 command[290:64]=227'd1|(227'd5<<2)|(227'd8192<<5)|(227'd1<<77)|(227'd5<<95)|((227'd2<<35|227'h2000000)<<98)|(227'd1<<170)|(227'd1<<186)|(227'd64<<206);
 command[291]=ebank;command[307:292]=epoch;entry={command,32'(at_date)};
 write_word(12'h81c,entry[255:0]);write_word(12'h81d,{172'd0,entry[339:256]});
 final_drain=drain_date;
 repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(16)tick();
 if(!configured)$fatal(1,"CP_PROVIDER_CONFIGURED");
 launch_v=1;tick();launch_v=0;
 repeat(final_drain+2048)tick();
 if(store_completions!=phase+1||physical_WR!=(phase+1)*8)$fatal(1,"SHARED_STORE_CONSERVATION cmds=%0d done=%0d WR=%0d fault=%b",store_cmds,store_completions,physical_WR,fault_o);
 if(got!=sent||got!=(phase+1)*896||busy_o||cp_active)$fatal(1,"CP_PROVIDER_DRAIN got=%0d sent=%0d busy=%b cpactive=%b",got,sent,busy_o,cp_active);
 if(load_dones!=(phase+1)*14||vm_acks!=got)$fatal(1,"VM_COMPLETION_CONSERVATION done=%0d acks=%0d packets=%0d",load_dones,vm_acks,got);
 // Read actual native SRAM through ordinary rq0/rr0 after real bankdone and
 // clean status. Requests use real calendar rslot0; no memory-model peeks.
 for(read_j=phase*896;read_j<(phase+1)*896;read_j=read_j+1)begin
  for(k=0;k<32;k=k+1)rq0_bank[k]=0;
  // The header SID chooses geographicSW0/SE1/NW2/NE3, then localbank.
  read_bank=integer'({expected[read_j][278:277],expected[read_j][266:264]});
  rq0_bank[read_bank]={1'b1,expected[read_j][279:264]};read_cycle[read_sent]=cyc+1;read_sent=read_sent+1;tick();
 end
 for(k=0;k<32;k=k+1)rq0_bank[k]=0;
 repeat(16)tick();
 if(read_got!=read_sent)$fatal(1,"VM_READBACK_DRAIN got=%0d sent=%0d",read_got,read_sent);
 release_buffer_i=ebank;release_epoch_i=epoch;release_v_i=1;tick();release_v_i=0;repeat(24)tick();
 end
 if(mut_epoch!=0||mut_deadline!=0)$fatal(1,"CP_PROVIDER_MUTANT_ESCAPED");
 $display("LOCAL_NS_COUNTS ACT=%0d PRE=%0d REF=%0d RD=%0d WR=%0d",ns_ACT,ns_PRE,ns_REF,ns_RD,ns_WR);
 $display("PASS TIMING833_ROLE_VMFC_SHARED_NATIVE_PHY_VM_CP_PROVIDER exact833ps descriptors=%0d packets=%0d words=%0d epochs=3 latency=%0d first_step=%0d last_step=%0d first_packet=%0d last_packet=%0d native_dq_done=%0d load_done=%0d SRAMreadback=%0d dqcap_to_ack=%0d read_latency=%0d first_dq_capture=%0d first_native_ack=%0d",cmds,got,got*8,latency,first_step,last_step,first_packet,last_packet,vm_acks,load_dones,read_got,vm_latency,read_latency,first_dq_capture,first_bank_ack);$finish;
 end
endmodule
`default_nettype wire
