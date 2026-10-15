`timescale 1ns/1ps
// Fixed-schedule SU/VM -> SVC probability boundary. A row contains 16
// FP32 head values. Even/odd natural rows become the low/high 256 bits of
// one service PV word. No ready/credit port: the compiler reserves this
// one-cycle conversion and two-row packing. An odd last row pads high=0.
// Registered output appears on the edge accepting the second/last row.
// Any gap between even and odd rows is permitted only if statically reserved;
// row ordering and exact length are checked without changing the timeline.
module ot_s81_svc_probability_pack #(parameter integer MUT = 0) (
    input wire clk, rst_n,
    input wire go,
    input wire [9:0] rows,
    input wire in_v,
    input wire [9:0] in_row,
    input wire [511:0] in_d,
    output reg out_v,
    output reg [8:0] out_word,
    output reg [511:0] out_d,
    output reg done,
    output reg fault
);
    reg active;
    reg [9:0] total, next_row;
    reg [255:0] low;
    wire [255:0] converted;
    genvar h;
    generate for (h=0; h<16; h=h+1) begin : g_head
        wire [31:0] x = in_d[h*32 +: 32];
        wire round_up = x[15] && (x[16] || (|x[14:0]));
        // Same finite probability rule as ot_dsrom_su_softmax.bf16.
        assign converted[h*16 +: 16] = x[31:16] + ((MUT == 1) ? 16'd0 : {15'd0,round_up});
    end endgenerate
    // Payload flops are unreset; valid/control reset owns their visibility.
    always @(posedge clk) if(in_v) begin
        if(in_row[0] || in_row+10'd1==total) begin
            out_word<=in_row[9:1];
            out_d<=in_row[0] ? ((MUT==2) ? {low,converted} : {converted,low}) : {256'd0,converted};
        end else low<=converted;
    end
    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active<=0; total<=0; next_row<=0;
            out_v<=0; done<=0; fault<=0;
        end else begin
            out_v<=0; done<=0;
            if (go) begin
                if (active || rows==0 || rows>640 || in_v) fault<=1;
                active<=1; total<=rows; next_row<=0;
            end
            if (in_v) begin
                if (!active || in_row != next_row || in_row >= total) fault<=1;
                for (j=0;j<16;j=j+1)
                    if (in_d[j*32 + 23 +: 8]==8'hff || (in_d[j*32+31] && (|in_d[j*32 +:31]))) fault<=1;
                if (in_row[0] || in_row+10'd1==total) begin
                    out_v<=1;
                end
                next_row<=next_row+10'd1;
                if (in_row+10'd1==total) begin active<=0; done<=1; end
            end
        end
    end
endmodule
