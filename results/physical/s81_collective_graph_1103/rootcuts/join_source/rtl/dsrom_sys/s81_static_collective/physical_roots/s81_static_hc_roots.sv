`timescale 1ns/1ps
// Wires-only physical composition of the exact slab HC bindings. No retiming,
// new protocol, clock alias, changed arithmetic, or row-layout transformation.
module s81_static_hc_roots #(parameter integer MUT=0)(
 input wire[15:0]clk_lane,input wire clk_control,rst_n,reduce_slot,
 input wire[3:0]rank_valid,input wire[2047:0]rank_data,
 input wire[31:0]tag,input wire[15:0]seq,input wire last,
 output wire word_valid,output wire[511:0]word_data,output wire[31:0]word_tag,
 output wire[15:0]word_seq,output wire word_last,word_error,reduce_fault,
 input wire assemble_slot,input wire[3:0]word_index,
 input wire emit_slot,input wire[31:0]emit_tag,
 output wire row_valid,output wire[8191:0]row_data,
 output wire[31:0]row_tag,output wire assemble_fault
);
 wire rst_n_hc,qualified_reduce_slot,write_good,emit_good;
 wire[3:0]destination_index;wire[15:0]lane_valid,lane_error;
 s81_static_hc_metadata_root #(.MUT(MUT)) metadata(
  .clk(clk_control),.rst_n(rst_n),.reduce_slot(reduce_slot),.rank_valid(rank_valid),
  .tag(tag),.seq(seq),.last(last),.lane_valid(lane_valid),.lane_error(lane_error),
  .word_valid(word_valid),.word_error(word_error),.word_tag(word_tag),.word_seq(word_seq),
  .word_last(word_last),.reduce_fault(reduce_fault),.assemble_slot(assemble_slot),
  .word_index(word_index),.emit_slot(emit_slot),.emit_tag(emit_tag),.rst_n_hc(rst_n_hc),
  .qualified_reduce_slot(qualified_reduce_slot),.write_good(write_good),.emit_good(emit_good),
  .destination_index(destination_index),.row_valid(row_valid),.row_tag(row_tag),.assemble_fault(assemble_fault));
 genvar g,w;
 generate for(g=0;g<16;g=g+1)begin:L
  wire[511:0]lane_row;
  s81_static_hc_payload_root #(.MUT(MUT)) payload(
   .clk(clk_lane[g]),.rst_n(rst_n_hc),.reduce_slot(qualified_reduce_slot),
   .rank_data({rank_data[1536+g*32+:32],rank_data[1024+g*32+:32],rank_data[512+g*32+:32],rank_data[g*32+:32]}),
   .word_data(word_data[g*32+:32]),.word_valid(lane_valid[g]),.word_error(lane_error[g]),
   .write_good(write_good),.emit_good(emit_good),.word_index(destination_index),.row_data(lane_row));
  for(w=0;w<16;w=w+1)begin:W
   assign row_data[w*512+g*32+:32]=lane_row[w*32+:32];
  end
 end endgenerate
endmodule
