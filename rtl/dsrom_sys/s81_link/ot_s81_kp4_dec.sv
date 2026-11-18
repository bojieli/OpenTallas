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
// DKREG (HEAD-SERDES-O 11-16, default 0 = unchanged): 1 = one register on the 320-bit k_* seam (k_v 4, k_lo 310, k_L 5,
//   k_any 1) between u_syn and u_chn, in the parent.  hd_serdes GRT RC TT: RiBM done[0] (late 900 ps tap) -> u_syn k_* select
//   -> hard tile u_chn k_lo/k_v pins (macro clock ~300 ps early + 233 ps lib setup), -43 ps; the register makes that a
//   flop-to-pin hop.  The corrections then reach u_out one cycle later, so u_dly delays the words one more (DDX = 1): DD
//   55 -> 56, decoder latency p_d -> q_d +1 recovered-clock cycle (PIN CYCLES +1 on the RX side, before the rate match).
// DOREG (HEAD-SERDES-O 11-16, default 0 = unchanged): 1 = one register on the chn -> out seam (cw 544, apply 8, o_unc, o_ne
//   5, fs) in the parent.  hd_serdes sd6 GRT RC TT -112: hard tile u_chn apply (clk->q 400 ps) -> ~480 ps of buffered wire
//   -> u_out bsrc (55 endpoints).  The corrections then reach u_out one more cycle later, so u_dly delays the words one more
//   (DDX + 1): decoder latency +1 recovered-clock cycle (with DKREG: +2).
module ot_s81_kp4_dec #(parameter integer MUT = 0, parameter integer NGB0 = 4, parameter integer DKREG = 0,
    parameter integer DOREG = 0) (
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
    wire [3:0]   kc_v;
    wire [309:0] kc_lo;
    wire [4:0]   kc_L;
    wire         kc_any;
    generate if (DKREG != 0) begin : g_kreg
        wire [0:0] ks_n;
        ot_s81_kp4_rst #(.NL(1)) u_rstk (.clk(clk), .rst_n(rst_n), .rs_n(ks_n));
        (* keep = 1, dont_touch = 1 *) reg [3:0]   r_kv;
        (* keep = 1, dont_touch = 1 *) reg [309:0] r_klo;
        (* keep = 1, dont_touch = 1 *) reg [4:0]   r_kL;
        (* keep = 1, dont_touch = 1 *) reg         r_kany;
        always @(posedge clk) if (!ks_n[0]) r_kv <= 4'd0; else r_kv <= k_v;
        always @(posedge clk) begin r_klo <= k_lo; r_kL <= k_L; r_kany <= k_any; end
        assign kc_v = r_kv; assign kc_lo = r_klo; assign kc_L = r_kL; assign kc_any = r_kany;
    end else begin : g_knone
        assign kc_v = k_v; assign kc_lo = k_lo; assign kc_L = k_L; assign kc_any = k_any;
    end endgenerate
`ifdef DKREG_MUT_NODD
    localparam integer DDX = 0;                  // bench mutant: k_* registered without the extra word delay
`elsif DOREG_MUT_NODD
    localparam integer DDX = (DKREG != 0) ? 1 : 0;   // bench mutant: chn -> out registered without its extra word delay
`else
    localparam integer DDX = ((DKREG != 0) ? 1 : 0) + ((DOREG != 0) ? 1 : 0);
`endif
    wire [543:0] cw_o;
    wire [7:0]   apply_o;
    wire [4:0]   o_ne_o;
    wire         o_unc_o, fs_o;
    generate if (DOREG != 0) begin : g_oreg
        wire [0:0] os_n;
        ot_s81_kp4_rst #(.NL(1)) u_rsto (.clk(clk), .rst_n(rst_n), .rs_n(os_n));
        (* keep = 1, dont_touch = 1 *) reg [543:0] r_cw;
        (* keep = 1, dont_touch = 1 *) reg [7:0]   r_apply;
        (* keep = 1, dont_touch = 1 *) reg [4:0]   r_one;
        (* keep = 1, dont_touch = 1 *) reg         r_unc;
        (* keep = 1, dont_touch = 1 *) reg         r_fs;
        always @(posedge clk) if (!os_n[0]) r_fs <= 1'b0; else r_fs <= fs;
        always @(posedge clk) begin r_cw <= cw; r_apply <= apply; r_one <= o_ne; r_unc <= o_unc; end
        assign cw_o = r_cw; assign apply_o = r_apply; assign o_ne_o = r_one; assign o_unc_o = r_unc; assign fs_o = r_fs;
    end else begin : g_onone
        assign cw_o = cw; assign apply_o = apply; assign o_ne_o = o_ne; assign o_unc_o = o_unc; assign fs_o = fs;
    end endgenerate
    // OT_S81_RCK_RX_SPCYC (COORD 11-17; undefined = unchanged): syndrome window partials registered (SPCYC 1), ddly DD +1
`ifdef OT_S81_RCK_RX_SPCYC
    localparam integer DSPC = 1;
`else
    localparam integer DSPC = 0;
`endif
`ifndef OT_KP4_DEC_HARD
    ot_s81_kp4_dsyn #(.MUT(MUT), .NGB0(NGB0), .SPCYC(DSPC)) u_syn (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
`else
    // hardened 2x2 parent (s81lk_kp4_dec): the closed child views carry MUT = 0
    ot_s81_kp4_dsyn u_syn (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
`endif
    ot_s81_kp4_ddly #(.DDX(DDX)) u_dly (.clk(clk), .rst_n(rst_n), .w_d(x_q), .r_d(d_q));
`ifndef OT_KP4_DEC_HARD
    ot_s81_kp4_dchn #(.MUT(MUT)) u_chn (.clk(clk), .rst_n(rst_n), .k_v(kc_v), .k_lo(kc_lo), .k_L(kc_L), .k_any(kc_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
`else
    // hardened 2x2 parent (s81lk_kp4_dec): the closed child views carry MUT = 0
    ot_s81_kp4_dchn u_chn (.clk(clk), .rst_n(rst_n), .k_v(kc_v), .k_lo(kc_lo), .k_L(kc_L), .k_any(kc_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
`endif
    ot_s81_kp4_dout u_out (.clk(clk), .rst_n(rst_n), .d_q(d_q), .cw(cw_o), .apply(apply_o), .o_unc(o_unc_o), .o_ne(o_ne_o), .fs(fs_o),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
endmodule
