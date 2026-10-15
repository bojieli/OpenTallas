`timescale 1ns/1ps
`default_nettype none
// Wires only. HOME0 owns the real registered return join; no fifth root.
// Four independent roots, exactly80 SRAMs, fixed latency4 (old1 +3).
module ot_hgi_sfu_bankhome_store #(parameter integer MUT=0)(
 input wire [3:0] clk_home,
 input wire rst_n,
 input wire [3:0] scalar_load,
 input wire [3:0] scalar_enable,
 input wire [95:0] scalar_addr,
 input wire [127:0] scalar_data,
 input wire [63:0] rd_re,
 input wire [1535:0] rd_addr,
 input wire [127:0] rd_src,
 input wire [15:0] vm_we,
 input wire [383:0] vm_waddr,
 input wire [511:0] vm_wdata,
 input wire [7:0] stage_v,
 input wire [15:0] stage_group,
 input wire [119:0] stage_addr,
 input wire [63:0] stage_mask,
 input wire [2047:0] stage_data,
 input wire [1:0] drain_v,
 input wire [29:0] drain_addr,
 output wire [2047:0] rd_q,
 output wire [511:0] drain_data,
 output wire [1:0] drain_result_v,
 output wire fault
);
 wire [2047:0] part_rd_q[0:3];
 wire [511:0] part_drain_data[0:3];
 wire [1:0] part_drain_result_v[0:3];
 wire [0:0] part_fault[0:3];
 for(genvar h=0;h<4;h=h+1)begin:g_home
 wire [2047:0] joined_rd_q;
 wire [511:0] joined_drain_data;
 wire [1:0] joined_drain_result_v;
 wire [0:0] joined_fault;
 ot_hgi_sfu_bankhome_leaf #(.HOME(h),.MUT(MUT)) leaf(
 .clk(clk_home[h]),
 .rst_n(rst_n),
 .scalar_load(scalar_load),
 .scalar_enable(scalar_enable),
 .scalar_addr(scalar_addr),
 .scalar_data(scalar_data),
 .rd_re(rd_re),
 .rd_addr(rd_addr),
 .rd_src(rd_src),
 .vm_we(vm_we),
 .vm_waddr(vm_waddr),
 .vm_wdata(vm_wdata),
 .stage_v(stage_v),
 .stage_group(stage_group),
 .stage_addr(stage_addr),
 .stage_mask(stage_mask),
 .stage_data(stage_data),
 .drain_v(drain_v),
 .drain_addr(drain_addr),
 .partial_rd_q(part_rd_q[h]),
 .partial_drain_data(part_drain_data[h]),
 .partial_drain_result_v(part_drain_result_v[h]),
 .partial_fault(part_fault[h]),
 .peer_rd_q({part_rd_q[3],part_rd_q[2],part_rd_q[1]}),
 .peer_drain_data({part_drain_data[3],part_drain_data[2],part_drain_data[1]}),
 .peer_drain_result_v({part_drain_result_v[3],part_drain_result_v[2],part_drain_result_v[1]}),
 .peer_fault({part_fault[3],part_fault[2],part_fault[1]}),
 .rd_q(joined_rd_q),
 .drain_data(joined_drain_data),
 .drain_result_v(joined_drain_result_v),
 .fault(joined_fault));
 if(h==0)begin:g_export
 assign rd_q=joined_rd_q;
 assign drain_data=joined_drain_data;
 assign drain_result_v=joined_drain_result_v;
 assign fault=joined_fault;
 end
 end
endmodule
`default_nettype wire
