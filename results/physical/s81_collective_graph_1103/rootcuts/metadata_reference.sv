// Automatically extracted original metadata processes; scalar generate loops removed.
module s81_static_hc_reduce_metadata_reference #(parameter integer MUT=0,parameter integer LOCAL_RESET_SYNC=0)(
 input wire [15:0] clk_lane,lane_valid,lane_error, input wire clk_control,rst_n,slot,
 input wire [3:0] rank_valid,
 input wire [2047:0] rank_data,
 input wire [31:0] tag,
 input wire [15:0] seq,
 input wire last,
 output wire word_valid,
 output wire [511:0] word_data,
 output wire [31:0] word_tag,
 output wire [15:0] word_seq,
 output wire word_last,
 output wire word_error,
 output reg fault

);
 reg [48:0] identity[0:17];integer k;
 wire [15:0] lv=lane_valid,le=lane_error;
 always @(posedge clk_control)begin
  identity[0]<={tag,seq,last};
  for(k=1;k<18;k=k+1)identity[k]<=identity[k-1];
 end
 assign {word_tag,word_seq,word_last}=identity[17];
 assign word_valid=&lv;
 assign word_error=word_valid && (|le);
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)fault<=0;
  else if((slot&&rank_valid!=15)||(!slot&&(|rank_valid))||
          (word_valid&&word_error)||((|lv)&&!( &lv)))fault<=1;
 end
endmodule
module s81_static_hc_assemble_metadata_reference #(parameter integer MUT=0)(
 input wire [15:0] clk_lane, input wire clk_control,rst_n,write_slot,
 input wire [3:0] word_index,
 input wire word_valid,
 input wire [511:0] word_data,
 input wire [31:0] word_tag,
 input wire word_error,
 input wire emit_slot,
 input wire [31:0] emit_tag,
 output wire write_good,emit_good,output wire[3:0]destination_index,output reg row_valid,
 output wire [8191:0] row_data,
 output reg [31:0] row_tag,
 output reg fault

);
 reg[15:0]seen;reg[31:0]assembly_tag;
 assign destination_index=(MUT==1)?(word_index^4'd1):word_index;
 assign write_good=write_slot&&word_valid&&!word_error&&!seen[word_index]&&((seen==0)||(assembly_tag==word_tag));
 assign emit_good=emit_slot&&!write_slot&&(&seen)&&(assembly_tag==emit_tag);
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin seen<=0;row_valid<=0;fault<=0;end
  else begin
   row_valid<=emit_good;
   if(write_slot!=word_valid||(write_slot&&!write_good)||(emit_slot&&!emit_good))fault<=1;
   if(write_good)seen[word_index]<=1;
   if(emit_slot)seen<=0;
  end
 end
 always @(posedge clk_control)begin
  if(write_good&&(seen==0))assembly_tag<=word_tag;
  if(emit_good)row_tag<=assembly_tag;
 end
endmodule
module s81_static_hc_metadata_reference #(parameter integer MUT=0)(
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
 always @(posedge clk or negedge rst_n)if(!rst_n)rr<=0;else rr<={rr[0],1'b1};
 assign rst_n_hc=rr[1];
 assign qualified_reduce_slot=reduce_slot&&(&rank_valid);
 s81_static_hc_reduce_metadata_reference reduce(.clk_lane(16'b0),.lane_valid(lane_valid),.lane_error(lane_error),.clk_control(clk),.rst_n(rst_n_hc),.slot(reduce_slot),.rank_valid(rank_valid),.rank_data(2048'b0),.tag(tag),.seq(seq),.last(last),.word_valid(word_valid),.word_data(),.word_tag(word_tag),.word_seq(word_seq),.word_last(word_last),.word_error(word_error),.fault(reduce_fault));
 s81_static_hc_assemble_metadata_reference #(.MUT(MUT)) assemble(.clk_lane(16'b0),.clk_control(clk),.rst_n(rst_n_hc),.write_slot(assemble_slot),.word_index(word_index),.word_valid(word_valid&&assemble_slot),.word_data(512'b0),.word_tag(word_tag),.word_error(word_error),.emit_slot(emit_slot),.emit_tag(emit_tag),.row_valid(row_valid),.row_data(),.row_tag(row_tag),.fault(assemble_fault),.write_good(write_good),.emit_good(emit_good),.destination_index(destination_index));
endmodule
