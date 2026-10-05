`timescale 1ns/1ps
// Bounded BF16 object-memory gather with one 16-byte cache line per lane/slot.
// A slot corresponds to an interleaved column group. All eight cache hits are
// assembled together; misses share one ordered external read channel. Object
// layout/permission admission belongs to the parent. This block enforces byte
// capacity and generation/response ownership. Not yet instantiated in G2.
// clear requires external cancellation acknowledgement or complete read drain;
// global reset must also reset transport. Exactly one response per read is required.
module ot_a3_bf16_weight_gather #(
 parameter integer SLOTS=3,
 parameter bit RETAIN_LINES=1,
 parameter integer SLOT_BITS=SLOTS<2?1:$clog2(SLOTS)
)(
 input wire clk,rst_n,clear,
 input wire command_valid,output wire command_ready,
 input wire [31:0] command_generation,command_object,command_lane_stride,
 input wire [63:0] command_object_bytes,
 input wire coordinate_valid,output wire coordinate_ready,
 input wire [63:0] coordinate_element_base,
 input wire [7:0] coordinate_mask,
 input wire [SLOT_BITS-1:0] coordinate_slot,
 input wire [31:0] coordinate_index,
 output wire word_valid,input wire word_ready,
 output reg [127:0] word_data,
 output reg [31:0] word_index,
 output wire read_valid,input wire read_ready,
 output wire [63:0] read_tag,
 output wire [31:0] read_object,
 output reg [63:0] read_offset,
 output reg [4:0] read_bytes,
 input wire response_valid,output wire response_ready,
 input wire [63:0] response_tag,
 input wire [127:0] response_data,
 input wire response_error,
 output reg protocol_error,
 output wire drained
);
 localparam [2:0] IDLE=0,BOUNDS=1,LOOKUP=2,REQUEST=3,WAIT_RESPONSE=4,SEND=5;
 reg [2:0] state;
 reg active;
 reg [31:0] generation,object_id,sequence_id;
 reg [63:0] last_element_offset;
 reg [4:0] last_line_bytes;
 reg [7:0] mask;
 reg [SLOT_BITS-1:0] slot;
 reg [65:0] addresses[0:7];
 reg [34:0] lane_offsets[0:7];
 reg [127:0] cache_data[0:SLOTS-1][0:7];
 reg [59:0] cache_tag[0:SLOTS-1][0:7];
 reg [7:0] cache_valid[0:SLOTS-1];
 reg [2:0] miss_lane;
 reg invalid_address,miss;
 reg [2:0] selected_lane;
 reg [127:0] assembled;
 integer l,s;
 wire enabled=rst_n && !clear;
 wire expected_response=(state==WAIT_RESPONSE || (state==REQUEST && read_ready)) && response_tag==read_tag;
 wire unexpected_response=response_valid && !expected_response;
 assign command_ready=enabled && !active && !protocol_error;
 assign coordinate_ready=enabled && active && state==IDLE && !protocol_error;
 assign word_valid=enabled && state==SEND;
 assign read_valid=enabled && state==REQUEST;
 assign read_tag={generation,sequence_id};
 assign read_object=object_id;
 assign response_ready=enabled;
 assign drained=state==IDLE;
 initial if(SLOTS<1 || SLOTS>16)$fatal(1,"invalid gather slot count");
 always @* begin
  invalid_address=0;miss=0;selected_lane=0;assembled=0;
  for(integer lane=0;lane<8;lane=lane+1)begin
   if(mask[lane])begin
    // addresses are even BF16 byte offsets, so a valid element never crosses
    // a 16-byte line. Keep both overflow bits until capacity validation.
    if(addresses[lane][65:64]!=0 || addresses[lane]>{2'd0,last_element_offset})invalid_address=1;
    if(32'(slot)<SLOTS)begin
     if(!cache_valid[slot][lane] || cache_tag[slot][lane]!=addresses[lane][63:4])begin
      if(!miss)selected_lane=3'(lane);
      miss=1;
     end else assembled[16*lane+:16]=16'(cache_data[slot][lane] >> {addresses[lane][3:0],3'b0});
    end else invalid_address=1;
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;active<=0;protocol_error<=0;sequence_id<=0;
   for(s=0;s<SLOTS;s=s+1)cache_valid[s]<=0;
  end else if(clear)begin
   state<=IDLE;active<=0;protocol_error<=0;sequence_id<=0;
   for(s=0;s<SLOTS;s=s+1)cache_valid[s]<=0;
  end else begin
   // An unrelated response never retires the outstanding expected read.
   if(unexpected_response)protocol_error<=1;
   if(command_valid && command_ready)begin
    if(command_object_bytes<2)protocol_error<=1;
    else active<=1;
   end
   case(state)
    IDLE:if(coordinate_valid && coordinate_ready)begin
     if(32'(coordinate_slot)>=SLOTS)protocol_error<=1;
     else begin
      if(!RETAIN_LINES)cache_valid[coordinate_slot]<=0;
      state<=BOUNDS;
     end
    end
    BOUNDS:begin
     if(invalid_address || protocol_error || unexpected_response)begin protocol_error<=1;state<=IDLE;end
     else state<=LOOKUP;
    end
    LOOKUP:begin
     if(protocol_error || unexpected_response)state<=IDLE;
     else if(miss)state<=REQUEST;
     else state<=SEND;
    end
    REQUEST:if(read_ready)state<=WAIT_RESPONSE;
    WAIT_RESPONSE:begin end
    SEND:if(word_ready)state<=IDLE;
    default:state<=IDLE;
   endcase
   if(response_valid && expected_response)begin
    sequence_id<=sequence_id+1'b1;
    if(response_error || protocol_error)begin protocol_error<=1;state<=IDLE;end
    else begin cache_valid[slot][miss_lane]<=1;state<=LOOKUP;end
   end
  end
 end
 // Payload is protected by validity and ownership. No payload reset tree.
 always @(posedge clk)begin
  if(command_valid && command_ready)begin
   generation<=command_generation;object_id<=command_object;
   // Descriptor strides are immutable for the generation. Compute lane
   // multiples once, removing multiply/add depth from every coordinate.
   for(l=0;l<8;l=l+1)lane_offsets[l]<=35'(command_lane_stride)*35'(l);
   // BF16 addresses are even. A final single byte cannot hold an element;
   // its preceding complete line is the last reachable line for capacity %16=1.
   last_element_offset<=command_object_bytes-64'd2;
   last_line_bytes<=command_object_bytes[3:1]==0?5'd16:{1'b0,command_object_bytes[3:0]};
  end
  if(coordinate_valid && coordinate_ready)begin
   mask<=coordinate_mask;slot<=coordinate_slot;word_index<=coordinate_index;
   for(l=0;l<8;l=l+1)
    addresses[l]<=({2'd0,coordinate_element_base}+{31'd0,lane_offsets[l]})<<1;
  end
  if(state==LOOKUP && !protocol_error)begin
   if(miss)begin
    miss_lane<=selected_lane;read_offset<={addresses[selected_lane][63:4],4'd0};
    read_bytes<=addresses[selected_lane][63:4]==last_element_offset[63:4]?last_line_bytes:5'd16;
   end else word_data<=assembled;
  end
  if(response_valid && expected_response && !response_error && !protocol_error)begin
   cache_data[slot][miss_lane]<=response_data;cache_tag[slot][miss_lane]<=addresses[miss_lane][63:4];
  end
 end
endmodule
