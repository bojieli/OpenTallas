`timescale 1ns/1ps
// One actual ck_hc_lane root. Existing arithmetic and assembly are instantiated
// unchanged. The two reset flops are the original reduce.L[g].reset_lane.rr.
module s81_static_hc_payload_root #(parameter integer MUT=0)(
 input wire clk,rst_n,reduce_slot,
 input wire[127:0]rank_data,
 output wire[31:0]word_data,output wire word_valid,word_error,
 input wire write_good,emit_good,input wire[3:0]word_index,
 output wire[511:0]row_data
);
 reg[1:0]rr;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 s81_static_hc_scalar_reduce #(.MUT(MUT)) reduce(
  .clk(clk),.rst_n(rr[1]),.slot(reduce_slot),.rank_data(rank_data),
  .word_data(word_data),.word_valid(word_valid),.word_error(word_error));
 s81_static_hc_scalar_assemble assemble(
  .clk(clk),.write_good(write_good),.emit_good(emit_good),
  .word_index(word_index),.word_data(word_data),.row_data(row_data));
endmodule
