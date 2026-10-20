`timescale 1ns/1ps
// Actual programme producer composition. issue captures independently compiled
// control data and authoritative HOST identity, then the source-native native59
// descriptor producer drives controller load one edge later. run is independently
// compiler scheduled after guard acceptance (at least 4 edges after issue).
// No programme or arithmetic is generated from link payloads or reference code.
// KV-ATTNKIT 10-18: LAND=1 (die knob OT_KV_ATTN_LAND) = qkd_native_attention_static_ctl LAND=1 (landed RX codec, TX
// launch flops: +1 edge on K.tx_record) and prg_l = the die prg word {q_data, q_beat, q_valid, request_position,
// request_valid} through a launch flop (+1 edge on ks_prg; request_valid is fault-gated combinationally, so the
// unlaunched word left the tile through logic).  LAND=0: prg_l is that word unregistered (= the generated tile's prg).
module qkd_native_attention_programme #(parameter integer MUT=0,parameter integer LAND=0,parameter integer RETIRE_STATIC=0)(
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
 output wire busy,output wire fault,output wire [15:0] age,
 output wire [536:0] prg_l
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
 generate if(LAND!=0)begin:g_pld
 qkd_native59_descriptor_producer_ld producer(.ck(ck),.rst_n(rst_n),.issue(issue),
  .authority_valid(authority_valid),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_stage(authority_stage),
  .descriptor_valid(load),.descriptor(command),.tag(command_tag),.fault(producer_fault));
 end else begin:g_pcd
 qkd_native59_descriptor_producer producer(.ck(ck),.rst_n(rst_n),.issue(issue),
  .authority_valid(authority_valid),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_stage(authority_stage),
  .descriptor_valid(load),.descriptor(command),.tag(command_tag),.fault(producer_fault));
 end endgenerate
 qkd_native_attention_static_ctl #(.MUT(MUT),.LAND(LAND),.RETIRE_STATIC(RETIRE_STATIC)) ctl(
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
 wire [536:0] prg_w={q_data,q_beat,q_valid,request_position,request_valid};
 generate if(LAND!=0)begin:g_prg
  reg prg_rv,prg_qv;reg [535:0] prg_d;
  always @(posedge ck or negedge rst_n)if(!rst_n)begin prg_rv<=0;prg_qv<=0;end else begin prg_rv<=request_valid;prg_qv<=q_valid;end
  always @(posedge ck)prg_d<=prg_w[536:1];
  assign prg_l={prg_d[535:19],prg_qv,prg_d[17:0],prg_rv};
 end else begin:g_prgc
  assign prg_l=prg_w;
 end endgenerate
endmodule

// KV-ATTNKIT 10-18: qkd_native59_descriptor_producer with the authority check behind its pin flops (programme LAND=1; gate
// g2: i_ctl authority_token -> tag capture enable 7 levels, 56 endpoints).  The original checks authority_valid / token /
// position / stage on the pins and uses the result as the capture enable of tag / descriptor.  Here the authority pins
// land in plain flops with the issue edge, tag / descriptor load on issue & !fault, and the check runs on the landed copy:
//   descriptor_valid = iss_l & !bad_l,  fault = f_r | (iss_l & bad_l)
// = the original's outputs edge for edge; tag / descriptor differ only on a faulting issue (then fault holds, no load).
module qkd_native59_descriptor_producer_ld(
 input wire ck,rst_n,issue,authority_valid,
 input wire [15:0] authority_epoch,
 input wire [17:0] authority_token,authority_position,
 input wire [5:0] authority_stage,
 output wire descriptor_valid,output reg [379:0] descriptor,
 output reg [58:0] tag,output wire fault
);
 localparam [379:0] NATIVE59={24'd0,1'b0,1'b0,1'b1,1'b1,
 24'd1,24'd1,24'd3167,1'b0,24'd0,4'd0,3'd0,
 24'd0,24'd0,24'd1,24'd13696,24'd0,24'd0,24'd0,24'd0,
 1'b1,18'd128,18'd1,18'd512,1'b1};
 reg iss_l,f_r,av_l;reg [17:0] tok_l,pos_l;reg [5:0] st_l;
 wire bad_l=!av_l||tok_l>=151936||pos_l>=8192||st_l<1||st_l>36;
 assign descriptor_valid=iss_l&&!bad_l;
 assign fault=f_r||(iss_l&&bad_l);
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin iss_l<=0;f_r<=0;descriptor<=0;tag<=0;end
  else begin
   iss_l<=issue&&!fault;f_r<=fault;
   if(issue&&!fault)begin descriptor<=NATIVE59;tag<={authority_epoch,authority_stage,authority_token,authority_position[12:0],6'd0};end
  end
 always @(posedge ck)begin av_l<=authority_valid;tok_l<=authority_token;pos_l<=authority_position;st_l<=authority_stage;end
endmodule
