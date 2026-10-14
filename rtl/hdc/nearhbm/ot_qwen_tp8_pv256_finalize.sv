`timescale 1ns/1ps
// Join the two canonical 128-residue subtrees, then scale once by 1/Z.
// The reciprocal is supplied by the actual native QK/exp/Z phase.
module ot_qwen_tp8_pv_join16 #(parameter integer ADD_LAT=7,MUL_LAT=6)(
 input wire clk,rst_n,start,input wire [15:0] epoch,
 input wire p0_valid,p1_valid,output wire p0_ready,p1_ready,
 input wire [15:0] p0_epoch,p1_epoch,input wire [511:0] p0_data,p1_data,
 input wire [31:0] reciprocal,input wire reciprocal_valid,output wire reciprocal_ready,
 input wire [15:0] reciprocal_epoch,
 output reg out_valid,input wire out_ready,output reg [15:0] out_epoch,
 output reg [511:0] out_data,output reg fault
);
 localparam IDLE=0,TAKE=1,ISSUE_ADD=2,WAIT_ADD=3,ISSUE_MUL=4,WAIT_MUL=5,DONE=6,BAD=7;
 reg [2:0] state;
 reg have0,have1,have_r;
 reg [511:0] a,b,saved_sum;
 reg [31:0] rz;
 reg [15:0] ep;
 wire [511:0] sum,product;
 wire [15:0] sum_valid,mul_valid;
 wire [31:0] sum_err,mul_err;
 assign reciprocal_ready=state==TAKE&&!have_r;
 assign p0_ready=state==TAKE&&!have0;
 assign p1_ready=state==TAKE&&!have1;
 genvar lane;
 generate for(lane=0;lane<16;lane=lane+1)begin:g_lane
  ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(state==ISSUE_ADD),
   .a(a[32*lane+:32]),.b(b[32*lane+:32]),.y(sum[32*lane+:32]),
   .err(sum_err[2*lane+:2]),.valid_out(sum_valid[lane]));
  ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_mul(.clk(clk),.rst_n(rst_n),.valid_in(state==ISSUE_MUL),
   .a(saved_sum[32*lane+:32]),.b(rz),.y(product[32*lane+:32]),
   .err(mul_err[2*lane+:2]),.valid_out(mul_valid[lane]));
 end endgenerate
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;have0<=0;have1<=0;have_r<=0;a<=0;b<=0;saved_sum<=0;rz<=0;ep<=0;out_valid<=0;out_data<=0;out_epoch<=0;fault<=0;end
  else if(start && state!=IDLE)begin fault<=1;state<=BAD;out_valid<=0;end
  else case(state)
   IDLE:if(start)begin ep<=epoch;have0<=0;have1<=0;have_r<=0;state<=TAKE;end
   TAKE:begin
    if(reciprocal_valid&&reciprocal_ready)begin if(reciprocal_epoch!=ep)begin fault<=1;state<=BAD;end else begin rz<=reciprocal;have_r<=1;end end
    if(p0_valid&&p0_ready)begin if(p0_epoch!=ep)begin fault<=1;state<=BAD;end else begin a<=p0_data;have0<=1;end end
    if(p1_valid&&p1_ready)begin if(p1_epoch!=ep)begin fault<=1;state<=BAD;end else begin b<=p1_data;have1<=1;end end
    if(have0&&have1&&have_r)state<=ISSUE_ADD;
   end
   ISSUE_ADD:state<=WAIT_ADD;
   WAIT_ADD:if(&sum_valid)begin if(|sum_err)begin fault<=1;state<=BAD;end else begin saved_sum<=sum;state<=ISSUE_MUL;end end
   ISSUE_MUL:state<=WAIT_MUL;
   WAIT_MUL:if(&mul_valid)begin if(|mul_err)begin fault<=1;state<=BAD;end else begin out_data<=product;out_epoch<=ep;out_valid<=1;state<=DONE;end end
   DONE:if(out_ready)begin out_valid<=0;state<=IDLE;end
   BAD:out_valid<=0;
   default:begin fault<=1;state<=BAD;end
  endcase
 end
endmodule

// Hardened handshake collector. Data stays on the producer's registered face
// until every slice captures it; the ready acknowledgement returns afterwards.
module ot_qwen_tp8_pv_final_ctl(
 input wire clk,rst_n,start,
 input wire p0_valid,p1_valid,reciprocal_valid,out_ready,
 input wire [31:0] slice_ready0,slice_ready1,slice_ready_r,slice_valid,slice_fault,
 output reg forward0,forward1,forward_r,
 output reg p0_ready,p1_ready,reciprocal_ready,out_valid,
 output reg take_output,output reg fault
);
 reg [31:0] r0,r1,rr,ov,fl;
 reg pv0,pv1,rv,ready_q;
 reg active;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin r0<=0;r1<=0;rr<=0;ov<=0;fl<=0;pv0<=0;pv1<=0;rv<=0;ready_q<=0;end
  else begin r0<=slice_ready0;r1<=slice_ready1;rr<=slice_ready_r;ov<=slice_valid;fl<=slice_fault;
   pv0<=p0_valid;pv1<=p1_valid;rv<=reciprocal_valid;ready_q<=out_ready;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;forward0<=0;forward1<=0;forward_r<=0;
   p0_ready<=0;p1_ready<=0;reciprocal_ready<=0;out_valid<=0;take_output<=0;fault<=0;end
  else begin
   p0_ready<=0;p1_ready<=0;reciprocal_ready<=0;
   if(start)begin
    if(active)fault<=1;
    else begin active<=1;forward0<=0;forward1<=0;forward_r<=0;out_valid<=0;take_output<=0;end
   end else if(active&&!fault)begin
    if(|fl)begin fault<=1;out_valid<=0;forward0<=0;forward1<=0;forward_r<=0;end
    else begin
     if(!forward0&&pv0&&(&r0))forward0<=1;
     if(!forward1&&pv1&&(&r1))forward1<=1;
     if(!forward_r&&rv&&(&rr))forward_r<=1;
     if(forward0&&!(|r0))begin forward0<=0;p0_ready<=1;end
     if(forward1&&!(|r1))begin forward1<=0;p1_ready<=1;end
     if(forward_r&&!(|rr))begin forward_r<=0;reciprocal_ready<=1;end
     if((&ov)&&!take_output)out_valid<=1;
     // External ready/valid retirement occurs on this edge, never a delayed ready level.
     if(out_valid&&out_ready&&!take_output)begin out_valid<=0;take_output<=1;end
     if(take_output&&!(|ov))begin take_output<=0;active<=0;end
    end
   end
  end
 end
endmodule

// Wires-only parent: each 16-lane join owns an independent clock entry.
module ot_qwen_tp8_pv256_finalize(
 input wire [31:0] clk_join,input wire clk_control,rst_n,start,
 input wire [15:0] epoch,input wire [127:0] reciprocal,
 input wire reciprocal_valid,output wire reciprocal_ready,input wire [15:0] reciprocal_epoch,
 input wire p0_valid,p1_valid,output wire p0_ready,p1_ready,
 input wire [15:0] p0_epoch,p1_epoch,input wire [16383:0] p0_partial,p1_partial,
 output wire out_valid,input wire out_ready,output wire [16383:0] out_data,
 output wire [15:0] out_epoch,output wire fault
);
 wire [31:0] r0,r1,rr,ov,jf;
 wire [511:0] oe;
 wire forward0,forward1,forward_r,take_output;
 assign out_epoch=oe[15:0];
 ot_qwen_tp8_pv_final_ctl u_ctl(.clk(clk_control),.rst_n(rst_n),.start(start),
  .p0_valid(p0_valid),.p1_valid(p1_valid),.reciprocal_valid(reciprocal_valid),.out_ready(out_ready),
  .slice_ready0(r0),.slice_ready1(r1),.slice_ready_r(rr),.slice_valid(ov),.slice_fault(jf),
  .forward0(forward0),.forward1(forward1),.forward_r(forward_r),.p0_ready(p0_ready),.p1_ready(p1_ready),
  .reciprocal_ready(reciprocal_ready),.out_valid(out_valid),.take_output(take_output),.fault(fault));
 genvar block;
 generate for(block=0;block<32;block=block+1)begin:g_block
  ot_qwen_tp8_pv_join16 u_join(.clk(clk_join[block]),.rst_n(rst_n),.start(start),.epoch(epoch),
   .p0_valid(forward0),.p1_valid(forward1),.p0_ready(r0[block]),.p1_ready(r1[block]),
   .p0_epoch(p0_epoch),.p1_epoch(p1_epoch),.p0_data(p0_partial[512*block+:512]),.p1_data(p1_partial[512*block+:512]),
   .reciprocal(reciprocal[32*(block/8)+:32]),.reciprocal_valid(forward_r),
   .reciprocal_ready(rr[block]),.reciprocal_epoch(reciprocal_epoch),.out_valid(ov[block]),.out_ready(take_output),
   .out_epoch(oe[16*block+:16]),.out_data(out_data[512*block+:512]),.fault(jf[block]));
 end endgenerate
endmodule
