`timescale 1ns/1ps
// qwen_glue_w514 (PM-H-S NL t_out face master, r13 NL helper 2026-10-15): qwen_glue_v514's exact RTL (one capture,
// 3-edge local reset release) under the NL face name. Physical convention (stated explicitly): W = q (output toward the
// tile W face), E = d, R0 placement; pins y = 5.292 + 0.192 k (k = 0..513) = the even TB slots s = 2k of the tile plan.
module qwen_glue_w514 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [513:0]d,output wire [513:0]q);
 ot_qkh_packet_pipe #(.W(514),.MUT(MUT)) u_pipe(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
