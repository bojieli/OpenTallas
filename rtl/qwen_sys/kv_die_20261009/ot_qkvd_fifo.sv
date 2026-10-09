`timescale 1ns/1ps
// kv-die 2026-10-09: flop FIFO for the ROM die <-> KV die adapter (ot_qkvd_d2d) and the KV-die sequencer.  Write is
// registered, the head is read from the array (first-word fall-through); count / empty / full move with the write.
module ot_qkvd_fifo #(
    parameter integer W = 528,
    parameter integer D = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire [W-1:0] dout,
    output wire         empty,
    output wire         full,
    output reg  [$clog2(D+1)-1:0] count
);
    localparam integer AW = (D > 1) ? $clog2(D) : 1;
    reg [W-1:0]  mem [0:D-1];
    reg [AW-1:0] wp, rp;
    assign dout  = mem[rp];
    assign empty = (count == 0);
    assign full  = (count == D[$clog2(D+1)-1:0]);
    always @(posedge clk) if (push) mem[wp] <= din;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; count <= 0; end
        else begin
            if (push) wp <= (wp == AW'(D - 1)) ? {AW{1'b0}} : wp + 1'b1;
            if (pop)  rp <= (rp == AW'(D - 1)) ? {AW{1'b0}} : rp + 1'b1;
            count <= count + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        end
endmodule
