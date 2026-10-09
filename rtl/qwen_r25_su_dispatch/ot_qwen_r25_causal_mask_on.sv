`timescale 1ns/1ps
module ot_qwen_r25_causal_mask_on #(parameter OWNER_W=74)(
 input wire clk,rst_n,in_v,out_rdy,input wire [1:0] in_checked,
 input wire [OWNER_W-1:0] in_owner,input wire [79:0] in_query_positions,
 input wire [2:0] in_queries,input wire [19:0] in_row0,
 output wire in_rdy,out_v,fault,output wire [OWNER_W-1:0] out_owner,
 output wire [19:0] out_row0,output wire [83:0] out_valid_lengths,
 output wire [127:0] out_live
);
 ot_qwen_r25_causal_mask #(.ENABLE(1),.CAPACITY(8224),.OWNER_W(OWNER_W)) u(.*);
endmodule
