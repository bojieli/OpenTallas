`timescale 1ns/1ps
// Hardened core root: endpoint plus actual fixed local alignment registers.
module s81_static_fmt1_core #(parameter integer RANK=0)(
 input wire clk,rst_n,issue_slot,src_valid,input wire[511:0]src_data,
 input wire[31:0]tag,input wire[15:0]seq,input wire last,input wire[3:0]rankmask,
 input wire commit_slot,input wire[31:0]commit_tag,input wire[15:0]commit_seq,
 input wire commit_last,input wire[3:0]commit_rankmask,input wire[59:0]commit_rows,
 output wire tx_valid,output wire[568:0]tx_frame,
 input wire[3:0]remote_v,input wire[2275:0]remote_frame,
 output wire[3:0]vm_we,output wire[59:0]vm_rows,output wire[2047:0]vm_data,
 output wire fault
);
 wire[3:0]rv;wire[2275:0]rf;reg[9:0]local_v;reg[5689:0]local_f;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin local_v<=0;local_f<=0;end
  else begin local_v<={local_v[8:0],tx_valid};local_f<={local_f[5120:0],tx_frame};end
 end
 genvar r;
 generate for(r=0;r<4;r=r+1)begin:P
  if(r==RANK)begin
   assign rv[r]=local_v[9];assign rf[r*569+:569]=local_f[5689:5121];
  end else begin assign rv[r]=remote_v[r];assign rf[r*569+:569]=remote_frame[r*569+:569];end
 end endgenerate
 s81_static_tp4_endpoint #(.RANK(RANK)) e(.*,.rx_valid(rv),.rx_frame(rf));
endmodule
