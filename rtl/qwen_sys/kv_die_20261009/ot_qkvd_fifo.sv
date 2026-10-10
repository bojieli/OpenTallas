`timescale 1ns/1ps
// kv-die 2026-10-09: flop FIFO for the ROM die <-> KV die adapter (ot_qkvd_d2d) and the KV-die sequencer.  Write is
// registered, the head is read from the array (first-word fall-through); count / empty / full move with the write.
// RH = 1 (timing successor, qfd_d2d_rom_b route TT -120.5 / SS -492: rp -> the D:1 head mux -> pop / class decode /
// r_d, 18-23 levels): the head is a REGISTER refilled from the array (or bypassed from din when the array is empty), so
// dout / empty are flops.  Same first-word latency (a word pushed at edge t is at dout after t), same count / full.
// 2026-10-10: the array is written on every push (no pop term in the write enable); a bypassed word also leaves the
// array that edge.  Cycle-identical to the previous RH 1.
module ot_qkvd_fifo #(
    parameter integer W = 528,
    parameter integer D = 8,
    parameter integer RH = 0
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
    assign full  = (count == D[$clog2(D+1)-1:0]);
    generate if (RH == 0) begin : g_ff
        assign dout  = mem[rp];
        assign empty = (count == 0);
        always @(posedge clk) if (push) mem[wp] <= din;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin wp <= 0; rp <= 0; count <= 0; end
            else begin
                if (push) wp <= (wp == AW'(D - 1)) ? {AW{1'b0}} : wp + 1'b1;
                if (pop)  rp <= (rp == AW'(D - 1)) ? {AW{1'b0}} : rp + 1'b1;
                count <= count + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            end
    end else begin : g_rh
        reg [W-1:0] hd;
        reg         hv;
        reg [$clog2(D+1)-1:0] mn;          // words in the array (behind the head)
        // every push writes the array (the write enable is the registered push alone: qkd_d2d_b TT -97.9, the TX grant ->
        // bypass -> array write enable of 400 x 528 flops); a bypassed word is consumed from the array the same edge
        wire        take = !hv || pop;     // the head register loads this edge
        wire        byp  = take && (mn == 0) && push;
        wire        ld   = take && (mn != 0);
        wire        adv  = ld || byp;      // the array's oldest word leaves (to the head)
        assign dout  = hd;
        assign empty = !hv;
        always @(posedge clk) begin
            if (push) mem[wp] <= din;
            if (ld) hd <= mem[rp]; else if (byp) hd <= din;
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin wp <= 0; rp <= 0; count <= 0; mn <= 0; hv <= 1'b0; end
            else begin
                if (push) wp <= (wp == AW'(D - 1)) ? {AW{1'b0}} : wp + 1'b1;
                if (adv)  rp <= (rp == AW'(D - 1)) ? {AW{1'b0}} : rp + 1'b1;
                mn <= mn + (push ? 1'b1 : 1'b0) - (adv ? 1'b1 : 1'b0);
                if (ld || byp) hv <= 1'b1; else if (pop) hv <= 1'b0;
                count <= count + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            end
    end endgenerate
endmodule
