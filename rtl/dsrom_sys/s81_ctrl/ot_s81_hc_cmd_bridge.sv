`timescale 1ns/1ps
// Native HC capture command endpoint. The generic op is only a job return tag.
// Compiler-owned arg24 is {18zero,epoch4,capture2}; no engine opcode inference.
// Enable only with actual capture_done after final SRAM commit, not busy/idle.
module ot_s81_hc_cmd_bridge #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire e_cmd_v,input wire[83:0] e_cmd_d,output wire e_cmd_ready,
 output reg e_done_v,output reg[7:0] e_done_tag,output reg fault,
 output wire h_cmd_valid,input wire h_cmd_ready,
 output wire[1:0] h_cmd_capture,output wire[9:0] h_cmd_user,
 output wire[20:0] h_cmd_position,output wire[3:0] h_cmd_epoch,
 input wire h_capture_done,input wire[1:0] h_done_capture,
 input wire[9:0] h_done_user,input wire[20:0] h_done_position,
 input wire[3:0] h_done_epoch,input wire h_fault
);
 wire[23:0] arg=e_cmd_d[30:7];
 wire legal=(arg[23:6]==0)&&(arg[1:0]<3);
 reg inflight;
 reg[7:0] tag;
 reg[1:0] capture;
 reg[9:0] user;
 reg[20:0] position;
 reg[3:0] epoch;
 assign e_cmd_ready=ENABLE&&!fault&&!inflight&&h_cmd_ready;
 assign h_cmd_valid=ENABLE&&!fault&&!inflight&&e_cmd_v&&legal;
 assign h_cmd_capture=arg[1:0];
 assign h_cmd_epoch=arg[5:2];
 assign h_cmd_user=e_cmd_d[82:73];
 assign h_cmd_position=e_cmd_d[72:52];
 wire take=h_cmd_valid&&h_cmd_ready;
 wire identity=(h_done_capture==capture)&&(h_done_user==user)&&
               (h_done_position==position)&&(h_done_epoch==epoch);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin inflight<=0;tag<=0;capture<=0;user<=0;position<=0;epoch<=0;
   e_done_v<=0;e_done_tag<=0;fault<=0;end
  else begin
   e_done_v<=0;
   if(h_fault||(e_cmd_v&&(!ENABLE||!legal||inflight||!h_cmd_ready)))fault<=1;
   if(take)begin
    inflight<=1;tag<={e_cmd_d[83],e_cmd_d[6:0]};
    capture<=h_cmd_capture;user<=h_cmd_user;position<=h_cmd_position;epoch<=h_cmd_epoch;
   end
   if(h_capture_done)begin
    if(!ENABLE||!inflight||!identity||fault||h_fault)fault<=1;
    else begin inflight<=0;e_done_v<=1;e_done_tag<=tag;end
   end
  end
 end
endmodule
