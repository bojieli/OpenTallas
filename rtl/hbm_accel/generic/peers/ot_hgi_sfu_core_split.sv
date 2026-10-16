`timescale 1ns/1ps
`default_nettype none
// SFU core without its programme calendars (H-SU 2026-10-16, die slot sfucore_<q> 763.56 x 3001.91 um).
// Identical to ot_hgi_sfu_scheduled_engine except that the IO word and the 1742-bit compiler control arrive from
// ot_hgi_sfu_programme_store (sfus_<q>) and are registered at this tile's pins (+1 edge; the store adds +2).
// Everything downstream (VM bridge with LG_PATH, 16 lanes, 80 operand SRAMs) is the unchanged RTL.
// OT_SFU_CORE_MUT_SKIP_REG (bench negative control): drop the core pin register -> the core runs one edge early.
module ot_hgi_sfu_core_split #(
 parameter integer LWB=15,
 parameter integer LG_PATH=0
)(
 input wire clk,rst_n,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [470:0] io_word,
 input wire [1741:0] compiler_control,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output wire [15:0] vi_re,
 output wire [383:0] vi_addr,
 input wire [511:0] vi_q,
 output wire [15:0] ro_v,kv_we,
 output wire [511:0] ro_x,kv_wdata,
 output wire [383:0] kv_waddr,
 output reg fault
);
 localparam IOW=8+8+128+16+8*LWB+24+96+4+2+2*LWB+32+2+1;
 initial if(LWB!=15 || IOW!=471)$fatal(1,"SFU IO programme ABI requires LWB15");
 reg [470:0] io_r;
 reg [1741:0] ctl_r;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin io_r<=0;ctl_r<=0;end
  else begin io_r<=io_word;ctl_r<=compiler_control;end
`ifdef OT_SFU_CORE_MUT_SKIP_REG
 wire [470:0] io=io_word;
 wire [1741:0] control=compiler_control;
`else
 wire [470:0] io=io_r;
 wire [1741:0] control=ctl_r;
`endif
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
 wire arithmetic_start_unused;
 assign {arithmetic_start_unused,drain_round_bf16,drain_vm_sector,drain_addr,drain_v,scalar_enable,
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
 ot_hgi_sfu_vm_static_bridge #(.LWB(LWB),.READ_RETURN(14+2*LG_PATH),.WRITE_RETURN(11+2*LG_PATH)) u_vm(
 .clk(clk),.rst_n(rst_n),.clk_lg(clk_lg),.rst_lg_n(rst_lg_n),.prefetch_v(prefetch_v),.prefetch_sector(prefetch_sector),.prefetch_group(prefetch_group),
 .prefetch_local_addr(prefetch_local_addr),.prefetch_scalar(prefetch_scalar),.prefetch_word(prefetch_word),.scalar_addr(scalar_addr),
 .local_rq(local_rq),.local_rr(local_rr),.local_wq(local_wq),.local_w_done(local_w_done),
 .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
 .scalar_load(scalar_load),.scalar_load_addr(scalar_load_addr),.scalar_data(scalar_data),
 .drain_v(drain_v),.drain_round_bf16(drain_round_bf16),.drain_vm_sector(drain_vm_sector),.drain_result_v(drain_result_v),.drain_data(drain_data),.fault(bridge_fault));
 ot_hgi_sfu_static_engine #(.LWB(LWB)) u_engine(
  .clk(clk),.rst_n(rst_n),.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
  .compiler_control(control),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_load_addr),.scalar_data(scalar_data),
  .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
  .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_result_v),
  .vi_re(vi_re),.vi_addr(vi_addr),.vi_q(vi_q),.ro_v(ro_v),.ro_x(ro_x),
  .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.fault(engine_fault));
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;else if(bridge_fault||engine_fault)fault<=1;
endmodule
`default_nettype wire
