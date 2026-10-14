`timescale 1ns/1ps
// Connect the streamer's two logical tail read ports to the vector writer's
// 2*SW FP8 tail banks. The compact streamer address is {layer/head, dimension};
// the port number supplies tile parity. Reads and writes share each bank's
// independent 1R1W ports, including reads made by the closed-tile flush.
module ot_hdc_qwen_kv_tail_bank_port #(
    parameter integer SW = 8,
    parameter integer AW = 24,
    parameter integer LOG_HD = 7,
    parameter integer LOG_TW = 2,
    parameter integer LLG = 3,
    parameter integer W = 16
) (
    input wire clk, rst_n,
    input wire [1:0] tl_re,
    input wire [2*(LLG+LOG_HD)-1:0] tl_raddr,
    output wire [2*W*16-1:0] tl_q,
    output wire [2*SW-1:0] bank_re,
    output wire [2*SW*AW-1:0] bank_row,
    input wire [2*SW*128-1:0] bank_q,
    output wire addr_error
);
    localparam integer TAW = LLG + LOG_HD;
    wire [2*AW-1:0] word;
    wire [1:0] rd_valid;
    wire [255:0] rd_data;
    genvar p, lane;
    generate for (p=0; p<2; p=p+1) begin : g_word
        assign word[p*AW +: AW] =
            (AW'(tl_raddr[p*TAW+LOG_HD +: LLG]) << (LOG_HD+LOG_TW)) |
            (AW'(p) << LOG_HD) |
            AW'(tl_raddr[p*TAW +: LOG_HD]);
    end endgenerate
    ot_hdc_qwen_kv_tail_read_mux #(.SW(SW), .AW(AW), .LOG_HD(LOG_HD), .LOG_TW(LOG_TW)) u_mux (
        .clk(clk), .rst_n(rst_n), .rd_v(tl_re), .rd_word(word),
        .bank_re(bank_re), .bank_row(bank_row), .bank_q(bank_q),
        .rd_valid(rd_valid), .rd_data(rd_data), .addr_error(addr_error));
    function automatic [15:0] fp8_to_bf16(input [7:0] c);
        reg [3:0] e;
        reg [2:0] m;
        begin
            e = c[6:3]; m = c[2:0];
            if (e != 0) fp8_to_bf16 = {c[7], (8'(e) + 8'd120), m, 4'b0};
            else if (m == 0) fp8_to_bf16 = {c[7], 15'b0};
            else if (m == 1) fp8_to_bf16 = {c[7], 8'd118, 7'b0};
            else if (m < 4) fp8_to_bf16 = {c[7], 8'd119, m[0], 6'b0};
            else fp8_to_bf16 = {c[7], 8'd120, m[1:0], 5'b0};
        end
    endfunction
    generate for (p=0; p<2; p=p+1) begin : g_expand
        for (lane=0; lane<W; lane=lane+1) begin : g_lane
            assign tl_q[(p*W+lane)*16 +: 16] = rd_valid[p] ?
                fp8_to_bf16(rd_data[(p*W+lane)*8 +: 8]) : 16'b0;
        end
    end endgenerate
endmodule
