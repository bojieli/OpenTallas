`timescale 1ns/1ps
// Local packed collective landing buffer for the TP=4, output-row split w2.
// Each rank contributes seven experts (six routed, sorted by expert ID, then
// shared). Per expert: nine 64-byte flits of contiguous FP8 E4M3 code bytes,
// then two flits of UE8M0 scale bytes in the low byte of each 32-bit word.
// The second scale flit uses only two words. Padding is required to be zero.
// The consumer reads codes and scale bytes directly; no expanded VM write is
// required. This is a standalone boundary, not yet wired into the die ME.
module ot_chip_v41x_w2_packed_spad #(
    parameter integer RANKS = 4,
    parameter integer EXPERTS = 7,
    parameter integer FW = 512,
    parameter integer CW = 10
) (
    input wire clk,
    input wire rst_n,
    input wire wr_valid,
    input wire [1:0] wr_rank,
    input wire [6:0] wr_word,
    input wire [FW-1:0] wr_data,
    output reg wr_fault,
    input wire rd_valid,
    input wire [1:0] rd_rank,
    input wire [2:0] rd_expert,
    input wire [CW-1:0] rd_col,
    output reg rd_valid_q,
    output reg [7:0] rd_code,
    output reg [7:0] rd_scale,
    output reg rd_fault_q
);
    localparam integer CODE_FLITS = 9;
    localparam integer SCALE_FLITS = 2;
    localparam integer FLITS_PER_EXPERT = CODE_FLITS + SCALE_FLITS;
    localparam integer CODE_SIZE = RANKS * EXPERTS * CODE_FLITS;
    localparam integer SCALE_SIZE = RANKS * EXPERTS * SCALE_FLITS;
    reg [FW-1:0] code_mem [0:CODE_SIZE-1];
    reg [FW-1:0] scale_mem [0:SCALE_SIZE-1];
    wire wr_bad = int'(wr_rank) >= RANKS || int'(wr_word) >= EXPERTS * FLITS_PER_EXPERT;
    wire [2:0] wr_expert = 3'(int'(wr_word) / FLITS_PER_EXPERT);
    wire [3:0] wr_local = 4'(int'(wr_word) % FLITS_PER_EXPERT);
    wire [7:0] wr_code_addr = 8'((int'(wr_rank) * EXPERTS + int'(wr_expert)) * CODE_FLITS + int'(wr_local));
    wire [5:0] wr_scale_addr = 6'((int'(wr_rank) * EXPERTS + int'(wr_expert)) * SCALE_FLITS + int'(wr_local) - CODE_FLITS);
    wire rd_bad = int'(rd_rank) >= RANKS || int'(rd_expert) >= EXPERTS || rd_col >= 10'd576;
    wire [7:0] rd_code_addr = 8'((int'(rd_rank) * EXPERTS + int'(rd_expert)) * CODE_FLITS + int'(rd_col[9:6]));
    wire [5:0] rd_scale_addr = 6'((int'(rd_rank) * EXPERTS + int'(rd_expert)) * SCALE_FLITS + int'(rd_col[9]));
    wire [5:0] code_byte = rd_col[5:0];
    wire [3:0] scale_slot = rd_col[8:5];
    reg [FW-1:0] code_q, scale_q;
    reg [5:0] code_byte_q;
    reg [3:0] scale_slot_q;
    reg rd_pending;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_fault <= 0;
            rd_fault_q <= 0;
            rd_valid_q <= 0;
            rd_pending <= 0;
            code_q <= 0;
            scale_q <= 0;
            code_byte_q <= 0;
            scale_slot_q <= 0;
            rd_code <= 0;
            rd_scale <= 0;
        end else begin
            if (wr_valid) begin
                if (wr_bad) wr_fault <= 1;
                else if (int'(wr_local) < CODE_FLITS) code_mem[wr_code_addr] <= wr_data;
                else scale_mem[wr_scale_addr] <= wr_data;
            end
            rd_pending <= rd_valid && !rd_bad;
            rd_fault_q <= rd_valid && rd_bad;
            if (rd_valid && !rd_bad) begin
                code_q <= code_mem[rd_code_addr];
                scale_q <= scale_mem[rd_scale_addr];
                code_byte_q <= code_byte;
                scale_slot_q <= scale_slot;
            end
            rd_valid_q <= rd_pending;
            if (rd_pending) begin
                rd_code <= code_q[code_byte_q*8 +: 8];
                rd_scale <= scale_q[scale_slot_q*32 +: 8];
            end
        end
    end
endmodule
