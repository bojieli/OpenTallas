`timescale 1ns/1ps
// Physical-bank-ordered register boundary for four 512-bit VM writes/cycle.
// Upstream transpose fills one slot for each word_addr[1:0]. No 2048-bit
// late rotation is present on the SRAM-facing path.
module ot_v41_vm_gw4_bank_order #(
    parameter integer A = 15
) (
    input wire clk,
    input wire [3:0] in_we,
    input wire [4*(A-2)-1:0] in_addr,
    input wire [2047:0] in_data,
    output reg [3:0] bank_we,
    output reg [4*(A-2)-1:0] bank_addr,
    output reg [2047:0] bank_data
);
    // One local output register per bank. The upstream DMA owns alignment.
    genvar b;
    generate for (b=0; b<4; b=b+1) begin: g_bank
        always @(posedge clk) begin
            bank_we[b] <= in_we[b];
            bank_addr[b*(A-2) +: A-2] <= in_addr[b*(A-2) +: A-2];
            bank_data[b*512 +: 512] <= in_data[b*512 +: 512];
        end
    end endgenerate
endmodule
