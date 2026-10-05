`timescale 1ns/1ps
// Bounded rank-two output transport. One atomic lane beat may be outstanding;
// the upstream reserved queue holds further beats. Acknowledgement, not request
// acceptance, releases the transaction. Command layout is immutable until clear.
// clear/global reset require transport quiescence; never clear an unacked write.
// Ordered lane-local addresses are checked against the command schedule. Object
// offsets use logical element strides, independent of padded execution width.
module ot_a3_output_object_writer #(
 parameter integer LANES=8
)(
 input wire clk,rst_n,clear,
 input wire command_valid,
 output wire command_ready,
 input wire [31:0] command_generation,command_object,command_element_base,
 input wire [31:0] command_row_stride,command_col_stride,
 input wire [15:0] command_rows,command_cols,command_padded_cols,
 input wire command_fp32,
 input wire [63:0] command_object_bytes,
 input wire part_valid,
 output wire part_ready,
 input wire [LANES-1:0] part_mask,
 input wire [32*LANES-1:0] part_address,part_data,
 output wire write_valid,
 input wire write_ready,
 output reg [31:0] write_generation,write_object,
 output reg [LANES-1:0] write_mask,
 output reg [64*LANES-1:0] write_offset,
 output reg [32*LANES-1:0] write_data,
 output reg write_fp32,
 input wire response_valid,
 output wire response_ready,
 input wire [31:0] response_generation,
 input wire response_error,
 output wire drained,
 output reg protocol_error
);
 localparam [1:0] IDLE=0,CHECK=1,SEND=2,WAIT_ACK=3;
 reg [1:0] state;
 reg active;
 reg [31:0] expected_address;
 reg [15:0] rows_left,cols_left,local_cols;
 // rows/cols are 16 bits and element strides/base are 32 bits. Even
 // base+(rows-1)*row_stride+(cols-1)*col_stride, scaled by four,
 // is below 2^51. Steps themselves need only 34 bits.
 reg [50:0] row_offset,cursor_offset;
 reg [33:0] row_step,col_step;
 reg [63:0] object_bytes;
 reg [LANES-1:0] tail_mask;
 reg beat_invalid;
 wire enabled=rst_n && !clear;
 assign command_ready=enabled && !active && state==IDLE;
 // After fault, consume queued results without publishing new writes so the
 // parent can abort and drain. An already published request must still finish.
 assign part_ready=enabled && active && state==IDLE;
 assign write_valid=enabled && state==SEND;
 assign response_ready=enabled && state==WAIT_ACK;
 assign drained=state==IDLE;
 wire accept_part=part_valid && part_ready;
 wire [LANES-1:0] expected_mask=cols_left==1?tail_mask:{LANES{1'b1}};
 wire [63:0] element_bytes=write_fp32?64'd4:64'd2;
 integer lane;
 reg invalid_input,invalid_bounds;
 always @* begin
  invalid_input=(rows_left==0 || part_mask!=expected_mask);
  invalid_bounds=0;
  for(integer i=0;i<LANES;i=i+1)begin
   if(part_mask[i] && part_address[32*i+:32]!=expected_address)invalid_input=1;
   if(write_mask[i] && ({1'b0,write_offset[64*i+:64]}+{1'b0,element_bytes})>{1'b0,object_bytes})
    invalid_bounds=1;
  end
 end
 // Payload has no reset fanout. Every published beat follows command capture
 // and an accepted input beat. Geometry bounds keep all offset sums below 2^51.
 always @(posedge clk)begin
  if(!active)begin
   write_generation<=command_generation;write_object<=command_object;
   write_fp32<=command_fp32;object_bytes<=command_object_bytes;
   expected_address<=command_element_base;
   row_offset<={19'b0,command_element_base}<<(command_fp32?2:1);
   cursor_offset<={19'b0,command_element_base}<<(command_fp32?2:1);
   row_step<={2'b0,command_row_stride}<<(command_fp32?2:1);
   col_step<={2'b0,command_col_stride}<<(command_fp32?2:1);
   rows_left<=command_rows;local_cols<=command_padded_cols/LANES;
   cols_left<=command_padded_cols/LANES;
   for(lane=0;lane<LANES;lane=lane+1)
    tail_mask[lane]<=command_cols%LANES==0 || lane<command_cols%LANES;
  end
  // Capture invalid payload freely while idle. State alone owns publication;
  // remove reset/ready/error fanout from the wide data and offset register bank.
  if(state==IDLE)begin
   write_mask<=part_mask;write_data<=part_data;beat_invalid<=invalid_input;
   for(lane=0;lane<LANES;lane=lane+1)
    write_offset[64*lane+:64]<={13'b0,(cursor_offset+51'(col_step)*51'(lane))};
  end
  if(accept_part && !protocol_error)begin
   expected_address<=expected_address+1'b1;
   if(cols_left==1)begin
    rows_left<=rows_left-1'b1;cols_left<=local_cols;
    row_offset<=row_offset+row_step;cursor_offset<=row_offset+row_step;
   end else begin
    cols_left<=cols_left-1'b1;cursor_offset<=cursor_offset+51'(col_step)*51'(LANES);
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;active<=0;protocol_error<=0;end
  else if(clear)begin state<=IDLE;active<=0;protocol_error<=0;end
  else begin
   if(command_valid && command_ready)begin
    active<=1;
    if(command_rows==0 || command_cols==0 || command_padded_cols==0 ||
       command_padded_cols%LANES!=0 || command_cols>command_padded_cols ||
       {16'b0,command_padded_cols}-{16'b0,command_cols}>=LANES ||
       ({1'b0,command_element_base}+33'(command_rows)*33'(command_padded_cols/LANES))>33'h100000000)
     protocol_error<=1;
   end
   case(state)
    IDLE:if(accept_part && !protocol_error)state<=CHECK;
    CHECK:if(beat_invalid || invalid_bounds)begin protocol_error<=1;state<=IDLE;end
          else state<=SEND;
    SEND:if(write_ready)state<=WAIT_ACK;
    WAIT_ACK:if(response_valid)begin
     if(response_generation!=write_generation)protocol_error<=1;
     else begin
      if(response_error)protocol_error<=1;
      state<=IDLE;
     end
    end
   endcase
  end
 end
 generate if(LANES<1 || LANES>64 || (LANES&(LANES-1))!=0)begin : bad_lanes
  initial $error("LANES must be a power of two in 1..64");
 end endgenerate
endmodule
