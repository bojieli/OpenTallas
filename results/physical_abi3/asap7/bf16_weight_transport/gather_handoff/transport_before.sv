`timescale 1ns/1ps
// Sequential G2 weight bursts -> descriptor-relative cursor -> cached gather.
// The caller supplies checked BF16 object permission/layout and clears only
// after external cancellation acknowledgement or drain. Resident-row replay
// may stop requesting after the first row; ownership lasts until clear.
// This adapter preserves the scheduler's generation/address tag and beat index.
module ot_a3_bf16_weight_transport #(
 parameter integer INTERLEAVE=3,
 parameter bit RETAIN_LINES=1
)(
 input wire clk,rst_n,clear,
 input wire command_valid,output wire command_ready,
 input wire [31:0] command_generation,command_object,command_service_base,
 input wire [63:0] command_object_bytes,command_element_base,
 input wire [15:0] command_rows,command_cols,command_depth,
 input wire [31:0] command_column_stride,command_k_stride,
 input wire request_valid,output wire request_ready,
 input wire [63:0] request_tag,
 input wire [31:0] request_address,
 input wire [9:0] request_words,
 output wire response_valid,input wire response_ready,
 output wire [63:0] response_tag,
 output reg [9:0] response_index,
 output wire [127:0] response_data,
 output wire read_valid,input wire read_ready,
 output wire [63:0] read_tag,read_offset,
 output wire [31:0] read_object,
 output wire [4:0] read_bytes,
 input wire memory_valid,output wire memory_ready,
 input wire [63:0] memory_tag,
 input wire [127:0] memory_data,
 input wire memory_error,
 output wire protocol_error,transport_drained
);
 localparam integer SB=INTERLEAVE<2?1:$clog2(INTERLEAVE);
 reg active,burst_active,exhausted,local_error;
 reg [31:0] generation;
 reg [32:0] next_address;
 reg [9:0] burst_words;
 reg [63:0] burst_tag;
 reg [15:0] logical_cols;
 reg [SB-1:0] slot;
 wire cursor_command_ready,gather_command_ready,cursor_valid,cursor_ready,cursor_last,cursor_error;
 wire [63:0] element_base;
 wire [15:0] column_base;
 wire [7:0] lane_mask;
 wire gather_ready,gather_valid,gather_error;
 wire [31:0] gathered_index;
 wire enabled=rst_n && !clear;
 wire launch=command_valid && command_ready;
 wire coordinate_fire=cursor_valid && cursor_ready;
 assign command_ready=enabled && !active && cursor_command_ready && gather_command_ready && !protocol_error;
 assign request_ready=enabled && active && !burst_active && !protocol_error;
 assign cursor_ready=gather_ready && burst_active && !protocol_error;
 assign response_valid=gather_valid && burst_active;
 assign response_tag=burst_tag;
 assign protocol_error=local_error || cursor_error || gather_error;
 // Row/K coordinates are observation-only at this boundary.
 /* verilator lint_off PINCONNECTEMPTY */
 ot_a3_weight_layout_cursor #(.INTERLEAVE(INTERLEAVE)) cursor(
  .clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(launch),.command_ready(cursor_command_ready),
  .command_generation(command_generation),.command_rows(command_rows),.command_cols(command_cols),.command_depth(command_depth),
  .command_element_base(command_element_base),.command_column_stride(command_column_stride),.command_k_stride(command_k_stride),
  .coordinate_valid(cursor_valid),.coordinate_ready(cursor_ready),.generation(),.element_base(element_base),
  .lane_stride(),.lane_mask(lane_mask),.row_index(),.column_base(column_base),.k_index(),.last(cursor_last),.command_error(cursor_error));
 /* verilator lint_on PINCONNECTEMPTY */
 ot_a3_bf16_weight_gather #(.SLOTS(INTERLEAVE),.RETAIN_LINES(RETAIN_LINES)) gather(
  .clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(launch),.command_ready(gather_command_ready),
  .command_generation(command_generation),.command_object(command_object),.command_object_bytes(command_object_bytes),.command_lane_stride(command_column_stride),
  .coordinate_valid(cursor_valid && burst_active && !protocol_error),.coordinate_ready(gather_ready),
  .coordinate_element_base(element_base),.coordinate_mask(lane_mask),
  .coordinate_slot(slot),.coordinate_index(next_address[31:0]),
  .word_valid(gather_valid),.word_ready(response_ready && burst_active),.word_data(response_data),.word_index(gathered_index),
  .read_valid(read_valid),.read_ready(read_ready),.read_tag(read_tag),.read_object(read_object),.read_offset(read_offset),.read_bytes(read_bytes),
  .response_valid(memory_valid),.response_ready(memory_ready),.response_tag(memory_tag),.response_data(memory_data),.response_error(memory_error),
  .protocol_error(gather_error),.drained(transport_drained));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;burst_active<=0;exhausted<=0;local_error<=0;response_index<=0;slot<=0;end
  else if(clear)begin active<=0;burst_active<=0;exhausted<=0;local_error<=0;response_index<=0;slot<=0;end
  else begin
   if(launch)begin active<=1;end
   if(request_valid && request_ready)begin
    if(exhausted || request_words==0 || request_words>512 || request_tag!={generation,request_address} ||
       {1'b0,request_address}!=next_address || ({1'b0,request_address}+{23'd0,request_words})>33'h100000000)
     local_error<=1;
    else begin burst_active<=1;response_index<=0;end
   end
   if(coordinate_fire)begin
    if(32'(slot)+1==INTERLEAVE || {1'b0,column_base}+17'd8>={1'b0,logical_cols})slot<=0;
    else slot<=slot+1'b1;
    if(cursor_last)begin
     exhausted<=1;
     if(response_index!=burst_words-1'b1)local_error<=1;
    end
   end
   if(response_valid && response_ready)begin
    if(gathered_index!=burst_tag[31:0]+{22'd0,response_index})local_error<=1;
    if(response_index==burst_words-1'b1)burst_active<=0;
    else response_index<=response_index+1'b1;
   end
  end
 end
 always @(posedge clk)begin
  if(launch)begin generation<=command_generation;next_address<={1'b0,command_service_base};logical_cols<=command_cols;end
  else if(coordinate_fire)next_address<=next_address+1'b1;
  if(request_valid && request_ready)begin burst_tag<=request_tag;burst_words<=request_words;end
 end
endmodule
