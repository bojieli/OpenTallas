`timescale 1ns/1ps
`default_nettype none
// Compiler-issued SFU arithmetic. The 1742-bit control word is the explicit
// lane-grid ABI (see ot_hgi_sfu_arithmetic_grid), not an instruction FIFO.
// Every edge is consumed; there is no ready, credit, lease, or issue retry.
// A zero word is a bubble. The compiler must preload operand memory and price
// the input register (one edge), mapper (four), and selected arithmetic pipes.
// Reduction results are exposed for an external compiler-scheduled reducer;
// this block does not silently implement the old dynamic reduction controller.
module ot_hgi_sfu_static_quarter #(
 parameter integer BTREE=0
)(
 input wire clk_control,rst_control_n,
 input wire [1741:0] compiler_control,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [511:0] vi_q,side_y,
 input wire [2047:0] rd_q,
 output wire [15:0] vi_re,vm_we,kv_we,ro_v,fault,coll,side_v,
 output wire [383:0] vi_addr,vm_waddr,kv_waddr,
 output wire [1535:0] rd_addr,
 output wire [63:0] rd_re,
 output wire [127:0] rd_src,
 output wire [511:0] vm_wdata,kv_wdata,ro_x,side_x
);
 reg [1741:0] control;
 always @(posedge clk_control or negedge rst_control_n)
  if(!rst_control_n)control<=0;else control<=compiler_control;
`ifdef OT_SFU_STATIC_PHASE_MUTANT
 reg [1741:0] late;
 always @(posedge clk_control or negedge rst_control_n)
  if(!rst_control_n)late<=0;else late<=control;
 wire [1741:0] grid_control=late;
`else
 wire [1741:0] grid_control=control;
`endif
 ot_hgi_sfu_arithmetic_grid #(.BTREE(BTREE)) u_grid(
 .clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
 .control(grid_control),.vi_q(vi_q),.side_y(side_y),.rd_q(rd_q),
 .vi_re(vi_re),.vm_we(vm_we),.kv_we(kv_we),.ro_v(ro_v),.fault(fault),.coll(coll),.side_v(side_v),
 .vi_addr(vi_addr),.vm_waddr(vm_waddr),.kv_waddr(kv_waddr),.rd_addr(rd_addr),.rd_re(rd_re),
 .rd_src(rd_src),.vm_wdata(vm_wdata),.kv_wdata(kv_wdata),.ro_x(ro_x),.side_x(side_x));
endmodule
`default_nettype wire
