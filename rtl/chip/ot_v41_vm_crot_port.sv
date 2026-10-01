`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// C_ROTATE strip PORT LOGIC (rtl/chip/ot_v41_vm_crot.sv): the per-vector row generator of the central bank array.
//
// The strip stores element e in bank column c = e mod NG (NG = 128 at full shape) at local word w = e / NG;
// a column's local word w lives in bank w[3], row w >> 4, slot w[2:0] (ot_v41_vm_group_phys: 2 banks of 256 rows
// x 8 words).  The column's 8 output words are put in SLOT order, so the bank array's output position of element e
// is p = NG * (w mod 8) + c = e mod (8 NG): a unit-stride vector at base B then reaches lane l = (p - B) mod (8 NG)
// through ONE rotation by B mod 8 NG (ot_v41_vm_rot), for every base.
//
// For a vector at base B (per class, one a cycle): r = B mod NG, q = B / NG.  Column c's first local word is
// w0 = q + (c < r); slot s holds w = (w0 & ~7) + s + (s < w0[2:0] ? 8 : 0), in bank w[3] at row w >> 4.  So per
// column the port drives two row addresses (one a bank: the words of a vector are at most one row of each bank),
// a per-slot bank select (8 bits) and the rotate amount B mod 8 NG; the only per-column logic is the comparator
// c < r (a thermometer decode of r) choosing between the two candidates (q, q + 1) computed once.  The same
// generator serves the element write (the write rotate's inverse amount, per-bank slot masks).
//
// This module is the slice of NCOL columns starting at column COL0 (the full strip is NG / NCOL slices on the
// broadcast of {q-candidates, r}), registered at its output; the broadcast's wire stages are CR_LEAD.
// Classes other than unit stride (broadcast scalars, gathers, other strides) take the permutation network's path
// and are not generated here.
// ---------------------------------------------------------------------------
module ot_v41_vm_crot_port #(
    parameter integer NG   = 128,               // bank columns of the full strip
    parameter integer NCOL = 16,                // columns in this slice
    parameter integer COL0 = 0,                 // first column of this slice
    parameter integer VMA  = 19,                // element address bits
    parameter integer NCLS = 6,                 // classes (A, B, C, D, G read; E write)
    parameter integer LG   = $clog2(NG),
    parameter integer RA   = VMA - LG - 4,      // row address bits (256 rows at VMA 19, NG 128)
    parameter integer LR   = LG + 3             // rotate amount bits (log2 of 8 NG lanes)
) (
    input  wire                         clk,
    input  wire [NCLS-1:0]              v,
    input  wire [NCLS*VMA-1:0]          base,
    output reg  [NCLS-1:0]              o_v,
    output reg  [NCLS*NCOL*2*RA-1:0]    o_row,      // per class, column, bank: the row
    output reg  [NCLS*NCOL*8-1:0]       o_bsel,     // per class, column, slot: the bank holding the slot's word
    output reg  [NCLS*LR-1:0]           o_rot       // per class: the rotate amount (B mod 8 NG)
);
    localparam integer QW = VMA - LG;               // local word bits
    integer k, c, s;
    reg [QW-1:0] q, w0, w;
    reg [LG-1:0] r;
    always @(posedge clk) begin
        for (k = 0; k < NCLS; k = k + 1) begin
            o_v[k] <= v[k];
            r = base[k*VMA +: LG];
            q = base[k*VMA + LG +: QW];
            o_rot[k*LR +: LR] <= base[k*VMA +: LR];
            for (c = 0; c < NCOL; c = c + 1) begin
                w0 = q + ((COL0 + c < r) ? 1 : 0);
                for (s = 0; s < 8; s = s + 1) begin
                    w = {w0[QW-1:3], 3'(s)} + ((s < w0[2:0]) ? QW'(8) : QW'(0));
                    o_bsel[(k*NCOL + c)*8 + s] <= w[3];
                    o_row[((k*NCOL + c)*2 + w[3])*RA +: RA] <= w[QW-1:4];
                end
            end
        end
    end
endmodule
