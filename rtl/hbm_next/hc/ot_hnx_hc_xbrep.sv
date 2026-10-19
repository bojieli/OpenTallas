`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT-UNITS-HUBFIX 2026-10-19: one per-face copy of the hc_<q> x_wave beat-control output register (v + beat).
// The hub tile drives the bank beat control on all four faces (W bank 0, N bank 2, E bank 4, S bank 6); one register
// fanned to four faces sat >= 530-608 um from one of its face pins (textbook_lint wire_reach, closure job
// hnx_hcq_hub_1019-n1-c8a284b41).  Each face now gets its own copy, loaded on the SAME edge from the SAME next-state as
// the original register (no added cycle: the static schedule is unchanged).  NOT parameterised on purpose: the kit keeps
// it by name (route.synth_keep_modules) so yosys opt_merge cannot fold the copies back into one register.
module ot_hnx_hc_xbrep (
    input  wire       clk, rst_n,
    input  wire       d_v,              // next x_wave_v
    input  wire       en,               // x_wave_beat load enable
    input  wire [1:0] d_beat,           // next x_wave_beat
    output reg        q_v,
    output reg  [1:0] q_beat
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q_v <= 1'b0; else q_v <= d_v;
    always @(posedge clk)
        if (en) q_beat <= d_beat;
endmodule
`default_nettype wire
