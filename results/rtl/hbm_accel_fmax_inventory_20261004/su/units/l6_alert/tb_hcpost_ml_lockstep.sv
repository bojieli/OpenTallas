`timescale 1ns/1ps
module tb_hcp_ml (input wire clk, input wire rst_n, input wire v, input wire [32*10-1:0] d, output wire [1:0] mism, output wire vo5);
    wire [31:0] o5, o6, o6f; wire v5, v6, v6f; wire f5, f6, f6f;
    ot_dsrom_su_hcpost_lane #(.ML(5), .AL(5)) a (clk, rst_n, v, d[0+:32], d[32+:32], d[64+:32], d[96+:32], d[128+:32], d[160+:32], d[192+:32], d[224+:32], d[256+:32], d[288+:32], v5, o5, f5);
    ot_dsrom_su_hcpost_lane #(.ML(6), .AL(5)) b (clk, rst_n, v, d[0+:32], d[32+:32], d[64+:32], d[96+:32], d[128+:32], d[160+:32], d[192+:32], d[224+:32], d[256+:32], d[288+:32], v6, o6, f6);
    ot_dsrom_su_hcpost_lane_fix #(.ML(6), .AL(5)) c (clk, rst_n, v, d[0+:32], d[32+:32], d[64+:32], d[96+:32], d[128+:32], d[160+:32], d[192+:32], d[224+:32], d[256+:32], d[288+:32], v6f, o6f, f6f);
    reg [32:0] r5; always @(posedge clk) r5 <= {v5, o5};       // ML 6 is one cycle later
    assign vo5 = r5[32];
    assign mism = {rst_n && r5[32] && ({v6f, o6f} != r5), rst_n && r5[32] && ({v6, o6} != r5)};
endmodule
