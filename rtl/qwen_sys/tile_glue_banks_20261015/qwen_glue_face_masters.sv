`timescale 1ns/1ps
// Full-word compute face captures. Physical21.6x75.6 slots give PG/pin margin
// without splitting a514-bit parent face into two tall overlapping banks.
module qwen_glue_v514 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [513:0]d,output wire [513:0]q);
 ot_qkh_packet_pipe #(.W(514),.MUT(MUT)) u_pipe(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
module qwen_glue_v508 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [507:0]d,output wire [507:0]q);
 ot_qkh_packet_pipe #(.W(508),.MUT(MUT)) u_pipe(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
