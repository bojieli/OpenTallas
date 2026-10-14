`timescale 1ps/1fs
// Opt4 descriptor generator; parent holds six accepted ascending IDs throughout
// busy. No same-set expert row alternation: finish its four GU chunks first.
module ot_hbm_accel_wg_dispatch #(parameter integer ENABLE=0)(
 input wire clk,rst_n, task_valid, input wire [53:0] ids,
 output wire task_ready, output wire desc_valid, input wire desc_ready,
 output wire [2:0] desc_slot, output wire [5:0] desc_j0,desc_n,
 output wire desc_keep,desc_last, output wire busy,output reg fault
);
 generate if (!ENABLE) begin : off
 assign task_ready=0;assign desc_valid=0;assign desc_slot=0;
 assign desc_j0=0;assign desc_n=0;assign desc_keep=0;assign desc_last=0;assign busy=0;
 always @* fault=0;
 end else begin : on
 reg active,w2;reg [2:0] progress[0:5];
 reg [6:0] visited;
 reg legal,pk_valid;reg [2:0] pk;reg [4:0] best;
 integer remaining,chosen_set;
 always @* begin
  legal=1;
  for(integer k=0;k<6;k=k+1) begin
   if(ids[k*9+:9]>=9'd384) legal=0;
   if(k!=0 && ids[k*9+:9]<=ids[(k-1)*9+:9]) legal=0;
  end
  pk_valid=0;pk=0;best=0;chosen_set=0;remaining=0;
  // First round in router class order, then longest remaining class, ties
  // earliest router slot. Only its first unfinished expert is eligible.
  for(integer k=5;k>=0;k=k-1) begin
   automatic bit front;
   automatic integer setid;
   front=(progress[k]<(w2?3:4));setid=int'(ids[k*9+:9])%7;
   for(integer r=0;r<k;r=r+1)
    if(int'(ids[r*9+:9])%7==setid && progress[r]<(w2?3:4)) front=0;
   remaining=0;
   for(integer r=0;r<6;r=r+1)
    if(int'(ids[r*9+:9])%7==setid) remaining=remaining+(w2?3:4)-int'(progress[r]);
   if(front && (!pk_valid || (!visited[setid] && visited[chosen_set]) ||
      (visited[setid]==visited[chosen_set] && ((!visited[setid]) || remaining>=int'(best))))) begin
    pk_valid=1;pk=3'(k);best=5'(remaining);chosen_set=setid;
   end
  end
 end
 assign task_ready=!active&&!fault;
 assign desc_valid=active&&!fault;
 assign desc_slot=pk;
 assign desc_j0=(w2?6'd32:6'd0)+{progress[pk],3'b000};
 assign desc_n=(w2&&progress[pk]==2)?6'd1:6'd8;
 assign desc_keep=progress[pk]!=(w2?2:3);
 wire all_other_done=(progress[0]>=3 || pk==0)&&(progress[1]>=3 || pk==1)&&
 (progress[2]>=3 || pk==2)&&(progress[3]>=3 || pk==3)&&
 (progress[4]>=3 || pk==4)&&(progress[5]>=3 || pk==5);
 assign desc_last=w2&&(progress[pk]==2)&&all_other_done;
 assign busy=active;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin active<=0;w2<=0;visited<=0;fault<=0;
   for(integer k=0;k<6;k=k+1) progress[k]<=0;
  end else begin
   if(task_valid&&task_ready) begin
    if(!legal) fault<=1;
    else begin active<=1;w2<=0;visited<=0;
     for(integer k=0;k<6;k=k+1) progress[k]<=0;
    end
   end
   if(desc_valid&&desc_ready) begin
    progress[pk]<=progress[pk]+1'b1;
    visited[int'(ids[pk*9+:9])%7]<=1;
    if(best==1) begin
     automatic bit last_phase;last_phase=1;
     for(integer k=0;k<6;k=k+1) if(k!=int'(pk)&&progress[k]<(w2?3:4)) last_phase=0;
     if(last_phase) begin
      if(w2) active<=0;
      else begin w2<=1;visited<=0;
       for(integer k=0;k<6;k=k+1) progress[k]<=0;
      end
     end
    end
   end
  end
 end
 end endgenerate
endmodule
