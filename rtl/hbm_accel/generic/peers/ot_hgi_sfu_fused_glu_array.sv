`timescale 1ns/1ps
// Actual256lane structural source; default off by separate instantiation.
// Fixed externally compiled row issues; no memory-wait or ready mechanism.
// Numerical leaf + full96SRAM component benches do NOT qualify this array's
// production throughput, clock roots, physical slot, or VM integration.
module ot_hgi_sfu_fused_glu_array(
 input wire clk,rst_n,
 input wire [7:0] stage_v,stage_group,
 input wire [39:0] stage_bank,
 input wire [55:0] stage_row,
 input wire [2047:0] stage_data,
 input wire issue,input wire [6:0] issue_row,
 input wire [31:0] route,
 input wire [7:0] drain_v,
 input wire [39:0] drain_bank,
 input wire [55:0] drain_row,
 output wire [7:0] drain_valid,
 output wire [2047:0] drain_data,
 output wire fault
);
 wire rv;
 wire [8191:0] gate_words,up_words,result_data;
 wire [255:0] result_v,leaf_fault;
 wire [31:0] tags[0:255];
 reg [6:0] row_q;
 reg [31:0] route_q;
 always @(posedge clk) begin row_q<=issue_row;route_q<=route;end
 wire store_fault;
 ot_hgi_sfu_fused_glu_store store(.clk(clk),.rst_n(rst_n),
  .stage_v(stage_v),.stage_group(stage_group),.stage_bank(stage_bank),.stage_row(stage_row),.stage_data(stage_data),
  .read_v(issue),.read_row(issue_row),.read_valid(rv),.gate_words(gate_words),.up_words(up_words),
  .result_v(result_v),.result_row(tags[0][6:0]),.result_data(result_data),
  .drain_v(drain_v),.drain_bank(drain_bank),.drain_row(drain_row),.drain_valid(drain_valid),.drain_data(drain_data),.fault(store_fault));
 genvar l;
 generate for(l=0;l<256;l=l+1) begin:lanes
  ot_hgi_sfu_fused_glu_lane leaf(.clk(clk),.rst_n(rst_n),.v(rv),
   .gate(gate_words[l*32+:32]),.up(up_words[l*32+:32]),.route(route_q),.tag({25'd0,row_q}),
   .vo(result_v[l]),.y(result_data[l*32+:32]),.out_tag(tags[l]),.fault(leaf_fault[l]));
 end endgenerate
 assign fault=store_fault|(|leaf_fault);
endmodule
