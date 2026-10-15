`timescale 1ns/1ps
// Original reducer and assembler control state plus slab.reset_root[4].rr.
// Identity/assembly-tag/row-tag retain their original unreset clock behavior.
module s81_static_hc_metadata_root #(parameter integer MUT=0)(
 input wire clk,rst_n,reduce_slot,input wire[3:0]rank_valid,
 input wire[31:0]tag,input wire[15:0]seq,input wire last,
 input wire[15:0]lane_valid,lane_error,
 output wire word_valid,word_error,output wire[31:0]word_tag,
 output wire[15:0]word_seq,output wire word_last,output reg reduce_fault,
 input wire assemble_slot,input wire[3:0]word_index,
 input wire emit_slot,input wire[31:0]emit_tag,
 output wire rst_n_hc,qualified_reduce_slot,
 output wire write_good,emit_good,output wire[3:0]destination_index,
 output reg row_valid,output reg[31:0]row_tag,output reg assemble_fault
);
 reg[1:0]rr;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 assign rst_n_hc=rr[1];
 reg[48:0]identity[0:17];integer k;
 always @(posedge clk)begin
  identity[0]<={tag,seq,last};
  for(k=1;k<18;k=k+1)identity[k]<=identity[k-1];
 end
 assign {word_tag,word_seq,word_last}=identity[17];
 assign word_valid=&lane_valid;
 assign word_error=word_valid&&(|lane_error);
 assign qualified_reduce_slot=reduce_slot&&(&rank_valid);
 always @(posedge clk or negedge rst_n_hc)begin
  if(!rst_n_hc)reduce_fault<=0;
  else if((reduce_slot&&rank_valid!=15)||(!reduce_slot&&(|rank_valid))||
          (word_valid&&word_error)||((|lane_valid)&&!(&lane_valid)))reduce_fault<=1;
 end
 reg[15:0]seen;reg[31:0]assembly_tag;
 // Exact slab binding: assembler.word_valid = reduced_valid && assemble_slot.
 wire assemble_word_valid=word_valid&&assemble_slot;
 assign destination_index=(MUT==1)?(word_index^4'd1):word_index;
 assign write_good=assemble_slot&&assemble_word_valid&&!word_error&&!seen[word_index]&&((seen==0)||(assembly_tag==word_tag));
 assign emit_good=emit_slot&&!assemble_slot&&(&seen)&&(assembly_tag==emit_tag);
 always @(posedge clk or negedge rst_n_hc)begin
  if(!rst_n_hc)begin seen<=0;row_valid<=0;assemble_fault<=0;end
  else begin
   row_valid<=emit_good;
   if(assemble_slot!=assemble_word_valid||(assemble_slot&&!write_good)||(emit_slot&&!emit_good))assemble_fault<=1;
   if(write_good)seen[word_index]<=1;
   if(emit_slot)seen<=0;
  end
 end
 always @(posedge clk)begin
  if(write_good&&(seen==0))assembly_tag<=word_tag;
  if(emit_good)row_tag<=assembly_tag;
 end
endmodule
