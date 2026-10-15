`timescale 1ns/1ps
`default_nettype none
// Actual sixteen-lane arithmetic joined to its mapped operand/output store.
// VM sector arrivals and drains are compiler slots; preload completes BEFORE
// arithmetic launch. The compiler prices the VM tap's14 edges separately from
// the local SRAM word-read edge. No combinational14-to1 latency substitution.
// Index ports require a separate actual mapped service. The inherited side
// pins are reserved: KIND1 lanes do not implement scalar-side classes; those
// opcodes fault and must dispatch through a real full-lane/side engine.
module ot_hgi_sfu_static_engine #(parameter integer LWB=15)(
 input wire clk,rst_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [1741:0] compiler_control,
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
 wire [63:0] rd_re;
 wire [1535:0] rd_addr;
 wire [127:0] rd_src;
 wire [2047:0] rd_q;
 wire [15:0] vm_we,lane_fault,lane_coll;
 wire [383:0] vm_addr;
 wire [511:0] vm_data;
 wire store_fault;
 ot_hgi_sfu_static_quarter u_arithmetic(
  .clk_control(clk),.rst_control_n(rst_n),.compiler_control(compiler_control),
  .clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
  .vi_q(vi_q),.side_y(side_y),.rd_q(rd_q),.vi_re(vi_re),.vi_addr(vi_addr),
  .rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),
  .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.ro_v(ro_v),.ro_x(ro_x),
  .side_v(side_v),.side_x(side_x),.fault(lane_fault),.coll(lane_coll));
 ot_hgi_sfu_static_operand_store #(.LWB(LWB)) u_memory(
  .clk(clk),.rst_n(rst_n),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(rd_q),
  .vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),
  .scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_addr),.scalar_data(scalar_data),
  .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
  .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_result_v),.fault(store_fault));
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if(store_fault || |lane_fault || |lane_coll ||
   (compiler_control[77:75]!=0 && compiler_control[77:75]!=1 && compiler_control[77:75]!=4 && compiler_control[77:75]!=5) ||
   (compiler_control[74:72]!=0 && compiler_control[74:72]!=1 && compiler_control[74:72]!=4 && compiler_control[74:72]!=5))fault<=1;
endmodule
`default_nettype wire
