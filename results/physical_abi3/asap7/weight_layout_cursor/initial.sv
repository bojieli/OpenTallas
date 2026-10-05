`timescale 1ns/1ps
// Descriptor-relative weight coordinates in LQ8 issue order. This is a layout
// cursor, not a memory service: a downstream gather/assembly stage must check
// object permissions/capacity, convert dtype elements to bytes/bits and retain
// response ownership. No memory request is authorized by this module alone.
// Walk: output row, INTERLEAVE column groups, K, column group. Each group has
// eight lanes. Tail lanes are masked; the next row replays the same weights.
// Admission checks element-address overflow before publishing any coordinate.
module ot_a3_weight_layout_cursor #(
 parameter integer INTERLEAVE=3
)(
 input wire clk,rst_n,clear,
 input wire command_valid, output wire command_ready,
 input wire [31:0] command_generation,
 input wire [15:0] command_rows,command_cols,command_depth,
 input wire [63:0] command_element_base,
 input wire [31:0] command_column_stride,command_k_stride,
 output wire coordinate_valid,input wire coordinate_ready,
 output reg [31:0] generation,
 output reg [63:0] element_base,
 output reg [31:0] lane_stride,
 output wire [7:0] lane_mask,
 output reg [15:0] row_index,column_base,k_index,
 output wire last,
 output reg command_error
);
 localparam integer CW=INTERLEAVE<2?1:$clog2(INTERLEAVE);
 localparam [2:0] IDLE=0,EXTENT=1,BOUND=2,CHECK=3,RUN=4;
 reg [2:0] state;
 reg [15:0] rows,cols,depth,groups_left,groups_total;
 reg [CW-1:0] column_in_pass;
 reg [63:0] origin,pass_base,k_base;
 reg [34:0] group_step;
 reg [63:0] pass_step;
 reg [31:0] k_step;
 reg [47:0] column_extent,k_extent;
 reg [48:0] extent;
 reg [64:0] bound;
 wire [15:0] pass_groups=groups_left<16'(INTERLEAVE)?groups_left:16'(INTERLEAVE);
 wire end_column=16'(column_in_pass)==pass_groups-1'b1;
 wire end_k=k_index==depth-1'b1;
 wire end_pass=groups_left<=16'(INTERLEAVE);
 wire take=coordinate_valid && coordinate_ready;
 assign command_ready=rst_n && !clear && state==IDLE && !command_error;
 assign coordinate_valid=rst_n && !clear && state==RUN && !command_error;
 assign last=end_column && end_k && end_pass && row_index==rows-1'b1;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:g_mask
  assign lane_mask[l]=({1'b0,column_base}+17'(l))<{1'b0,cols};
 end endgenerate
 initial if(INTERLEAVE<1 || INTERLEAVE>65535)$fatal(1,"invalid interleave");
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;command_error<=0;end
  else if(clear)begin state<=IDLE;command_error<=0;end
  else case(state)
   IDLE:if(command_valid && command_ready)begin
    if(command_rows==0 || command_cols==0 || command_depth==0)command_error<=1;
    else state<=EXTENT;
   end
   EXTENT:state<=BOUND;
   BOUND:state<=CHECK;
   CHECK:if(bound[64])begin command_error<=1;state<=IDLE;end else state<=RUN;
   RUN:if(take && last)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
 // Payload has local ownership through state; reset/clear does not fan out to
 // address registers. Multiplication is confined to command admission.
 always @(posedge clk)begin
  if(command_valid && command_ready)begin
   generation<=command_generation;rows<=command_rows;cols<=command_cols;depth<=command_depth;
   origin<=command_element_base;pass_base<=command_element_base;k_base<=command_element_base;
   element_base<=command_element_base;lane_stride<=command_column_stride;k_step<=command_k_stride;
   group_step<={command_column_stride,3'b0};
   pass_step<=64'(command_column_stride)*64'(8*INTERLEAVE);
   groups_total<=16'(({1'b0,command_cols}+17'd7)>>3);
   groups_left<=16'(({1'b0,command_cols}+17'd7)>>3);
   row_index<=0;column_base<=0;k_index<=0;column_in_pass<=0;
   column_extent<=48'(command_cols-16'd1)*48'(command_column_stride);
   k_extent<=48'(command_depth-16'd1)*48'(command_k_stride);
  end
  if(state==EXTENT)extent<={1'b0,column_extent}+{1'b0,k_extent};
  if(state==BOUND)bound<={1'b0,origin}+{16'd0,extent};
  if(take && !last)begin
   if(!end_column)begin
    column_in_pass<=column_in_pass+1'b1;column_base<=column_base+16'd8;
    element_base<=element_base+{29'd0,group_step};
   end else begin
    column_in_pass<=0;
    if(!end_k)begin
     k_index<=k_index+1'b1;k_base<=k_base+{32'd0,k_step};
     element_base<=k_base+{32'd0,k_step};
     column_base<=column_base-(16'(column_in_pass)<<3);
    end else begin
     k_index<=0;
     if(end_pass)begin
      row_index<=row_index+1'b1;column_base<=0;groups_left<=groups_total;
      pass_base<=origin;k_base<=origin;element_base<=origin;
     end else begin
      column_base<=column_base+16'd8;groups_left<=groups_left-16'(INTERLEAVE);
      pass_base<=pass_base+pass_step;k_base<=pass_base+pass_step;element_base<=pass_base+pass_step;
     end
    end
   end
  end
 end
endmodule
