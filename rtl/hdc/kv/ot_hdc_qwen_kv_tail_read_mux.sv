`timescale 1ns/1ps
// Read companion to ot_hdc_qwen_kv_write_adapter. Each tile parity has SW
// independent 1R1W banks; the existing streamer issues at most one tail-word
// read per parity in a cycle. bank_q is the synchronous, one-cycle SRAM read
// result. The selected bank is delayed by the same cycle before output muxing.
module ot_hdc_qwen_kv_tail_read_mux #(
    parameter integer SW = 8,
    parameter integer AW = 24,
    parameter integer LOG_HD = 7,
    parameter integer LOG_TW = 2
) (
    input  wire clk, rst_n,
    input  wire [1:0] rd_v,
    input  wire [2*AW-1:0] rd_word,
    output reg  [2*SW-1:0] bank_re,
    output reg  [2*SW*AW-1:0] bank_row,
    input  wire [2*SW*128-1:0] bank_q,
    output wire [1:0] rd_valid,
    output wire [255:0] rd_data,
    output reg addr_error
);
    localparam integer LG_SW = $clog2(SW);
    reg [LG_SW-1:0] sel0, sel1;
    reg [1:0] valid_q;
    wire [AW-1:0] word0 = rd_word[0 +: AW];
    wire [AW-1:0] word1 = rd_word[AW +: AW];
    wire [AW-1:0] row0 =
        ((word0 >> (LOG_HD + LOG_TW)) << (LOG_HD - LG_SW)) |
        ((word0 & ((1 << LOG_HD) - 1)) >> LG_SW);
    wire [AW-1:0] row1 =
        ((word1 >> (LOG_HD + LOG_TW)) << (LOG_HD - LG_SW)) |
        ((word1 & ((1 << LOG_HD) - 1)) >> LG_SW);
    always @(*) begin
        bank_re = 0; bank_row = 0;
        if (rd_v[0] && !word0[LOG_HD]) begin
            bank_re[word0[LG_SW-1:0]] = 1'b1;
            bank_row[word0[LG_SW-1:0]*AW +: AW] = row0;
        end
        if (rd_v[1] && word1[LOG_HD]) begin
            bank_re[SW + word1[LG_SW-1:0]] = 1'b1;
            bank_row[(SW + word1[LG_SW-1:0])*AW +: AW] = row1;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sel0 <= 0; sel1 <= 0; valid_q <= 0; addr_error <= 0;
        end else begin
            valid_q[0] <= rd_v[0] && !word0[LOG_HD];
            valid_q[1] <= rd_v[1] && word1[LOG_HD];
            if (rd_v[0] && word0[LOG_HD]) addr_error <= 1'b1;
            if (rd_v[1] && !word1[LOG_HD]) addr_error <= 1'b1;
            sel0 <= word0[LG_SW-1:0];
            sel1 <= word1[LG_SW-1:0];
        end
    end
    assign rd_valid = valid_q;
    assign rd_data[0 +: 128] = bank_q[sel0*128 +: 128];
    assign rd_data[128 +: 128] = bank_q[(SW + sel1)*128 +: 128];
endmodule
