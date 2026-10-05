`timescale 1ns/1ps
// Lossless TP=4 w2 activation packer. One input is sixteen 32-bit VM entries;
// four FP8-code inputs become one 64-byte link flit. Each 576-code expert has
// 36 code inputs followed by two inputs holding 18 UE8M0 scale bytes in the
// low byte of 32-bit entries. Scales remain in 32-bit slots in link flits 9/10
// to match the 77-flit per-rank, seven-expert contract.
module ot_chip_v41x_w2_pack4 (
    input wire clk, rst_n,
    input wire in_valid,
    output wire in_ready,
    input wire [1:0] in_rank,
    input wire [2:0] in_expert,
    input wire [5:0] in_word,
    input wire [511:0] in_data,
    output reg out_valid,
    input wire out_ready,
    output reg [1:0] out_rank,
    output reg [6:0] out_word,
    output reg [511:0] out_data,
    output reg fault
);
    reg [1:0] expected_rank;
    reg [2:0] expected_expert;
    reg [5:0] expected_word;
    reg [511:0] acc;
    reg [511:0] assembled;
    integer lane, j;
    wire accept = in_valid && in_ready;
    assign in_ready = !out_valid || out_ready;
    always @* begin
        assembled = (in_word[1:0] == 0) ? 512'b0 : acc;
        for (j = 0; j < 16; j = j + 1)
            assembled[(in_word[1:0]*16+j)*8 +: 8] = in_data[j*32 +: 8];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            expected_rank <= 0;
            expected_expert <= 0;
            expected_word <= 0;
            acc <= 0;
            out_valid <= 0;
            out_rank <= 0;
            out_word <= 0;
            out_data <= 0;
            fault <= 0;
        end else begin
            if (in_ready) out_valid <= 0;
            if (accept) begin
                if (in_rank != expected_rank || in_expert != expected_expert || in_word != expected_word)
                    fault <= 1;
                if (in_word < 6'd36) begin
                    acc <= assembled;
                    if (in_word[1:0] == 2'd3) begin
                        out_valid <= 1;
                        out_rank <= in_rank;
                        out_word <= in_expert*7'd11 + {3'b0, in_word[5:2]};
                        out_data <= assembled;
                    end
                end else begin
                    out_valid <= 1;
                    out_rank <= in_rank;
                    out_word <= in_expert*7'd11 + 7'd9 + {6'b0, in_word[0]};
                    out_data <= 0;
                    for (lane = 0; lane < 16; lane = lane + 1)
                        if (in_word == 6'd36 || lane < 2)
                            out_data[lane*32 +: 8] <= in_data[lane*32 +: 8];
                end
                if (expected_word == 6'd37) begin
                    expected_word <= 0;
                    if (expected_expert == 3'd6) begin
                        expected_expert <= 0;
                        expected_rank <= expected_rank + 1'b1;
                    end else expected_expert <= expected_expert + 1'b1;
                end else expected_word <= expected_word + 1'b1;
            end
        end
    end
endmodule
