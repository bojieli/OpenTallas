`timescale 1ns/1ps
// Explicit first register of the existing HUBW packet pipeline. Remaining
// HUBW-1 stages preserve the original total delay. Receipt means this real
// register owns the data; it is not merely a SRAM response or arithmetic done.
module ot_hbm_collective_hub_capture #(parameter W=544,FRAME_W=176)(
 input wire clk,rst_n,in_valid,input wire[W-1:0] in_packet,
 input wire[FRAME_W-1:0] in_frame,
 output reg out_valid,output reg[W-1:0] out_packet,
 output wire captured_valid,output wire[15:0] captured_index,
 output reg[FRAME_W-1:0] captured_frame
);
 always@(posedge clk or negedge rst_n)begin
 if(!rst_n)out_valid<=0;
 else begin
 out_valid<=in_valid;
 if(in_valid)begin out_packet<=in_packet;captured_frame<=in_frame;end
 end end
 assign captured_valid=out_valid;
 assign captured_index=out_packet[W-32+:16];
endmodule
