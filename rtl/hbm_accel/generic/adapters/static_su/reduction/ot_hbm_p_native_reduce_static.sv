`timescale 1ns/1ps
`default_nettype none
// Actual source SRAM -> native scratch SRAM reducer -> masked VM publication.
// Compiler command arrives one edge before the reducer's literal issue edge.
// source_operand is true only for op1/3. LOAD operands remain compiler constants.
module ot_hbm_p_native_reduce_static(
 input wire clk,rst_n,fill_slot,
 input wire [3:0] fill_burst,
 input wire [2055:0] vm_rr,
 input wire command_v,source_operand,
 input wire [9:0] source_word,
 input wire [2:0] command_op,
 input wire [9:0] command_a,command_b,command_dst,
 input wire [31:0] constant_operand,command_tag,
 input wire publish_slot,
 input wire [31:0] expected_tag,
 input wire [15:0] publish_sector,
 input wire [2:0] publish_word,
 output wire [2247:0] vm_wq,
 output wire scalar_valid,
 output wire [31:0] scalar_tag,scalar_fp32,
 output wire [15:0] scalar_bf16,
 output wire fault
);
 wire source_valid;wire [31:0] source_fp32;
 wire ingress_fault,reducer_fault,publish_fault;
 reg cv,sx;reg[2:0]op;reg[9:0]a,b,d;
 reg[31:0]x,tag;reg command_fault;
 always @(posedge clk)begin
  if(!rst_n)begin cv<=0;sx<=0;command_fault<=0;end
  else begin
   cv<=command_v;sx<=source_operand;
   if(command_v&&(source_operand!=(command_op==1||command_op==3)))command_fault<=1;
   if(cv&&sx&&!source_valid)command_fault<=1;
  end
  op<=command_op;a<=command_a;b<=command_b;d<=command_dst;
  x<=constant_operand;tag<=command_tag;
 end
 ot_hbm_p_reduce_ingress_static u_ingress(
  .clk(clk),.rst_n(rst_n),.fill_slot(fill_slot),.fill_burst(fill_burst),.vm_rr(vm_rr),
  .source_read(command_v&&source_operand),.source_word(source_word),
  .source_valid(source_valid),.source_fp32(source_fp32),.fault(ingress_fault));
 ot_hbm_su_reduce_static u_reduce(
  .clk(clk),.rst_n(rst_n),.cmd_valid(cv),.cmd_op(op),.cmd_a(a),.cmd_b(b),.cmd_dst(d),
  .operand_fp32(sx?source_fp32:x),.cmd_tag(tag),.scalar_valid(scalar_valid),
  .scalar_tag(scalar_tag),.scalar_fp32(scalar_fp32),.scalar_bf16(scalar_bf16),.fault(reducer_fault));
 ot_hbm_p_scalar_publish_static u_publish(
  .clk(clk),.rst_n(rst_n),.publish_slot(publish_slot),.expected_tag(expected_tag),
  .publish_sector(publish_sector),.publish_word(publish_word),.scalar_valid(scalar_valid),
  .scalar_tag(scalar_tag),.scalar_fp32(scalar_fp32),.vm_wq(vm_wq),.fault(publish_fault));
 assign fault=ingress_fault||reducer_fault||publish_fault||command_fault;
endmodule
`default_nettype wire
