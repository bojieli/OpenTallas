`timescale 1ns/1ps
// Two VM words of sixteen 32-bit BF16 containers become one 64-byte flit.
module ot_chip_v41x_w2_y_pack2 (
    input wire clk, rst_n,
    input wire in_valid,
    output wire in_ready,
    input wire [1:0] in_rank,
    input wire [6:0] in_word,
    input wire [511:0] in_data,
    output reg out_valid,
    input wire out_ready,
    output reg [1:0] out_rank,
    output reg [5:0] out_word,
    output reg [511:0] out_data,
    output reg fault
);
    reg [1:0] expected_rank;
    reg [6:0] expected_word;
    reg [255:0] half;
    reg [255:0] packed_half;
    integer j;
    assign in_ready = !out_valid || out_ready;
    always @* begin
        packed_half = 0;
        for (j = 0; j < 16; j = j + 1)
            packed_half[j*16 +: 16] = in_data[j*32 +: 16];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            expected_rank <= 0;
            expected_word <= 0;
            half <= 0;
            out_valid <= 0;
            out_rank <= 0;
            out_word <= 0;
            out_data <= 0;
            fault <= 0;
        end else begin
            if (in_ready) out_valid <= 0;
            if (in_valid && in_ready) begin
                if (in_rank != expected_rank || in_word != expected_word) fault <= 1;
                if (!in_word[0]) half <= packed_half;
                else begin
                    out_valid <= 1;
                    out_rank <= in_rank;
                    out_word <= in_word[6:1];
                    out_data <= {packed_half, half};
                end
                if (expected_word == 7'd79) begin
                    expected_word <= 0;
                    expected_rank <= expected_rank + 1'b1;
                end else expected_word <= expected_word + 1'b1;
            end
        end
    end
endmodule
