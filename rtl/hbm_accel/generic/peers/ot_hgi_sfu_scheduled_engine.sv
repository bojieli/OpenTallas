`timescale 1ns/1ps
`default_nettype none
// Actual fixed programme/operand SRAM/arithmetic, joined to the measured VM tap.
// Compiler reserves request, scalar-publish and output-drain slots explicitly.
// No internal credits, leases, normal ready or runtime rescheduling.
module ot_hgi_sfu_scheduled_engine #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW, LWB=15
)(
 input wire clk,rst_n,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output wire programme_active,programme_done,
 output wire [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output wire io_active,io_done,
 output wire [31:0] io_ordinal,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output wire [15:0] vi_re,
 output wire [383:0] vi_addr,
 input wire [511:0] vi_q,side_y,
 output wire [15:0] ro_v,side_v,kv_we,
 output wire [511:0] ro_x,side_x,kv_wdata,
 output wire [383:0] kv_waddr,
 output reg fault
);
 localparam IOW=8+8+128+16+8*LWB+24+96+4+2+2*LWB+32+2+1;
 initial if(LWB!=15 || IOW!=471)$fatal(1,"SFU IO programme ABI requires LWB15");
 wire [7:0] prefetch_v,prefetch_scalar;
 wire [127:0] prefetch_sector;
 wire [15:0] prefetch_group;
 wire [119:0] prefetch_local_addr;
 wire [23:0] prefetch_word;
 wire [95:0] scalar_addr;
 wire [3:0] scalar_enable;
 wire [1:0] drain_v,drain_round_bf16;
 wire [29:0] drain_addr;
 wire [31:0] drain_vm_sector;
 wire arithmetic_start,io_fault;
 wire [470:0] io;
 ot_hgi_sfu_io_calendar_static #(.PAGE_AW(PAGE_AW)) u_io(
 .clk(clk),.rst_n(rst_n),.cfg_we(io_cfg_we),.cfg_stripe(io_cfg_stripe),.cfg_addr(io_cfg_addr),.cfg_data(io_cfg_data),
 .start_v(io_start_v),.start_base(io_start_base),.start_limit(io_start_limit),.start_loops(io_start_loops),
 .compiler_control(io),.control_v(),.ordinal(io_ordinal),.active(io_active),.done(io_done),.fault(io_fault));
 assign {arithmetic_start,drain_round_bf16,drain_vm_sector,drain_addr,drain_v,scalar_enable,
         scalar_addr,prefetch_word,prefetch_local_addr,prefetch_group,prefetch_sector,prefetch_scalar,prefetch_v}=io;
 wire [7:0] stage_v;
 wire [15:0] stage_group;
 wire [8*LWB-1:0] stage_addr;
 wire [63:0] stage_mask;
 wire [2047:0] stage_data;
 wire [3:0] scalar_load;
 wire [95:0] scalar_load_addr;
 wire [127:0] scalar_data;
 wire [511:0] drain_data;
 wire [1:0] drain_result_v;
 wire bridge_fault,engine_fault;
 ot_hgi_sfu_vm_static_bridge #(.LWB(LWB)) u_vm(
 .clk(clk),.rst_n(rst_n),.clk_lg(clk_lg),.rst_lg_n(rst_lg_n),.prefetch_v(prefetch_v),.prefetch_sector(prefetch_sector),.prefetch_group(prefetch_group),
 .prefetch_local_addr(prefetch_local_addr),.prefetch_scalar(prefetch_scalar),.prefetch_word(prefetch_word),.scalar_addr(scalar_addr),
 .local_rq(local_rq),.local_rr(local_rr),.local_wq(local_wq),.local_w_done(local_w_done),
 .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
 .scalar_load(scalar_load),.scalar_load_addr(scalar_load_addr),.scalar_data(scalar_data),
 .drain_v(drain_v),.drain_round_bf16(drain_round_bf16),.drain_vm_sector(drain_vm_sector),.drain_result_v(drain_result_v),.drain_data(drain_data),.fault(bridge_fault));
 ot_hgi_sfu_programmed_engine #(.PAGE_AW(PAGE_AW),.LWB(LWB)) u_engine(
 .clk(clk),.rst_n(rst_n),.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
 .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start_v(arithmetic_start),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
 .programme_active(programme_active),.programme_done(programme_done),.programme_ordinal(programme_ordinal),
 .scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_load_addr),.scalar_data(scalar_data),
 .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
 .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_result_v),
 .vi_re(vi_re),.vi_addr(vi_addr),.vi_q(vi_q),.side_y(side_y),.ro_v(ro_v),.ro_x(ro_x),.side_v(side_v),.side_x(side_x),
 .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.fault(engine_fault));
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;else if(bridge_fault||engine_fault||io_fault)fault<=1;
endmodule
`default_nettype wire
