`timescale 1ns/1ps
// Actual clock partition: 16 payload leaves, each 512 assembly +512 output
// bits, with an independent clock pin. Metadata/bitmap have their own root.
module s81_static_hc_assemble_clocked #(parameter integer MUT=0)(
 input wire [15:0] clk_lane, input wire clk_control,rst_n,write_slot,
 input wire [3:0] word_index,
 input wire word_valid,
 input wire [511:0] word_data,
 input wire [31:0] word_tag,
 input wire [4:0] word_row,   // additive y_row5 (10-16): the reduced word's seq[8:4], latched with the tag
 input wire word_error,
 input wire emit_slot,
 input wire [31:0] emit_tag,
 output reg row_valid,
 output wire [8191:0] row_data,
 output reg [31:0] row_tag,
 output reg [4:0] row_y5,     // registered at the existing emit_good edge: aligned with row_valid/row_tag/row_data
 output reg fault

);
 reg[15:0]seen;reg[31:0]assembly_tag;reg[4:0]assembly_row;
 // MUT 3: row ordinal registered one edge late (off emit_good); MUT 4: tag registered one edge late.
 reg emit_good_q;
 wire[3:0]destination_index=(MUT==1)?(word_index^4'd1):word_index;
 wire write_good=write_slot&&word_valid&&!word_error&&!seen[word_index]&&((seen==0)||(assembly_tag==word_tag));
 wire emit_good=emit_slot&&!write_slot&&(&seen)&&(assembly_tag==emit_tag);
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
  if((MUT==4)?emit_good_q:emit_good)row_tag<=assembly_tag;
 end
 // y_row5: same capture edges as the tag (first write of the row / emit_good); no new state on any existing path
 always @(posedge clk_control)begin
  emit_good_q<=emit_good;
  if(write_good&&(seen==0))assembly_row<=word_row;
  if((MUT==3)?emit_good_q:emit_good)row_y5<=assembly_row;
 end
 genvar g,w;
 generate for(g=0;g<16;g=g+1)begin:L
  wire[511:0]lane_row;
  s81_static_hc_scalar_assemble leaf(.clk(clk_lane[g]),.write_good(write_good),.emit_good(emit_good),
   .word_index(destination_index),.word_data(word_data[g*32+:32]),.row_data(lane_row));
  for(w=0;w<16;w=w+1)begin:W
   assign row_data[w*512+g*32+:32]=lane_row[w*32+:32];
  end
 end endgenerate
endmodule

module s81_static_hc_scalar_assemble(
 input wire clk,write_good,emit_good,input wire[3:0]word_index,
 input wire[31:0]word_data,output reg[511:0]row_data
);
 reg[511:0]assembly;
 always @(posedge clk)begin
  if(write_good)assembly[{word_index,5'b0}+:32]<=word_data;
  if(emit_good)row_data<=assembly;
 end
endmodule

// Functional compatibility wrapper only; clocks are independent in the native
// physical interface above. No single-root physical qualification is implied.
module s81_static_hc_assemble #(parameter integer MUT=0)(
 input wire clk,rst_n,write_slot,
 input wire [3:0] word_index,
 input wire word_valid,
 input wire [511:0] word_data,
 input wire [31:0] word_tag,
 input wire [4:0] word_row,
 input wire word_error,
 input wire emit_slot,
 input wire [31:0] emit_tag,
 output wire row_valid,
 output wire [8191:0] row_data,
 output wire [31:0] row_tag,
 output wire [4:0] row_y5,
 output wire fault

);
 s81_static_hc_assemble_clocked #(.MUT(MUT)) core(.clk_lane({16{clk}}),.clk_control(clk),
  .rst_n(rst_n),.write_slot(write_slot),.word_index(word_index),.word_valid(word_valid),.word_data(word_data),
  .word_tag(word_tag),.word_row(word_row),.word_error(word_error),.emit_slot(emit_slot),.emit_tag(emit_tag),
  .row_valid(row_valid),.row_data(row_data),.row_tag(row_tag),.row_y5(row_y5),.fault(fault));
endmodule
