`timescale 1ns/1ps
// Opaque RF/shared connectivity ONLY: arithmetic invocation explicitly refuses.
module ot_gpu_fadd #(parameter integer LAT=7)(
 input wire clk,rst_n,v,input wire [31:0] a,b,output wire [31:0] y,output wire fault);
 assign y=0;assign fault=0;
 always @(posedge clk) if(rst_n && v) $fatal(1,"arithmetic outside storage connectivity gate");
endmodule
module ot_gpu_fmul #(parameter integer LAT=7)(
 input wire clk,rst_n,v,input wire [31:0] a,b,output wire [31:0] y,output wire fault);
 assign y=0;assign fault=0;
 always @(posedge clk) if(rst_n && v) $fatal(1,"arithmetic outside storage connectivity gate");
endmodule
module tb_h4_hbm_rf_shared_context;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [31:0] rf_owner_grant=0,shared_owner_grant=0;
 wire [31:0] command_conflict;
 reg [31:0] host_rd_valid=0,host_wr_valid=0,host_rsp_ready=0,host_ack_ready=0;
 wire [31:0] host_rd_ready,host_wr_ready,host_rsp_valid,host_ack_valid;
 reg [31:0][8:0] host_a=0,host_b=0,host_dst=0;
 reg [31:0][4095:0] host_wdata=0;
 wire [31:0][4095:0] host_rsp_a,host_rsp_b;
 reg [31:0] simd_valid=0,simd_mul=0,simd_done_ready=0;
 reg [31:0][8:0] simd_a=0,simd_b=0,simd_dst=0;
 wire [31:0] simd_ready,simd_done,simd_fault;
 reg [31:0] scratch_valid=0,scratch_write=0,scratch_done_ready=0;
 reg [31:0][9:0] scratch_addr=0;
 reg [31:0][511:0] scratch_wdata=0;
 wire [31:0] scratch_ready,scratch_done;
 wire [31:0][511:0] scratch_rdata;
 ot_gpu_hbm_rf_shared_context #(.ENABLE(1)) dut(.*);
 task tick;begin @(posedge clk);#1;end endtask
 integer i;
 initial begin
  tick();tick();@(negedge clk);rst_n=1;
  // Requests without real source-owner grants cannot acquire leaf credits.
  host_wr_valid[31]=1;scratch_valid[0]=1;scratch_write[0]=1;
  tick();tick();
  if(host_wr_ready[31] || scratch_ready[0] || host_ack_valid[31] || scratch_done[0])
   $fatal(1,"unowned source request accepted");
  @(negedge clk);
  rf_owner_grant[31]=1;host_rd_valid[31]=1;
  tick();tick();
  if(!command_conflict[31] || host_rd_ready[31] || host_wr_ready[31] || host_ack_valid[31])
   $fatal(1,"conflicting RF commands accepted");
  @(negedge clk);host_rd_valid=0;
  rf_owner_grant[31]=1;shared_owner_grant[0]=1;
  host_dst[31]=511;host_wdata[31]={64{64'h800000007fc00001}};
  scratch_addr[0]=1023;scratch_wdata[0]={8{64'h7fc0000180000000}};
  tick();@(negedge clk);host_wr_valid=0;scratch_valid=0;
  tick();tick();
  if(!host_ack_valid[31] || !scratch_done[0]) $fatal(1,"source write ACK missing");
  // Hold finite returns; no new command enters while ACK/done credit is held.
  for(i=0;i<3;i=i+1) begin
   tick();
   if(!host_ack_valid[31] || !scratch_done[0] || host_wr_ready[31] || scratch_ready[0])
    $fatal(1,"held ACK/credit changed");
  end
  @(negedge clk);host_ack_ready[31]=1;scratch_done_ready[0]=1;
  tick();@(negedge clk);host_ack_ready=0;scratch_done_ready=0;
  host_a[31]=511;host_b[31]=511;host_rd_valid[31]=1;
  scratch_valid[0]=1;scratch_write[0]=0;
  tick();@(negedge clk);host_rd_valid=0;scratch_valid=0;
  tick();tick();tick();
  if(!host_rsp_valid[31] || !scratch_done[0]) $fatal(1,"source read capture missing");
  if(host_rsp_a[31]!==host_wdata[31] || host_rsp_b[31]!==host_wdata[31])
   $fatal(1,"actual RF page3/two-copy bits changed");
  if(scratch_rdata[0]!==scratch_wdata[0]) $fatal(1,"shared last beat bits changed");
  if(host_rsp_valid[30] || scratch_done[1]) $fatal(1,"source SM ownership alias");
  @(negedge clk);host_rsp_ready[31]=1;scratch_done_ready[0]=1;
  tick();@(negedge clk);host_rsp_ready=0;scratch_done_ready=0;
  rf_owner_grant=0;shared_owner_grant=0;
  tick();
  if(host_rsp_valid || scratch_done || host_ack_valid) $fatal(1,"retirement did not drain");
  $display("PASS_32SM_SOURCE_RF_SHARED_STORAGE_CONNECTIVITY_ONLY");$finish;
 end
endmodule
