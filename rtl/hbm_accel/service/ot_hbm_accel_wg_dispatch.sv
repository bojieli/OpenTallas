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
 reg active,w2;reg [2:0] progress[0:5],wk;
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
   front=(progress[k]<4);setid=int'(ids[k*9+:9])%7;
   for(integer r=0;r<k;r=r+1)
    if(int'(ids[r*9+:9])%7==setid && progress[r]<4) front=0;
   remaining=0;
   for(integer r=0;r<6;r=r+1)
    if(int'(ids[r*9+:9])%7==setid) remaining=remaining+4-int'(progress[r]);
   if(front && (!pk_valid || (!visited[setid] && visited[chosen_set]) ||
      (visited[setid]==visited[chosen_set] && ((!visited[setid]) || remaining>=int'(best))))) begin
    pk_valid=1;pk=3'(k);best=5'(remaining);chosen_set=setid;
   end
  end
 end
 assign task_ready=!active&&!fault;
 assign desc_valid=active&&!fault;
 assign desc_slot=w2?wk:pk;
 assign desc_j0=w2?6'd32:{progress[pk],3'b000};
 assign desc_n=w2?6'd17:6'd8;
 assign desc_keep=!w2&&(progress[pk]!=3);
 assign desc_last=w2&&(wk==5);
 assign busy=active;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin active<=0;w2<=0;wk<=0;visited<=0;fault<=0;
   for(integer k=0;k<6;k=k+1) progress[k]<=0;
  end else begin
   if(task_valid&&task_ready) begin
    if(!legal) fault<=1;
    else begin active<=1;w2<=0;wk<=0;visited<=0;
     for(integer k=0;k<6;k=k+1) progress[k]<=0;
    end
   end
   if(desc_valid&&desc_ready) begin
    if(w2) begin
     if(wk==5) active<=0;else wk<=wk+1'b1;
    end else begin
     progress[pk]<=progress[pk]+1'b1;
     visited[int'(ids[pk*9+:9])%7]<=1;
     if(best==1) begin
      automatic bit last_gu;last_gu=1;
      for(integer k=0;k<6;k=k+1) if(k!=int'(pk)&&progress[k]<4) last_gu=0;
      if(last_gu) begin w2<=1;wk<=0;end
     end
    end
   end
  end
 end
 end endgenerate
endmodule
