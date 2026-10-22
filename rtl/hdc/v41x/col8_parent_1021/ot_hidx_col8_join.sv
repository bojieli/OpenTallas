`timescale 1ns/1ps
module ot_hidx_col8_join(input wire clk,rst_n,input wire[31:0]s,input wire f,p0,p1,p2,p3,output reg[31:0]score,output reg fault,o0,o1,o2,o3);
always@(posedge clk)begin score<=s;fault<=f;end
always@(posedge clk or negedge rst_n)if(!rst_n)begin o0<=0;o1<=0;o2<=0;o3<=0;end else begin o0<=p0;o1<=p1;o2<=p2;o3<=p3;end
endmodule
