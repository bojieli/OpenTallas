`timescale 1ps/1fs
`default_nettype none
// Simulation-only primitive vehicle. HOST/test control inputs are leaf inputs;
// every data response, write completion and refill below comes from real RTL.
// Staged DQ is explicit initialization, NOT a claimed canonical VM COPY path.
module source_write_vehicle_1101 #(
 parameter integer STK=0, PHY_QUAD=0, VM_SID=3, RR_RT=8, WB_MUT=0
)(
 input wire clk,rst_n,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire[7:0]refresh_lo_tgt,refresh_hi_tgt,write_tgt,
 input wire write_desc_v,input wire[12:0]write_limit,input wire write_launch,
 input wire calendar_v,input wire[88:0]calendar_payload,
 input wire load_desc_v,input wire[226:0]load_desc,input wire load_step,
 input wire window_buffer,input wire[15:0]window_epoch,input wire[14:0]window_row,input wire[3:0]window_col,
 input wire release_v,input wire[15:0]release_epoch,
 input wire[280:0]staged_dq,
 input wire[135:0]readback_rq,output wire[2055:0]readback_rr,
 output wire[7:0]VM_done,output wire[15:0]block_ready,
 output wire store_src,store_done,store_busy,store_quiet,load_active,
 output wire[11:0]true_ACKs,output wire fault,
 output reg[31:0]physical_write_count,physical_read_count
);
 initial if((STK!=0&&STK!=3)||PHY_QUAD<0||PHY_QUAD>1)$fatal(1,"fixture supports exact STK0/STK3 and two real PHY halves");
 wire cmd_v,cp_fault,cp_configured,cp_active;wire[307:0]cmd;wire[31:0]cycle;
 wire store_fault,wb_fault,wb_ready;wire[135:0]store_rq;wire[2055:0]store_rr;
 wire reserve_v,reserve_bank,fill_bank,fill_start;wire[15:0]reserve_epoch,fill_epoch;
 wire[11:0]reserve_sectors;wire[31:0]reserve_base;wire[2311:0]wd;
 wire wbw_v;wire[29:0]wbw_base;wire[11:0]wbw_total;
 wire[15:0]wk_v,wk_ready,wk_done;wire[479:0]wk_addr;wire[4095:0]wk_data;
 ot_hgi_dma_back_cp_collar cp(.clk(clk),.rst_n(rst_n),.tgt(write_tgt),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(write_desc_v),.desc_base(12'd0),.desc_limit(write_limit),.desc_loops(16'd1),.launch_v(write_launch),
  .tgt_active(store_busy),.tgt_fault(store_fault|wb_fault),.cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),
  .configured(cp_configured),.fault(cp_fault),.active(cp_active));
 ot_hgi_dma_back_static_vp4_banks_rs #(.RR_RT(RR_RT)) back(.clk(clk),.rst_ctl_n(rst_n),.rst_bank_n({8{rst_n}}),
  .stk(2'(STK)),.clk_bank({8{clk}}),.cycle(cycle),.mv_v(cmd_v),.mv(cmd[290:64]),
  .issue_at(cmd[31:0]),.drain_at(cmd[63:32]),.mv_wb_bank(cmd[291]),.mv_wb_epoch(cmd[307:292]),
  .mv_src(store_src),.mv_done(store_done),.mv_fault(store_fault),.quiet(store_quiet),.busy(store_busy),
  .rq(store_rq),.rr(store_rr),.wb_reserve_v(reserve_v),.wb_reserve_bank(reserve_bank),.wb_fill_bank(fill_bank),
  .wb_reserve_epoch(reserve_epoch),.wb_fill_epoch(fill_epoch),.wb_reserve_sectors(reserve_sectors),
  .wb_reserve_base(reserve_base),.wb_fill_start(fill_start),.wb_ready(wb_ready),.wd(wd),.wa(true_ACKs));
 ot_hbm_svc_wb_kport_q #(.WOPEN(0),.MUT(WB_MUT)) wb(.stream_clk(clk),.stream_rst_n(rst_n),
  .hbm_clk(clk),.hbm_rst_n(rst_n),.stream_fifo_clk({4{clk}}),.stk(2'(STK)),.quad(1'(PHY_QUAD)),
  .wb_reserve_v(reserve_v),.wb_reserve_bank(reserve_bank),.wb_fill_bank(fill_bank),
  .wb_reserve_epoch(reserve_epoch),.wb_fill_epoch(fill_epoch),.wb_reserve_sectors(reserve_sectors),
  .wb_reserve_base(reserve_base),.wb_fill_start(fill_start),.wd(wd),.wb_ready(wb_ready),.wa(true_ACKs),
  .wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),.w_k_v(wk_v),.w_k_rdy(wk_ready),
  .w_k_addr(wk_addr),.w_k_wdata(wk_data),.w_k_wr_done(wk_done),.fault(wb_fault));
 wire[31:0]service_wv,service_wrdy,service_done;wire[959:0]service_wa;wire[8191:0]service_wd;
 assign service_wv=PHY_QUAD==0?{16'd0,wk_v}:{wk_v,16'd0};
 assign service_wa=PHY_QUAD==0?{480'd0,wk_addr}:{wk_addr,480'd0};
 assign service_wd=PHY_QUAD==0?{4096'd0,wk_data}:{wk_data,4096'd0};
 assign wk_ready=service_wrdy[PHY_QUAD*16+:16];assign wk_done=service_done[PHY_QUAD*16+:16];
 wire[31:0]row_v,col_v,col_we,dram_v;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;
 wire[607:0]row_row;wire[8191:0]col_data,dram_data;wire[1023:0]col_strb;
 wire[15:0]lfv,lfb,hfv,hfb;wire[95:0]lfs,hfs;wire[255:0]lfe,hfe;wire[4095:0]lfd,hfd;
 wire[1:0]refresh_ready,refresh_active,refresh_fault;wire[31:0]pc_fault;wire[7:0]vmks_fault;wire source_fault;
 ot_hbm_static_service_write_fixture #(.TIMING_833(1)) service(.clk(clk),.rst_n(rst_n),
  .strap_refresh_lo_tgt(refresh_lo_tgt),.strap_refresh_hi_tgt(refresh_hi_tgt),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .lo_calendar_v(calendar_v&&PHY_QUAD==0),.hi_calendar_v(calendar_v&&PHY_QUAD==1),
  .lo_calendar_payload(calendar_payload),.hi_calendar_payload(calendar_payload),
  .lo_wbw_v(wbw_v&&PHY_QUAD==0),.hi_wbw_v(wbw_v&&PHY_QUAD==1),
  .lo_wbw_base(wbw_base),.hi_wbw_base(wbw_base),.lo_wbw_total(wbw_total),.hi_wbw_total(wbw_total),
  .write_v(service_wv),.write_addr(service_wa),.write_data(service_wd),
  .write_ready(service_wrdy),.write_done(service_done),
  .phy0_dram_rvalid(dram_v),.phy0_dram_rdata(dram_data),.phy0_row_v(row_v),.phy0_row_op(row_op),
  .phy0_row_bank(row_bank),.phy0_row_row(row_row),.phy0_col_v(col_v),.phy0_col_we(col_we),
  .phy0_col_bank(col_bank),.phy0_col_col(col_col),.phy0_col_data(col_data),.phy0_col_strb(col_strb),
  .lo_fill_v(lfv),.lo_fill_bank(lfb),.lo_fill_slot(lfs),.lo_fill_epoch(lfe),.lo_fill_data(lfd),
  .hi_fill_v(hfv),.hi_fill_bank(hfb),.hi_fill_slot(hfs),.hi_fill_epoch(hfe),.hi_fill_data(hfd),
  .refresh_ready(refresh_ready),.refresh_active(refresh_active),.refresh_fault(refresh_fault),
  .pc_fault(pc_fault),.vmks_fault(vmks_fault),.source_fault_o(source_fault));
 // External memory, not an internal response producer. Different STK image keys;
 // physical row/column writes and strobes mutate its actual persistent contents.
 ot_hbm3e_phy_rc_e8p5 #(.IMAGE_KEY(STK==0?"stack0":"stack3"),.REQUIRE_INITIALIZED(1),.CLOCK_PERIOD_PS(833))
 dram(.clk(clk),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
  .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
  .dram_rvalid(dram_v),.dram_rdata(dram_data));
 always @(posedge clk)begin
  if(!rst_n)begin physical_write_count<=0;physical_read_count<=0;end
  else begin
   physical_write_count<=physical_write_count+32'($countones(col_v&col_we));
   physical_read_count<=physical_read_count+32'($countones(col_v&~col_we));
  end
 end
 wire provider_fault;wire[7:0]leaf_fault;wire[280:0]delivery;
 ot_hbm_static_load_provider_quad #(.SOURCE_STACK(STK),.SOURCE_LOW_QUAD(0),.SOURCE_QUAD(PHY_QUAD)) reader(
  .clk(clk),.rst_n(rst_n),.desc_v_i(load_desc_v),.desc_i(load_desc),.step_i(load_step),
  .window_buffer_i(window_buffer),.window_epoch_i(window_epoch),.window_row_i(window_row),.window_col_i(window_col),
  .begin_v(calendar_v&&calendar_payload[0]),.begin_bank(calendar_payload[1]),.begin_epoch(calendar_payload[17:2]),
  .begin_row(calendar_payload[84:70]),.begin_col(calendar_payload[88:85]),
  .fill_v(PHY_QUAD==0?lfv:hfv),.fill_bank(PHY_QUAD==0?lfb:hfb),.fill_slot(PHY_QUAD==0?lfs:hfs),
  .fill_epoch(PHY_QUAD==0?lfe:hfe),.fill_data(PHY_QUAD==0?lfd:hfd),
  .release_v_i(release_v),.release_buffer_i(window_buffer),.release_epoch_i(release_epoch),
  .active_o(load_active),.vm_dq(delivery),.block_ready(block_ready),.leaf_fault(leaf_fault),.fault_o(provider_fault));
 wire dq_collision=staged_dq[280]&&delivery[280];wire[280:0]dq=staged_dq|delivery;
 wire bad_sid=dq[280]&&dq[278:277]!=2'(VM_SID);wire[7:0]vm_fault;
 for(genvar b=0;b<8;b=b+1)begin:VM
  wire[17:0]status;
  hfd_vms_bank_native_q0_faces bank(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
   .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.sid(2'(VM_SID)),.bid(3'(b)),
   .rq0(readback_rq[b*17+:17]),.rr0(readback_rr[b*257+:257]),.rq1(store_rq[b*17+:17]),.rr1(store_rr[b*257+:257]),
   .rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
   .wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),
   .rslot_v(readback_rq[b*17+16]|store_rq[b*17+16]),.rslot(store_rq[b*17+16]?3'd1:3'd0),
   .wslot_v(dq[280]&&dq[266:264]==3'(b)),.wslot(3'd6),
   .dq(dq[280]&&dq[266:264]==3'(b)?dq:281'd0),.dq_done(VM_done[b]),
   .kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
   .xq2(276'd0),.xq2_done(),.pq(285'd0),.pr(),.eg(),.status(status));
  assign vm_fault[b]=status[17]|status[16];
 end
 assign fault=cp_fault|store_fault|wb_fault|provider_fault|source_fault|(|pc_fault)|(|vmks_fault)|(|refresh_fault)|
  (|vm_fault)|dq_collision|bad_sid;
endmodule
`default_nettype wire
