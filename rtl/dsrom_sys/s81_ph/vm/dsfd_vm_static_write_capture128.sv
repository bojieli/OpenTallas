`timescale 1ns/1ps
// First existing scatter stage, one bank-local 156-bit record. Independent pin/root.
module dsfd_vm_static_write_capture128(
 input wire ck,rst_n,input wire i_v,i_we,input wire [13:0] i_row,
 input wire [3:0] i_mask,input wire [127:0] i_data,input wire [7:0] i_tag,
 output reg o_v,o_we,output reg [13:0] o_row,
 output reg [3:0] o_mask,output reg [127:0] o_data,output reg [7:0] o_tag
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 always @(posedge ck or negedge rn)if(!rn)o_v<=0;else o_v<=i_v;
 always @(posedge ck)begin o_we<=i_we;o_row<=i_row;o_mask<=i_mask;o_data<=i_data;o_tag<=i_tag;end
endmodule
