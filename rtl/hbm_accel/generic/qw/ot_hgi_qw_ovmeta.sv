`timescale 1ns/1ps
`default_nettype none
// Existing OV write row state, separated without an additional registered edge.
module ot_hgi_qw_ovmeta(
 input wire clk,rst_n,input wire [1:0] row_j,
 input wire i_v,input wire [14:0] i_sec,input wire [2:0] i_n,
 output reg [7:0] o_v,output reg [31:0] o_slot,output reg [119:0] o_sec
);
 reg [1:0] f_row;always @(posedge clk)f_row<=row_j;
 always @(posedge clk)begin
  for(integer j=0;j<8;j=j+1)begin
   o_slot[j*4+:4]<=4'(1)<<2'((int'(f_row)*8+j)-i_sec[4:0]);
   o_sec[j*15+:15]<=i_sec+15'(5'((int'(f_row)*8+j)-i_sec[4:0]));
  end
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)o_v<=0;
  else for(integer j=0;j<8;j=j+1)o_v[j]<=i_v&&(5'((int'(f_row)*8+j)-i_sec[4:0])<5'(i_n));
endmodule
`default_nettype wire
