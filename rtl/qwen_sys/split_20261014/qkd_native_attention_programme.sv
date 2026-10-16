`timescale 1ns/1ps
// Actual programme producer composition. issue captures independently compiled
// control data and authoritative HOST identity, then the source-native native59
// descriptor producer drives controller load one edge later. run is independently
// compiler scheduled after guard acceptance (at least 4 edges after issue).
// No programme or arithmetic is generated from link payloads or reference code.
module qkd_native_attention_programme #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire issue,run,
 input wire fused_program_capability,authority_valid,
 input wire [15:0] authority_epoch,
 input wire [17:0] authority_token,authority_position,
 input wire [5:0] authority_stage,
 input wire [175:0] compiled_calendar,
 input wire [15:0] compiled_rx_cmd,compiled_tx_first,compiled_end,
 input wire rx_event,input wire [547:0] rx_payload,
 input wire tx_slot,input wire [3:0] tx_slot_kind,input wire [4:0] tx_slot_beat,
 output wire tx_valid,output wire [547:0] tx_payload,
 output wire request_valid,input wire request_ready,
 output wire [15:0] request_epoch,output wire [5:0] request_layer,
 output wire [17:0] request_position,output wire [175:0] request_calendar,
 output wire q_valid,output wire [4:0] q_beat,output wire [511:0] q_data,
 input wire result_valid,input wire [4:0] result_beat,input wire [511:0] result_data,
 input wire [15:0] result_epoch,input wire [5:0] result_layer,
 input wire result_done,service_fault,
 output wire result_reserved,
 output wire busy,output wire fault,output wire [15:0] age
);

 wire load,producer_fault,ctl_fault;
 wire [379:0] command;wire [58:0] command_tag;
 reg authority_valid_q,capability_q;
 reg [15:0] authority_epoch_q,rx_cmd_q,tx_first_q,end_q;
 reg [17:0] authority_token_q,authority_position_q;
 reg [5:0] authority_stage_q;reg [175:0] calendar_q;
 always @(posedge ck)if(issue)begin
  authority_valid_q<=authority_valid;authority_epoch_q<=authority_epoch;
  authority_token_q<=authority_token;authority_position_q<=authority_position;authority_stage_q<=authority_stage;
  capability_q<=fused_program_capability;calendar_q<=compiled_calendar;
  rx_cmd_q<=compiled_rx_cmd;tx_first_q<=compiled_tx_first;end_q<=compiled_end;
 end
 qkd_native59_descriptor_producer producer(.ck(ck),.rst_n(rst_n),.issue(issue),
  .authority_valid(authority_valid),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_stage(authority_stage),
  .descriptor_valid(load),.descriptor(command),.tag(command_tag),.fault(producer_fault));
 qkd_native_attention_static_ctl #(.MUT(MUT)) ctl(
  .load(load),.command(command),.command_tag(command_tag),.fault(ctl_fault),
  .ck(ck),
  .rst_n(rst_n),
  .run(run),
  .fused_program_capability(capability_q),
  .authority_valid(authority_valid_q),
  .authority_epoch(authority_epoch_q),
  .authority_token(authority_token_q),
  .authority_position(authority_position_q),
  .authority_stage(authority_stage_q),
  .compiled_calendar(calendar_q),
  .compiled_rx_cmd(rx_cmd_q),
  .compiled_tx_first(tx_first_q),
  .compiled_end(end_q),
  .rx_event(rx_event),
  .rx_payload(rx_payload),
  .tx_slot(tx_slot),
  .tx_slot_kind(tx_slot_kind),
  .tx_slot_beat(tx_slot_beat),
  .tx_valid(tx_valid),
  .tx_payload(tx_payload),
  .request_valid(request_valid),
  .request_ready(request_ready),
  .request_epoch(request_epoch),
  .request_layer(request_layer),
  .request_position(request_position),
  .request_calendar(request_calendar),
  .q_valid(q_valid),
  .q_beat(q_beat),
  .q_data(q_data),
  .result_valid(result_valid),
  .result_beat(result_beat),
  .result_data(result_data),
  .result_epoch(result_epoch),
  .result_layer(result_layer),
  .result_done(result_done),
  .service_fault(service_fault|producer_fault),
  .result_reserved(result_reserved),
  .busy(busy),
  .age(age));
 assign fault=ctl_fault|producer_fault;
endmodule
