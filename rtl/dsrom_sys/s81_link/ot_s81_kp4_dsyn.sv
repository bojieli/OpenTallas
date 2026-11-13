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
// BMTHC (opt-in, default 0): ot_s81_kp4_bm THC (theta_45 reachable form) in the RiBM units.
// SPCYC (opt-in, default 0; S81-TYPES-9-RCK 11-08, COORD +1 pin cycle on the sc_q -> sp tree): the two syndrome window
//   matrices are computed as FOUR registered partial products sq0..3 (ot_s81_kp4_syn_mat_q4.svh = the exact mask split of
//   ot_s81_kp4_syn_mat.svh, cut at the 138-bit sc_q select copies) and sp0 = sq0 ^ sq1, sp1 = sq2 ^ sq3 one stage later.
//   The S final stage, the RiBM load and the k_* results move one cycle (k_* +1 rck); x_q, lock and n_relock are
//   unchanged.  The word delay tile must wait one more word: ot_s81_kp4_ddly DD +1 under OT_S81_RCK_RX_SPCYC.
// ---------------------------------------------------------------------------------------------------------------
// OT_S81_KP4_BM_IT2 (HARD-S81-SERDES-1 11-13, opt-in; needs OT_S81_KP4_SYN_LOCAL without BM_PREL): the RiBM units are
//   ot_s81_kp4_bm_it2 (two-cycle iteration, done 31 cycles later) and there are NBM = 7 of them; k_* +31 rck; the delay
//   tile ot_s81_kp4_ddly holds the words 31 more under the same define.
module ot_s81_kp4_dsyn #(parameter integer MUT = 0,
`ifdef OT_S81_KP4_BM_IT2
    parameter integer NBM = 7,
`else
    parameter integer NBM = 3,
