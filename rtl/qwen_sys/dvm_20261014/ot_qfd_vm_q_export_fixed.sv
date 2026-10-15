`timescale 1ns/1ps
// Compiler-reserved Q window:32 consecutive row reads,RL13,32 consecutive responses/output beats.
// No credits,ready-driven issue,queue or runtime rescheduling. Violations report fault while the compiled cadence continues.
module ot_qfd_vm_q_export_fixed #(parameter integer RL=13,MUT_BEAT=0)(
 input wire clk,rst_n,epoch_begin,input wire [511:0] commit_mask,input wire start_v,
 output wire qr_committed,output wire window_active,
 output wire read_v,output wire [19:0] read_row,input wire rsp_v,input wire [511:0] rsp_data,
 output reg [523:0] q,output reg emitted_done,output reg fault
);
 reg [511:0] committed;
 reg active;reg [6:0] cycle;
 wire emit=active && cycle>=RL && cycle<RL+32;
 wire [4:0] beat=cycle-RL;
 assign qr_committed=&committed;
 assign window_active=active;
 assign read_v=active && cycle<32;
 assign read_row=20'd856+cycle;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin committed<=0;active<=0;cycle<=0;q<=0;emitted_done<=0;fault<=0;end
  else begin
   q[523]<=0;emitted_done<=0;
   committed<=epoch_begin ? commit_mask : committed|commit_mask;
   if(epoch_begin && active)fault<=1;
   if(rsp_v!=emit)fault<=1;
   if(emit)q<={1'b1,3'b001,2'b00,1'b0,beat^(MUT_BEAT!=0 ? 5'd1 : 5'd0),rsp_data};
   if(active)begin
    cycle<=cycle+1'b1;
    if(cycle==RL+31)begin active<=0;emitted_done<=1;end
   end
   if(start_v)begin
    if((active && cycle!=RL+31)||!qr_committed||epoch_begin)fault<=1;
    active<=1;cycle<=0;
   end
  end
endmodule
