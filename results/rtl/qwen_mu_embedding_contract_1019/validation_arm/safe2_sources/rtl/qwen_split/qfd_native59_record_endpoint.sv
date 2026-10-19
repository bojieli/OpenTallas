`timescale 1ns/1ps
// Actual native548 compute endpoint: each Q is injected once, directly into
// the typed codec. Historical x3 Q is not a second attention-service source.
// operation_tag is captured at the actual accepted CMD, held through all
// returned results/done. Epoch/layer/beat are checked before restoring TAG59.
module qfd_native59_record_endpoint #(parameter integer CODEC_MUT=0)(
 input wire ck,rst_n,
 input wire [58:0] operation_tag,
 input wire kernel_request_v,input wire [58:0] kernel_request_tag,
 input wire kernel_q_v,input wire [4:0] kernel_q_beat,input wire [58:0] kernel_q_tag,
 input wire [511:0] kernel_q_data,
 input wire tx_slot,input wire [3:0] tx_slot_kind,input wire [4:0] tx_slot_beat,
 output wire tx_valid,output wire [547:0] tx_payload,
 input wire rx_event,input wire [547:0] rx_payload,
 input wire rx_slot,input wire [3:0] rx_slot_kind,input wire [4:0] rx_slot_beat,
 output wire result_v,output wire [4:0] result_beat,output wire [58:0] result_tag,
 output wire [511:0] result_data,
 output reg result_slot,output reg [4:0] result_slot_beat,
 output wire kernel_done,output wire [58:0] kernel_done_tag,
 output wire fault
);
 wire request=kernel_request_v;
 wire [58:0] actual_tag=request?kernel_request_tag:kernel_q_tag;
 // Position is an18-bit count, zero-extended from the actual TAG59 position13.
 wire [511:0] cmd_data={493'd0,5'd0,kernel_request_tag[18:6],1'b1};
 wire rv;wire[3:0]rk;wire[15:0]re;wire[5:0]rl;wire[4:0]rb;wire[511:0]rd;
 wire codec_fault;wire[3:0]fault_cause;reg local_fault;
 qkd_native_attention_record #(.KV_SIDE(0),.MUT(CODEC_MUT))u_codec(
 .ck(ck),.rst_n(rst_n),.tx_event(kernel_request_v||kernel_q_v),.tx_expected(tx_slot),
 .tx_kind(request?4'd1:4'd2),.tx_expected_kind(tx_slot_kind),
 .tx_epoch(actual_tag[58:43]),.tx_expected_epoch(operation_tag[58:43]),
 .tx_layer(actual_tag[42:37]-6'd1),.tx_expected_layer(operation_tag[42:37]-6'd1),
 .tx_beat(request?5'd0:kernel_q_beat),.tx_expected_beat(tx_slot_beat),
 .tx_data(request?cmd_data:kernel_q_data),.tx_valid(tx_valid),.tx_payload(tx_payload),
 .rx_event(rx_event),.rx_expected(rx_slot),.rx_payload(rx_payload),.rx_expected_kind(rx_slot_kind),
 .rx_expected_epoch(operation_tag[58:43]),.rx_expected_layer(operation_tag[42:37]-6'd1),.rx_expected_beat(rx_slot_beat),
 .rx_valid(rv),.rx_kind(rk),.rx_epoch(re),.rx_layer(rl),.rx_beat(rb),.rx_data(rd),.fault(codec_fault),.fault_cause(fault_cause));
 assign result_v=rv&&rk==3;
 assign result_beat=rb;
 assign result_tag=operation_tag;
 assign result_data=rd;
 assign kernel_done=rv&&rk==4&&rd[3];
 assign kernel_done_tag=operation_tag;
 assign fault=codec_fault||local_fault||(rv&&rk==4&&rd[2]);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin result_slot<=0;result_slot_beat<=0;local_fault<=0;end
  else begin
   result_slot<=rx_slot&&rx_slot_kind==3;result_slot_beat<=rx_slot_beat;
   if(kernel_request_v&&kernel_q_v)local_fault<=1;
   if((kernel_request_v||kernel_q_v)&&actual_tag!=operation_tag)local_fault<=1;
  end
 end
endmodule
