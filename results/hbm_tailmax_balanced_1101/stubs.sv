`timescale 1ns/1ps
module ot_hdc_fp32_mul_fast(input clk,rst_n,valid_in,input [31:0] a,b,output [31:0] y,output [1:0] err,output valid_out);assign y=0;assign err=0;assign valid_out=0;endmodule
module ot_hdc_fp32_add_fast(input clk,rst_n,valid_in,input [31:0] a,b,output [31:0] y,output [1:0] err,output valid_out);assign y=0;assign err=0;assign valid_out=0;endmodule
module ot_hdc_v41x_exp #(parameter integer LM=3,LA=3)(input clk,rst_n,v,input [31:0] x,output [31:0] y,output vo,fault);assign y=0;assign vo=0;assign fault=0;endmodule
module ot_hdc_v41x_fdiv(input clk,rst_n,v,input [31:0] a,b,output [31:0] y,output vo,fault);assign y=0;assign vo=0;assign fault=0;endmodule
