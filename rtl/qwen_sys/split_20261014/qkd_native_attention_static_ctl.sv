`timescale 1ns/1ps
// One compiler-loaded operation. No queue, ready-based issue, runtime credits,
// local epoch allocation, compute or memory emulation. Link codec and native59
// guard are actual source instances. The service pins must bind to the actual
// w16 native service; this module cannot supply missing arithmetic/memory.
// Timing: run edge is age 0. RX CMD at age RX_CMD; Q at RX_CMD+1..+32.
// Codec CMD appears one edge later. Q has one additional register so service
// samples Q beat0 two edges after request, as its start_qk/q_window require.
// RESULT age TX_FIRST..+31 and idle +32, STATUS +33 are TX codec input events.
module qkd_native_attention_static_ctl #(
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire load,run,
 input wire [379:0] command,
 input wire [58:0] command_tag,
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
 output reg q_valid,output reg [4:0] q_beat,output reg [511:0] q_data,
 input wire result_valid,input wire [4:0] result_beat,input wire [511:0] result_data,
 input wire [15:0] result_epoch,input wire [5:0] result_layer,
 input wire result_done,service_fault,
 output wire result_reserved,
 output reg busy,output wire fault,output reg [15:0] age
);
 wire accepted,guard_fault;wire [379:0] ac;wire [58:0] at;
 wire [17:0] pos;wire [15:0] ep;wire [5:0] layer;
 qkd_native59_command_guard guard(.ck(ck),.rst_n(rst_n),.command_valid(load),
  .command(command),.command_tag(command_tag),.fused_program_capability(fused_program_capability),
  .authority_valid(authority_valid),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_stage(authority_stage),.accepted(accepted),
  .accepted_command(ac),.accepted_tag(at),.native_xbase(),.native_obase(),.native_nout(),.native_k(),
  .native_position(pos),.native_epoch(ep),.native_layer(layer),.fault(guard_fault),.fault_cause());
 reg loaded,local_fault,loading;reg [175:0] cal;
 reg [15:0] rx_cmd,tx_first,last;
 // Guard consumes the registered descriptor one edge after load. Keep the
 // compiled values with that descriptor, independently of link record fields.
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;loading<=0;local_fault<=0;busy<=0;age<=0;cal<=0;rx_cmd<=0;tx_first<=0;last<=0;end
  else begin
   if(load)begin
    if(busy||loading||loaded||compiled_rx_cmd<2||compiled_tx_first<=compiled_rx_cmd+34||compiled_end!=compiled_tx_first+34)
     local_fault<=1;
    cal<=compiled_calendar;rx_cmd<=compiled_rx_cmd;tx_first<=compiled_tx_first;last<=compiled_end;
    loading<=1;
   end
   if(accepted)begin loaded<=1;loading<=0;end
   if(run)begin
    if(!loaded||busy||fault)local_fault<=1;
    else begin busy<=1;age<=0;loaded<=0;end
   end else if(busy)begin
    age<=age+1'b1;
    if(age==last)busy<=0;
   end
   if(request_valid&&!request_ready)local_fault<=1;
   if(rx_valid&&rx_kind==1&&rx_data!={493'd0,5'd0,pos[12:0],1'b1})local_fault<=1;
   if(result_valid!=result_reserved)local_fault<=1;
   if(result_valid&&({result_epoch,result_layer,result_beat}!={ep,layer,result_expected_beat}))local_fault<=1;
   if(result_done!=(busy&&age==tx_first+32))local_fault<=1;
  end
 end
 wire [4:0] result_expected_beat=age-tx_first;
 wire rx_expected=busy&&(age>=rx_cmd)&&(age<=rx_cmd+32);
 wire [3:0] rx_kind_expected=(age==rx_cmd)?4'd1:4'd2;
 wire [4:0] rb=age-rx_cmd-1;
 wire tx_expected=result_reserved||status_slot;
 wire status_slot=busy&&age==tx_first+33;
 assign result_reserved=busy&&age>=tx_first&&age<tx_first+32;
 wire rx_valid;wire [3:0] rx_kind;wire [4:0] rx_beat;wire [511:0] rx_data;wire record_fault;wire codec_tx_valid;
 wire [511:0] tx_data=status_slot?512'd0:result_data;
 qkd_native_attention_record codec(.ck(ck),.rst_n(rst_n),
  .tx_event(result_valid||status_slot),.tx_expected(tx_expected),.tx_kind(status_slot?4'd4:4'd3),
  .tx_expected_kind(status_slot?4'd4:4'd3),.tx_epoch(ep),.tx_expected_epoch(ep),
  .tx_layer(layer),.tx_expected_layer(layer),.tx_beat(status_slot?5'd0:result_beat),
  .tx_expected_beat(status_slot?5'd0:result_expected_beat),.tx_data(tx_data),.tx_valid(codec_tx_valid),.tx_payload(tx_payload),
  .rx_event(rx_event),.rx_expected(MUT==1?rx_event:rx_expected),.rx_payload(rx_payload),
  .rx_expected_kind(rx_kind_expected),.rx_expected_epoch(ep),.rx_expected_layer(layer),
  .rx_expected_beat(age==rx_cmd?5'd0:rb),.rx_valid(rx_valid),.rx_kind(rx_kind),
  .rx_epoch(),.rx_layer(),.rx_beat(rx_beat),.rx_data(rx_data),.fault(record_fault),.fault_cause());
 reg slot_fault;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin q_valid<=0;q_beat<=0;q_data<=0;slot_fault<=0;end
  else begin
   q_valid<=!fault&&rx_valid&&rx_kind==2;q_beat<=rx_beat;q_data<=rx_data;
   if(tx_slot!=tx_expected||(tx_slot&&{tx_slot_kind,tx_slot_beat}!={status_slot?4'd4:4'd3,status_slot?5'd0:result_expected_beat}))slot_fault<=1;
  end
 end
 assign tx_valid=codec_tx_valid&&!fault;
 assign request_valid=rx_valid&&rx_kind==1&&!fault;
 assign request_epoch=ep;assign request_layer=layer;assign request_position=pos;assign request_calendar=cal;
 assign fault=local_fault||guard_fault||record_fault||slot_fault||service_fault;
endmodule
