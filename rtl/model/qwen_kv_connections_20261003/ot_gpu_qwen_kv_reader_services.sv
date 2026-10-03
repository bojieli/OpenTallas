`timescale 1ns/1ps
// Real source-issued SCORES/PV parent55 acceptance, native done and W6 reverse.
// One source-serialized operator credit. No arithmetic, elapsed completion,
// tag truncation or constructing a parent from the last emitted child.
// Each drain reply is an identified actual endpoint quiescence receipt.
module ot_gpu_qwen_kv_reader_services #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable,
 input wire operation_valid, output wire operation_ready,
 input wire [63:0] operation_identity, input wire [19:0] operation_key,
 input wire operation_stage, input wire [54:0] operation_owner,
 input wire native_done_valid, output wire native_done_ready,
 input wire [54:0] native_done_owner,
 input wire native_reverse_valid, output wire native_reverse_ready,
 input wire [54:0] native_reverse_owner,
 output wire consumer_valid, input wire consumer_ready,
 output wire [63:0] consumer_identity, output wire [19:0] consumer_key,
 output wire consumer_stage, consumer_accepted, consumer_reverse,
 input wire drain_valid, output wire drain_ready,
 input wire [63:0] drain_identity, input wire [19:0] drain_key,
 output wire drain_done_valid, input wire drain_done_ready,
 output wire [63:0] drain_done_identity, output wire [19:0] drain_done_key,
 output wire [7:0] drain_done_allcopies,
 //0stage,1payloadReq,2payloadReturn,3metadata,4RF/commonACK,5consumer,
 //6requestCDC,7reverseCDC. These are actual endpoint ports, never ready ties.
 output wire [7:0] endpoint_req_valid, input wire [7:0] endpoint_req_ready,
 output wire [63:0] endpoint_req_identity, output wire [19:0] endpoint_req_key,
 input wire [7:0] endpoint_rsp_valid, output wire [7:0] endpoint_rsp_ready,
 input wire [511:0] endpoint_rsp_identity, input wire [159:0] endpoint_rsp_key,
 input wire [7:0] endpoint_rsp_quiet,
 output reg fault, output wire drained
);
 reg operator_live, done_seen, reverse_seen, stage;
 reg [63:0] identity; reg [19:0] key; reg [54:0] owner;
 reg release_live; reg [63:0] release_identity; reg [19:0] release_key;
 reg [7:0] sent, replies;
 wire active=ENABLE && por_n && run_enable && !fault;
 assign operation_ready=active && !operator_live && !release_live;
 assign native_done_ready=active && operator_live && !done_seen;
 assign native_reverse_ready=active && operator_live && !reverse_seen;
 assign consumer_valid=active && operator_live && done_seen && reverse_seen;
 assign consumer_identity=identity; assign consumer_key=key; assign consumer_stage=stage;
 assign consumer_accepted=done_seen; assign consumer_reverse=reverse_seen;
 assign drain_ready=active && !operator_live && !release_live;
 assign endpoint_req_valid=active && release_live ? ~sent : 8'b0;
 assign endpoint_req_identity=release_identity; assign endpoint_req_key=release_key;
 assign endpoint_rsp_ready=active && release_live ? sent & ~replies : 8'b0;
 assign drain_done_valid=active && release_live && (&sent) && (&replies);
 assign drain_done_identity=release_identity; assign drain_done_key=release_key;
 assign drain_done_allcopies=replies;
 assign drained=!operator_live && !release_live;
 integer i;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin operator_live<=0; done_seen<=0; reverse_seen<=0;
   stage<=0; identity<=0; key<=0; owner<=0; release_live<=0;
   release_identity<=0; release_key<=0; sent<=0; replies<=0; fault<=0; end
  else if(active) begin
   if(operation_valid && operation_ready) begin
    operator_live<=1; done_seen<=0; reverse_seen<=0; identity<=operation_identity;
    key<=operation_key; owner<=operation_owner; stage<=operation_stage;
   end
   if(native_done_valid) begin
    if(!native_done_ready || native_done_owner!=owner) fault<=1;
    else done_seen<=1;
   end
   if(native_reverse_valid) begin
    if(!native_reverse_ready || native_reverse_owner!=owner || (!done_seen && !native_done_valid)) fault<=1;
    else reverse_seen<=1;
   end
   if(consumer_valid && consumer_ready) operator_live<=0;
   if(drain_valid && drain_ready) begin release_live<=1; release_identity<=drain_identity;
    release_key<=drain_key; sent<=0; replies<=0; end
   for(i=0;i<8;i=i+1) begin
    if(endpoint_req_valid[i] && endpoint_req_ready[i]) sent[i]<=1;
    if(endpoint_rsp_valid[i]) begin
     if(!endpoint_rsp_ready[i] || endpoint_rsp_identity[i*64+:64]!=release_identity
       || endpoint_rsp_key[i*20+:20]!=release_key || !endpoint_rsp_quiet[i]) fault<=1;
     else replies[i]<=1;
    end
   end
   if(drain_done_valid && drain_done_ready) release_live<=0;
  end
 end
endmodule
