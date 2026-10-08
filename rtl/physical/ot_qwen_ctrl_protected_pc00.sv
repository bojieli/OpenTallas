`timescale 1ns/1ps
module ot_qwen_ctrl_protected_pc00(
 input wire clk,rst_n,cmd_v,input wire [31:0] cmd,
 input wire [2:0] read_credit,
 output wire cmd_credit,row_v,output wire [2:0] row_op,
 output wire [4:0] row_bank,output wire [18:0] row_row,
 output wire col_v,output wire [4:0] col_bank,col_col,
 output wire col_we,busy,fault
);
 ot_qwen_ctrl_pc_protected #(.ENABLE(1),.PC(0)) u(.*);
endmodule
