`timescale 1ns/1ps
// Streaming CRC-16/CCITT-FALSE.  A record may be split into arbitrary beats;
// start initializes the state and last latches the final result.
module ot_crc16_ccitt #(
    parameter integer DATA_W = 64
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 in_valid,
    input  wire                 start,
    input  wire                 last,
    input  wire [DATA_W-1:0]    data,
    output reg                  out_valid,
    output reg [15:0]           crc
);
    integer byte_i;
    integer bit_i;
    reg [15:0] next_crc;
    reg [15:0] work_crc;
    reg fb;

    always @* begin
        work_crc = start ? 16'hffff : crc;
        for (byte_i = 0; byte_i < DATA_W/8; byte_i = byte_i + 1) begin
            for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                fb = work_crc[15] ^ data[byte_i*8 + bit_i];
                work_crc = {work_crc[14:0], 1'b0};
                if (fb)
                    work_crc = work_crc ^ 16'h1021;
            end
        end
        next_crc = work_crc;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            crc <= 16'hffff;
            out_valid <= 1'b0;
        end else begin
            out_valid <= 1'b0;
            if (in_valid) begin
                crc <= next_crc;
                if (last)
                    out_valid <= 1'b1;
            end
        end
    end
endmodule
