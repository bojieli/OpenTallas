`timescale 1ns/1ps
`default_nettype none
// Opt-in 0az successor: complete block admission precedes HOST launch.
// All boundary clocks are same logical edge as native link (not a CDC).
// Slot S -> registered raw pin S+4 -> native sample S+5 -> RX publish S+7.
module ot_hfd_coll_q3_static_host_v4_elastic_rx_pingpong #(parameter [1:0] QID=2'd0)(
 input wire [2:0] clk_rx_boundary,
 input wire [2:0] rx_arm_v,
 input wire [20:0] rx_block_words,
 input wire [2:0] rx_required,
 output wire [2:0] rx_pin_ready,
 output wire [5:0] rx_block_ready,
 input wire [2:0] rx_arm_bank,rx_release_bank,rx_slot_bank,rx_required_bank,
 input wire [2:0] rx_release_v,rx_slot_v,
 input wire [17:0] rx_slot_index,
 output wire rx_boundary_fault,
 input wire rst_n,
 input wire clk_program,
 input wire clk_control,
 input wire [3:0] clk_issue,
 input wire [1:0] clk_qslots,
 input wire [16:0] clk_ring,
 input wire [32:0] clk_reduce,
 input wire clk_arg,
 input wire [33:0] clk_tkm,
 input wire clk_vmwrite,
 input wire [14:0] clk_link,
 input wire cfg_v,
 input wire [7:0] cfg_target,
 input wire [11:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire desc_v,
 input wire [11:0] desc_base,
 input wire [12:0] desc_limit,
 input wire [15:0] desc_loops,
 input wire launch_v,
 output wire program_configured,program_init_busy,program_fault,
 output wire hgi_busy,hgi_done,hgi_fault,
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
 output wire [1835:0] tx_pin_flit,
 input wire [2:0] rx_pin_v,
 input wire [1835:0] rx_pin_flit,
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
 wire [2:0] fixed_rx_v,stage_fault;
 wire [1835:0] fixed_rx_flit;
 wire native_fault,native_hgi_fault;
 assign hgi_fault=native_hgi_fault | rx_boundary_fault;
 wire [2:0] admitted_blocks;
 wire admission_ok= &admitted_blocks;
 wire admitted_launch=launch_v && admission_ok;
 reg admission_fault;
 always @(posedge clk_program or negedge rst_n)
  if(!rst_n)admission_fault<=0;
  else if(launch_v && !admission_ok)admission_fault<=1;
 assign rx_boundary_fault=admission_fault | (|stage_fault);
 assign fault=native_fault | rx_boundary_fault;
 for(genvar k=0;k<3;k=k+1)begin:g_rx_boundary
  assign admitted_blocks[k]=rx_block_ready[2*k+rx_required_bank[k]] | ~rx_required[k];
  ot_hgi_coll_offdie_rx_pingpong u_stage(
   .clk(clk_rx_boundary[k]),.rst_n(rst_n),.arm_v(rx_arm_v[k]),.arm_bank(rx_arm_bank[k]),
   .block_words(rx_block_words[k*7+:7]),.phy_v(rx_pin_v[k]),
   .phy_flit(rx_pin_flit[k*612+:612]),.phy_ready(rx_pin_ready[k]),
   .block_ready(rx_block_ready[k*2+:2]),.release_v(rx_release_v[k]),.release_bank(rx_release_bank[k]),
   .slot_v(rx_slot_v[k]),.slot_bank(rx_slot_bank[k]),.slot_index(rx_slot_index[k*6+:6]),
   .pin_v(fixed_rx_v[k]),.pin_flit(fixed_rx_flit[k*612+:612]),
   .fault(stage_fault[k]),.fault_cause());
 end
 ot_hfd_coll_q3_static_host_v4 #(.QID(QID)) u_native(
  .rst_n(rst_n),
  .clk_program(clk_program),
  .clk_control(clk_control),
  .clk_issue(clk_issue),
  .clk_qslots(clk_qslots),
  .clk_ring(clk_ring),
  .clk_reduce(clk_reduce),
  .clk_arg(clk_arg),
  .clk_tkm(clk_tkm),
  .clk_vmwrite(clk_vmwrite),
  .clk_link(clk_link),
  .cfg_v(cfg_v),
  .cfg_target(cfg_target),
  .cfg_addr(cfg_addr),
  .cfg_data(cfg_data),
  .desc_v(desc_v),
  .desc_base(desc_base),
  .desc_limit(desc_limit),
  .desc_loops(desc_loops),
  .launch_v(admitted_launch),
  .program_configured(program_configured),
  .program_init_busy(program_init_busy),
  .program_fault(program_fault),
  .hgi_busy(hgi_busy),
  .hgi_done(hgi_done),
  .hgi_fault(native_hgi_fault),
  .inj_rd(inj_rd),
  .inj_idx(inj_idx),
  .hgi_inj_addr(hgi_inj_addr),
  .inj_d(inj_d),
  .del_valid(del_valid),
  .del_flit(del_flit),
  .hgi_del_obase(hgi_del_obase),
  .rc_v(rc_v),
  .rc_tag(rc_tag),
  .rc_d(rc_d),
  .rr_v(rr_v),
  .rr_tag(rr_tag),
  .rr_d(rr_d),
  .phy_up(phy_up),
  .tx_pin_v(tx_pin_v),
  .tx_pin_flit(tx_pin_flit),
  .rx_pin_v(fixed_rx_v),
  .rx_pin_flit(fixed_rx_flit),
  .retry_requested(retry_requested),
  .pr_cw_i(pr_cw_i),
  .pr_ccw_i(pr_ccw_i),
  .pr_cw_o(pr_cw_o),
  .pr_ccw_o(pr_ccw_o),
  .vm_rq(vm_rq),
  .vm_rr(vm_rr),
  .vm_kq(vm_kq),
  .fault(native_fault),
  .done(done),
  .stat_cycles(stat_cycles)
 );
endmodule
`default_nettype wire
