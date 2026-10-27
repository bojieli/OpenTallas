`timescale 1ns/1ps
`default_nettype none
// HEAD-RTL2 compiled-date authority. S is the first sampled high START.
// Issue k occurs only at S+offset+k*period while run_i remains high. Readiness
// is checked at the date; a miss faults, never moves a date or stalls a ring.
// This block adds zero datapath cycles. Retirement is matching token emission,
// supplied by the caller; replay completion is deliberately not an input.
module ot_s81hd_static_issue #(parameter integer MUT_MODE=0)(
 input wire ck,rn,start_i,run_i,
 input wire[15:0]issue_offset,issue_period,merge_deadline,
 input wire loaded_ready,replay_busy,token_retire,merged_valid,
 output wire issue_o,output reg job_active_o,output wire due_o,output reg fault_o
);
 reg started;reg[31:0]age,next_date;reg waiting_merge;reg[15:0]merge_left;
 wire first=start_i&&!started;
 wire due=run_i && ((first&&issue_offset==0)||(started&&age==next_date));
 assign due_o=due;
 assign issue_o=(MUT_MODE==1 ? (run_i&&loaded_ready&&!replay_busy&&!job_active_o) : due)
                &&loaded_ready&&!replay_busy&&(!job_active_o||token_retire);
 always@(posedge ck or negedge rn)
  if(!rn)begin started<=0;age<=0;next_date<=0;job_active_o<=0;fault_o<=0;waiting_merge<=0;merge_left<=0;end
  else begin
   if(first)begin
    started<=1;age<=1;next_date<=issue_offset;
    if(!run_i||issue_period==0||merge_deadline==0)fault_o<=1;
   end else if(started)age<=age+1'b1;
   if(due)begin
    next_date<=(first?{16'd0,issue_offset}:next_date)+{16'd0,issue_period};
    if(!loaded_ready||replay_busy||(job_active_o&&!token_retire)||issue_period==0)fault_o<=1;
   end
   if(token_retire)begin
    if(!job_active_o)fault_o<=1;
    job_active_o<=0;
   end
   if(issue_o)begin job_active_o<=1;waiting_merge<=1;merge_left<=merge_deadline;end
   else if(waiting_merge)begin
    if(merged_valid)waiting_merge<=0;
    else if(merge_left<=1)begin fault_o<=1;waiting_merge<=0;end
    else merge_left<=merge_left-1'b1;
   end
   if(MUT_MODE==2&&merged_valid)job_active_o<=0;
  end
endmodule
`default_nettype wire
