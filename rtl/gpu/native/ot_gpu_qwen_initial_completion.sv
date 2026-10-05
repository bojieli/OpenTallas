`timescale 1ns/1ps
// ONE default-off, real INITIAL input producer for literal banks0 and32.
// The source program has exactly token/position scalar initial homes. This
// endpoint observes actual SRAM acceptance, matched common ACK, protected
// all-bank receipt and physical query/RF drain. No host ACK-count terminal.
module ot_gpu_qwen_initial_completion #(parameter bit ENABLE=0)(
 input wire clk,power_on_reset_n,warm_reset,
 input wire go_valid,output wire go_ready,
 input wire [238:0] go_tuple,input wire [54:0] go_owner,
 input wire [31:0] go_input_bits,
 input wire [1:0] write_accept,
 input wire [17:0] write_slots,input wire [91:0] write_owners,
 input wire [8191:0] write_data,
 input wire [1:0] query_valid,query_owner_retained,
 input wire [477:0] query_tuples,input wire [17:0] query_slots,
 input wire [91:0] query_owners,
 input wire [1:0] ACK_accept,input wire [17:0] ACK_slots,input wire [91:0] ACK_owners,
 input wire root_ACK_accept,input wire [238:0] root_ACK_tuple,input wire [54:0] root_ACK_owner,
 input wire close_valid,output wire close_ready,
 input wire [238:0] close_tuple,input wire [54:0] close_owner,
 // Actual physical RF/query producer emptiness after CLOSE. No timer/idle stub.
 input wire [1:0] RF_drained,
 output wire [1:0] initial_write_admit,
 output wire provider_quiesce,
 output wire visible_valid,input wire visible_ready,
 output wire terminal_valid,input wire terminal_ready,
 output wire reverse_valid,input wire reverse_ready,
 output wire [238:0] event_tuple,output wire [54:0] event_owner,
 input wire frame_retire_accept,input wire [238:0] frame_retire_tuple,input wire [54:0] frame_retire_owner,
 output wire busy,output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 localparam integer RAW=335,WORDS=6;
 localparam integer R=0,O=239,V=294,W=326,A=328,K=330,P=331,F=334;
 localparam [2:0] IDLE=0,ACTIVE=1,DRAIN=2,VISIBLE=3,TERMINAL=4,REVERSE=5,RETIRE=6;
 reg [71:0] code[0:WORDS-1];
 reg [WORDS*64-1:0] decoded,next_data;
 reg clean,bad,ce;
 reg [65:0] d;integer j,b;
 always @* begin
  decoded=0;clean=1;bad=0;ce=0;
  for(j=0;j<WORDS;j=j+1)begin
   d=decode64(code[j]);decoded[j*64+:64]=d[63:0];
   if(d[65])bad=1;if(d[64])begin clean=0;ce=1;end
  end
  if(bad||decoded[WORDS*64-1:RAW]!=0)clean=0;
 end
 wire [2:0] phase=decoded[P+:3];
 wire [238:0] root=decoded[R+:239];wire [54:0] owner=decoded[O+:55];
 wire active=ENABLE&&power_on_reset_n&&!warm_reset&&clean&&!bad&&!decoded[F];
 wire initial_legal=go_tuple[174:164]==2047&&go_tuple[29:19]<=1&&
  (go_tuple[35:30]==0||go_tuple[35:30]==32)&&
  go_tuple[18:10]==(go_tuple[29:19]==0?32:33)&&
  go_tuple[9:0]==(go_tuple[29:19]==0?33:34);
 assign busy=ENABLE&&phase!=IDLE;
 assign fault=ENABLE&&(bad||decoded[F]||decoded[WORDS*64-1:RAW]!=0);
 assign go_ready=active&&phase==IDLE&&initial_legal;
 assign close_ready=active&&phase==ACTIVE&&close_tuple==root&&close_owner==owner;
 assign initial_write_admit={2{active&&phase==ACTIVE}}&~decoded[W+:2];
 assign provider_quiesce=ENABLE&&phase>=DRAIN;
 assign visible_valid=active&&phase==VISIBLE;
 assign terminal_valid=active&&phase==TERMINAL;
 assign reverse_valid=active&&phase==REVERSE;
 assign event_tuple=root;assign event_owner=owner;
 reg event_bad,query_match,write_match,ACK_match;
 reg [8:0] expected_slot;
 always @* begin
  next_data=decoded;event_bad=0;query_match=0;write_match=0;ACK_match=0;
  expected_slot=root[29:19]==0?32:33;
  if(active)begin
   if(go_valid&&phase!=IDLE)event_bad=1;
   if(go_valid&&go_ready)begin
    next_data=0;next_data[R+:239]=go_tuple;next_data[O+:55]=go_owner;
    next_data[V+:32]=go_input_bits;next_data[P+:3]=ACTIVE;
   end
   for(b=0;b<2;b=b+1)begin
    query_match=query_valid[b]&&query_owner_retained[b]&&query_tuples[b*239+:239]==root&&
     query_slots[b*9+:9]==expected_slot;
    write_match=query_match&&write_slots[b*9+:9]==expected_slot&&
     write_owners[b*46+:46]==query_owners[b*46+:46]&&
     write_data[b*4096+:32]==decoded[V+:32]&&write_data[b*4096+32+:4064]==0;
    ACK_match=query_match&&ACK_slots[b*9+:9]==expected_slot&&
     ACK_owners[b*46+:46]==query_owners[b*46+:46];
    if(write_accept[b])begin
     if(phase!=ACTIVE||decoded[W+b]||!write_match)event_bad=1;
     else next_data[W+b]=1;
    end
    if(ACK_accept[b])begin
     if((phase!=ACTIVE&&phase!=DRAIN)||!decoded[W+b]||decoded[A+b]||!ACK_match)event_bad=1;
     else next_data[A+b]=1;
    end
   end
   if(root_ACK_accept)begin
    if((phase!=ACTIVE&&phase!=DRAIN)||decoded[K]||root_ACK_tuple!=root||root_ACK_owner!=owner||decoded[A+:2]!=3)
     event_bad=1;
    else next_data[K]=1;
   end
   if(close_valid)begin
    if(phase!=ACTIVE||close_tuple!=root||close_owner!=owner)event_bad=1;
    else if(close_ready)next_data[P+:3]=DRAIN;
   end
   if(phase==DRAIN&&decoded[W+:2]==3&&decoded[A+:2]==3&&decoded[K]&&
      RF_drained==3&&query_valid==0)next_data[P+:3]=VISIBLE;
   if(visible_valid&&visible_ready)next_data[P+:3]=TERMINAL;
   if(terminal_valid&&terminal_ready)next_data[P+:3]=REVERSE;
   if(reverse_valid&&reverse_ready)next_data[P+:3]=RETIRE;
   if(frame_retire_accept)begin
    if(phase!=RETIRE||frame_retire_tuple!=root||frame_retire_owner!=owner)event_bad=1;
    else next_data=0;
   end
   if(event_bad)next_data[F]=1;
  end
  // Warm reset retains every accepted receipt and quarantines new service.
  if(ENABLE&&power_on_reset_n&&clean&&!bad&&warm_reset)next_data[F]=1;
 end
 integer z;reg [65:0] current_word;
 always @(posedge clk or negedge power_on_reset_n)begin
  if(!power_on_reset_n)begin for(z=0;z<WORDS;z=z+1)code[z]<=encode64(0);end
  else if(ENABLE)begin
   for(z=0;z<WORDS;z=z+1)begin
    current_word=decode64(code[z]);
    if(!current_word[65]&&current_word[64])code[z]<=encode64(current_word[63:0]);
    else if(clean&&!bad)code[z]<=encode64(next_data[z*64+:64]);
   end
  end
 end
endmodule
