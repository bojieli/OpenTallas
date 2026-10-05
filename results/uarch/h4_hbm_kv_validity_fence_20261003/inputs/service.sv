`timescale 1ns/1ps
// Additive conventional GPU RF/SIMD/shared-memory provider, absent by default.
// Parent matrix ports/arithmetic stay in their original modules. Parent source
// join owns wiring these explicit ports and matrix result acceptance fences.
// No optional epilogue, gather, reduction, SFU or numerical-contract change.
module ot_gpu_full_sm_service #(parameter integer ENABLE=0) (
 input wire clk,rst_n,
 input wire host_rd_valid, output wire host_rd_ready,
 input wire [8:0] host_a,host_b,
 output wire host_rsp_valid, input wire host_rsp_ready,
 output wire [4095:0] host_rsp_a,host_rsp_b,
 input wire host_wr_valid, output wire host_wr_ready,
 input wire [8:0] host_dst, input wire [4095:0] host_wdata,
 output wire host_ack_valid, input wire host_ack_ready,
 input wire simd_valid, output wire simd_ready,
 input wire simd_mul, input wire [8:0] simd_a,simd_b,simd_dst,
 output wire simd_done, input wire simd_done_ready, output wire simd_fault,
 input wire scratch_valid,scratch_write,output wire scratch_ready,
 input wire [9:0] scratch_addr,input wire [511:0] scratch_wdata,
 output wire scratch_done,input wire scratch_done_ready,output wire [511:0] scratch_rdata
);
 generate if(ENABLE) begin:g_enabled
  localparam IDLE=0, READ=1, OPERATE=2, WAIT_ALU=3, WRITE=4, ACK=5, DONE=6;
  reg [2:0] state;
  reg mul_q, fault_q, prefer_simd;
  reg [8:0] a_q,b_q,dst_q;
  reg [4095:0] result_q;
  wire rr,rv,wr,wack;
  wire [4095:0] ra,rb;
  wire idle=state==IDLE;
  // Arbitration only at RF idle. An accepted SIMD reserves the entire RF
  // through its write ACK, preventing host modification between operands and writeback.
  wire choose_simd=simd_valid && (!host_rd_valid && !host_wr_valid || prefer_simd);
  assign simd_ready=idle && rr && wr && choose_simd;
  wire sg=simd_valid && simd_ready;
  assign host_rd_ready=idle && !choose_simd && rr;
  assign host_wr_ready=idle && !choose_simd && wr;
  assign host_rsp_valid=idle && rv;
  assign host_ack_valid=idle && wack;
  assign host_rsp_a=ra;assign host_rsp_b=rb;
  ot_gpu_rf_service u_rf (
   .clk(clk),.rst_n(rst_n),
   .rd_valid(state==READ || (idle && !choose_simd && host_rd_valid)),.rd_ready(rr),
   .rd_a(idle?host_a:a_q),.rd_b(idle?host_b:b_q),
   .rsp_valid(rv),.rsp_ready(state==OPERATE || (idle && host_rsp_ready)),.rsp_a(ra),.rsp_b(rb),
   .wr_valid(state==WRITE || (idle && !choose_simd && host_wr_valid)),.wr_ready(wr),
   .wr_addr(idle?host_dst:dst_q),.wr_data(idle?host_wdata:result_q),
   .ack_valid(wack),.ack_ready(state==ACK || (idle && host_ack_ready)));
  wire [4095:0] add_result,mul_result;
  wire [127:0] add_fault,mul_fault;
  genvar l;
  for(l=0;l<128;l=l+1) begin:g_lane
   ot_gpu_fadd #(.LAT(7)) u_add (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && !mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(add_result[l*32+:32]),.fault(add_fault[l]));
   ot_gpu_fmul #(.LAT(7)) u_mul (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(mul_result[l*32+:32]),.fault(mul_fault[l]));
  end
  reg [6:0] alu_valid;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) alu_valid<=0;
   else alu_valid<={alu_valid[5:0],state==OPERATE && rv};
  end
  assign simd_done=state==DONE;assign simd_fault=fault_q;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin state<=IDLE;mul_q<=0;fault_q<=0;prefer_simd<=0;a_q<=0;b_q<=0;dst_q<=0;end
   else case(state)
    IDLE: begin
     if(sg) begin state<=READ;mul_q<=simd_mul;a_q<=simd_a;b_q<=simd_b;dst_q<=simd_dst;fault_q<=0;prefer_simd<=0;end
     else if((host_rd_valid && host_rd_ready)||(host_wr_valid && host_wr_ready)) prefer_simd<=1;
    end
    READ: if(rr) state<=OPERATE;
    OPERATE: if(rv) state<=WAIT_ALU;
    WAIT_ALU: if(alu_valid[6]) begin
     result_q<=mul_q?mul_result:add_result;fault_q<=mul_q?(|mul_fault):(|add_fault);state<=WRITE;
    end
    WRITE: if(wr) state<=ACK;
    ACK: if(wack) state<=DONE;
    DONE: if(simd_done_ready) state<=IDLE;
    default: state<=IDLE;
   endcase
  end
  ot_gpu_scratch_service u_scratch (.clk(clk),.rst_n(rst_n),.valid(scratch_valid),.write(scratch_write),
   .ready(scratch_ready),.addr(scratch_addr),.wdata(scratch_wdata),.done(scratch_done),
   .done_ready(scratch_done_ready),.rdata(scratch_rdata));
 end else begin:g_disabled
  assign host_rd_ready=0;assign host_wr_ready=0;assign host_rsp_valid=0;assign host_ack_valid=0;
  assign host_rsp_a=0;assign host_rsp_b=0;assign simd_ready=0;assign simd_done=0;assign simd_fault=0;
  assign scratch_ready=0;assign scratch_done=0;assign scratch_rdata=0;
 end endgenerate
endmodule
