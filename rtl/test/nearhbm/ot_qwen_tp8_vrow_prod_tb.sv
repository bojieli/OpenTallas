`timescale 1ns/1ps
module ot_qwen_tp8_vrow_prod_tb #(parameter integer PAIR=0) (
 input wire clk,rst_n,start,input wire [13:0] context_len,input wire [15:0] epoch,
 input wire want_valid,output wire want_ready,input wire [13:0] want_t,
 output wire lo_req_valid,hi_req_valid,input wire lo_req_ready,hi_req_ready,
 output wire [2:0] req_slot,output wire [13:0] req_t,output wire [15:0] req_epoch,
 input wire lo_rsp_valid,hi_rsp_valid,output wire lo_rsp_ready,hi_rsp_ready,
 input wire [2:0] lo_rsp_slot,hi_rsp_slot,input wire [13:0] lo_rsp_t,hi_rsp_t,
 input wire [15:0] lo_rsp_epoch,hi_rsp_epoch,
 input wire [1023:0] lo_vrow,hi_vrow,input wire [63:0] lo_exp,hi_exp,
 output wire out_valid,input wire out_ready,output wire [13:0] out_t,
 output wire done,fault,output wire product_valid,product_fault,
 output wire [4*128*32-1:0] products
);
 wire [1023:0] out_vrow;wire [63:0] out_exp;wire [15:0] out_epoch;
 wire out_first,out_last;
 ot_qwen_tp8_vrow_merge #(.PAIR(PAIR)) u_merge(.*);
 wire [511:0] pv,pf;
 for(genvar h=0;h<4;h=h+1)begin:g_head
  for(genvar d=0;d<128;d=d+1)begin:g_dim
   ot_qwen_nearhbm_prod u_prod(.clk(clk),.rst_n(rst_n),.valid_in(out_valid&&out_ready),
      .a(out_exp[16*h+:16]),.k(out_vrow[8*d+:8]),
      .y(products[32*(128*h+d)+:32]),.valid_out(pv[128*h+d]),.fault(pf[128*h+d]));
  end
 end
 assign product_valid=&pv;
 assign product_fault=|pf;
endmodule
