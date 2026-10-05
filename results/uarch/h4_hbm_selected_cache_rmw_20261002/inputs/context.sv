`timescale 1ns/1ps
// Additive source connectivity for the selected32SM HBM service.
// Existing finite H1 RF/SIMD/shared machinery owns actual acceptance/ACKs.
// A source-bound gateway must hold each external ownership grant through all
// accepted results and reverse retirement; this wrapper does not fabricate it.
// No L2 or matrix producer may infer ownership from these ready signals.
// Default absent. This source-preparation wrapper is not full-token admission.
module ot_gpu_hbm_rf_shared_context #(parameter integer ENABLE=0) (
 input wire clk,rst_n,
 input wire [31:0] rf_owner_grant,shared_owner_grant,
 output wire [31:0] command_conflict,
 input wire [31:0] host_rd_valid,output wire [31:0] host_rd_ready,
 input wire [31:0][8:0] host_a,host_b,
 output wire [31:0] host_rsp_valid,input wire [31:0] host_rsp_ready,
 output wire [31:0][4095:0] host_rsp_a,host_rsp_b,
 input wire [31:0] host_wr_valid,output wire [31:0] host_wr_ready,
 input wire [31:0][8:0] host_dst,input wire [31:0][4095:0] host_wdata,
 output wire [31:0] host_ack_valid,input wire [31:0] host_ack_ready,
 input wire [31:0] simd_valid,output wire [31:0] simd_ready,
 input wire [31:0] simd_mul,input wire [31:0][8:0] simd_a,simd_b,simd_dst,
 output wire [31:0] simd_done,input wire [31:0] simd_done_ready,
 output wire [31:0] simd_fault,
 input wire [31:0] scratch_valid,scratch_write,output wire [31:0] scratch_ready,
 input wire [31:0][9:0] scratch_addr,input wire [31:0][511:0] scratch_wdata,
 output wire [31:0] scratch_done,input wire [31:0] scratch_done_ready,
 output wire [31:0][511:0] scratch_rdata
);
 genvar sm;
 generate for(sm=0;sm<32;sm=sm+1) begin:g_sm
  wire rd_ready,wr_ready,alu_ready,shared_ready;
  // One source command credit. Refuse conflicting valids before the actual
  // leaf can accept simultaneous reads/writes to the same RF version.
  wire collision=(host_rd_valid[sm] && host_wr_valid[sm]) ||
                 (host_rd_valid[sm] && simd_valid[sm]) ||
                 (host_wr_valid[sm] && simd_valid[sm]);
  wire grant=rf_owner_grant[sm] && !collision;
  assign command_conflict[sm]=rf_owner_grant[sm] && collision;
  // Sixteen single-bit gate equivalents per SM; no new FIFO, wide data mux,
  // clock or numerical primitive. Previously accepted sinks stay unmasked.
  assign host_rd_ready[sm]=rd_ready && grant;
  assign host_wr_ready[sm]=wr_ready && grant;
  assign simd_ready[sm]=alu_ready && grant;
  assign scratch_ready[sm]=shared_ready && shared_owner_grant[sm];
  ot_gpu_full_sm_service #(.ENABLE(ENABLE)) u_service (
   .clk(clk),.rst_n(rst_n),
   .host_rd_valid(host_rd_valid[sm] && grant),.host_rd_ready(rd_ready),
   .host_a(host_a[sm]),.host_b(host_b[sm]),
   .host_rsp_valid(host_rsp_valid[sm]),.host_rsp_ready(host_rsp_ready[sm]),
   .host_rsp_a(host_rsp_a[sm]),.host_rsp_b(host_rsp_b[sm]),
   .host_wr_valid(host_wr_valid[sm] && grant),.host_wr_ready(wr_ready),
   .host_dst(host_dst[sm]),.host_wdata(host_wdata[sm]),
   .host_ack_valid(host_ack_valid[sm]),.host_ack_ready(host_ack_ready[sm]),
   .simd_valid(simd_valid[sm] && grant),.simd_ready(alu_ready),
   .simd_mul(simd_mul[sm]),.simd_a(simd_a[sm]),.simd_b(simd_b[sm]),.simd_dst(simd_dst[sm]),
   .simd_done(simd_done[sm]),.simd_done_ready(simd_done_ready[sm]),.simd_fault(simd_fault[sm]),
   .scratch_valid(scratch_valid[sm] && shared_owner_grant[sm]),.scratch_write(scratch_write[sm]),
   .scratch_ready(shared_ready),.scratch_addr(scratch_addr[sm]),.scratch_wdata(scratch_wdata[sm]),
   .scratch_done(scratch_done[sm]),.scratch_done_ready(scratch_done_ready[sm]),.scratch_rdata(scratch_rdata[sm])
  );
 end endgenerate
endmodule
