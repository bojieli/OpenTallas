`timescale 1ns/1ps
// Distinct real physical masters. Each owns the same one-edge packet hardware
// at its literal width; H/V are separately routed and exported pin contracts.
module qkh_packet_h263 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [262:0] d,output wire [262:0] q);
 ot_qkh_packet_pipe #(.W(263),.MUT(MUT)) u_pipe (.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
module qkh_packet_v263 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [262:0] d,output wire [262:0] q);
 ot_qkh_packet_pipe #(.W(263),.MUT(MUT)) u_pipe (.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
module qkh_packet_h256 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [255:0] d,output wire [255:0] q);
 ot_qkh_packet_pipe #(.W(256),.MUT(MUT)) u_pipe (.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
module qkh_packet_v256 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [255:0] d,output wire [255:0] q);
 ot_qkh_packet_pipe #(.W(256),.MUT(MUT)) u_pipe (.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
module qkh_packet_v34 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [33:0] d,output wire [33:0] q);
 ot_qkh_packet_pipe #(.W(34),.MUT(MUT)) u_pipe (.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
module qkh_packet_v16 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [15:0] d,output wire [15:0] q);
 ot_qkh_packet_pipe #(.W(16),.MUT(MUT)) u_pipe (.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