`endif
    parameter integer BMTHC = 0, parameter integer PIN_X = 0,
`ifdef OT_S81_RCK_RX_SPCYC
    parameter integer SPCYC = 1) (     // the define is the form switch in every parent (flat column and RE-FORM cores)
`else
    parameter integer SPCYC = 0) (
`endif
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
`ifdef OT_S81_KP4_AM_FACE3
    , input wire [8:0] am_face3   // three counts captured with p_d's existing face register
`endif
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
`ifdef OT_S81_KP4_AM_FACE3
    wire [3:0] am_distance = {1'b0, am_face3[2:0]} + {1'b0, am_face3[5:3]} + {1'b0, am_face3[8:6]};
    always @(posedge clk) begin am_ok <= p_v && (am_distance <= 4'd2); pv <= p_v; end
`else
    always @(posedge clk) begin am_ok <= p_v && (pop12(amx) <= 2); pv <= p_v; end
`endif
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
    reg  [543:0] x0, x2;
    (* keep = 1, dont_touch = 1 *) reg [543:0] x1; // internal syndrome/word history apart from optional face copy
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
    generate if (SPCYC != 0) begin : g_spc
        // +1 pin cycle: four registered partial products, one per 138-bit sc_q select copy
        wire [299:0] s_q0, s_q1, s_q2, s_q3;
`include "ot_s81_kp4_syn_mat_q4.svh"
        reg  [299:0] sq0, sq1, sq2, sq3;
        always @(posedge clk) begin
            sq0 <= s_q0; sq1 <= s_q1; sq2 <= s_q2; sq3 <= s_q3;
`ifdef RCKRF_MUT_SPCYC
            sp0 <= sq0 ^ sq1; sp1 <= sq2;        // bench mutant: partial 3 dropped
`else
            sp0 <= sq0 ^ sq1; sp1 <= sq2 ^ sq3;
`endif
        end
    end else begin : g_sp
        always @(posedge clk) begin sp0 <= s_p0; sp1 <= s_p1; end
    end endgenerate
    reg  [3:0] g0, g9;                   // chunk-0 / chunk-9 flags: [0] sc stage (T + c + 1), [1+P] sp stage, [2+P] S final
    (* keep *) reg [3:0] g0s;            // chunk-0 flag at the sp stage, 4 copies (75 S bits each)
    reg  [NBM-1:0] bsel;                 // round robin: the unit that takes the next frame
`ifdef OT_S81_KP4_SYN_LOCAL
    // S81-RCK-10 11-07 (vJ, DSYN class): the vI probe's worst u_syn class was S_q (one 300-b register) -> load mux /
    // upd / GF multiply of all three RiBM units (TT -663 ps, ~1780 ep) plus ldr -> unit (-404): one source fanned out
    // to three units placed apart.  Fix: each unit loads from its OWN kept copy of S (Sl, captured from S_q at the S
    // final cycle) with its own kept load copies (ld2, one cycle after ldr), and the units run 8 PE control groups
    // (NG 8: <= 6 PEs, ~70 loads per upd / ld copy) instead of 4.  The k_* result (done-select OR over the units, to
    // the syn->chn landings, -226 ps) is registered here.  PIN CYCLES: +2 rck on k_* (load copy + result register);
    // ot_s81_kp4_ddly DD 55 -> 57 under the same define keeps words and corrections aligned at dout.
`ifdef OT_S81_KP4_BM_PE_LOCAL
    // Private compact RX-SYN form: same-cycle load copies per PE remove measured ld2 broadcast.
    // Arithmetic recurrence already meets placed TT; no extra algorithm or interface cycles.
    localparam integer NGB = 46;
`else
    localparam integer NGB = 8;
`endif
`else
    localparam integer NGB = 4;
`endif
    (* keep *) reg [NGB-1:0] ldr [0:NBM-1];  // unit load, one copy per PE group
    always @(posedge clk)
        if (!rs_n[1]) begin
            g0 <= 0; g9 <= 0; g0s <= 0; bsel <= {{(NBM-1){1'b0}}, 1'b1};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= {NGB{1'b0}};
        end else begin
            g0 <= {g0[2:0], xs[0][0]};
            g9 <= {g9[2:0], xs[0][9]};
            g0s <= {4{g0[SPCYC]}};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= {NGB{g9[1 + SPCYC] && bsel[i]}};     // ld at T + 12 (+SPCYC) (S final)
            if (g9[1 + SPCYC]) bsel <= {bsel[NBM-2:0], bsel[NBM-1]};
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
`ifdef OT_S81_KP4_SYN_LOCAL
`ifdef OT_S81_KP4_BM_PREL
    // S81-TYPES-10-RCK (RXS vF): each RiBM unit preloads from S_q with ldr one cycle earlier (ot_s81_kp4_bm PREL): no per-unit
    // S copy, no ld2 PE copies; one per-unit ld copy keeps the control timing.  PIN CYCLES +0.
    (* keep *) reg [NBM-1:0] ld2p;
    always @(posedge clk)
        if (!rs_n[1]) ld2p <= {NBM{1'b0}};
        else for (i = 0; i < NBM; i = i + 1) ld2p[i] <= ldr[i][0];
    generate for (gu = 0; gu < NBM; gu = gu + 1) begin : g_bm
        ot_s81_kp4_bm #(.NG(NGB), .NCD(4), .THC(BMTHC), .PREL(1)) u_bm (.clk(clk), .rs_n(rs_n[2]), .ld({NGB{ld2p[gu]}}), .S(300'd0),
            .lam(u_lam[gu]), .om(u_om[gu]), .L(u_L[gu]), .any(u_any[gu]), .done(u_dn[gu]), .ldp(ldr[gu]), .Sp(S_q));
    end endgenerate
`else
    (* keep *) reg [299:0]    Sl  [0:NBM-1];   // per-unit S copy (valid in the ld2 cycle)
    (* keep *) reg [NGB-1:0]  ld2 [0:NBM-1];   // per-unit load copies, one cycle after ldr
    always @(posedge clk) for (i = 0; i < NBM; i = i + 1) Sl[i] <= S_q;
    always @(posedge clk)
        if (!rs_n[1]) for (i = 0; i < NBM; i = i + 1) ld2[i] <= {NGB{1'b0}};
`ifdef SYNL_MUT_LD
        else for (i = 0; i < NBM; i = i + 1) ld2[i] <= (i == 1) ? {NGB{g9[1 + SPCYC] && bsel[i]}} : ldr[i];  // MUTANT: unit 1 loads a cycle early
`else
        else for (i = 0; i < NBM; i = i + 1) ld2[i] <= ldr[i];
`endif
    generate for (gu = 0; gu < NBM; gu = gu + 1) begin : g_bm
`ifdef OT_S81_KP4_BM_IT2
        ot_s81_kp4_bm_it2 #(.NG(NGB), .NCD(4)) u_bm (.clk(clk), .rs_n(rs_n[2]), .ld(ld2[gu]), .S(Sl[gu]),
            .lam(u_lam[gu]), .om(u_om[gu]), .L(u_L[gu]), .any(u_any[gu]), .done(u_dn[gu]));
`else
        ot_s81_kp4_bm #(.NG(NGB), .NCD(4), .THC(BMTHC)) u_bm (.clk(clk), .rs_n(rs_n[2]), .ld(ld2[gu]), .S(Sl[gu]),
            .lam(u_lam[gu]), .om(u_om[gu]), .L(u_L[gu]), .any(u_any[gu]), .done(u_dn[gu]), .ldp({NGB{1'b0}}), .Sp(300'd0));
`endif
    end endgenerate
`endif
`else
    generate for (gu = 0; gu < NBM; gu = gu + 1) begin : g_bm
        ot_s81_kp4_bm #(.NG(4), .NCD(4), .THC(BMTHC)) u_bm (.clk(clk), .rs_n(rs_n[2]), .ld(ldr[gu]), .S(S_q),
            .lam(u_lam[gu]), .om(u_om[gu]), .L(u_L[gu]), .any(u_any[gu]), .done(u_dn[gu]), .ldp(4'd0), .Sp(300'd0));
    end endgenerate
`endif
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
`ifdef OT_S81_KP4_SYN_LOCAL
    reg [309:0] k_lo_q; reg [3:0] k_v_q; reg [4:0] k_L_c; reg k_any_c;
    always @* begin
        k_L_c = 5'd0; k_any_c = 1'b0;
        for (q = 0; q < NBM; q = q + 1) if (u_dn[q][0]) begin k_L_c = k_L_c | u_L[q]; k_any_c = k_any_c | u_any[q]; end
    end
    always @(posedge clk) begin k_lo_q <= lsel; k_L <= k_L_c; k_any <= k_any_c; end
    // Preserve the four identical output face flops at the CELL, without alias-wire KEEP.
    (* keep = 1, dont_touch = 1, face_keep = 1 *) always @(posedge clk) if (!rs_n[2]) k_v_q <= 4'd0; else k_v_q <= cl;
    assign k_lo = k_lo_q;
    assign k_v  = k_v_q;
`else
    assign k_lo = lsel;
    assign k_v  = cl;
    always @* begin
        k_L = 5'd0; k_any = 1'b0;
        for (q = 0; q < NBM; q = q + 1) if (u_dn[q][0]) begin k_L = k_L | u_L[q]; k_any = k_any | u_any[q]; end
    end
`endif
    // RCK extraction: x1 also feeds x2/the syndrome cone. A separate copy of
    // its NEXT data gives the output its own face flop, with ZERO added cycles.
    generate if (PIN_X != 0) begin : g_x_face
        reg [543:0] x_face;
        (* keep = 1, dont_touch = 1, face_keep = 1 *) always @(posedge clk)
`ifdef RCKRF_MUT_XFACE_DELAY
            x_face <= x1;
`else
            x_face <= x0;
`endif
        assign x_q = x_face;
    end else begin : g_x_plain
        assign x_q = x1;
    end endgenerate
endmodule

`ifdef OT_S81_KP4_AM_FACE3
// S81-RCK-1: literal metadata half of the existing 544-bit input face.
// Datapath is deliberately unreset, matching ot_pl_pad's existing data face.
// Existing face_p_v and regional resets retain all qualification/calendar rules.
module ot_s81_kp4_am_face3 (
    input wire clk,
    input wire [543:0] p_d,
    output reg [8:0] parts
);
    wire [11:0] amx = p_d[543:532] ^ 12'hA5C;
    function automatic [2:0] pop4(input [3:0] x);
        begin pop4 = {2'b0,x[0]} + {2'b0,x[1]} + {2'b0,x[2]} + {2'b0,x[3]}; end
    endfunction
    always @(posedge clk) begin
        parts[2:0] <= pop4(amx[3:0]);
        parts[5:3] <= pop4(amx[7:4]);
        parts[8:6] <= pop4(amx[11:8]);
    end
endmodule
`endif
