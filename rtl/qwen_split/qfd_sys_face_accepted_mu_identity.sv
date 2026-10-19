// REPLACEMENT CANDIDATE ONLY (+40 FF estimated), never instantiate beside old observer.
// Authenticated token/generation share the exact fresh full-identity acceptance.
// SOURCE CANDIDATE ONLY: explicit static epoch roles; no production FACE wiring.
`timescale 1ns/1ps
// Observe the ACTUAL host receiver acceptance at E+1, before a user0-restore NBA.
// Never convert a raw offered record to a loader write. An E offer must have a
// fresh acceptance pulse for its full identity and still-installed image tuple.
module qfd_sys_face_accepted_mu_identity #(parameter integer EPOCH_EXPORT=0, parameter integer MUT=0)(
 input wire ck,rst_n,offer_slot,offer_v,input wire[547:0]offer_record,
 input wire host_accept_v,host_epoch_valid,input wire[15:0]host_epoch,
 input wire[58:0]host_tag,input wire[1:0]host_gen,
 input wire program_ready,program_cap,program_fault,
 input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire epoch_slot,input wire[1:0]epoch_user,
 output reg accepted_epoch_v,output reg[1:0]accepted_epoch_user,output reg[15:0]accepted_epoch,
 output reg[17:0]accepted_token,output reg[1:0]accepted_generation,
 output wire[128:0]ctx_x,output reg fault);
 reg offered;reg[58:0]tag;reg[1:0]gen;reg[15:0]image_epoch;
 reg[63:0]digest;reg cap;
 wire[1:0]user_id=tag[44:43];
 wire accepted=(MUT==1)||
  (host_accept_v&&host_epoch_valid&&host_epoch==tag[58:43]&&host_tag==tag&&
   ((MUT==4)||host_gen==gen)&&program_ready&&!program_fault&&
   program_epoch==image_epoch&&program_digest==digest&&program_cap==cap);
 reg load;reg[127:0]payload;reg role_q;reg[1:0]role_user;
 wire role_match=(MUT==7)||user_id==role_user;
 wire epoch_accept=EPOCH_EXPORT&&offered&&role_q&&accepted&&role_match;
 assign ctx_x={load,payload};
 // Payload has no reset loads: load is the sole validity bit and resets low.
 // It is always registered, and is zeroed whenever no accepted MU record emits.
 always @(posedge ck)begin
  tag<=offer_record[58:0];gen<=offer_record[60:59];image_epoch<=offer_record[77:62];
  digest<=offer_record[141:78];cap<=offer_record[61];
  role_user<=epoch_user;
  if(epoch_accept)begin
   accepted_epoch<=(MUT==5)?(tag[58:43]^16'd4):tag[58:43];
   accepted_epoch_user<=(MUT==6)?user_id+2'd1:user_id;
   accepted_token<=(MUT==8)?(tag[36:19]^18'd1):tag[36:19];
   accepted_generation<=(MUT==9)?gen+2'd1:gen;
  end
  payload<=0;
  if(offered&&user_id!=0&&accepted)begin
   payload[127:112]<=16'h4d43;
   payload[110:108]<=3'b001<<((MUT==2)?(user_id%3):(user_id-1));
   for(integer u=1;u<=3;u=u+1)if(user_id==u)begin
    payload[36*(u-1)+18+:18]<=tag[36:19];
    payload[36*(u-1)+:18]<={5'd0,tag[18:6]};
   end
  end
 end
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin offered<=0;load<=0;fault<=0;role_q<=0;accepted_epoch_v<=0;end
  else begin
   offered<=offer_slot&&offer_v;
   role_q<=EPOCH_EXPORT&&epoch_slot;
   accepted_epoch_v<=epoch_accept;
   if(EPOCH_EXPORT&&offered&&role_q&&accepted&&!role_match)fault<=1;
   load<=offered&&user_id!=0&&accepted;
   if(offered&&user_id!=0&&!accepted)fault<=1;
  end
endmodule
