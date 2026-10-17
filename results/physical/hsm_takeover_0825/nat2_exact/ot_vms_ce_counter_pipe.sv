`timescale 1ns/1ps
`default_nettype none
// Exact saturating count with a registered carry crossing the low/high boundary.
// An event sampled at edge n is visible in count after n+1 (one status-only edge).
// Consecutive events are accepted every edge. No data/calendar/response signals enter.
module ot_vms_ce_counter_pipe #(parameter integer MUT=0)(
 input wire clk,rst_n,event_v,input wire [3:0] event_count,output wire [15:0] count);
 reg [3:0] low,low_aligned;
 reg carry_q,saturated;
 reg [11:0] upper;
 wire [4:0] low_sum={1'b0,low}+{1'b0,(event_v?event_count:4'd0)};
 wire carry_effective=MUT==1?1'b0:carry_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin low<=0;low_aligned<=0;carry_q<=0;upper<=0;saturated<=0;end
  else begin
   low<=low_sum[3:0];carry_q<=low_sum[4];low_aligned<=low;
   if(carry_effective)begin
    upper<=upper+12'd1;
    if(&upper)saturated<=1'b1;
   end
  end
 assign count=saturated?16'hffff:{upper,low_aligned};
endmodule
`default_nettype wire
