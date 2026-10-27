`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qkvd_kcmd_tap -- qwen-1010/b 2026-10-11: one station of the KV-die stream-command chain (hclk), beside one controller
// head (ot_qwen_ctrl_pc_head).  The issuer ot_qkvd_kv_desc sends {op[1:0], 10'b0, layer[5:0], T[13:0]} (op 0 DESC,
// 1 GO) through an async FIFO into the chain; every station registers the word on to the next (o_*) and hands its own
// head the controller command (c_*):
//   DESC -> cmd 0 {n[10:0], row[18:0]} with row = ROW0 + layer (CONTRACT map v2: one HBM row index a layer) and
//           n = 1,024 sectors (the PC's whole layer region {v, g, t[6], t[13:9], t[5:3]}; at T < 8,192 the region's
//           positions >= T are streamed too and dropped by the landing -- the price point is T = 8,192);
//   GO   -> cmd 1.
// G (the PC's t[2:0] group) and ST (its stack t[8:7]) are this station's identity, kept for the landing's own map.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kcmd_tap #(
    parameter integer G    = 0,
    parameter integer ST   = 0,
    parameter integer ROW0 = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_d,
    output reg         o_v,
    output reg  [31:0] o_d,
    output reg         c_v,
    output reg  [31:0] c_d
);
    wire [1:0]  op    = i_d[31:30];
    wire [5:0]  layer = i_d[19:14];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; c_v <= 1'b0; end
        else begin o_v <= i_v; c_v <= i_v && (op == 2'd0 || op == 2'd1); end
    always @(posedge clk) begin
        o_d <= i_d;
        c_d <= (op == 2'd0) ? {2'd0, 11'd1024, 19'(ROW0 + layer)} : {2'd1, 30'd0};
    end
endmodule
