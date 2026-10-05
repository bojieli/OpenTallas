`timescale 1ns/1ps
// One actual expert descriptor, one retained source line per SM. The line
// cannot retire until EVERY selected column's real consumer accepts it.
// Out_ready is a TC column-context acceptance, not an invented bulk-copy ACK.
// Does not cache whole experts, compute results or reorder column arithmetic.
module ot_ds_hbm_union_replay #(
 parameter integer ENABLE=0, NSM=2, PM=8, IW=9
)(
 input wire clk,rst_n,
 input wire u_v, output wire u_ready,
 input wire [IW-1:0] u_id, input wire [PM-1:0] u_mask,
 input wire u_last, input wire [NSM*16-1:0] cfg_lines,
 output wire e_valid, input wire e_ready, output wire [IW-1:0] e_id,
 input wire fetch_idle,
 input wire [NSM-1:0] in_valid, output wire [NSM-1:0] in_ready,
 input wire [NSM*1024-1:0] in_data,
 output wire [NSM-1:0] out_valid, input wire [NSM-1:0] out_ready,
 output wire [NSM*1024-1:0] out_data,
 output wire [NSM*$clog2(PM)-1:0] out_col,
 output wire [NSM*16-1:0] out_line,
 output wire [IW-1:0] out_expert,
 output reg expert_done, output reg pass_done, output reg fault
);
generate if(ENABLE==0) begin:g_off
 assign u_ready=0;assign e_valid=0;assign e_id=0;assign in_ready=0;
 assign out_valid=0;assign out_data=0;assign out_col=0;assign out_line=0;assign out_expert=0;
 always @(posedge clk) begin expert_done<=0;pass_done<=0;fault<=0;end
end else begin:g_on
 reg active,issued,last_q;
 reg [IW-1:0] expert;
 reg [PM-1:0] columns;
 reg [15:0] total[0:NSM-1], consumed[0:NSM-1];
 reg [1023:0] data_q[0:NSM-1];
 reg [PM-1:0] pending[0:NSM-1];
 reg have[0:NSM-1];
 reg all_done;
 integer i;
 assign u_ready=!active && fetch_idle && !fault;
 assign e_valid=active && !issued && !fault;
 assign e_id=expert;assign out_expert=expert;
 always @(*) begin
  all_done=issued;
  for(integer s=0;s<NSM;s=s+1)
   if(consumed[s]!=total[s] || have[s]) all_done=0;
 end
 for(genvar s=0;s<NSM;s=s+1) begin:g_sm
  reg [$clog2(PM)-1:0] first;
  always @(*) begin
   first=0;
   for(integer c=PM-1;c>=0;c=c-1) if(pending[s][c]) first=c;
  end
  assign in_ready[s]=active && issued && !have[s] && consumed[s]<total[s] && !fault;
  assign out_valid[s]=have[s] && |pending[s] && !fault;
  assign out_data[s*1024+:1024]=data_q[s];
  assign out_col[s*$clog2(PM)+:$clog2(PM)]=first;
  assign out_line[s*16+:16]=consumed[s];
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin have[s]<=0;pending[s]<=0;consumed[s]<=0;data_q[s]<=0;total[s]<=0;end
   else begin
    if(u_v && u_ready) begin total[s]<=cfg_lines[s*16+:16];consumed[s]<=0;end
    if(in_valid[s] && in_ready[s]) begin
     data_q[s]<=in_data[s*1024+:1024];pending[s]<=columns;have[s]<=1;
    end
    if(out_valid[s] && out_ready[s]) begin
     pending[s][first]<=0;
     if((pending[s] & ~( {{(PM-1){1'b0}},1'b1} << first))==0) begin
      have[s]<=0;consumed[s]<=consumed[s]+1;
     end
    end
   end
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin active<=0;issued<=0;last_q<=0;expert<=0;columns<=0;expert_done<=0;pass_done<=0;fault<=0;end
  else begin
   expert_done<=0;pass_done<=0;
   if(u_v && u_ready) begin
    if(u_mask==0) fault<=1;
    else begin active<=1;issued<=0;expert<=u_id;columns<=u_mask;last_q<=u_last;end
   end
   if(e_valid && e_ready) issued<=1;
   if(active && all_done && fetch_idle && !fault) begin
    active<=0;issued<=0;expert_done<=1;pass_done<=last_q;
   end
  end
 end
end endgenerate
endmodule
