`timescale 1ns/1ps
// Native finite S7 dependency sequencer. Every backend command/completion
// carries the same full cohort and a distinct command command_seq. S3 output
// truncation still executes all7 drafter positions. This block supplies real
// dispatch/accept/commit control, not numerical or physical backend evidence.
module ot_qwen_dspark_s7_control #(parameter integer ENABLE=0,MUT_FENCE=0)(
 input wire clk,rst_n,input wire start_v,output wire start_r,
 input wire [63:0] start_id,input wire [17:0] start_token,start_pos,
 input wire [3:0] context_n,input wire truncate3,
 input wire allcopy_fenced,
 output wire cmd_v,input wire cmd_r,
 output wire [4:0] cmd_op,output wire [2:0] cmd_layer,cmd_slot,
 output wire [3:0] cmd_positions,cmd_commit_n,
 output wire [17:0] cmd_token,cmd_pos,
 output wire [63:0] cmd_id,output wire [7:0] cmd_sequence,
 input wire done_v,input wire [63:0] done_id,input wire [7:0] done_sequence,
 input wire [17:0] done_token,input wire [143:0] done_targets,
 input wire [3:0] done_n,input wire done_fault,
 output reg result_v,input wire result_r,
 output reg [63:0] result_id,output reg [3:0] result_n,
 output reg [17:0] result_bonus,result_pos,
 output reg fault
);
 localparam integer FEATURE=0,FC=1,FC_GATHER=2,HIDDEN_NORM=3,CTX_KV=4,
  EMBED=5,DRAFT_LAYER=6,DRAFT_NORM=7,DRAFT_HEAD=8,W1=9,
  MKV_PROJECT=10,MKV_ADD=11,MKV_AMAX=12,MKV_GATHER=13,VERIFY=14,COMMIT=15;
 reg live,outstanding;
 reg [4:0] op;
 reg [2:0] layer,slot,gamma;
 reg [3:0] ctx,emit;
 reg [7:0] command_seq;
 reg [63:0] cohort;
 reg [17:0] pending,pos,prev,bonus;
 reg [17:0] drafts[0:6];
 reg [143:0] targets;
 reg compare_pending;
 reg [2:0] compare_index;
 reg seen_cohort;reg [63:0] previous_cohort;
 assign start_r=(ENABLE!=0)&&!fault&&!live&&!result_v&&allcopy_fenced;
 assign cmd_v=(ENABLE!=0)&&live&&!outstanding&&!compare_pending&&!fault;
 assign cmd_op=op;assign cmd_layer=layer;assign cmd_slot=slot;
 assign cmd_positions=(op<=CTX_KV)?ctx:(op<=DRAFT_HEAD)?4'd7:(op==VERIFY)?{1'b0,gamma}+4'd1:4'd1;
 assign cmd_commit_n=emit;assign cmd_token=(op>=W1&&op<=MKV_GATHER)?prev:pending;
 assign cmd_pos=pos;assign cmd_id=cohort;assign cmd_sequence=command_seq;
 integer k;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin live<=0;outstanding<=0;op<=0;layer<=0;slot<=0;command_seq<=0;
   result_v<=0;fault<=0;compare_pending<=0;seen_cohort<=0;end
  else begin
   if(result_v&&result_r)result_v<=0;
   if(start_v&&start_r)begin
    if(context_n==0||context_n>8||start_token>=151936||(seen_cohort&&start_id==previous_cohort))fault<=1;
    else begin
     live<=1;outstanding<=0;compare_pending<=0;op<=FEATURE;layer<=0;slot<=0;command_seq<=0;
     ctx<=context_n;gamma<=truncate3?3'd3:3'd7;cohort<=start_id;pending<=start_token;pos<=start_pos;prev<=start_token;
     previous_cohort<=start_id;seen_cohort<=1;emit<=0;
    end
   end
   if(cmd_v&&cmd_r)outstanding<=1;
   if(done_v)begin
    if(!outstanding||done_id!=cohort||done_sequence!=command_seq||done_fault)fault<=1;
    else begin
     outstanding<=0;command_seq<=command_seq+1'b1;
     if(op==CTX_KV||op==DRAFT_LAYER)begin
      if(layer==4)begin layer<=0;op<=op+1'b1;end else layer<=layer+1'b1;
     end else if(op==MKV_GATHER)begin
      if(done_token>=151936)fault<=1;
      else begin
       drafts[slot]<=done_token;prev<=done_token;
       if(slot==6)begin slot<=0;op<=VERIFY;end else begin slot<=slot+1'b1;op<=W1;end
      end
     end else if(op==VERIFY)begin
      if(done_n!=({1'b0,gamma}+4'd1))fault<=1;
      else begin
       targets<=done_targets;compare_pending<=1;compare_index<=0;
       for(k=0;k<8;k=k+1)if(k<done_n&&done_targets[k*18+:18]>=151936)fault<=1;
      end
     end else if(op==COMMIT)begin
      // Backend positive all-copy drain is authoritative; no FIFO push or
      // offered write completion can substitute for it.
      if((!allcopy_fenced&&MUT_FENCE==0)||done_n!=emit||({1'b0,pos}+emit)>19'h3ffff)fault<=1;
      else begin live<=0;result_v<=1;result_id<=cohort;result_n<=emit;result_bonus<=bonus;result_pos<=pos+18'(emit);end
     end else op<=op+1'b1;
    end
   end
   if(compare_pending&&!fault)begin
    if(compare_index==gamma||drafts[compare_index]!=targets[compare_index*18+:18])begin
     emit<={1'b0,compare_index}+4'd1;bonus<=targets[compare_index*18+:18];compare_pending<=0;op<=COMMIT;
    end else compare_index<=compare_index+1'b1;
   end
  end
 end
endmodule
