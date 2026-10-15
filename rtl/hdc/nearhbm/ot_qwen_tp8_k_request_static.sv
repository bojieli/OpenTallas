`timescale 1ns/1ps
// Compiled K transport: exactly one register to the request face, then exactly
// RETURN_LATENCY clocks from request face to return. Readiness is an assertion
// input only; it never postpones an issue or retains a request for retry.
// Pipeline occupancy is a timing check, not a credit count or allocator.
module ot_qwen_tp8_k_request_static #(
 parameter integer RETURN_LATENCY=16
) (
 input wire clk,rst_n,start,input wire [15:0] epoch,input wire [5:0] layer,
 input wire raw_valid,input wire [12:0] raw_t,input wire raw_wrong_type,
 output wire req_valid,input wire req_ready,output wire [12:0] req_t,
 input wire rsp_valid,input wire [12:0] rsp_t,input wire [15:0] rsp_epoch,input wire [5:0] rsp_layer,
 output wire checked_rsp,output reg fault,output reg [31:0] accepted
);
 reg active;
 reg face_valid;
 reg [12:0] face_t;
 reg [RETURN_LATENCY-1:0] expected_valid;
 reg [12:0] expected_t[0:RETURN_LATENCY-1];
 wire expected=expected_valid[RETURN_LATENCY-1];
 wire good=active && expected && rsp_t==expected_t[RETURN_LATENCY-1]
              && rsp_epoch==epoch && rsp_layer==layer;
 assign req_valid=active && face_valid && !fault;
 assign req_t=face_t;
 assign checked_rsp=rsp_valid && good && !fault;
 integer i;
 initial begin
  if(RETURN_LATENCY<1)$fatal(1,"K return latency must be positive");
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active<=0;face_valid<=0;face_t<=0;expected_valid<=0;fault<=0;accepted<=0;
   for(i=0;i<RETURN_LATENCY;i=i+1)expected_t[i]<=0;
  end else if(start)begin
   if(face_valid || (|expected_valid) || raw_valid || rsp_valid)fault<=1;
   else begin active<=1;face_valid<=0;expected_valid<=0;accepted<=0;end
  end else begin
   face_valid<=raw_valid && active;
   face_t<=raw_t;
   expected_valid[0]<=req_valid;
   expected_t[0]<=req_t;
   for(i=1;i<RETURN_LATENCY;i=i+1)begin
    expected_valid[i]<=expected_valid[i-1];expected_t[i]<=expected_t[i-1];
   end
   if(raw_valid && (!active || raw_wrong_type))fault<=1;
   if(req_valid && !req_ready)fault<=1;
   if(rsp_valid!=expected || (rsp_valid && !good))fault<=1;
   if(checked_rsp)accepted<=accepted+1'b1;
  end
 end
endmodule
