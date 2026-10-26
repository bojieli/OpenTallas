`timescale 1ns/1ps
`default_nettype none
// Actual lowered-ISA static quadrant composition. No legacy record decoder.
module ot_hfd_coll_q_static #(
 parameter integer NPT=3,SOLO=1,INJLAT=12,
 parameter integer NS=2+NPT+4+1,ND=NPT+12+1,SELW=$clog2(NS)
)(
 input wire rst_n,
 input wire clk_control,
 input wire [3:0] clk_issue,
 input wire [1:0] clk_qslots,
 input wire [16:0] clk_ring,
 input wire clk_vmwrite,
 input wire [5*NPT-1:0] clk_link,
 input wire [33:0] clk_tkm,
 input wire [1:0] qid,
 input wire hgi_start,
 input wire [5:0] hgi_start_pc,
 input wire [36:0] program_cfg,
 output wire hgi_busy,
 output wire hgi_done,
 output wire hgi_fault,
 output wire [1:0] inj_rd,
 output wire [31:0] inj_idx,
 output wire [159:0] hgi_inj_addr,
 input wire [1023:0] inj_d,
 output wire [3:0] del_valid,
 output wire [2179:0] del_flit,
 output wire [159:0] hgi_del_obase,
 input wire rc_v,
 input wire [2:0] rc_tag,
 input wire [255:0] rc_d,
 output wire rr_v,
 output wire [2:0] rr_tag,
 output wire [255:0] rr_d,
 input wire [NPT-1:0] phy_up,
 output wire [NPT-1:0] tx_pin_v,
 output wire [NPT*596-1:0] tx_pin_flit,
 input wire [NPT-1:0] rx_pin_v,
 input wire [NPT*596-1:0] rx_pin_flit,
 output wire [NPT-1:0] retry_requested,
 input wire [279:0] pr_cw_i,pr_ccw_i,
 output wire [279:0] pr_cw_o,pr_ccw_o,
 output wire [135:0] vm_rq,
 input wire [2055:0] vm_rr,
 output wire [2247:0] vm_kq,
 output wire fault,
 output wire done,
 output wire [31:0] stat_cycles
);

 wire uop_v,issue_fault,issue_done;
 wire [1535:0] uop;
 wire [31:0] iteration;
 wire [5:0] uop_pc;
 ot_hgi_coll_static_issuer u_issuer(.clk_control(clk_issue[0]),.clk_mem(clk_issue[3:1]),
  .rst_n(rst_n),.cfg(program_cfg),.start(hgi_start),.start_pc(hgi_start_pc),
  .busy(hgi_busy),.done(issue_done),.fault(issue_fault),.uop_v(uop_v),.uop(uop),
  .iteration(iteration),.uop_pc(uop_pc));
 // Validity masks only undefined/idle instruction words, never normal faults.
 wire [1535:0] inst=uop_v?uop:1536'd0;
 wire [9:0] p_capture_slot=inst[0 +: 10];
 wire [15:0] p_sink_slot=inst[10 +: 16];
 wire [63:0] p_sink_select=inst[26 +: 64];
 wire [1:0] p_inj_rd=inst[90 +: 2];
 wire [31:0] p_inj_idx=inst[92 +: 32];
 wire [159:0] p_inj_addr=inst[124 +: 160];
 wire [65:0] p_inj_meta=inst[284 +: 66];
 wire [2:0] p_lk_wr_v=inst[350 +: 3];
 wire [17:0] p_lk_wr_slot=inst[353 +: 18];
 wire [2:0] p_lk_rd_v=inst[371 +: 3];
 wire [17:0] p_lk_rd_slot=inst[374 +: 18];
 wire [2:0] p_lk_rx_expect=inst[392 +: 3];
 wire [17:0] p_lk_rx_slot=inst[395 +: 18];
 wire [2:0] p_lk_epoch_begin=inst[413 +: 3];
 wire [7:0] p_lk_epoch=inst[416 +: 8];
 wire [159:0] p_rgx_addr=inst[424 +: 160];
 wire [0:0] p_rgx_vm=inst[584 +: 1];
 wire [4:0] p_vm_ingress_slot=inst[585 +: 5];
 wire [7:0] p_vm_slot_valid=inst[590 +: 8];
 wire [31:0] p_vm_slot_owner=inst[598 +: 32];
 wire [87:0] p_ring=inst[630 +: 88];
 wire [0:0] p_tkm_start=inst[718 +: 1];
 wire [3:0] p_tkm_del_slot=inst[719 +: 4];
 wire [11:0] p_tkm_cfg_n=inst[723 +: 12];
 wire [12:0] p_tkm_cfg_k=inst[735 +: 13];
 wire [12:0] p_tkm_cfg_nout=inst[748 +: 13];
 wire [7:0] p_tkm_cfg_g=inst[761 +: 8];
 wire [7:0] p_tkm_cfg_gbase=inst[769 +: 8];
 wire [15:0] p_tkm_cfg_pf=inst[777 +: 16];
 wire [39:0] p_tkm_cfg_obase=inst[793 +: 40];
 wire [39:0] p_tkm_cfg_rbase=inst[833 +: 40];
 wire [0:0] p_tkm_cfg_has_r=inst[873 +: 1];
 wire [159:0] p_del_obase=inst[874 +: 160];
 wire [135:0] p_vm_rq=inst[1034 +: 136];
 wire [131:0] p_vm_meta=inst[1170 +: 132];
 wire [15:0] p_iter_vm_step=inst[1302 +: 16];
 wire [15:0] p_iter_rgx_step=inst[1318 +: 16];
 wire [15:0] p_iter_inj_idx_step=inst[1334 +: 16];
 wire [15:0] p_iter_del_step=inst[1350 +: 16];
 wire [15:0] p_iter_inj_addr_step=inst[1366 +: 16];
 wire [0:0] p_tkm_done_slot=inst[1382 +: 1];
 wire [7:0] p_iter_link_slot_step=inst[1407 +: 8];
 wire [39:0] link_slot_offset=40'(iteration)*40'(p_iter_link_slot_step);
 wire [23:0] p_vm_pair_select=inst[1383 +: 24];
 wire [0:0] r_lp_we=p_ring[0 +: 1];
 wire [2:0] r_lp_tag=p_ring[1 +: 3];
 wire [0:0] r_state_read_add=p_ring[4 +: 1];
 wire [2:0] r_state_add_tag=p_ring[5 +: 3];
 wire [1:0] r_state_add_src=p_ring[8 +: 2];
 wire [0:0] r_state_add_rhs_acc=p_ring[10 +: 1];
 wire [0:0] r_state_read_tx=p_ring[11 +: 1];
 wire [2:0] r_state_tx_tag=p_ring[12 +: 3];
 wire [0:0] r_state_tx_acc=p_ring[15 +: 1];
 wire [0:0] r_state_read_rr=p_ring[16 +: 1];
 wire [2:0] r_state_rr_tag=p_ring[17 +: 3];
 wire [0:0] r_add_v=p_ring[20 +: 1];
 wire [2:0] r_add_tag=p_ring[21 +: 3];
 wire [1:0] r_add_src=p_ring[24 +: 2];
 wire [0:0] r_add_rhs_acc=p_ring[26 +: 1];
 wire [1:0] r_tx_inject=p_ring[27 +: 2];
 wire [1:0] r_tx_forward=p_ring[29 +: 2];
 wire [2:0] r_tx_tag=p_ring[31 +: 3];
 wire [1:0] r_tx_dst=p_ring[34 +: 2];
 wire [0:0] r_tx_result=p_ring[36 +: 1];
 wire [0:0] r_tx_acc=p_ring[37 +: 1];
 wire [1:0] r_rx_slot=p_ring[38 +: 2];
 wire [3:0] r_rx_kind=p_ring[40 +: 4];
 wire [3:0] r_rx_src=p_ring[44 +: 4];
 wire [5:0] r_rx_tag=p_ring[48 +: 6];
 wire [0:0] r_rr_local=p_ring[54 +: 1];
 wire [2:0] r_rr_local_tag=p_ring[55 +: 3];

 wire [135:0] vm_req_pin;
 wire [1:0] inj_req_pin,inj_source_v;
 wire [31:0] inj_idx_pin;
 wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin;
 wire [65:0] inj_source_meta;
 wire [131:0] vm_source_meta;
 wire [2047:0] vm_assembled;
 wire [3:0] vm_assembled_v;
 wire [8*NPT-1:0] held_epoch;
 assign hgi_del_obase=delivery_obase_pin;
 wire [NPT-1:0] link_rx_v,link_abort;
 wire [NPT*545-1:0] link_rx_data;
 wire [NPT*10-1:0] link_cause;
 wire [NS-1:0] source_v;
 wire [NS*545-1:0] source_d;
 wire [ND-1:0] dest_v;
 wire [ND*545-1:0] dest_d;
 wire slot_fault,ring_fault,writer_fault,tkm_fault,tkm_done,tkm_busy;
 wire [3:0] slot_cause;
 wire tk_w_v;
 wire [39:0] tk_w_addr;
 wire [15:0] tk_w_mask;
 wire [511:0] tk_w_data;
 wire [31:0] tk_cycles;
 wire [4:0] writer_launch_done;
 wire protocol_fault;
 wire [31:0] cycles;
 assign stat_cycles=cycles;
 assign fault=issue_fault | slot_fault | ring_fault | writer_fault | tkm_fault | (|link_abort) | protocol_fault;
 assign hgi_fault=fault;
 assign hgi_done=issue_done;
 assign done=issue_done;
 assign inj_rd=inj_req_pin;
 assign inj_idx=inj_idx_pin;
 assign hgi_inj_addr=inj_addr_pin;
 assign vm_rq=vm_req_pin;
 ot_hgi_coll_q_static_ctl #(.NPT(NPT),.SOLO(SOLO),.INJLAT(INJLAT)) u_control(
  .clk_control(clk_control),.rst_n(rst_n),.inst(inst),.iteration(iteration),
  .hgi_start(hgi_start),.hgi_busy(hgi_busy),.issue_done(issue_done),.tkm_done(tkm_done),.tkm_busy(tkm_busy),
  .dest_v(dest_v),.rc_v(rc_v),.rc_tag(rc_tag),.vm_rr(vm_rr),
  .vm_req_pin(vm_req_pin),.inj_req_pin(inj_req_pin),.inj_idx_pin(inj_idx_pin),.inj_addr_pin(inj_addr_pin),
  .delivery_obase_pin(delivery_obase_pin),.rgx_addr_pin(rgx_addr_pin),
  .inj_source_v(inj_source_v),.inj_source_meta(inj_source_meta),.vm_source_meta(vm_source_meta),
  .vm_assembled(vm_assembled),.vm_assembled_v(vm_assembled_v),.held_epoch(held_epoch),
  .protocol_fault(protocol_fault),.cycles(cycles));
 for(genvar j=0;j<2;j=j+1)begin:g_inj
  assign source_v[j]=inj_source_v[j];
  assign source_d[j*545+:545]={inj_source_meta[j*33+:33],inj_d[j*512+:512]};
 end
 for(genvar j=0;j<4;j=j+1)begin:g_vm
  assign source_v[2+NPT+j]=vm_assembled_v[j];
  assign source_d[(2+NPT+j)*545+:545]={vm_source_meta[j*33+:33],vm_assembled[j*512+:512]};
 end
 // Encoding keeps one reserved source/sink position for component compatibility.
 // These positions are invalid ISA entries, checked above; they are not producers.
 assign source_v[NS-1]=1'b0;
 assign source_d[(NS-1)*545+:545]=545'd0;
 ot_hgi_coll_qslots #(.NPT(NPT)) u_qslots(
  .clk_capture(clk_qslots[0]),.clk_output(clk_qslots[1]),.rst_n(rst_n),
  .src_v(source_v),.src_d(source_d),.capture_slot(p_capture_slot[NS-1:0]),
  .sink_slot(p_sink_slot[ND-1:0]),.sink_select(p_sink_select[ND*SELW-1:0]),
  .dst_v(dest_v),.dst_d(dest_d),.fault(slot_fault),.fault_kind(slot_cause));
 for(genvar k=0;k<NPT;k=k+1)begin:g_link
  assign source_v[2+k]=link_rx_v[k];
  assign source_d[(2+k)*545+:545]=link_rx_data[k*545+:545];
  ot_hgi_coll_static_link u_link(.ck(clk_link[k*5+:5]),.rst_n(rst_n),
   .epoch_begin(p_lk_epoch_begin[k]),.epoch(p_lk_epoch_begin[k]?p_lk_epoch:held_epoch[k*8+:8]),
   .wr_v(p_lk_wr_v[k]),.wr_observed_v(dest_v[k]),.wr_slot(6'(40'(p_lk_wr_slot[k*6+:6])+link_slot_offset)),
   .wr_flit(dest_d[k*545+:545]),.rd_v(p_lk_rd_v[k]),.rd_slot(6'(40'(p_lk_rd_slot[k*6+:6])+link_slot_offset)),
   .rx_expect_v(p_lk_rx_expect[k]),.rx_expect_slot(6'(40'(p_lk_rx_slot[k*6+:6])+link_slot_offset)),
   .phy_up(phy_up[k]),.tx_pin_v(tx_pin_v[k]),.tx_pin_flit(tx_pin_flit[k*596+:596]),
   .rx_pin_v(rx_pin_v[k]),.rx_pin_flit(rx_pin_flit[k*596+:596]),
   .rx_v(link_rx_v[k]),.rx_flit(link_rx_data[k*545+:545]),
   .epoch_abort(link_abort[k]),.retry_requested(retry_requested[k]),.fault_cause(link_cause[k*10+:10]));
 end
 for(genvar j=0;j<4;j=j+1)begin:g_delivery
  assign del_valid[j]=dest_v[NPT+j];
  assign del_flit[j*545+:545]=dest_d[(NPT+j)*545+:545];
 end
 wire [159:0] rgx_addr;
 wire [2047:0] rgx_data;
 for(genvar j=0;j<4;j=j+1)begin:g_rgx
  assign rgx_addr[j*40+:40]=rgx_addr_pin[j*40+:40];
  assign rgx_data[j*512+:512]=dest_d[(NPT+4+j)*545+:512];
 end
 ot_hgi_coll_static_vmwrite u_writer(.clk(clk_vmwrite),.rst_n(rst_n),.sid(qid),
  .rgx_v(dest_v[NPT+4+:4]),.rgx_addr(rgx_addr),.rgx_data(rgx_data),.rgx_vm(p_rgx_vm),
  .tkw_v(tk_w_v),.tkw_d({tk_w_addr,tk_w_mask,tk_w_data}),
  .ingress_slot(p_vm_ingress_slot),.slot_valid(p_vm_slot_valid),.slot_owner(p_vm_slot_owner),
  .kq(vm_kq),.launch_done(writer_launch_done),.fault(writer_fault));
 generate if(SOLO!=0)begin:g_tkm
  ot_hgi_coll_tkm_static u_tkm(.clk(clk_tkm[33]),.tile_clk(clk_tkm[31:0]),.buffer_clk(clk_tkm[32]),
   .rst_n(rst_n),.start(p_tkm_start),.cfg_n(p_tkm_cfg_n),.cfg_k(p_tkm_cfg_k),
   .cfg_nout(p_tkm_cfg_nout),.cfg_g(p_tkm_cfg_g),.cfg_gbase(p_tkm_cfg_gbase),
   .cfg_pf(p_tkm_cfg_pf),.cfg_obase(p_tkm_cfg_obase),.cfg_rbase(p_tkm_cfg_rbase),.cfg_has_r(p_tkm_cfg_has_r),
   .del_slot(p_tkm_del_slot),.del_valid(dest_v[NPT+8+:4]),.del_flit(dest_d[(NPT+8)*545+:2180]),
   .w_v(tk_w_v),.w_addr(tk_w_addr),.w_mask(tk_w_mask),.w_data(tk_w_data),
   .busy(tkm_busy),.done(tkm_done),.fault(tkm_fault),.stat_cycles(tk_cycles));
 end else begin:g_no_tkm
  assign tk_w_v=0;assign tk_w_addr=0;assign tk_w_mask=0;assign tk_w_data=0;
  assign tkm_done=0;assign tkm_busy=0;assign tk_cycles=0;
  assign tkm_fault=p_tkm_start || (|dest_v[NPT+8+:4]) || (|p_tkm_del_slot);
 end endgenerate
 ot_hgi_coll_pring_static #(.SPLIT_CLOCKS(1)) u_ring(
  .clk(clk_ring[0]),.clk_state(clk_ring[8:1]),.clk_add(clk_ring[16:9]),.rst_n(rst_n),.qid(qid),
  .cw_i(pr_cw_i),.ccw_i(pr_ccw_i),.cw_o(pr_cw_o),.ccw_o(pr_ccw_o),
  .lp_data(rc_d),.rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.fault(ring_fault),
  .lp_we(r_lp_we),
  .lp_tag(r_lp_tag),
  .state_read_add(r_state_read_add),
  .state_add_tag(r_state_add_tag),
  .state_add_src(r_state_add_src),
  .state_add_rhs_acc(r_state_add_rhs_acc),
  .state_read_tx(r_state_read_tx),
  .state_tx_tag(r_state_tx_tag),
  .state_tx_acc(r_state_tx_acc),
  .state_read_rr(r_state_read_rr),
  .state_rr_tag(r_state_rr_tag),
  .add_v(r_add_v),
  .add_tag(r_add_tag),
  .add_src(r_add_src),
  .add_rhs_acc(r_add_rhs_acc),
  .tx_inject(r_tx_inject),
  .tx_forward(r_tx_forward),
  .tx_tag(r_tx_tag),
  .tx_dst(r_tx_dst),
  .tx_result(r_tx_result),
  .tx_acc(r_tx_acc),
  .rx_slot(r_rx_slot),
  .rx_kind(r_rx_kind),
  .rx_src(r_rx_src),
  .rx_tag(r_rx_tag),
  .rr_local(r_rr_local),
  .rr_local_tag(r_rr_local_tag));
