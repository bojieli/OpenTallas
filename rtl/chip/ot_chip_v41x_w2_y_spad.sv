`timescale 1ns/1ps
// Finished w2 row-split output: 1,280 BF16 values per rank, 40 packed flits.
// hc_post reads the BF16 value directly; no 32-bit-element VM expansion.
module ot_chip_v41x_w2_y_spad #(
    parameter integer RANKS = 4,
    parameter integer FW = 512
) (
    input wire clk, rst_n,
    input wire wr_valid,
    input wire [1:0] wr_rank,
    input wire [5:0] wr_word,
    input wire [FW-1:0] wr_data,
    output reg wr_fault,
    input wire rd_valid,
    input wire [1:0] rd_rank,
    input wire [10:0] rd_col,
    output reg rd_valid_q,
    output reg [15:0] rd_bf16,
    output reg rd_fault_q
);
    localparam integer WORDS = 40;
    reg [FW-1:0] mem [0:RANKS*WORDS-1];
    wire wr_bad = int'(wr_rank) >= RANKS || wr_word >= 6'd40;
    wire rd_bad = int'(rd_rank) >= RANKS || rd_col >= 11'd1280;
    wire [7:0] wr_addr = 8'(int'(wr_rank)*WORDS + int'(wr_word));
    wire [7:0] rd_addr = 8'(int'(rd_rank)*WORDS + int'(rd_col[10:5]));
    reg [FW-1:0] data_q;
    reg [4:0] slot_q;
    reg pending;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_fault <= 0;
            rd_fault_q <= 0;
            rd_valid_q <= 0;
            pending <= 0;
            data_q <= 0;
            slot_q <= 0;
            rd_bf16 <= 0;
        end else begin
            if (wr_valid) begin
                if (wr_bad) wr_fault <= 1;
                else mem[wr_addr] <= wr_data;
            end
            pending <= rd_valid && !rd_bad;
            rd_fault_q <= rd_valid && rd_bad;
            if (rd_valid && !rd_bad) begin
                data_q <= mem[rd_addr];
                slot_q <= rd_col[4:0];
            end
            rd_valid_q <= pending;
            if (pending) rd_bf16 <= data_q[slot_q*16 +: 16];
        end
    end
endmodule
