`timescale 1ns/1ps
// Enclosing descriptor seat. CP remains the owner; this module cannot grant a
// shared seat, invent a producer result, or truncate a transaction identity.
// Root POR only. Warm requests block enrollment/start while existing work drains.
module ot_hbm_integrated_stage_join #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire enroll_v,output wire enroll_r,
 input wire [72:0] enroll_frame,input wire [31:0] enroll_pc,enroll_op,
 input wire [15:0] enroll_source,input wire [8:0] enroll_expert,
 input wire enroll_matrix,input wire [11:0] enroll_row,input wire [8:0] enroll_count,
 input wire owner_valid,input wire [72:0] owner_frame,input wire source_permit,
 output wire start_v,input wire start_r,
 input wire finish_v,output wire finish_r,
 input wire producer_drained,consumer_drained,
 output wire complete_v,input wire complete_r,
 input wire warm_req,output wire warm_ack,
 output wire retained,issued,ce,due,fault,
 output wire [72:0] held_frame,output wire [31:0] held_pc,held_op,
 output wire [15:0] held_source,output wire [8:0] held_expert,
 output wire held_matrix,output wire [11:0] held_row,output wire [8:0] held_count
);
 generate if(!ENABLE)begin:g_off
  assign enroll_r=0;assign start_v=0;assign finish_r=0;assign complete_v=0;
  assign warm_ack=0;assign retained=0;assign issued=0;assign ce=0;assign due=0;assign fault=0;
  assign held_frame=0;assign held_pc=0;assign held_op=0;assign held_source=0;
  assign held_expert=0;assign held_matrix=0;assign held_row=0;assign held_count=0;
 end else begin:g_on
  localparam [1:0] EMPTY=0,READY=1,RUNNING=2,COMPLETE=3;
  wire [187:0] data;reg [187:0] next_data;
  wire good;wire [1:0] phase=data[185:184];
  wire quarantine=data[186],sticky_fault=data[187];
  wire drained=producer_drained&&consumer_drained;
  wire owner_match=owner_valid&&owner_frame==data[72:0];
  wire live_bad=phase!=EMPTY&&!owner_match;
  wire shape_bad=enroll_count==0||({1'b0,enroll_row}+enroll_count)>13'd4096;
  wire malformed=enroll_v&&phase==EMPTY&&!quarantine&&!warm_req&&shape_bad;
  assign fault=due||sticky_fault||live_bad||malformed;
  assign retained=phase!=EMPTY||!good||sticky_fault;
  assign issued=good&&!fault&&(phase==RUNNING||phase==COMPLETE);
  assign enroll_r=good&&!fault&&phase==EMPTY&&!quarantine&&!warm_req&&drained;
  assign start_v=good&&!fault&&phase==READY&&!quarantine&&!warm_req&&source_permit&&owner_match;
  // Warm does not cancel an accepted producer or erase its drain/completion debt.
  assign finish_r=good&&!fault&&phase==RUNNING&&owner_match&&drained;
  assign complete_v=good&&!fault&&phase==COMPLETE&&owner_match&&drained;
  assign warm_ack=good&&!fault&&quarantine&&phase==EMPTY&&drained;
  assign held_frame=data[72:0];assign held_pc=data[104:73];assign held_op=data[136:105];
  assign held_source=data[152:137];assign held_expert=data[161:153];
  assign held_matrix=data[162];assign held_row=data[174:163];assign held_count=data[183:175];
  always @*begin
   next_data=data;
   if(warm_req)next_data[186]=1;
   else if(phase==EMPTY)next_data[186]=0;
   if(live_bad||malformed)next_data[187]=1;
   if(enroll_v&&enroll_r)begin
    next_data[183:0]={enroll_count,enroll_row,enroll_matrix,enroll_expert,
                     enroll_source,enroll_op,enroll_pc,enroll_frame};
    next_data[185:184]=READY;
   end
   if(start_v&&start_r)next_data[185:184]=RUNNING;
   if(finish_v&&finish_r)next_data[185:184]=COMPLETE;
   if(complete_v&&complete_r)next_data[185:184]=EMPTY;
  end
  ot_hbm_accel_gu_metadata #(.WIDTH(188)) descriptor(
   .clk(clk),.rst_n(por_n),.we(good&&next_data!=data),.next_data(next_data),
   .data(data),.good(good),.ce(ce),.due(due));
 end endgenerate
endmodule