endmodule

module ot_hfd_coll_q3_static(
 input wire rst_n,
 input wire clk_control,
 input wire [3:0] clk_issue,
 input wire [1:0] clk_qslots,
 input wire [16:0] clk_ring,
 input wire clk_vmwrite,
 input wire [15-1:0] clk_link,
 input wire [33:0] clk_tkm,
 input wire [1:0] qid,
 input wire hgi_start,
 input wire [5:0] hgi_start_pc,
 input wire [36:0] program_cfg,
 output wire hgi_busy,
 output wire hgi_done,
 output wire hgi_fault,
 output wire [1:0] inj_rd,
 output wire [31:0] inj_idx,
 output wire [159:0] hgi_inj_addr,
 input wire [1023:0] inj_d,
 output wire [3:0] del_valid,
 output wire [2179:0] del_flit,
 output wire [159:0] hgi_del_obase,
 input wire rc_v,
 input wire [2:0] rc_tag,
 input wire [255:0] rc_d,
 output wire rr_v,
 output wire [2:0] rr_tag,
 output wire [255:0] rr_d,
 input wire [2:0] phy_up,
 output wire [2:0] tx_pin_v,
 output wire [1788-1:0] tx_pin_flit,
 input wire [2:0] rx_pin_v,
 input wire [1788-1:0] rx_pin_flit,
 output wire [2:0] retry_requested,
 input wire [279:0] pr_cw_i,pr_ccw_i,
 output wire [279:0] pr_cw_o,pr_ccw_o,
 output wire [135:0] vm_rq,
 input wire [2055:0] vm_rr,
 output wire [2247:0] vm_kq,
 output wire fault,
 output wire done,
 output wire [31:0] stat_cycles
);
 ot_hfd_coll_q_static #(.NPT(3),.SOLO(1)) u_q(.*);
