`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dsyn (S81-KP4 2026-10-17): front hard tile of the S81 KP4 RS(544,514) decoder cluster ot_s81_kp4_dec
// (frame / code: tools/s81_link/rs544.py; cluster structure and schedule: ot_s81_kp4_dec.sv).  West tile, PMA side:
//   codeword alignment (AM hunt / lock, as 8cd04168b) on REGISTERED port data (am_ok and p_v are registered before the
//   FSM: no popcount -> FSM -> 32-bit counter path from the pins), syndromes on the arriving stream (fixed-offset
//   one-hot chunk select, window matrix registered a cycle ahead), NBM = 3 RiBM key-equation units taken round robin,
//   and the 3:1 result select.  Out: the received words x_q (to ot_s81_kp4_ddly) and the key-equation result k_* (to
//   ot_s81_kp4_dchn).  T = the cycle word 0 of a frame sits in x1.  Regional synchronous reset, no datapath reset.
// MUT 3: the syndrome loop is not restarted at chunk 0 (stale syndromes) -- bench mutant of this tile.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dsyn #(parameter integer MUT = 0, parameter integer NBM = 3) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          p_v,
    input  wire [543:0]  p_d,
    output wire [543:0]  x_q,           // received word k of a frame at T + k (to the word delay tile)
    output wire [3:0]    k_v,           // key-equation result valid (4 identical copies)
    output wire [309:0]  k_lo,          // {omega_14..0, lambda_15..0}, 10 b each
    output reg  [4:0]    k_L,
    output reg           k_any,
    output reg           lock,
    output reg  [31:0]   n_relock
);
`include "ot_s81_gf1024.svh"
    localparam integer NT = 30;
    localparam integer NRS = 4;          // syndrome chunk-select copies (138 window bits each)
    wire [2:0] rs_n;
    ot_s81_kp4_rst #(.NL(3)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
    integer i, q;
    genvar gk, gb, gu;
    // ================= alignment: am_ok / p_v registered with the word (x0); FSM -> one-hot index registered (x1)
    wire [11:0] amx = p_d[543:532] ^ 12'hA5C;
    function automatic [3:0] pop12(input [11:0] x); integer b; begin pop12 = 0; for (b = 0; b < 12; b = b + 1) pop12 = pop12 + x[b]; end endfunction
    reg        am_ok, pv;
    always @(posedge clk) begin am_ok <= p_v && (pop12(amx) <= 2); pv <= p_v; end
    reg  [3:0] wc;
    reg        cand;
    reg  [1:0] miss;
    wire       acq  = !lock && pv && cand && wc == 4'd9 && am_ok;           // word 0 of the first locked frame
    wire       drop = lock && pv && wc == 4'd0 && !am_ok && miss == 2'd3;  // 4th bad AM: frame dropped
    wire [9:0] xsel = acq ? 10'd1 : ((lock && pv && !drop) ? (10'd1 << wc) : 10'd0);
    always @(posedge clk)
        if (!rs_n[0]) begin lock <= 1'b0; cand <= 1'b0; wc <= 0; miss <= 0; n_relock <= 0; end
        else if (!pv) begin
            if (lock) begin lock <= 1'b0; cand <= 1'b0; wc <= 0; miss <= 0; end
        end else if (!lock) begin
            if (cand && wc == 4'd9) begin
                if (am_ok) begin lock <= 1'b1; wc <= 4'd1; n_relock <= n_relock + 1; end
                else begin cand <= 1'b0; wc <= 0; end
            end else if (cand) wc <= wc + 1'b1;
            else if (am_ok) begin cand <= 1'b1; wc <= 4'd0; end
        end else begin
            if (wc == 4'd0) begin
                if (am_ok) miss <= 0;
                else if (miss == 2'd3) begin lock <= 1'b0; cand <= 1'b0; miss <= 0; end
                else miss <= miss + 1'b1;
            end
            wc <= (wc == 4'd9) ? 4'd0 : wc + 1'b1;
        end
    reg  [543:0] x0, x1, x2;
    (* keep *) reg [9:0] xs [0:NRS-1];   // one-hot index of the word in x1 (zero = none)
    always @(posedge clk) begin x0 <= p_d; x1 <= x0; x2 <= x1; end
    always @(posedge clk)
        if (!rs_n[0]) for (i = 0; i < NRS; i = i + 1) xs[i] <= 10'd0;
        else for (i = 0; i < NRS; i = i + 1) xs[i] <= xsel;
    // ================= syndromes
    wire [1087:0] wd = {x2, x1};
    wire [549:0]  ssrc [0:9];
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_ssrc
        if (gk == 0) begin : g0
            assign ssrc[gk] = {60'b0, x1[543:54]};
        end else begin : gn
            assign ssrc[gk] = wd[603 - 6 * gk -: 550];
        end
    end endgenerate
    reg  [549:0] sc_q;
    generate for (gb = 0; gb < 550; gb = gb + 1) begin : g_scm
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = ssrc[gk][gb];
        end
        always @(posedge clk) sc_q[gb] <= |(s & xs[gb / 138]);
    end endgenerate
    wire [299:0] s_ar, s_p0, s_p1;
    reg  [299:0] S_q, sp0, sp1;
`include "ot_s81_kp4_syn_mat.svh"
    always @(posedge clk) begin sp0 <= s_p0; sp1 <= s_p1; end
    reg  [2:0] g0, g9;                   // chunk-0 / chunk-9 flags: [0] sc stage (T + c + 1), [1] sp stage, [2] S final
    (* keep *) reg [3:0] g0s;            // chunk-0 flag at the sp stage, 4 copies (75 S bits each)
    reg  [NBM-1:0] bsel;                 // round robin: the unit that takes the next frame
    (* keep *) reg [3:0] ldr [0:NBM-1];  // unit load, one copy per PE group
    always @(posedge clk)
        if (!rs_n[1]) begin
            g0 <= 0; g9 <= 0; g0s <= 0; bsel <= {{(NBM-1){1'b0}}, 1'b1};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= 4'd0;
        end else begin
            g0 <= {g0[1:0], xs[0][0]};
            g9 <= {g9[1:0], xs[0][9]};
            g0s <= {4{g0[0]}};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= {4{g9[1] && bsel[i]}};     // ld at T + 12 (S final)
            if (g9[1]) bsel <= {bsel[NBM-2:0], bsel[NBM-1]};
        end
    generate for (gb = 0; gb < 300; gb = gb + 1) begin : g_S
        always @(posedge clk) S_q[gb] <= ((MUT != 3 && g0s[gb / 75]) ? 1'b0 : s_ar[gb]) ^ sp0[gb] ^ sp1[gb];  // MUT 3: no restart
    end endgenerate
    // ================= key equation: NBM RiBM units
    wire [159:0] u_lam [0:NBM-1];
    wire [149:0] u_om  [0:NBM-1];
    wire [4:0]   u_L   [0:NBM-1];
    wire         u_any [0:NBM-1];
    wire [3:0]   u_dn  [0:NBM-1];
    generate for (gu = 0; gu < NBM; gu = gu + 1) begin : g_bm
        ot_s81_kp4_bm #(.NG(4), .NCD(4)) u_bm (.clk(clk), .rs_n(rs_n[2]), .ld(ldr[gu]), .S(S_q),
            .lam(u_lam[gu]), .om(u_om[gu]), .L(u_L[gu]), .any(u_any[gu]), .done(u_dn[gu]));
    end endgenerate
    // ================= result of the unit that is done (to the back tile)
    // load (T + 42): Rl_i = lambda_i alpha^(-543 i), Ro_i = omega_i alpha^(-543 (i + 30)); advance: x alpha^(55 i),
    // x alpha^(55 (i + 30)).  Lane k multiplies by alpha^(i k) / alpha^((i + 30) k): X^-1 = alpha^(55 c + k - 543).
    wire [309:0] lsel;                   // {omega, lambda} of the unit that is done (one-hot), bit b uses copy b / 78
    wire [3:0]   cl;                     // load copies
    generate for (gb = 0; gb < 310; gb = gb + 1) begin : g_lsel
        wire [NBM-1:0] t;
        for (gu = 0; gu < NBM; gu = gu + 1) begin : g_t
            wire [309:0] v = {u_om[gu], u_lam[gu]};
            assign t[gu] = u_dn[gu][gb / 78] & v[gb];
        end
        assign lsel[gb] = |t;
    end endgenerate
    generate for (gb = 0; gb < 4; gb = gb + 1) begin : g_cl
        wire [NBM-1:0] t;
        for (gu = 0; gu < NBM; gu = gu + 1) begin : g_t
            assign t[gu] = u_dn[gu][gb];
        end
        assign cl[gb] = |t;
    end endgenerate
    assign k_lo = lsel;
    assign k_v  = cl;
    always @* begin
        k_L = 5'd0; k_any = 1'b0;
        for (q = 0; q < NBM; q = q + 1) if (u_dn[q][0]) begin k_L = k_L | u_L[q]; k_any = k_any | u_any[q]; end
    end
    assign x_q = x1;
endmodule
