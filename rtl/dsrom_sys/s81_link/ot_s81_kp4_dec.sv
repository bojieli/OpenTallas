`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dec (s81-die-rtl-bind 2026-10-14, die item F10; STREAMING rewrite S81-KP4 2026-10-17): the receive FEC of
// one S81 die link -- RS(544,514) KP4 decoder (t = 15) behind codeword alignment.  Frame / code as ot_s81_kp4_enc and
// tools/s81_link/rs544.py.
//   in : one 544-b PMA word a cycle (p_v) in the RECOVERED clock domain of the link (clk = the PMA's recovered clock)
//   out: the frame's 10 lane beats, one a cycle (q_v, q_d), corrected; per frame: q_unc (the codeword was not
//        correctable: beats passed uncorrected, the link CRC / replay above takes them), q_nerr (symbols corrected)
// Alignment (unchanged): hunt for the 12-b AM at word bits [543:532] (<= 2 bit errors), lock on two AMs exactly 10
// words apart, stay locked through up to 3 consecutive bad AMs (the AM is checked before correction), re-hunt on the
// 4th.  NEW: a missing PMA word while locked (the PMA never pauses on the static schedule) also re-hunts; the partial
// frame is dropped like a frame cut by the 4th bad AM.
// CLUSTER of two hard sub-tiles (S81-KP4 10-17; one ~350 um tile measured 383-513 ps TT clock insertion, spread 130 ps):
//   u_a = ot_s81_kp4_dec_a (west, PMA side): alignment, syndromes on the arriving stream, 3 RiBM key-equation units,
//         the 64 x 546 received-word SRAM delay line;
//   u_b = ot_s81_kp4_dec_b (east, core side): forward Chien / Forney, root count + decision, the 32 x 546 correction-mask
//         SRAM delay, corrected words and lane beats.
//   Seam a -> b (registered at both pins): d_q 544 + k_v 4 + k_lo 310 + k_L 5 + k_any 1 = 864 bits.  The words and the
//   key-equation result cross the SAME seam, so u_b's fixed schedule is independent of the seam latency.
//   Schedule (T = word 0 of a frame in u_a.x1): S final T + 12, RiBM T + 12 .. T + 42, Chien chunks T + 43 + c, decision
//   T + 56, beat k in q_d at T + 58 + k (+ the seam's 2 pin registers in hardware).  RTL latency p_d (word 0) -> q_d
//   (beat 0): 60 cycles (8cd04168b: ~81); with the tiles' pin registers 64.
// STRUCTURE (replaces 8cd04168b, whose 6 whole-codeword copies cap/sb/bcw x4/cw/orig/ob = 57.6k flops on one root,
// 5,500-bit barrel windows, bsel / sc selects with 11.8k-23.6k loads and a 46-level Chien/Forney cycle): see the two
// sub-tiles.  Uncorrectable: deg Lambda (L) > 15, or roots found != L (as rs544.decode).
// MUT 2 (u_b): Forney error value without the division by Lambda'(X^-1) (wrong correction); MUT 3 (u_a): the syndrome
// loop is not restarted at a frame -- bench mutants.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dec #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          p_v,
    input  wire [543:0]  p_d,
    output wire          q_v,
    output wire [511:0]  q_d,
    output wire          q_first,       // first beat of a frame
    output wire          q_unc,         // with q_first: this frame was uncorrectable
    output wire [4:0]    q_nerr,        // with q_first: symbols corrected
    output wire [7:0]    q_seq,         // with q_first: the frame's sequence number (header, after correction)
    output wire          lock,
    output wire [31:0]   n_corr, n_unc, n_relock
);
    wire [543:0] d_q;
    wire [3:0]   k_v;
    wire [309:0] k_lo;
    wire [4:0]   k_L;
    wire         k_any;
    ot_s81_kp4_dec_a #(.MUT(MUT)) u_a (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .d_q(d_q), .k_v(k_v), .k_lo(k_lo), .k_L(k_L),
        .k_any(k_any), .lock(lock), .n_relock(n_relock));
    ot_s81_kp4_dec_b #(.MUT(MUT)) u_b (.clk(clk), .rst_n(rst_n), .d_q(d_q), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .n_corr(n_corr), .n_unc(n_unc));
endmodule