endmodule

module ot_hfd_coll_q2_static(
 input wire rst_n,
 input wire clk_control,
 input wire [3:0] clk_issue,
 input wire [1:0] clk_qslots,
 input wire [16:0] clk_ring,
 input wire clk_vmwrite,
 input wire [10-1:0] clk_link,
 input wire [1:0] qid,
 input wire hgi_start,
 input wire [5:0] hgi_start_pc,
 input wire [36:0] program_cfg,
 output wire hgi_busy,
 output wire hgi_done,
 output wire hgi_fault,
 output wire [1:0] inj_rd,
 output wire [31:0] inj_idx,
 output wire [159:0] hgi_inj_addr,
 input wire [1023:0] inj_d,
 output wire [3:0] del_valid,
 output wire [2179:0] del_flit,
 output wire [159:0] hgi_del_obase,
 input wire rc_v,
 input wire [2:0] rc_tag,
 input wire [255:0] rc_d,
 output wire rr_v,
 output wire [2:0] rr_tag,
 output wire [255:0] rr_d,
 input wire [1:0] phy_up,
 output wire [1:0] tx_pin_v,
 output wire [1192-1:0] tx_pin_flit,
 input wire [1:0] rx_pin_v,
 input wire [1192-1:0] rx_pin_flit,
 output wire [1:0] retry_requested,
 input wire [279:0] pr_cw_i,pr_ccw_i,
 output wire [279:0] pr_cw_o,pr_ccw_o,
 output wire [135:0] vm_rq,
 input wire [2055:0] vm_rr,
 output wire [2247:0] vm_kq,
 output wire fault,
 output wire done,
 output wire [31:0] stat_cycles
);
 wire [33:0] clk_tkm=34'd0;
 ot_hfd_coll_q_static #(.NPT(2),.SOLO(0)) u_q(.*);
