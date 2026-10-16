`timescale 1ns/1ps
// Source-native typed static endpoint: actual programme controller + actual
// G3S2/HXK13 attention service. Every K/V boundary remains an explicit real
// memory-service port. No arithmetic, SRAM or link event is supplied internally
// by a model. Common-phase component composition; physical clocks/pins unbound.
module qkd_native_attention_endpoint #(
 parameter integer K_EXT=16,V_EXT=16,MUT=0,DMUT=0
)(
 input wire  ck,
 input wire  rst_n,
 input wire  issue,
 input wire  run,
 input wire  fused_program_capability,
 input wire  authority_valid,
 input wire [15:0] authority_epoch,
 input wire [17:0] authority_token,
 input wire [17:0] authority_position,
 input wire [5:0] authority_stage,
 input wire [175:0] compiled_calendar,
 input wire [15:0] compiled_rx_cmd,
 input wire [15:0] compiled_tx_first,
 input wire [15:0] compiled_end,
 input wire  rx_event,
 input wire [547:0] rx_payload,
 input wire  tx_slot,
 input wire [3:0] tx_slot_kind,
 input wire [4:0] tx_slot_beat,
 output wire  tx_valid,
 output wire [547:0] tx_payload,
 output wire  busy,
 output wire  fault,
 output wire [15:0] age,
 output wire [31:0] k_req_valid,input wire [31:0] k_req_ready,
 output wire [415:0] k_req_t,output wire [15:0] active_epoch,output wire [5:0] active_layer,
 input wire [31:0] k_rsp_valid,input wire [415:0] k_rsp_t,
 input wire [511:0] k_rsp_epoch,input wire [191:0] k_rsp_layer,input wire [32767:0] k_rsp_data,
 output wire [15:0] v_req_valid,input wire [15:0] v_req_ready,
 output wire [223:0] v_req_t,
 input wire [15:0] v_rsp_valid,output wire [15:0] v_rsp_ready,
 input wire [223:0] v_rsp_t,
 input wire [255:0] v_rsp_epoch,input wire [95:0] v_rsp_layer,input wire [16383:0] v_rsp_data

);
 wire  request_valid;
 wire  request_ready;
 wire [15:0] request_epoch;
 wire [5:0] request_layer;
 wire [17:0] request_position;
 wire [175:0] request_calendar;
 wire  q_valid;
 wire [4:0] q_beat;
 wire [511:0] q_data;
 wire  result_valid;
 wire [4:0] result_beat;
 wire [511:0] result_data;
 wire [15:0] result_epoch;
 wire [5:0] result_layer;
 wire  result_done;
 wire  service_fault;
 wire  result_reserved;
wire ctl_fault;wire [31:0] cycles,k_words,v_words;wire [15:0] service_fault_cause;
qkd_native_attention_programme #(.MUT(MUT)) programme(
 .ck(ck),
 .rst_n(rst_n),
 .issue(issue),
 .run(run),
 .fused_program_capability(fused_program_capability),
 .authority_valid(authority_valid),
 .authority_epoch(authority_epoch),
 .authority_token(authority_token),
 .authority_position(authority_position),
 .authority_stage(authority_stage),
 .compiled_calendar(compiled_calendar),
 .compiled_rx_cmd(compiled_rx_cmd),
 .compiled_tx_first(compiled_tx_first),
 .compiled_end(compiled_end),
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
 .service_fault(service_fault),
 .result_reserved(result_reserved),
 .busy(busy),
 .fault(ctl_fault),
 .age(age));
ot_qwen_tp8_attention_native_service_w16_g3s2 #(.K_EXT(K_EXT),.V_EXT(V_EXT),.QK_ISSUE_AGE(34),.DMUT(DMUT)) service(
 .clk(ck),.rst_n(rst_n),.request_valid(request_valid),.request_ready(request_ready),
 .request_epoch(request_epoch),.request_layer(request_layer),.request_position(request_position),
 // request_valid can assert only after native59 capability and independent HOST
 // authority have passed the actual guard. This is that validated certificate.
 .fused_program_capability(request_valid),.request_calendar(request_calendar),
 .q_valid(q_valid),.q_ready(),.q_beat(q_beat),.q_data(q_data),
 .k_req_valid(k_req_valid),.k_req_ready(k_req_ready),.k_req_t(k_req_t),.active_epoch(active_epoch),.active_layer(active_layer),
 .k_rsp_valid(k_rsp_valid),.k_rsp_t(k_rsp_t),.k_rsp_epoch(k_rsp_epoch),.k_rsp_layer(k_rsp_layer),.k_rsp_data(k_rsp_data),
 .v_req_valid(v_req_valid),.v_req_ready(v_req_ready),.v_req_t(v_req_t),
 .v_rsp_valid(v_rsp_valid),.v_rsp_ready(v_rsp_ready),.v_rsp_t(v_rsp_t),.v_rsp_epoch(v_rsp_epoch),.v_rsp_layer(v_rsp_layer),.v_rsp_data(v_rsp_data),
 .result_valid(result_valid),.result_ready(result_reserved),.result_beat(result_beat),.result_data(result_data),
 .result_epoch(result_epoch),.result_layer(result_layer),.result_done(result_done),.busy(),.fault(service_fault),
 .cycles(cycles),.k_words(k_words),.v_words(v_words),.fault_cause(service_fault_cause));
 assign fault=ctl_fault|service_fault;
endmodule
