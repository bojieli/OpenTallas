`timescale 1ns/1ps
`default_nettype none
// Compiler-prefetched operand store for the actual sixteen-lane SFU.
// Four independent operand groups and one output group, each with sixteen
// interleaved physical banks. No issue/return queues, credits or leases.
// Eight arriving sectors can fill all four operand groups at two sectors per
// group per edge. A conflicting same-bank write is an error, never a retry.
// Index/gather memory and non-VM sources are NOT aliased onto these operands.
// The separate engine index port must receive its own actual mapped service.
module ot_hgi_sfu_bankhome_core #(
 parameter integer HOME=0, LWB=15, MUT_XBAR=0
)(
 input wire clk,rst_n,
 input wire [3:0] scalar_load,scalar_enable,
 input wire [95:0] scalar_addr,
 input wire [127:0] scalar_data,
 input wire [63:0] rd_re,
 input wire [1535:0] rd_addr,
 input wire [127:0] rd_src,
 output wire [2047:0] rd_q,
 input wire [15:0] vm_we,
 input wire [383:0] vm_waddr,
 input wire [511:0] vm_wdata,
 input wire [7:0] stage_v,
 input wire [15:0] stage_group,
 input wire [8*LWB-1:0] stage_addr,
 input wire [63:0] stage_mask,
 input wire [2047:0] stage_data,
 input wire [1:0] drain_v,
 input wire [2*LWB-1:0] drain_addr,
 output wire [511:0] drain_data,
 output wire [1:0] drain_result_v,
 output reg fault
);
 generate if(LWB<14 || LWB>17)begin:g_bad_size
  ot_sfu_store_requires_actual_supported_SRAM_geometry u_refuse();
 end endgenerate
 wire [4:0] group_fault;
 reg [23:0] scalar_addr_q[0:3];
 reg [31:0] scalar_data_q[0:3];
 reg [3:0] scalar_valid;
 reg scalar_bad;
 always @(posedge clk)for(integer g=0;g<4;g=g+1)
  if(scalar_load[g])begin scalar_addr_q[g]<=scalar_addr[24*g+:24];scalar_data_q[g]<=scalar_data[32*g+:32];end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)scalar_valid<=0;else scalar_valid<=scalar_valid|scalar_load;
 always @*begin
  scalar_bad=0;
  for(integer l=0;l<16;l=l+1)for(integer g=0;g<4;g=g+1)
   if(rd_re[4*l+g] && scalar_enable[g] &&
    (!scalar_valid[g] || rd_addr[24*(4*l+g)+:24]!=scalar_addr_q[g]))scalar_bad=1;
 end
 reg bad_source,bad_range;
 always @*begin
  bad_source=0;bad_range=0;
  for(integer l=0;l<16;l=l+1)begin
   if(vm_we[l] && |vm_waddr[24*l+LWB+:24-LWB])bad_range=1;
   for(integer g=0;g<4;g=g+1)
    if(rd_re[4*l+g] && !scalar_enable[g] && |rd_addr[24*(4*l+g)+LWB+:24-LWB])bad_range=1;
  end
  for(integer b=0;b<8;b=b+1)
   if(stage_v[b] && stage_addr[LWB*b+:LWB]>{LWB{1'b1}}-7)bad_range=1;
  for(integer b=0;b<2;b=b+1)
   if(drain_v[b] && drain_addr[LWB*b+:LWB]>{LWB{1'b1}}-7)bad_range=1;
  for(integer l=0;l<16;l=l+1)
   for(integer s=0;s<4;s=s+1)
    if(rd_re[4*l+s] && rd_src[8*l+2*s+:2]!=0)bad_source=1;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if(bad_source || bad_range || scalar_bad || |group_fault)fault<=1;
 for(genvar g=0;g<4;g=g+1)begin:g_operand
  wire [15:0] req;
  wire [383:0] addr;
  wire [511:0] data;
  reg [511:0] scalar_read;
  reg scalar_selected;
  always @(posedge clk)begin
   scalar_selected<=scalar_enable[g];
   for(integer l=0;l<16;l=l+1)if(rd_re[4*l+g] && scalar_enable[g])scalar_read[32*l+:32]<=scalar_data_q[g];
  end
  wire [7:0] sw;
  for(genvar l=0;l<16;l=l+1)begin:g_lane
   assign req[l]=rd_re[4*l+g] && rd_src[8*l+2*g+:2]==0 && !scalar_enable[g];
   assign addr[24*l+:24]=rd_addr[(4*l+g)*24+:24];
   assign rd_q[(4*l+g)*32+:32]=scalar_selected?scalar_read[32*l+:32]:data[32*l+:32];
  end
  for(genvar b=0;b<8;b=b+1)begin:g_stage
   assign sw[b]=stage_v[b] && stage_group[2*b+:2]==g;
  end
  ot_hgi_sfu_bankhome_group #(.HOME(HOME),.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(0),
   .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(8)) u_group(
   .clk(clk),.rst_n(rst_n),.rq(req),.rr(req),.ra(addr),.rd(data),
   .sr_v(8'd0),.sr_addr({8*LWB{1'b0}}),.sr_d(),.sr_rv(),
   .sw_v(sw),.sw_addr(stage_addr),.sw_mask(stage_mask),.sw_d(stage_data),
   .lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
   .flt(group_fault[g]));
 end
 ot_hgi_sfu_bankhome_group #(.HOME(HOME),.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(16),
  .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(2)) u_output(
  .clk(clk),.rst_n(rst_n),.rq(16'd0),.rr(16'd0),.ra(384'd0),.rd(),
  .sr_v(drain_v),.sr_addr(drain_addr),.sr_d(drain_data),.sr_rv(drain_result_v),
  .sw_v(2'd0),.sw_addr({2*LWB{1'b0}}),.sw_mask(16'd0),.sw_d(512'd0),
  .lw(vm_we),.lwa(vm_waddr),.lwd(vm_wdata),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
  .flt(group_fault[4]));
endmodule
`default_nettype wire
