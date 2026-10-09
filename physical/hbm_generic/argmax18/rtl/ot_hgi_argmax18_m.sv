`timescale 1ns/1ps
// HGI-1 LOCAL endpoint. Configuration is captured on the first accepted row beat.
// Generic mode is opt-in. DS-default keeps the qualified IW17 arithmetic verbatim.
module ot_hgi_argmax18_m #(
 parameter integer LP=8, FLAT=7, FAST=1, GENERIC18=0
)(
 input wire clk, rst_n, in_v, in_last, in_bias_en,
 input wire [LP-1:0] in_mask,
 input wire [LP*32-1:0] in_vals, in_bias,
 input wire [6:0] cfg_rank,
 input wire [17:0] cfg_imm_a,
 output wire out_v,
 output wire [17:0] out_idx,
 output wire out_nan, fault, out_range_fault,
 output wire [31:0] out_value
);
 localparam integer IW=GENERIC18 ? 18 : 17;
 localparam integer LL=(LP>1)?$clog2(LP):1;
 localparam integer LAT=FLAT+FAST+LL+2;
 wire [IW-1:0] local_idx;
 wire [24:0] end_offset;
 wire core_range_fault;
 generate if(GENERIC18) begin:g_value_leaf
 ot_hgi_argmax18_value_m #(.LP(LP),.IW(IW),.FLAT(FLAT),.FAST(FAST)) u_native(
 .clk(clk),.rst_n(rst_n),.in_v(in_v),.in_last(in_last),.in_bias_en(in_bias_en),
 .in_mask(in_mask),.in_vals(in_vals),.in_bias(in_bias),
 .out_v(out_v),.out_idx(local_idx),.out_nan(out_nan),.fault(fault),.out_value(out_value),.global_offset(end_offset),.out_range_fault(core_range_fault));
 end else begin:g_native_leaf
 ot_dshbm_argmax_m #(.LP(LP),.IW(IW),.FLAT(FLAT),.FAST(FAST)) u_native(
 .clk(clk),.rst_n(rst_n),.in_v(in_v),.in_last(in_last),.in_bias_en(in_bias_en),
 .in_mask(in_mask),.in_vals(in_vals),.in_bias(in_bias),
 .out_v(out_v),.out_idx(local_idx),.out_nan(out_nan),.fault(fault));
 assign out_value=32'b0;
 assign core_range_fault=1'b0;
 end endgenerate
 generate if(GENERIC18) begin:g_generic
   reg fresh;
   reg [6:0] rank_q;
   reg [17:0] imm_q;
   reg [24:0] offset_pipe[0:LAT-2];
   wire [24:0] registered_offset={18'b0,rank_q} * {7'b0,imm_q};
   integer j;
   always @(posedge clk or negedge rst_n) begin
     if(!rst_n) begin
       fresh<=1'b1;rank_q<=0;imm_q<=0;
       for(j=0;j<=LAT-2;j=j+1) offset_pipe[j]<=0;
     end else begin
       if(in_v) begin
         if(fresh) begin rank_q<=cfg_rank;imm_q<=cfg_imm_a;end
         fresh<=in_last;
       end
       offset_pipe[0]<=registered_offset;
       for(j=1;j<=LAT-2;j=j+1) offset_pipe[j]<=offset_pipe[j-1];
     end
   end
   assign end_offset=offset_pipe[LAT-2];
   assign out_idx=local_idx;
   assign out_range_fault=out_v && core_range_fault;
 end else begin:g_ds
   assign end_offset=25'b0;
   assign out_idx={1'b0,local_idx};
   assign out_range_fault=1'b0;
 end endgenerate
endmodule
