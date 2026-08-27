`timescale 1ns/1ps
// Streaming CRC-32C/Castagnoli with reflected input/output and the ICD's
// little-endian byte order.
module ot_crc32c #(
    parameter integer DATA_W = 64
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 in_valid,
    input  wire                 start,
    input  wire                 last,
    input  wire [DATA_W-1:0]    data,
    output reg                  out_valid,
    output reg [31:0]           crc
);
    integer byte_i;
    integer bit_i;
    reg [31:0] work_crc;
    reg [31:0] next_crc;
    reg fb;

    always @* begin
        work_crc = start ? 32'hffffffff : crc;
        for (byte_i = 0; byte_i < DATA_W/8; byte_i = byte_i + 1) begin
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                fb = work_crc[0] ^ data[byte_i*8 + bit_i];
                work_crc = work_crc >> 1;
                if (fb)
                    work_crc = work_crc ^ 32'h82f63b78;
            end
        end
        next_crc = work_crc ^ 32'hffffffff;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            crc <= 32'hffffffff;
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
