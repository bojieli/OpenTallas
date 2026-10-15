// Reference uses original unmodified clocked modules and original slab bindings.
module s81_static_hc_roots_reference #(parameter integer MUT=0)(
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
 reg[1:0]rr;
 always @(posedge clk_control or negedge rst_n)if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 wire rn=rr[1];
 s81_static_hc_reduce_clocked #(.MUT(MUT),.LOCAL_RESET_SYNC(1)) reduce(
 .clk_lane(clk_lane),.clk_control(clk_control),.rst_n(rn),.slot(reduce_slot),.rank_valid(rank_valid),.rank_data(rank_data),.tag(tag),.seq(seq),.last(last),.word_valid(word_valid),.word_data(word_data),.word_tag(word_tag),.word_seq(word_seq),.word_last(word_last),.word_error(word_error),.fault(reduce_fault));
 s81_static_hc_assemble_clocked #(.MUT(MUT)) assemble(
 .clk_lane(clk_lane),.clk_control(clk_control),.rst_n(rn),.write_slot(assemble_slot),.word_index(word_index),.word_valid(word_valid&&assemble_slot),.word_data(word_data),.word_tag(word_tag),.word_error(word_error),.emit_slot(emit_slot),.emit_tag(emit_tag),.row_valid(row_valid),.row_data(row_data),.row_tag(row_tag),.fault(assemble_fault));
endmodule
