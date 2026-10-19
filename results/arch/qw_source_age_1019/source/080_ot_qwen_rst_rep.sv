`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// qwen-tp8 2026-10-13 (owner release gate: register at the pin -> wire <= 500 um -> register at the pin).
// ot_qwen_rst_rep: one node of the registered die reset tree (die masters qfd_rst_rep = PAD 0, qfd_rst_rep_p8 = PAD 8;
// tools/qwen_rom_fulldie_b3r2.py _reset_tree).  An active-low reset level travels as DATA: one input flop at the d pin,
// PAD pad flops (equal-depth padding), two registered outputs q0 / q1 (a T-junction is two nets, each with its own
// flop at the pin).  Latency d -> q = PAD + 2 cycles.  The flops have NO reset of their own: the tree is flushed by the
// root holding the level for at least the tree depth (ot_qwen_rst_root), which is why the clock must run in reset.
// MUT (bench only): 1 = q1 taken one stage early (unequal outputs).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_rst_rep #(
    parameter integer PAD = 0,
    parameter integer MUT = 0
) (
    input  wire clk,
    input  wire d,
    output wire q0,
    output wire q1
);
    reg [PAD:0] s;                               // s[0] = input flop, s[PAD:1] = pad flops
    (* keep = "true", dont_touch = "true" *) reg r0;
    (* keep = "true", dont_touch = "true" *) reg r1;
    integer i;
    always @(posedge clk) begin
        s[0] <= d;
        for (i = 1; i <= PAD; i = i + 1) s[i] <= s[i - 1];
        r0 <= s[PAD];
        r1 <= (MUT == 1) ? ((PAD == 0) ? d : s[PAD - 1]) : s[PAD];
    end
    assign q0 = r0;
    assign q1 = r1;
endmodule
