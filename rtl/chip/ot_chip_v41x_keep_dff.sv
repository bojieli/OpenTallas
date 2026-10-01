`timescale 1ns/1ps
// ot_chip_v41x_keep_dff -- one flop that synthesis may NOT merge with an identical copy (W18b).
// Replicated control flops (a queue's read pointer per payload slice) are structurally identical, so Yosys's
// opt_merge folds them back into one wide-fanout net.  Under SYNTHESIS the flop is the ASAP7 library cell
// itself (a black-box cell, outside opt_merge's built-in types); QN follows D in that cell (next_state !D,
// function IQN), and RESETN (the library's "preset" of IQ) resets QN to 0.  Simulation: a plain flop.
module ot_chip_v41x_keep_dff (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);
`ifdef SYNTHESIS
    DFFASRHQNx1_ASAP7_75t_R u_ff (.CLK(clk), .D(d), .RESETN(rst_n), .SETN(1'b1), .QN(q));
`else
    reg r;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= d;
    assign q = r;
`endif
endmodule
