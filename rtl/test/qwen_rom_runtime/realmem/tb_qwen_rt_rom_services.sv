`timescale 1ns/1ps
// Standalone bench top for the REAL_MEM ROM services: one scale-ROM port bank (13 x
// ot_rom_4096x266_m8) and the INT8 embedding ROM (2 x 2,374 + 3 macros).  Driven by
// tb_qwen_rt_rom_services.cpp, which preloads via masks and checks every read against the image.
module tb_qwen_rt_rom_services (
    input  wire clk, input wire rst_n,
    input  wire s_re, input wire [23:0] s_addr, output wire [255:0] s_q, output wire s_fault,
    input  wire c_re, input wire [23:0] c_addr, output wire [511:0] c_q,
    input  wire e_re, input wire [17:0] e_addr, output wire [15:0] e_q, output wire e_fault
);
    ot_qwen_rt_rom_bank #(.NB(13)) u_bank (.clk(clk), .rst_n(rst_n), .re(s_re), .addr(s_addr), .q(s_q), .addr_fault(s_fault));
    ot_qwen_rt_embed_rom u_emb (.clk(clk), .rst_n(rst_n), .code_re(c_re), .code_addr(c_addr), .code_q(c_q),
                                .scale_re(e_re), .scale_addr(e_addr), .scale_q(e_q), .fault(e_fault));
endmodule
