`timescale 1ns/1ps
// Translate an admitted service-word burst into an object-relative byte burst.
// Layout records are immutable until clear. This covers contiguous power-of-two
// byte words (1/2/4/8), not packed sub-byte or strided/tiled weight layouts.
// Object identity accompanies every burst; no global address is invented.
module ot_a3_operand_byte_mapper(
 input wire clk,rst_n,clear,
 input wire command_valid,
 output wire command_ready,
 input wire [31:0] command_generation,
 input wire [95:0] command_objects,command_word_bases,
 input wire [191:0] command_byte_bases,command_object_bytes,
 input wire [5:0] command_word_shifts,
 input wire request_valid,
 output wire request_ready,
 input wire [63:0] request_tag,
 input wire [1:0] request_plane,
 input wire [31:0] request_address,
 input wire [8:0] request_words,
 output wire burst_valid,
 input wire burst_ready,
 output reg [63:0] burst_tag,burst_offset,
 output reg [31:0] burst_object,
 output reg [11:0] burst_bytes,
 output reg [8:0] burst_words,
 output reg [1:0] burst_shift,
 output reg protocol_error
);
 localparam [2:0] IDLE=0,SCALE=1,ADD=2,CHECK=3,VALIDATE=4,SEND=5;
 reg [2:0] state;
 reg active;
 reg [31:0] generation,objects[0:2],word_bases[0:2];
 reg [63:0] byte_bases[0:2],object_bytes[0:2];
 reg [1:0] shifts[0:2];
 reg [31:0] delta;
 reg [63:0] base_q,limit_q;
 reg [64:0] offset_q,end_q;
 reg [34:0] scaled_delta;
 wire enabled=rst_n && !clear && !protocol_error;
 assign command_ready=enabled && !active;
 assign request_ready=enabled && active && state==IDLE;
 assign burst_valid=enabled && state==SEND;
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;active<=0;generation<=0;protocol_error<=0;delta<=0;base_q<=0;limit_q<=0;
   offset_q<=0;end_q<=0;scaled_delta<=0;burst_tag<=0;burst_offset<=0;burst_object<=0;
   burst_bytes<=0;burst_words<=0;burst_shift<=0;
   for(i=0;i<3;i=i+1)begin objects[i]<=0;word_bases[i]<=0;byte_bases[i]<=0;object_bytes[i]<=0;shifts[i]<=0;end
  end else if(clear)begin state<=IDLE;active<=0;protocol_error<=0;end
  else if(enabled)begin
   if(command_valid && command_ready)begin
    active<=1;generation<=command_generation;
    for(i=0;i<3;i=i+1)begin
     objects[i]<=command_objects[32*i+:32];word_bases[i]<=command_word_bases[32*i+:32];
     byte_bases[i]<=command_byte_bases[64*i+:64];object_bytes[i]<=command_object_bytes[64*i+:64];
     shifts[i]<=command_word_shifts[2*i+:2];
    end
   end
   case(state)
    IDLE:if(request_valid && request_ready)begin
     if(request_plane>=3 || request_tag[63:32]!=generation || request_words==0 || request_words>256)
      protocol_error<=1;
     else if(request_address<word_bases[request_plane] ||
             ({1'b0,request_address}+{24'd0,request_words})>33'h100000000)
      protocol_error<=1;
     else begin
      burst_tag<=request_tag;burst_object<=objects[request_plane];
      burst_words<=request_words;burst_shift<=shifts[request_plane];
      delta<=request_address-word_bases[request_plane];
      base_q<=byte_bases[request_plane];limit_q<=object_bytes[request_plane];state<=SCALE;
     end
    end
    SCALE:begin
     scaled_delta<={3'd0,delta}<<burst_shift;
     burst_bytes<={3'd0,burst_words}<<burst_shift;state<=ADD;
    end
    ADD:begin offset_q<={1'b0,base_q}+{30'd0,scaled_delta};state<=CHECK;end
    CHECK:begin
     end_q<=offset_q+{53'd0,burst_bytes};
     burst_offset<=offset_q[63:0];state<=VALIDATE;
    end
    VALIDATE:begin
     if(offset_q[64] || end_q>{1'b0,limit_q})protocol_error<=1;
     else state<=SEND;
    end
    SEND:if(burst_ready)state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
endmodule
