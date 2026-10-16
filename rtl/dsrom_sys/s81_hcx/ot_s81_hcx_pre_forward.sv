`timescale 1ns/1ps
`default_nettype none
// HC pre coefficients belong to the NEXT block. The current block's NORM
// consumes the pending pre from its predecessor (golden hc_pre semantics).
// Keep the native tail's current post/comb and its exact write calendar; replace
// only the pre quartet in its first coefficient packet with the carried quartet.
// The native computed quartet advances at the compiler's fixed done edge.
// Incoming/outgoing are actual layer-boundary data ports, never a golden result
// substitution. The full token must wire them through its real stage handoff.
// Storage: 3 x 128 bits plus control (pending, next, outgoing). Added VM traffic/cycles: zero.
module ot_s81_hcx_pre_forward #(parameter integer MUT_CURRENT_PRE=0)(
 input wire clk,rst_n,
 input wire incoming_v,input wire [127:0] incoming_pre,
 input wire start,done,input wire [13:0] coef_base_row,
 input wire i_v,input wire [13:0] i_row,input wire [15:0] i_mask,input wire [511:0] i_data,
 output wire [511:0] o_data,
 output reg outgoing_v,output reg [127:0] outgoing_pre,
 output reg fault
);
 reg [127:0] pending_pre,next_pre;
 reg pending_valid,busy,next_valid;
 reg [13:0] base;
 wire pre_packet=i_v && i_row==base+14'd1 && |i_mask[3:0];
 assign o_data=(pre_packet && !MUT_CURRENT_PRE) ? {i_data[511:128],pending_pre} : i_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin pending_pre<=0;next_pre<=0;pending_valid<=0;busy<=0;next_valid<=0;outgoing_v<=0;outgoing_pre<=0;fault<=0;base<=0;end
  else begin
   outgoing_v<=0;
   if(incoming_v)begin
    if(busy || start || i_v || done)fault<=1;
    pending_pre<=incoming_pre;pending_valid<=1;
   end
   if(start)begin
    if(busy || !pending_valid || incoming_v)fault<=1;
    busy<=1;next_valid<=0;base<=coef_base_row;
   end
   if(pre_packet)begin
    if(!busy || !pending_valid || next_valid || i_mask[3:0]!=4'hf)fault<=1;
    next_pre<=i_data[127:0];next_valid<=1;
   end
   if(done)begin
    if(!busy || !next_valid || incoming_v || start || pre_packet)fault<=1;
    busy<=0;pending_pre<=next_pre;outgoing_pre<=next_pre;outgoing_v<=1;
   end
  end
 end
endmodule
`default_nettype wire
