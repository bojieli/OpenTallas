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
// CLUSTER of four hard tiles (S81-KP4 10-17).  Measured CTS gates: one 367 x 346 um tile 383-513 ps TT insertion
// (spread 130 ps); two 259 um tiles 307-455 / 295-417 ps (spread 148 / 122): clock wire RC across the tile dominates,
// so every tile here is <= ~180 um or a single-macro delay tile:
//   u_syn = ot_s81_kp4_dsyn (W, PMA side): alignment, syndromes, 3 RiBM key-equation units, 3:1 result select;
//   u_dly = ot_s81_kp4_ddly: the 64 x 546 received-word SRAM delay line (DD = 55);
//   u_chn = ot_s81_kp4_dchn: Chien / Forney, root count, decision, correction masks per PMA word;
//   u_out = ot_s81_kp4_dout (E, core side): the 32 x 546 mask SRAM delay (DC = 9), corrected words, lane beats.
//   Seams (registered at both pins): syn -> dly 544, syn -> chn 320 (k_v 4 + k_lo 310 + k_L 5 + k_any 1),
//   dly -> out 544, chn -> out 559.  Words (syn -> dly -> out) and corrections (syn -> chn -> out) cross the SAME number
//   of seams, so DD / DC hold at any seam latency.
//   Schedule (T = word 0 of a frame in u_syn.x1, pure RTL): S final T + 12, RiBM T + 12 .. T + 42, Chien chunks
//   T + 43 + c, decision T + 56, beat k in q_d at T + 58 + k.  RTL latency p_d (word 0) -> q_d (beat 0): 60 cycles
//   (8cd04168b: ~81); with the tiles' pin registers (2 seams + the cluster's own in / out) 66.
// STRUCTURE (replaces 8cd04168b, whose 6 whole-codeword copies cap/sb/bcw x4/cw/orig/ob = 57.6k flops on one root,
// 5,500-bit barrel windows, bsel / sc selects with 11.8k-23.6k loads and a 46-level Chien/Forney cycle): see the two
// sub-tiles.  Uncorrectable: deg Lambda (L) > 15, or roots found != L (as rs544.decode).
// MUT 2 (u_chn): Forney error value without the division by Lambda'(X^-1) (wrong correction); MUT 3 (u_syn): the syndrome
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
    wire [543:0] x_q, d_q, cw;
    wire [3:0]   k_v;
    wire [309:0] k_lo;
    wire [4:0]   k_L, o_ne;
    wire         k_any, o_unc, fs;
    wire [7:0]   apply;
`ifndef OT_KP4_DEC_HARD
    ot_s81_kp4_dsyn #(.MUT(MUT)) u_syn (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
`else
    // hardened 2x2 parent (s81lk_kp4_dec): the closed child views carry MUT = 0
    ot_s81_kp4_dsyn u_syn (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
`endif
    ot_s81_kp4_ddly u_dly (.clk(clk), .rst_n(rst_n), .w_d(x_q), .r_d(d_q));
`ifndef OT_KP4_DEC_HARD
    ot_s81_kp4_dchn #(.MUT(MUT)) u_chn (.clk(clk), .rst_n(rst_n), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
`else
    // hardened 2x2 parent (s81lk_kp4_dec): the closed child views carry MUT = 0
    ot_s81_kp4_dchn u_chn (.clk(clk), .rst_n(rst_n), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
`endif
    ot_s81_kp4_dout u_out (.clk(clk), .rst_n(rst_n), .d_q(d_q), .cw(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
endmodule
