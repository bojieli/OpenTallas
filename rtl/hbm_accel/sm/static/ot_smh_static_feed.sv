`timescale 1ns/1ps
// Production-shape static S1 feed. The compiler supplies every issue slot,
// including padding slots and format launch slots. Arrival faults never stall.
// command[82:40] = expected request {v,address32,tag10}; observational only.
// command[39:30] = expected response tag; command[29] = expected packet valid.
// command[28:26] = {format_launch,format2}.
// command[25:0] = {valid,first,last,row12,group_last,slot3,xaddr7}.
// packet[1098:0] = {valid,tag10,scale64,weights1024}.
module ot_smh_static_feed #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [82:0] command,input wire [1098:0] packet,
 output reg [42:0] expected_request,output reg fault,
 output wire [1081:0] lt0,lt1,output wire [569:0] lb0,lb1,
 output reg [11:0] fm
);
 reg [1087:0] s1_w;
 reg [25:0] s1_c;
 reg [25:0] hc[0:3];
 reg [1055:0] hw0,hw2;
 reg [543:0] hw1,hw3;
 integer k;
 always @(posedge clk) begin
   s1_w<=packet[1087:0] ^ ((MUT==1)?1088'd8:1088'd0);
   hw0<=s1_w[1055:0];hw2<=s1_w[1055:0];
   hw1<={s1_w[1087:1056],s1_w[1023:512]};
   hw3<={s1_w[1087:1056],s1_w[1023:512]};
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   fault<=0;expected_request<=0;fm<=0;
   s1_c<=0;for(k=0;k<4;k=k+1)hc[k]<=0;
  end else begin
   s1_c<=command[25:0];
   for(k=0;k<4;k=k+1)hc[k]<=s1_c;
   expected_request<=command[82:40];
   for(k=0;k<4;k=k+1)fm[3*k+:3]<=command[28:26];
   if(packet[1098]!=command[29] ||
      (command[29] && packet[1097:1088]!=command[39:30]) ||
      (command[25] && !command[29]))fault<=1;
  end
 assign lt0={hc[0],hw0};assign lb0={hc[1],hw1};
 assign lt1={hc[2],hw2};assign lb1={hc[3],hw3};
endmodule
