// Finite score winner merge. Scores MUST already include the actual stored
// draft logits plus Markov contribution in the golden FP32 addition order.
// Same primitive folds real rows,32 SM winners, then96 die winners. Empty
// ranks are explicit present=0 records, not invented scores or completions.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_native_mtp_rank_argmax_mx1 #(
 parameter integer ENABLE=0,MAX_RANKS=3072
)(
 input wire clk,rst_n,
 input wire start_v,output wire start_ready,input wire [72:0] start_owner,
 input wire [11:0] nranks,
 input wire i_v,output wire i_ready,input wire [72:0] i_owner,
 input wire [11:0] i_rank,input wire i_present,
 input wire [16:0] i_token,input wire [31:0] i_score,
 output reg o_v,input wire o_ready,output wire [72:0] o_owner,
 output wire [16:0] o_token,output wire [31:0] o_score,
 output reg fault,output wire drained_ready
);
 reg active,found;reg [72:0] owner;reg [11:0] count,next_rank;
 reg [16:0] best_token;reg [31:0] best_score;
 wire finite_score=i_score[30:23]!=8'hff;
 wire zero_in=i_score[30:0]==0,zero_best=best_score[30:0]==0;
 wire equal_score=(i_score==best_score)||(zero_in&&zero_best);
 wire greater_score=!equal_score &&
  ((i_score[31]!=best_score[31]) ? !i_score[31] :
    (i_score[31] ? i_score[30:0]<best_score[30:0] : i_score[30:0]>best_score[30:0]));
 wire take_best=i_present && (!found || greater_score || (equal_score && i_token<best_token));
 wire legal=i_owner==owner && i_rank==next_rank &&
  (!i_present || (i_token<129280 && finite_score));
 assign start_ready=ENABLE && rst_n && !active && !o_v && !fault;
 assign i_ready=ENABLE && rst_n && active && !fault;
 assign o_owner=owner;assign o_token=best_token;assign o_score=best_score;
 assign drained_ready=ENABLE && rst_n && !active && !o_v && !fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;found<=0;owner<=0;count<=0;next_rank<=0;
   best_token<=0;best_score<=0;o_v<=0;fault<=0;end
  else if(ENABLE)begin
   if(o_v && o_ready)o_v<=0;
   if(start_v && start_ready)begin
    if(nranks==0 || nranks>MAX_RANKS)fault<=1;
    else begin active<=1;found<=0;owner<=start_owner;count<=nranks;next_rank<=0;end
   end
   if(i_v && i_ready)begin
    if(!legal)begin fault<=1;active<=0;end
    else begin
     if(take_best)begin best_token<=i_token;best_score<=i_score;found<=1;end
     next_rank<=next_rank+1;
     if(next_rank+1==count)begin
      active<=0;if(!found && !i_present)fault<=1;else o_v<=1;
     end
    end
   end
  end
 end
endmodule
`default_nettype wire