endmodule

// Actual hardenable protocol leaf: all parent request/assembly/pipeline state.
// One synchronous clock entry; no change to the compiler edge contract.
module ot_hgi_coll_q_static_ctl #(
 parameter integer NPT=3,SOLO=1,INJLAT=12,NS=NPT+7,ND=NPT+13
)(
 input wire clk_control,rst_n,
 input wire [1535:0] inst,
 input wire [31:0] iteration,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,
 input wire [ND-1:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,
 input wire [2055:0] vm_rr,
 output wire [135:0] vm_req_pin,
 output reg [1:0] inj_req_pin,
 output reg [31:0] inj_idx_pin,
 output reg [159:0] inj_addr_pin,
 output reg [159:0] delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,
 output wire [65:0] inj_source_meta,
 output wire [131:0] vm_source_meta,
 output reg [2047:0] vm_assembled,
 output reg [3:0] vm_assembled_v,
 output wire [NPT*8-1:0] held_epoch,
 output reg protocol_fault,
 output reg [31:0] cycles
);
 wire [9:0] p_capture_slot=inst[0 +: 10];
 wire [15:0] p_sink_slot=inst[10 +: 16];
 wire [63:0] p_sink_select=inst[26 +: 64];
 wire [1:0] p_inj_rd=inst[90 +: 2];
 wire [31:0] p_inj_idx=inst[92 +: 32];
 wire [159:0] p_inj_addr=inst[124 +: 160];
 wire [65:0] p_inj_meta=inst[284 +: 66];
 wire [2:0] p_lk_wr_v=inst[350 +: 3];
 wire [17:0] p_lk_wr_slot=inst[353 +: 18];
 wire [2:0] p_lk_rd_v=inst[371 +: 3];
 wire [17:0] p_lk_rd_slot=inst[374 +: 18];
 wire [2:0] p_lk_rx_expect=inst[392 +: 3];
 wire [17:0] p_lk_rx_slot=inst[395 +: 18];
 wire [2:0] p_lk_epoch_begin=inst[413 +: 3];
 wire [7:0] p_lk_epoch=inst[416 +: 8];
 wire [159:0] p_rgx_addr=inst[424 +: 160];
 wire [0:0] p_rgx_vm=inst[584 +: 1];
 wire [4:0] p_vm_ingress_slot=inst[585 +: 5];
 wire [7:0] p_vm_slot_valid=inst[590 +: 8];
 wire [31:0] p_vm_slot_owner=inst[598 +: 32];
 wire [87:0] p_ring=inst[630 +: 88];
 wire [0:0] p_tkm_start=inst[718 +: 1];
 wire [3:0] p_tkm_del_slot=inst[719 +: 4];
 wire [11:0] p_tkm_cfg_n=inst[723 +: 12];
 wire [12:0] p_tkm_cfg_k=inst[735 +: 13];
 wire [12:0] p_tkm_cfg_nout=inst[748 +: 13];
 wire [7:0] p_tkm_cfg_g=inst[761 +: 8];
 wire [7:0] p_tkm_cfg_gbase=inst[769 +: 8];
 wire [15:0] p_tkm_cfg_pf=inst[777 +: 16];
 wire [39:0] p_tkm_cfg_obase=inst[793 +: 40];
 wire [39:0] p_tkm_cfg_rbase=inst[833 +: 40];
 wire [0:0] p_tkm_cfg_has_r=inst[873 +: 1];
 wire [159:0] p_del_obase=inst[874 +: 160];
 wire [135:0] p_vm_rq=inst[1034 +: 136];
 wire [131:0] p_vm_meta=inst[1170 +: 132];
 wire [15:0] p_iter_vm_step=inst[1302 +: 16];
 wire [15:0] p_iter_rgx_step=inst[1318 +: 16];
 wire [15:0] p_iter_inj_idx_step=inst[1334 +: 16];
 wire [15:0] p_iter_del_step=inst[1350 +: 16];
 wire [15:0] p_iter_inj_addr_step=inst[1366 +: 16];
 wire [0:0] p_tkm_done_slot=inst[1382 +: 1];
 wire [7:0] p_iter_link_slot_step=inst[1407 +: 8];
 wire [39:0] link_slot_offset=40'(iteration)*40'(p_iter_link_slot_step);
 wire [23:0] p_vm_pair_select=inst[1383 +: 24];
 wire [0:0] r_lp_we=p_ring[0 +: 1];
 wire [2:0] r_lp_tag=p_ring[1 +: 3];
 wire [0:0] r_state_read_add=p_ring[4 +: 1];
 wire [2:0] r_state_add_tag=p_ring[5 +: 3];
 wire [1:0] r_state_add_src=p_ring[8 +: 2];
 wire [0:0] r_state_add_rhs_acc=p_ring[10 +: 1];
 wire [0:0] r_state_read_tx=p_ring[11 +: 1];
 wire [2:0] r_state_tx_tag=p_ring[12 +: 3];
 wire [0:0] r_state_tx_acc=p_ring[15 +: 1];
 wire [0:0] r_state_read_rr=p_ring[16 +: 1];
 wire [2:0] r_state_rr_tag=p_ring[17 +: 3];
 wire [0:0] r_add_v=p_ring[20 +: 1];
 wire [2:0] r_add_tag=p_ring[21 +: 3];
 wire [1:0] r_add_src=p_ring[24 +: 2];
 wire [0:0] r_add_rhs_acc=p_ring[26 +: 1];
 wire [1:0] r_tx_inject=p_ring[27 +: 2];
 wire [1:0] r_tx_forward=p_ring[29 +: 2];
 wire [2:0] r_tx_tag=p_ring[31 +: 3];
 wire [1:0] r_tx_dst=p_ring[34 +: 2];
 wire [0:0] r_tx_result=p_ring[36 +: 1];
 wire [0:0] r_tx_acc=p_ring[37 +: 1];
 wire [1:0] r_rx_slot=p_ring[38 +: 2];
 wire [3:0] r_rx_kind=p_ring[40 +: 4];
 wire [3:0] r_rx_src=p_ring[44 +: 4];
 wire [5:0] r_rx_tag=p_ring[48 +: 6];
 wire [0:0] r_rr_local=p_ring[54 +: 1];
 wire [2:0] r_rr_local_tag=p_ring[55 +: 3];

 reg [1:0] inj_valid_pipe[0:INJLAT-1];
 reg [65:0] inj_meta_pipe[0:INJLAT-1];
 reg [131:0] vm_meta_pipe[0:9];
 reg [23:0] vm_select_pipe[0:8];
 wire [2055:0] vm_raw;
 reg [2047:0] vm_raw_data;
 reg [7:0] vm_raw_valid;
 reg [7:0] vm_valid_pipe[0:7];
 reg [127:0] vm_req_sector;
 reg [7:0] vm_req_valid;
 for(genvar bank=0;bank<8;bank=bank+1)assign vm_req_pin[bank*17+:17]={vm_req_valid[bank],vm_req_sector[bank*16+:16]};
 reg [7:0] link_epoch[0:NPT-1];
 // Registered requests and metadata have one real, explicit protocol root.
 // Request launch P ->SU source capture P+INJLAT; VM capture P+10.
 always @(posedge clk_control) begin
  for(integer j=0;j<2;j=j+1)begin
   inj_idx_pin[j*16+:16]<=p_inj_idx[j*16+:16]+16'(iteration*p_iter_inj_idx_step);
   for(integer h=0;h<2;h=h+1)
    inj_addr_pin[j*80+h*40+:40]<=p_inj_addr[j*80+h*40+:40]+40'(iteration*p_iter_inj_addr_step);
   inj_meta_pipe[0][j*33+:33]<={p_inj_meta[j*33+16+:17],
     16'(p_inj_meta[j*33+:16]+iteration*p_iter_inj_idx_step)};
  end
  for(integer j=1;j<INJLAT;j=j+1)inj_meta_pipe[j]<=inj_meta_pipe[j-1];
  for(integer j=0;j<4;j=j+1)begin
   delivery_obase_pin[j*40+:40]<=p_del_obase[j*40+:40]+40'(iteration*p_iter_del_step);
   rgx_addr_pin[j*40+:40]<=p_rgx_addr[j*40+:40]+40'(iteration*p_iter_rgx_step);
  end
  vm_meta_pipe[0]<=p_vm_meta;
  for(integer j=1;j<10;j=j+1)vm_meta_pipe[j]<=vm_meta_pipe[j-1];
  vm_select_pipe[0]<=p_vm_pair_select;
  for(integer j=1;j<9;j=j+1)vm_select_pipe[j]<=vm_select_pipe[j-1];
  for(integer b=0;b<8;b=b+1)vm_raw_data[b*256+:256]<=vm_rr[b*257+:256];
  for(integer j=0;j<4;j=j+1)
   vm_assembled[j*512+:512]<={vm_raw[257*int'(vm_select_pipe[8][j*6+3+:3])+:256],
     vm_raw[257*int'(vm_select_pipe[8][j*6+:3])+:256]};
  for(integer b=0;b<8;b=b+1)
   vm_req_sector[b*16+:16]<=p_vm_rq[b*17+:16]+16'(iteration*p_iter_vm_step);
 end
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin
   protocol_fault<=0;cycles<=0;inj_req_pin<=0;vm_assembled_v<=0;vm_raw_valid<=0;
   for(integer j=0;j<INJLAT;j=j+1)inj_valid_pipe[j]<=0;
   for(integer j=0;j<8;j=j+1)vm_valid_pipe[j]<=0;
   for(integer b=0;b<8;b=b+1)vm_req_valid[b]<=0;
   for(integer k=0;k<NPT;k=k+1)link_epoch[k]<=0;
  end else begin
   if(hgi_start)cycles<=0;else if(hgi_busy)cycles<=cycles+1;
   inj_req_pin<=p_inj_rd;
   for(integer b=0;b<8;b=b+1)vm_raw_valid[b]<=vm_rr[b*257+256];
   inj_valid_pipe[0]<=p_inj_rd;
   for(integer j=1;j<INJLAT;j=j+1)inj_valid_pipe[j]<=inj_valid_pipe[j-1];
   for(integer b=0;b<8;b=b+1)begin
    vm_req_valid[b]<=p_vm_rq[b*17+16];
    vm_valid_pipe[0][b]<=p_vm_rq[b*17+16];
    if(vm_rr[b*257+256]!=vm_valid_pipe[7][b])protocol_fault<=1;
   end
   for(integer j=1;j<8;j=j+1)vm_valid_pipe[j]<=vm_valid_pipe[j-1];
   for(integer j=0;j<4;j=j+1)begin
    vm_assembled_v[j]<=vm_raw[257*int'(vm_select_pipe[8][j*6+:3])+256] &&
                        vm_raw[257*int'(vm_select_pipe[8][j*6+3+:3])+256] &&
                        vm_select_pipe[8][j*6+:3]!=vm_select_pipe[8][j*6+3+:3];
    if(vm_select_pipe[8][j*6+:3]!=vm_select_pipe[8][j*6+3+:3] &&
       vm_raw[257*int'(vm_select_pipe[8][j*6+:3])+256] !=
       vm_raw[257*int'(vm_select_pipe[8][j*6+3+:3])+256])protocol_fault<=1;

   end
   for(integer k=0;k<NPT;k=k+1)begin
    if(p_lk_epoch_begin[k])link_epoch[k]<=p_lk_epoch;
    if(dest_v[k]!=p_lk_wr_v[k])protocol_fault<=1;
    if((p_lk_wr_v[k] && (40'(p_lk_wr_slot[k*6+:6])+link_slot_offset)>=64) ||
       (p_lk_rd_v[k] && (40'(p_lk_rd_slot[k*6+:6])+link_slot_offset)>=64) ||
       (p_lk_rx_expect[k] && (40'(p_lk_rx_slot[k*6+:6])+link_slot_offset)>=64))protocol_fault<=1;
   end
   if(rc_v!=r_lp_we || (rc_v && rc_tag!=r_lp_tag))protocol_fault<=1;
   if(tkm_done!=p_tkm_done_slot || (issue_done && tkm_busy))protocol_fault<=1;
   if(SOLO==0 && (p_tkm_start || (|dest_v[NPT+8+:4]) || (|p_tkm_del_slot)))protocol_fault<=1;
   if(|inst[1535:1415] || |p_ring[87:58])protocol_fault<=1;
   if(NPT==2 && (p_capture_slot[9] || p_sink_slot[15] || |p_sink_select[63:60] ||
      p_lk_wr_v[2] || p_lk_rd_v[2] || p_lk_rx_expect[2] || p_lk_epoch_begin[2]))protocol_fault<=1;
   if(p_capture_slot[NS-1] || p_sink_slot[ND-1])protocol_fault<=1;
  end
 end
 for(genvar b=0;b<8;b=b+1)assign vm_raw[b*257+:257]={vm_raw_valid[b],vm_raw_data[b*256+:256]};
 assign inj_source_v=inj_valid_pipe[INJLAT-1];
 assign inj_source_meta=inj_meta_pipe[INJLAT-1];
 assign vm_source_meta=vm_meta_pipe[9];
 for(genvar k=0;k<NPT;k=k+1)assign held_epoch[k*8+:8]=link_epoch[k];
endmodule
`default_nettype wire
