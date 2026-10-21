`timescale 1ns/1ps
// S81-COLLECT/HGRP (10-21): hgrp8r write-face register for the svc8 ring SRAMs.
// hgrp8 gate3 (GRT overflow 0) missed setup by -167.9 ps on SRAM wd_in: the ring write data came combinationally
// from the arithmetic pipeline straight into the macro's write setup window.  This wrapper registers the whole write
// port (w_ce, w_addr, wd, w_mask) one edge before the macro, so the macro write pins are driven flop->macro only.
// Ring timing (ot_s81svc8_ring): write at t, read address at t + D - 2, capture at t + D - 1, D >= 4 in svc8
// (FPL 4 .. 24, FML 6).  The registered write lands at t + 1 < t + D - 2, and the macro is read-before-write only on
// the same edge, so every read still returns the word written for it: ring delay and the static schedule are
// unchanged (0 added cycles).  Read port untouched.  No reset: the registers only pipeline signals that are held
// inactive by the landed reset upstream (w_ce = run), so after >= 1 reset edge they are defined.
// verilator lint_off UNUSED
module ot_s81svc8_sram_wreg (
    input  wire        clk,
    input  wire        r_ce_in,
    input  wire [4:0]  r_addr_in,
    output wire [63:0] rd_out,
    input  wire        w_ce_in,
    input  wire [4:0]  w_addr_in,
    input  wire [63:0] wd_in,
    input  wire [63:0] w_mask_in
);
    (* keep *) reg        w_ce_q;
    (* keep *) reg [4:0]  w_addr_q;
    (* keep *) reg [63:0] wd_q;
    reg [63:0] w_mask_q;
    always @(posedge clk) begin
        w_ce_q   <= w_ce_in;
        w_addr_q <= w_addr_in;
        wd_q     <= wd_in;
        w_mask_q <= w_mask_in;
    end
    ot_sram_1r1w_32x64_m1 u_mem (
        .clk(clk), .r_ce_in(r_ce_in), .r_addr_in(r_addr_in), .rd_out(rd_out),
        .w_ce_in(w_ce_q), .w_addr_in(w_addr_q), .wd_in(wd_q), .w_mask_in(w_mask_q));
endmodule
// verilator lint_on UNUSED
