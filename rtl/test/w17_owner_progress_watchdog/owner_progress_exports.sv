`timescale 1ns/1ps
// Simulation-only event counters; no DUT control/ready feedback.
module ot_w17_owner_progress_exports #(parameter bit ENABLED=0)(
 input wire clk,rst_n, su_retire, window_read_accept,window_return_accept,
 output wire [63:0] su_retired,window_accepted,window_returned
);
 generate if(ENABLED) begin:g_enabled
 reg[63:0] su_count,req_count,rsp_count;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin su_count<=0;req_count<=0;rsp_count<=0;end
  else begin
   su_count<=su_count+64'(su_retire);
   req_count<=req_count+64'(window_read_accept);
   rsp_count<=rsp_count+64'(window_return_accept);
  end
 assign su_retired=su_count;assign window_accepted=req_count;assign window_returned=rsp_count;
 end else begin:g_disabled
 assign su_retired=0;assign window_accepted=0;assign window_returned=0;
 end endgenerate
endmodule
