`timescale 1ns/1ps
`default_nettype none
// Actual protected programme SRAM -> fixed SFU arithmetic -> mapped SRAM store.
// No runtime issue/ready loop. Host configuration and VM sector prefetch are
// explicit setup ports. Index reads require an actual external mapped service.
// Scalar-side opcodes fault in this KIND1 engine and require a real full-lane
// dispatch; its inherited side pins are reserved, not an implementation.
module ot_hgi_sfu_programmed_engine #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW, LWB=15
)(
 input wire clk,rst_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire start_v,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output wire programme_active,programme_done,
 output wire [31:0] programme_ordinal,
 input wire [3:0] scalar_load,scalar_enable,
 input wire [95:0] scalar_addr,
 input wire [127:0] scalar_data,
 input wire [7:0] stage_v,
 input wire [15:0] stage_group,
 input wire [8*LWB-1:0] stage_addr,
 input wire [63:0] stage_mask,
 input wire [2047:0] stage_data,
 input wire [1:0] drain_v,
 input wire [2*LWB-1:0] drain_addr,
 output wire [511:0] drain_data,
 output wire [1:0] drain_result_v,
 output wire [15:0] vi_re,
 output wire [383:0] vi_addr,
 input wire [511:0] vi_q,side_y,
 output wire [15:0] ro_v,side_v,kv_we,
 output wire [511:0] ro_x,side_x,kv_wdata,
 output wire [383:0] kv_waddr,
 output reg fault
);
 wire [1741:0] control;
 wire program_fault,engine_fault;
 ot_hgi_sfu_calendar_paged_static #(.PAGE_AW(PAGE_AW)) u_programme(
  .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
  .compiler_control(control),.control_v(),.ordinal(programme_ordinal),
  .active(programme_active),.done(programme_done),.fault(program_fault));
 ot_hgi_sfu_static_engine #(.LWB(LWB)) u_engine(
  .clk(clk),.rst_n(rst_n),.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
  .compiler_control(control),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_addr),.scalar_data(scalar_data),
  .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
  .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_result_v),
  .vi_re(vi_re),.vi_addr(vi_addr),.vi_q(vi_q),.side_y(side_y),.ro_v(ro_v),.ro_x(ro_x),.side_v(side_v),.side_x(side_x),
  .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.fault(engine_fault));
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;else if(program_fault||engine_fault)fault<=1;
endmodule
`default_nettype wire
