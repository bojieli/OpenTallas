`timescale 1ns/1ps
// Real macro read -> exact64-lane dequant, one finite request lease through
// final converted retirement. This is one real bank, replicated38/rank.
module ot_qwen_dspark_w1_lookup #(parameter integer ENABLE=0,BANK=0)(
 input wire clk,rst_n,input wire i_v,output wire i_r,
 input wire [17:0] i_token,input wire [63:0] i_id,input wire [7:0] i_sequence,
 output wire o_v,input wire o_r,output wire [2047:0] o_values,
 output wire [63:0] o_id,output wire [7:0] o_sequence,
 output wire [1:0] o_quarter,output wire o_last,output wire fault
);
 reg active;reg [7:0] lease_sequence;
 wire bank_ready,bank_valid,bank_retire,bank_last,bank_fault,dequant_fault;
 wire [511:0] codes;wire [15:0] scale;wire [63:0] bank_id;wire [1:0] quarter;
 assign fault=bank_fault|dequant_fault;
 assign i_r=(ENABLE!=0)&&!active&&!fault&&bank_ready;
 assign o_sequence=lease_sequence;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;lease_sequence<=0;end
  else begin
   if(i_v&&i_r)begin active<=1;lease_sequence<=i_sequence;end
   if(o_v&&o_r&&o_last)active<=0;
  end
 end
 ot_qwen_dspark_w1_bank #(.ENABLE(ENABLE),.BANK(BANK)) rom_bank(
  .clk(clk),.rst_n(rst_n),.i_v(i_v&&i_r),.i_r(bank_ready),.i_token(i_token),.i_id(i_id),
  .o_v(bank_valid),.o_r(bank_retire),.o_codes(codes),.o_scale(scale),.o_quarter(quarter),.o_id(bank_id),.o_last(bank_last),.fault(bank_fault));
 ot_qwen_dspark_w1_dequant #(.ENABLE(ENABLE)) converter(
  .clk(clk),.rst_n(rst_n),.i_v(bank_valid&&!fault),.i_r(bank_retire),.i_codes(codes),.i_scale(scale),
  .i_id(bank_id),.i_quarter(quarter),.i_last(bank_last),.o_v(o_v),.o_r(o_r),.o_values(o_values),
  .o_id(o_id),.o_quarter(o_quarter),.o_last(o_last),.fault(dequant_fault));
endmodule
