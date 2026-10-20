`timescale 1ns/1ps
// Actual native548 compute endpoint: each Q is injected once, directly into
// the typed codec. Historical x3 Q is not a second attention-service source.
// operation_tag is captured at the actual accepted CMD, held through all
// returned results/done. Epoch/layer/beat are checked before restoring TAG59.
module qfd_native59_record_endpoint #(parameter integer CODEC_MUT=0,RX_FREE=0,TX_FREE=0,LOCAL32=0)(  // RX_FREE / TX_FREE: qkd_native_attention_record (QW-N59-4)
 input wire ck,rst_n,
 input wire [58:0] operation_tag,
 input wire kernel_request_v,input wire[23:0]kernel_request_pub,input wire [58:0] kernel_request_tag,
 input wire kernel_q_v,input wire [4:0] kernel_q_beat,input wire [58:0] kernel_q_tag,
 input wire [511:0] kernel_q_data,
 input wire tx_slot,input wire [3:0] tx_slot_kind,input wire [4:0] tx_slot_beat,
 output wire tx_valid,output wire [547:0] tx_payload,
 output wire tx_valid_pub,tx_valid_pub2,   // R3h/j: == tx_valid (LOCAL32 kept copies; else alias)
 input wire rx_event,input wire [547:0] rx_payload,
 input wire rx_slot,input wire [3:0] rx_slot_kind,input wire [4:0] rx_slot_beat,
 output wire result_v,output wire [4:0] result_beat,output wire [58:0] result_tag,
 output wire [511:0] result_data,
 input wire[9:0]rx_result_pub,slot_back_pub,
 output wire[75:0]result_slot_pub,
 output reg result_slot,output reg [4:0] result_slot_beat,
 output wire kernel_done,output wire [58:0] kernel_done_tag,
 output wire fault
);
 // Same original result_slot edge, independently kept per 8-bit service hold.
 generate if(LOCAL32)begin:g_result_pub
  for(genvar rc=0;rc<76;rc=rc+1)begin:g_copy
   (* keep = "true" *) reg q;
   always @(posedge ck or negedge rst_n)
    if(!rst_n)q<=0;else q<=rx_result_pub[rc/8]&&slot_back_pub[rc/8];
   assign result_slot_pub[rc]=q;
  end
 end else begin:g_result_alias
  assign result_slot_pub={76{result_slot}};
 end endgenerate
 wire request=kernel_request_v;
 // R3c (QW-CB16A0 10-20): the 512-bit tx_data and 59-bit tag selects use the service's kept same-edge request copies
 // (kernel_request_pub[c] == kernel_request_v on every edge): [21:0] 24-bit tx_data segments, [22]/[23] tag low/high.
 wire [58:0] actual_tag;
 assign actual_tag[29:0]=kernel_request_pub[22]?kernel_request_tag[29:0]:kernel_q_tag[29:0];
 assign actual_tag[58:30]=kernel_request_pub[23]?kernel_request_tag[58:30]:kernel_q_tag[58:30];
 // Position is an18-bit count, zero-extended from the actual TAG59 position13.
 wire [511:0] cmd_data={493'd0,5'd0,kernel_request_tag[18:6],1'b1};
 wire [511:0] tx_sel_data;
 for(genvar tb=0;tb<512;tb=tb+1)begin:g_txd
  assign tx_sel_data[tb]=kernel_request_pub[tb/24]?cmd_data[tb]:kernel_q_data[tb];
 end
 wire rv;wire[3:0]rk;wire[15:0]re;wire[5:0]rl;wire[4:0]rb;wire[511:0]rd;
 wire codec_fault;wire[3:0]fault_cause;reg local_fault;
 wire tx_valid_b,tx_valid_c;
 generate if(LOCAL32)begin:g_codec32
  qkd_native_attention_record_n59 #(.KV_SIDE(0),.MUT(CODEC_MUT),.RX_FREE(RX_FREE),.TX_FREE(TX_FREE))u_codec(
  .ck(ck),.rst_n(rst_n),.tx_event(kernel_request_v||kernel_q_v),.tx_expected(tx_slot),
  .tx_kind(request?4'd1:4'd2),.tx_expected_kind(tx_slot_kind),
  .tx_epoch(actual_tag[58:43]),.tx_expected_epoch(operation_tag[58:43]),
  .tx_layer(actual_tag[42:37]-6'd1),.tx_expected_layer(operation_tag[42:37]-6'd1),
  .tx_beat(request?5'd0:kernel_q_beat),.tx_expected_beat(tx_slot_beat),
  .tx_data(tx_sel_data),.tx_valid(tx_valid),.tx_payload(tx_payload),
  .rx_event(rx_event),.rx_expected(rx_slot),.rx_payload(rx_payload),.rx_expected_kind(rx_slot_kind),
  .rx_expected_epoch(operation_tag[58:43]),.rx_expected_layer(operation_tag[42:37]-6'd1),.rx_expected_beat(rx_slot_beat),
  .rx_valid(rv),.rx_kind(rk),.rx_epoch(re),.rx_layer(rl),.rx_beat(rb),.rx_data(rd),.fault(codec_fault),.fault_cause(fault_cause),.tx_valid_b(tx_valid_b),.tx_valid_c(tx_valid_c));
  assign tx_valid_pub=tx_valid_b;assign tx_valid_pub2=tx_valid_c;
 end else begin:g_codec
  qkd_native_attention_record #(.KV_SIDE(0),.MUT(CODEC_MUT),.RX_FREE(RX_FREE),.TX_FREE(TX_FREE))u_codec(
  .ck(ck),.rst_n(rst_n),.tx_event(kernel_request_v||kernel_q_v),.tx_expected(tx_slot),
  .tx_kind(request?4'd1:4'd2),.tx_expected_kind(tx_slot_kind),
  .tx_epoch(actual_tag[58:43]),.tx_expected_epoch(operation_tag[58:43]),
  .tx_layer(actual_tag[42:37]-6'd1),.tx_expected_layer(operation_tag[42:37]-6'd1),
  .tx_beat(request?5'd0:kernel_q_beat),.tx_expected_beat(tx_slot_beat),
  .tx_data(tx_sel_data),.tx_valid(tx_valid),.tx_payload(tx_payload),
  .rx_event(rx_event),.rx_expected(rx_slot),.rx_payload(rx_payload),.rx_expected_kind(rx_slot_kind),
  .rx_expected_epoch(operation_tag[58:43]),.rx_expected_layer(operation_tag[42:37]-6'd1),.rx_expected_beat(rx_slot_beat),
  .rx_valid(rv),.rx_kind(rk),.rx_epoch(re),.rx_layer(rl),.rx_beat(rb),.rx_data(rd),.fault(codec_fault),.fault_cause(fault_cause));
  assign tx_valid_pub=tx_valid;assign tx_valid_pub2=tx_valid;
 end endgenerate
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

// R3h (QW-N59-6 10-20): native59-local copy of qkd_native_attention_record (rtl/qwen_sys/split_20261014, unchanged) with
// one added output, tx_valid_b = a kept copy of tx_valid written by the same statements, so the native59 slot merge can
// gate each payload half by its own register (R3f census: tx_valid 39 loads).  Every other line is the original module.
module qkd_native_attention_record_n59 #(
    parameter integer KV_SIDE=1,
    parameter integer MUT=0,
    // QW-N59-4 (10-19, default 0 = as built): RX_FREE 1 = rx_data captures rx_payload[511:0] on EVERY edge (no 512-bit
    // enable from the record checks; native59 svc placed STA: rx header / legal() / tx checks -> 512-flop enable = -220 ps).
    // Consumers read rx_data only on the edge after a valid, non-faulting rx_event (rx_valid / result slot), where both
    // forms hold the same word; after a bad record the codec faults and no consumer uses rx_data again.
    parameter integer RX_FREE=0,
    // QW-N59-4 v3 (default 0 = as built): TX_FREE 1 = tx_payload captures {kind, layer, epoch, beat, data} on EVERY edge
    // (no 548-bit enable from the tx record checks).  Only for a consumer that reads tx_payload qualified by tx_valid
    // (native59 MCTX 1: the slot merge ORs a payload only with its tx_valid).
    parameter integer TX_FREE=0
)(
    input wire ck,rst_n,
    input wire tx_event,tx_expected,
    input wire [3:0] tx_kind,tx_expected_kind,
    input wire [15:0] tx_epoch,tx_expected_epoch,
    input wire [5:0] tx_layer,tx_expected_layer,
    input wire [4:0] tx_beat,tx_expected_beat,
    input wire [511:0] tx_data,
    output reg tx_valid,output reg [547:0] tx_payload,
    (* keep = "true" *) output reg tx_valid_b,   // R3h: kept copy of tx_valid (same statements)
    (* keep = "true" *) output reg tx_valid_c,   // R3j: second kept copy
    input wire rx_event,rx_expected,
    input wire [547:0] rx_payload,
    input wire [3:0] rx_expected_kind,
    input wire [15:0] rx_expected_epoch,
    input wire [5:0] rx_expected_layer,
    input wire [4:0] rx_expected_beat,
    output reg rx_valid,
    output reg [3:0] rx_kind,
    output reg [15:0] rx_epoch,
    output reg [5:0] rx_layer,
    output reg [4:0] rx_beat,
    output reg [511:0] rx_data,
    output reg fault,output reg [3:0] fault_cause
);
    localparam [3:0] CMD=1,Q=2,RESULT=3,STATUS=4;
    function legal(input [3:0] kind,input [5:0] layer,input [4:0] beat,input [511:0] data);
        begin
            legal=layer<36 && ((kind==Q)||(kind==RESULT)||
                (kind==CMD && beat==0 && data[511:19]==0 && data[18:1]<8192)||
                (kind==STATUS && beat==0 && data[511:5]==0));
        end
    endfunction
    function direction(input [3:0] kind,input bit transmit);
        begin
            if((KV_SIDE!=0)==transmit)direction=kind==RESULT||kind==STATUS;
            else direction=kind==CMD||kind==Q;
        end
    endfunction
    wire [3:0] rk=rx_payload[542:539];
    wire [5:0] rl=rx_payload[538:533];
    wire [15:0] re=rx_payload[532:517];
    wire [4:0] rb=rx_payload[516:512];
    wire tx_time_bad=MUT!=1 && tx_event!=tx_expected;
    wire rx_time_bad=MUT!=1 && rx_event!=rx_expected;
    wire tx_record_bad=tx_event && (!legal(tx_kind,tx_layer,tx_beat,tx_data)||!direction(tx_kind,1'b1)||
        (MUT!=2 && {tx_kind,tx_epoch,tx_layer,tx_beat}!={tx_expected_kind,tx_expected_epoch,tx_expected_layer,tx_expected_beat}));
    wire rx_record_bad=rx_event && (rx_payload[547:543]!=0||!legal(rk,rl,rb,rx_payload[511:0])||!direction(rk,1'b0)||
        (MUT!=2 && {rk,re,rl,rb}!={rx_expected_kind,rx_expected_epoch,rx_expected_layer,rx_expected_beat}));
    wire bad=tx_time_bad||rx_time_bad||tx_record_bad||rx_record_bad;
    always @(posedge ck or negedge rst_n)begin
        if(!rst_n)begin
            tx_valid<=0;tx_valid_b<=0;tx_valid_c<=0;tx_payload<=0;rx_valid<=0;rx_kind<=0;rx_epoch<=0;rx_layer<=0;rx_beat<=0;rx_data<=0;
            fault<=0;fault_cause<=0;
        end else begin
            if(RX_FREE!=0)rx_data<=rx_payload[511:0];
            if(TX_FREE!=0)tx_payload<={5'd0,tx_kind,tx_layer,tx_epoch,tx_beat,tx_data};
            tx_valid<=0;tx_valid_b<=0;tx_valid_c<=0;rx_valid<=0;
            if(!fault)begin
                if(bad)begin
                    fault<=1;fault_cause<={rx_record_bad,tx_record_bad,rx_time_bad,tx_time_bad};
                end else begin
                    tx_valid<=tx_event;tx_valid_b<=tx_event;tx_valid_c<=tx_event;
                    if(tx_event&&TX_FREE==0)tx_payload<={5'd0,tx_kind,tx_layer,tx_epoch,tx_beat,tx_data};
                    rx_valid<=rx_event;
                    if(rx_event)begin
                        rx_kind<=rk;rx_epoch<=re;rx_layer<=rl;rx_beat<=rb;if(RX_FREE==0)rx_data<=rx_payload[511:0];
                    end
                end
            end
        end
    end
endmodule
