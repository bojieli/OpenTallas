`timescale 1ns/1ps
`default_nettype none
// Actual raw HOST F20 target plus native V4 quadrant. QID is physical identity,
// not a programmable destination. Every clock has the same logical edge;
// physical phi-R insertion is supplied independently at each clock entry.
module ot_hfd_coll_q3_static_host_v4 #(parameter [1:0] QID=2'd0)(
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
 output reg fault,
 output wire done,
 output wire [31:0] stat_cycles
);
 initial if(QID!=0)$fatal(1,"physical quadrant QID incompatible with q3");
 wire [36:0] program_cfg;
 wire hgi_start;
 wire [5:0] hgi_start_pc;
 wire issuer_busy,issuer_fault,issuer_uop_v;
 wire [5:0] issuer_uop_pc;
 wire quad_fault,quad_hgi_fault;
 ot_hgi_coll_static_program_target #(.TARGET(8'd52+8'(QID))) u_program(
  .clk(clk_program),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),
  .desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
  .program_active(hgi_busy),.issuer_busy(issuer_busy),.issuer_fault(issuer_fault),
  .issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),
  .issuer_cfg(program_cfg),.issuer_start(hgi_start),.issuer_start_pc(hgi_start_pc),
  .configured(program_configured),.init_busy(program_init_busy),.fault(program_fault));
 // Joined fault is captured at the new assembler root. It never changes a
 // reservation or inhibits an already-issued instruction; report latency+1.
 always @(posedge clk_program or negedge rst_n)
  if(!rst_n)fault<=0;
  else fault<=fault | program_fault | quad_fault;
 assign hgi_fault=fault;
 ot_hfd_coll_q3_static_v4 u_q(
  .rst_n(rst_n),.clk_control(clk_control),.clk_issue(clk_issue),
  .clk_qslots(clk_qslots),.clk_ring(clk_ring),.clk_reduce(clk_reduce),
  .clk_arg(clk_arg),.clk_tkm(clk_tkm),
  .clk_vmwrite(clk_vmwrite),.clk_link(clk_link),.qid(QID),
  .hgi_start(hgi_start),.hgi_start_pc(hgi_start_pc),.program_cfg(program_cfg),
  .hgi_busy(hgi_busy),.hgi_done(hgi_done),.hgi_fault(quad_hgi_fault),
  .issuer_busy(issuer_busy),.issuer_fault(issuer_fault),
  .issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(hgi_inj_addr),.inj_d(inj_d),
  .del_valid(del_valid),.del_flit(del_flit),.hgi_del_obase(hgi_del_obase),
  .rc_v(rc_v),.rc_tag(rc_tag),.rc_d(rc_d),.rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),
  .phy_up(phy_up),.tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_flit),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.retry_requested(retry_requested),
  .pr_cw_i(pr_cw_i),.pr_ccw_i(pr_ccw_i),.pr_cw_o(pr_cw_o),.pr_ccw_o(pr_ccw_o),
  .vm_rq(vm_rq),.vm_rr(vm_rr),.vm_kq(vm_kq),.fault(quad_fault),.done(done),.stat_cycles(stat_cycles));
endmodule
`default_nettype wire
