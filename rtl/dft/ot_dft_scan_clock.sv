`timescale 1ns/1ps
// Core clock selection for scan access through the TAP.
//
// Functional mode: core_clk = func_clk.  TAP scan mode (scan_clk_sel = 1):
// core_clk = TCK, gated cycle by cycle by scan_clk_en from ot_tap, through a
// latch-based gate (the enable is sampled while TCK is low, so each passed
// pulse is a whole TCK high phase and never a glitch).
//
// The select is switched glitch-free: each clock has a two-stage negative-edge
// synchroniser for its own enable, and a clock is enabled only after the other
// clock's enable has been seen low, so the output is never driven by both and
// no pulse is shortened.  Both clocks must toggle for a switch to complete; a
// tester that stops func_clk should switch before stopping it.
//
// This is the reference clock controller for integrators; ATE-driven scan
// through package pins instead drives func_clk directly and leaves
// scan_clk_sel low.
module ot_dft_scan_clock (
    input  logic func_clk,
    input  logic tck,
    input  logic rst_n,          // asynchronous, active low: selects func_clk
    input  logic scan_clk_sel,   // from ot_tap (TCK domain)
    input  logic scan_clk_en,    // from ot_tap (TCK domain)
    output logic core_clk
);
    logic f_q1, f_q2;   // func_clk enable
    logic t_q1, t_q2;   // tck enable

    always_ff @(negedge func_clk or negedge rst_n) begin
        if (!rst_n) begin
            f_q1 <= 1'b1;
            f_q2 <= 1'b1;
        end else begin
            f_q1 <= !scan_clk_sel && !t_q2;
            f_q2 <= f_q1;
        end
    end

    always_ff @(negedge tck or negedge rst_n) begin
        if (!rst_n) begin
            t_q1 <= 1'b0;
            t_q2 <= 1'b0;
        end else begin
            t_q1 <= scan_clk_sel && !f_q2;
            t_q2 <= t_q1;
        end
    end

    // latch-based clock gate on TCK: transparent while TCK is low
    logic tck_en_l;
    always_latch begin
        if (!tck) tck_en_l = scan_clk_en && t_q2;
    end
    wire tck_gated = tck && tck_en_l;

    assign core_clk = (func_clk && f_q2) || tck_gated;
endmodule
