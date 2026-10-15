`timescale 1ns/1ps
`default_nettype none
// Greedy DSpark G<=5 acceptance, fixed six-edge result. Input operands are
// actual draft and target argmax tokens for ONE compiler-owned user epoch.
// Every result has deterministic commit/rollback metadata. There is no ready,
// speculative runtime reissue, or hidden schedule extension in this block.
module ot_s81_mtp_accept_static #(parameter integer ID_W=60,POS_W=21)(
 input wire clk,rst_n,accept_slot,input wire[2:0]draft_count,
 input wire[84:0]draft_tokens,input wire[101:0]target_tokens,
 input wire[POS_W-1:0]base_position,input wire[3:0]epoch,
 input wire[ID_W-1:0]identity,
 output reg result_valid,output reg[2:0]accepted,squashed,
 output reg[16:0]bonus_token,output reg[POS_W-1:0]commit_position,next_base,
 output reg[3:0]next_epoch,output reg rejected,
 output reg[ID_W-1:0]result_identity,output reg fault);
 reg[5:0]v;reg[84:0]draft_q;reg[101:0]target_q;
 reg[2:0]count_q;reg[POS_W-1:0]base_q;reg[3:0]epoch_q;reg[ID_W-1:0]id_q;
 reg[2:0]a[0:5];reg closed[0:5];reg[16:0]bonus[0:5];integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   v<=0;draft_q<=0;target_q<=0;count_q<=0;base_q<=0;epoch_q<=0;id_q<=0;
   result_valid<=0;accepted<=0;squashed<=0;bonus_token<=0;commit_position<=0;next_base<=0;next_epoch<=0;rejected<=0;result_identity<=0;fault<=0;
   for(i=0;i<6;i=i+1)begin a[i]<=0;closed[i]<=0;bonus[i]<=0;end
  end else begin
   v<={v[4:0],accept_slot};result_valid<=v[5];
   if(accept_slot)begin
    if(|v||draft_count>5||base_position>{POS_W{1'b1}}-6)fault<=1;
    draft_q<=draft_tokens;target_q<=target_tokens;count_q<=draft_count;base_q<=base_position;epoch_q<=epoch;id_q<=identity;
    a[0]<=0;closed[0]<=0;bonus[0]<=target_tokens[16:0];
    for(i=0;i<5;i=i+1)if(i<draft_count&&draft_tokens[17*i+:17]>=129280)fault<=1;
    for(i=0;i<6;i=i+1)if(i<=draft_count&&target_tokens[17*i+:17]>=129280)fault<=1;
   end
   for(i=0;i<5;i=i+1)begin
    a[i+1]<=a[i];closed[i+1]<=closed[i];bonus[i+1]<=bonus[i];
    if(v[i]&&!closed[i])begin
     if(i<count_q)begin
      if(target_q[17*i+:17]==draft_q[17*i+:17])begin a[i+1]<=3'(i+1);bonus[i+1]<=target_q[17*(i+1)+:17];end
      else begin closed[i+1]<=1;bonus[i+1]<=target_q[17*i+:17];end
     end else begin closed[i+1]<=1;bonus[i+1]<=target_q[17*i+:17];end
    end
   end
   if(v[5])begin
    accepted<=a[5];squashed<=count_q-a[5];bonus_token<=bonus[5];
    commit_position<=base_q+a[5];next_base<=base_q+a[5]+1'b1;
    rejected<=a[5]<count_q;next_epoch<=epoch_q+4'(a[5]<count_q);result_identity<=id_q;
   end
  end
 end
endmodule
`default_nettype wire
