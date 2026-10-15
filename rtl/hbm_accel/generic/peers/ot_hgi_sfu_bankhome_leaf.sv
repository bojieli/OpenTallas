`timescale 1ns/1ps
`default_nettype none
// One real home: twenty SRAMs (4 banks x 5 groups), own root,
// registered request and registered partial return. HOME0 owns final join.
// Component read latency 4 edges vs original1; production FETCH join OPEN.
module ot_hgi_sfu_bankhome_leaf #(parameter integer HOME=0, MUT=0)(
 input wire clk,
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
 output reg [2047:0] partial_rd_q,
 output reg [511:0] partial_drain_data,
 output reg [1:0] partial_drain_result_v,
 output reg partial_fault,
 input wire [6143:0] peer_rd_q,
 input wire [1535:0] peer_drain_data,
 input wire [5:0] peer_drain_result_v,
 input wire [2:0] peer_fault,
 output reg [2047:0] rd_q,
 output reg [511:0] drain_data,
 output reg [1:0] drain_result_v,
 output reg fault
);
 reg [3:0] scalar_load_q;
 reg [3:0] scalar_enable_q;
 reg [95:0] scalar_addr_q;
 reg [127:0] scalar_data_q;
 reg [63:0] rd_re_q;
 reg [1535:0] rd_addr_q;
 reg [127:0] rd_src_q;
 reg [15:0] vm_we_q;
 reg [383:0] vm_waddr_q;
 reg [511:0] vm_wdata_q;
 reg [7:0] stage_v_q;
 reg [15:0] stage_group_q;
 reg [119:0] stage_addr_q;
 reg [63:0] stage_mask_q;
 reg [2047:0] stage_data_q;
 reg [1:0] drain_v_q;
 reg [29:0] drain_addr_q;
 always @(posedge clk) begin
  scalar_addr_q <= scalar_addr;
  scalar_data_q <= scalar_data;
  rd_addr_q <= rd_addr;
  rd_src_q <= rd_src;
  vm_waddr_q <= vm_waddr;
  vm_wdata_q <= vm_wdata;
  stage_group_q <= stage_group;
  stage_addr_q <= stage_addr;
  stage_mask_q <= stage_mask;
  stage_data_q <= stage_data;
  drain_addr_q <= drain_addr;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin
   scalar_load_q <= 0;
   scalar_enable_q <= 0;
   rd_re_q <= 0;
   vm_we_q <= 0;
   stage_v_q <= 0;
   drain_v_q <= 0;
  end else begin
   scalar_load_q <= scalar_load;
   scalar_enable_q <= scalar_enable;
   rd_re_q <= rd_re;
   vm_we_q <= vm_we;
   stage_v_q <= stage_v;
   drain_v_q <= drain_v;
  end
 wire [2047:0] raw_rd_q;
 wire [511:0] raw_drain_data;
 wire [1:0] raw_drain_result_v;
 wire raw_fault;
 ot_hgi_sfu_bankhome_core #(.HOME(HOME),.LWB(15),.MUT_XBAR(MUT==1)) core(
 .clk(clk),.rst_n(rst_n),
 .scalar_load(scalar_load_q),
 .scalar_enable(scalar_enable_q),
 .scalar_addr(scalar_addr_q),
 .scalar_data(scalar_data_q),
 .rd_re(rd_re_q),
 .rd_addr(rd_addr_q),
 .rd_src(rd_src_q),
 .vm_we(vm_we_q),
 .vm_waddr(vm_waddr_q),
 .vm_wdata(vm_wdata_q),
 .stage_v(stage_v_q),
 .stage_group(stage_group_q),
 .stage_addr(stage_addr_q),
 .stage_mask((MUT==3 ? (stage_mask_q & 64'hfefefefefefefefe) : stage_mask_q)),
 .stage_data(stage_data_q),
 .drain_v(drain_v_q),
 .drain_addr(drain_addr_q),
 .rd_q(raw_rd_q),
 .drain_data(raw_drain_data),
 .drain_result_v(raw_drain_result_v),
 .fault(raw_fault));
 always @(posedge clk) begin
  partial_rd_q <= raw_rd_q;
  partial_drain_data <= raw_drain_data;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin partial_fault<=0;partial_drain_result_v<=0;end
  else begin partial_fault<=raw_fault;partial_drain_result_v<=raw_drain_result_v;end
 generate if(HOME==0) begin:g_join
 always @(posedge clk) begin
  rd_q <= (MUT==2 ? raw_rd_q : partial_rd_q) | peer_rd_q[0+:2048] | peer_rd_q[2048+:2048] | peer_rd_q[4096+:2048];
  drain_data <= partial_drain_data | peer_drain_data[0+:512] | peer_drain_data[512+:512] | peer_drain_data[1024+:512];
 end
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin fault<=0;drain_result_v<=0;end
 else begin
  drain_result_v <= partial_drain_result_v | peer_drain_result_v[0+:2] | peer_drain_result_v[2+:2] | peer_drain_result_v[4+:2];
  fault <= partial_fault | peer_fault[0+:1] | peer_fault[1+:1] | peer_fault[2+:1];
 end
 end else begin:g_no_join
 always @* begin rd_q=0;drain_data=0;drain_result_v=0;fault=0;end
 end endgenerate
endmodule
`default_nettype wire
