`timescale 1ps/1ps
module mechanism(input wire clk,input wire[2247:0]x,output wire[280:0] writer_kq0,output wire[280:0] writer_kq1,output wire[280:0] writer_kq2,output wire[280:0] writer_kq3,output wire[280:0] writer_kq4,output wire[280:0] writer_kq5,output wire[280:0] writer_kq6,output wire[280:0] writer_kq7,output wire writer_fault);
assign writer_kq0=x[0*281+:281];
assign writer_kq1=x[1*281+:281];
assign writer_kq2=x[2*281+:281];
assign writer_kq3=x[3*281+:281];
assign writer_kq4=x[4*281+:281];
assign writer_kq5=x[5*281+:281];
assign writer_kq6=x[6*281+:281];
assign writer_kq7=x[7*281+:281];
assign writer_fault=^x;endmodule
