`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// Compiler-prefetched operand store for the actual sixteen-lane SFU.
// Four independent operand groups and one output group, each with sixteen
// interleaved physical banks. No issue/return queues, credits or leases.
// Eight arriving sectors can fill all four operand groups at two sectors per
// group per edge. A conflicting same-bank write is an error, never a retry.
// Index/gather memory and non-VM sources are NOT aliased onto these operands.
// The separate engine index port must receive its own actual mapped service.
module ot_hgi_sfu_static_operand_store #(
 parameter integer LWB=15, MUT_XBAR=0,
 // HBM-SAFE-K9 (10-19, coordinator 0ks): WPIPE=1 registers every bank-write input (VM stage sector meta + data and the
 // lane element writes vm_*) once on clk before the groups' write select, cutting the VM meta -> bank w_mask_in
 // (~702 ps / 19 lv) and lane u_sfu -> u_output wcoll_q (~717 ps / 19 lv) stages. Every bank write lands 1 edge later
 // (priced: SFU calendar write-landing +1; reads stay at their edges). GCLK=1: group g (0-3 operand, 4 output) runs on
 // its own regional root clk_grp[g] (its 16 macros + bank/crossbar logic sit in one floorplan column). Defaults 0 keep
 // every other user bit-identical (clk_grp unused).
 parameter integer WPIPE=0, GCLK=0,
 // LH-SU (10-19, safe-design items 3/4/6): WROT=1 bank-aligns each of the 8 stage sectors ONCE here (shared by the
 // four operand groups): slot b of sector s = the word j = (b - addr_lo) mod 16 when j < 8 (its mask bit), with the
 // row hi or hi+1 (wrap = b < addr_lo). Each group bank then takes the highest-numbered sector hitting it (the same
 // last-writer-wins order and same-bank collision fault as the per-word loop). Same edges; no schedule change.
 parameter integer WROT=0
)(
 input wire clk,rst_n,
 input wire [4:0] clk_grp,
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
 always @(posedge clk `OT_SFU_ARST(rst_n))
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
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)fault<=0;
  else if(bad_source || bad_range || scalar_bad || |group_fault)fault<=1;
 // ---- bank-write landing stage (WPIPE): fault checks above keep the raw inputs (unchanged fault edges)
 wire [7:0] w_stage_v; wire [15:0] w_stage_group; wire [8*LWB-1:0] w_stage_addr; wire [63:0] w_stage_mask;
 wire [2047:0] w_stage_data; wire [15:0] w_vm_we; wire [383:0] w_vm_waddr; wire [511:0] w_vm_wdata;
 generate if(WPIPE)begin:g_wpipe
  reg [7:0] sv_q; reg [15:0] sg_q; reg [8*LWB-1:0] sa_q; reg [63:0] sm_q; reg [2047:0] sd_q;
  reg [15:0] we_q; reg [383:0] wa_q; reg [511:0] wd_q;
  always @(posedge clk `OT_SFU_ARST(rst_n))
   if(!rst_n)begin sv_q<=0;we_q<=0;end else begin sv_q<=stage_v;we_q<=vm_we;end
  always @(posedge clk)begin sg_q<=stage_group;sa_q<=stage_addr;sm_q<=stage_mask;sd_q<=stage_data;wa_q<=vm_waddr;wd_q<=vm_wdata;end
`ifdef OT_SFU_STORE_MUT_WPIPE_SKEW
  // bench negative control: the write enables bypass the landing stage while address / data take it (must mismatch)
  assign w_stage_v=stage_v; assign w_vm_we=vm_we;
`else
  assign w_stage_v=sv_q; assign w_vm_we=we_q;
`endif
  assign w_stage_group=sg_q; assign w_stage_addr=sa_q; assign w_stage_mask=sm_q; assign w_stage_data=sd_q;
  assign w_vm_waddr=wa_q; assign w_vm_wdata=wd_q;
 end else begin:g_wdirect
  assign w_stage_v=stage_v; assign w_stage_group=stage_group; assign w_stage_addr=stage_addr; assign w_stage_mask=stage_mask;
  assign w_stage_data=stage_data; assign w_vm_we=vm_we; assign w_vm_waddr=vm_waddr; assign w_vm_wdata=vm_wdata;
 end endgenerate
 // ---- shared bank-aligned sector rotate (WROT)
 localparam integer RBS=LWB-4;
 wire [8*16*32-1:0] swr_d; wire [8*16-1:0] swr_m, swr_w; wire [8*RBS-1:0] swr_r0, swr_r1;
 generate if(WROT)begin:g_wrot
  for(genvar s=0;s<8;s=s+1)begin:g_s
   wire [3:0] lo=w_stage_addr[LWB*s+:4];
   wire [RBS-1:0] hi=w_stage_addr[LWB*s+4+:RBS];
   assign swr_r0[RBS*s+:RBS]=hi;
   assign swr_r1[RBS*s+:RBS]=hi+1'b1;
   for(genvar b=0;b<16;b=b+1)begin:g_b
    localparam [3:0] B4=b;
`ifdef OT_SFU_STORE_MUT_WROT
    // bench negative control: the rotate is off by one bank (every staged word lands in the neighbouring bank)
    wire [3:0] d=B4-lo-4'd1;
`else
    wire [3:0] d=B4-lo;
`endif
    assign swr_m[16*s+b]=!d[3] && w_stage_mask[8*s+d[2:0]];
    assign swr_w[16*s+b]=(B4<lo);
    assign swr_d[32*(16*s+b)+:32]=w_stage_data[256*s+32*d[2:0]+:32];
   end
  end
 end else begin:g_nowrot
  assign swr_d=0; assign swr_m=0; assign swr_w=0; assign swr_r0=0; assign swr_r1=0;
 end endgenerate
 wire [4:0] gck;
 for(genvar g=0;g<5;g=g+1)begin:g_gck
  assign gck[g]=GCLK?clk_grp[g]:clk;
 end
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
   assign sw[b]=w_stage_v[b] && w_stage_group[2*b+:2]==g;
  end
  ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(0),
   .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(8),.WROT(WROT)) u_group(
   .clk(gck[g]),.rst_n(rst_n),.rq(req),.rr(req),.ra(addr),.rd(data),
   .sr_v(8'd0),.sr_addr({8*LWB{1'b0}}),.sr_d(),.sr_rv(),
   .sw_v(sw),.sw_addr(w_stage_addr),.sw_mask(w_stage_mask),.sw_d(w_stage_data),
   .swr_d(swr_d),.swr_m(swr_m),.swr_w(swr_w),.swr_r0(swr_r0),.swr_r1(swr_r1),
   .lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
   .flt(group_fault[g]));
 end
 ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(16),
  .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(2)) u_output(
  .clk(gck[4]),.rst_n(rst_n),.rq(16'd0),.rr(16'd0),.ra(384'd0),.rd(),
  .sr_v(drain_v),.sr_addr(drain_addr),.sr_d(drain_data),.sr_rv(drain_result_v),
  .sw_v(2'd0),.sw_addr({2*LWB{1'b0}}),.sw_mask(16'd0),.sw_d(512'd0),
  .lw(w_vm_we),.lwa(w_vm_waddr),.lwd(w_vm_wdata),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
  .flt(group_fault[4]));
endmodule
`default_nettype wire
