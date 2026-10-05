`timescale 1ns/1ps
// One 128-bit bit-slice of a four-bank, 512-bit/word VM gather destination.
// Four copies carry the complete 64-byte word.  The four input words have
// consecutive word addresses.  The bank row includes the carry when the
// first word is not four-word aligned.  A register separates the collective
// output network from the SRAM write pins. Two pipeline stages let the
// high-fanout four-way data rotation occur between local registers, while
// accepting a fresh four-word beat each cycle.
module ot_v41_vm_gw4_slice #(
    parameter integer A = 15,
    parameter integer BW = 128
) (
    input wire clk,
    input wire [A-1:0] base_word,
    input wire [3:0] in_v,
    input wire [4*BW-1:0] in_data,
    output reg [3:0] bank_we,
    output reg [4*(A-2)-1:0] bank_addr,
    output reg [4*BW-1:0] bank_data
);
    reg [A-1:0] base_q;
    reg [3:0] valid_q;
    reg [4*BW-1:0] data_q;
    // Bank-local control replicas keep one selector from driving all 512 data
    // bits. One 2-bit replica selects each 16-bit slice of each bank.
    (* keep = "true" *) reg [1:0] select_q [0:3][0:BW/16-1];
    always @(posedge clk) begin
        base_q <= base_word;
        valid_q <= in_v;
        data_q <= in_data;
    end
    genvar b, g;
    generate for (b=0; b<4; b=b+1) begin: g_bank
        wire [1:0] lane = select_q[b][0];
        wire [A-1:0] word_addr = base_q + {{(A-2){1'b0}}, lane};
        always @(posedge clk) begin
            bank_we[b] <= valid_q[lane];
            bank_addr[b*(A-2) +: A-2] <= word_addr[A-1:2];
        end
        for (g=0; g<BW/16; g=g+1) begin: g_group
            wire [1:0] sl = select_q[b][g];
            always @(posedge clk) begin
                select_q[b][g] <= 2'(b) - base_word[1:0];
                case (sl)
                    2'd0: bank_data[b*BW+g*16 +: 16] <= data_q[0*BW+g*16 +: 16];
                    2'd1: bank_data[b*BW+g*16 +: 16] <= data_q[1*BW+g*16 +: 16];
                    2'd2: bank_data[b*BW+g*16 +: 16] <= data_q[2*BW+g*16 +: 16];
                    2'd3: bank_data[b*BW+g*16 +: 16] <= data_q[3*BW+g*16 +: 16];
                endcase
            end
        end
    end endgenerate
endmodule
