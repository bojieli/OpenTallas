`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dec (s81-die-rtl-bind 2026-10-14, die item F10): the receive FEC of one S81 die link -- RS(544,514) KP4
// decoder (t = 15) behind codeword alignment.  Frame / code as ot_s81_kp4_enc and tools/s81_link/rs544.py.
//   in : one 544-b PMA word a cycle (p_v) in the RECOVERED clock domain of the link (clk = the PMA's recovered clock)
//   out: the frame's 10 lane beats, one a cycle (q_v, q_d), corrected; per frame: q_unc (the codeword was not
//        correctable: beats passed uncorrected, the link CRC / replay above takes them), q_nerr (symbols corrected)
// Alignment: hunt for the 12-b AM at word bits [543:532] (<= 2 bit errors), lock on two AMs exactly 10 words apart,
// stay locked through up to 3 consecutive bad AMs (the AM is checked before correction), re-hunt on the 4th.
// Stages, one codeword every 10 cycles (strobe = locked word 9):
//   capture (10 words) -> syndromes S_0..S_29 over the stored codeword, 55 symbols a cycle (10 cycles)
//   -> Berlekamp-Massey, one iteration a cycle (30) + Omega, in one of NBM = 4 units taken round robin
//   -> Chien search + Forney over 55 degrees a cycle (10 cycles): e = X Omega(X^-1) / Lambda'(X^-1) (b = 0)
//   -> emit 10 beats.  Uncorrectable: deg Lambda > 15, or roots found != deg Lambda.
// Latency ~ 10 + 10 + 40 + 10 + 10 cycles.  Every output leaves a flop.
// MUT 2: Forney error value not multiplied by X (wrong correction) -- bench mutant.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dec #(parameter integer MUT = 0, parameter integer NBM = 4) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          p_v,
    input  wire [543:0]  p_d,
    output reg           q_v,
    output reg  [511:0]  q_d,
    output reg           q_first,       // first beat of a frame
    output reg           q_unc,         // with q_first: this frame was uncorrectable
    output reg  [4:0]    q_nerr,        // with q_first: symbols corrected
    output reg  [7:0]    q_seq,         // with q_first: the frame's sequence number (header, after correction)
    output reg           lock,
    output reg  [31:0]   n_corr, n_unc, n_relock
);
`include "ot_s81_gf1024.svh"
    localparam integer NT = 30, SPC = 55;
    // ---------------- alignment
    wire [11:0] amx = p_d[543:532] ^ 12'hA5C;
    function automatic [3:0] pop12(input [11:0] x); integer b; begin pop12 = 0; for (b = 0; b < 12; b = b + 1) pop12 = pop12 + x[b]; end endfunction
    wire am_ok = p_v && (pop12(amx) <= 2);
    reg  [3:0] wc;          // word index in frame (locked) / words since candidate (hunt)
    reg        cand;
    reg  [1:0] miss;
    reg  [5439:0] cap;
    reg        strobe;      // the cycle after word 9 was captured: cap holds a whole codeword
    integer i, j, k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lock <= 1'b0; cand <= 1'b0; wc <= 0; miss <= 0; strobe <= 1'b0; n_relock <= 0; end
        else begin
            strobe <= 1'b0;
            if (p_v) begin
                if (!lock) begin
                    if (cand && wc == 4'd9) begin
                        if (am_ok) begin lock <= 1'b1; wc <= 4'd1; cap[5439 -: 544] <= p_d; n_relock <= n_relock + 1; end
                        else begin cand <= 1'b0; wc <= 0; end
                    end else if (cand) wc <= wc + 1'b1;
                    else if (am_ok) begin cand <= 1'b1; wc <= 4'd0; end
                end else begin
                    case (wc)   // fixed part-selects (H-DIE 10-16: variable lvalue part-select blew up the yosys frontend)
                        4'd0: cap[5439 -: 544] <= p_d;  4'd1: cap[4895 -: 544] <= p_d;
                        4'd2: cap[4351 -: 544] <= p_d;  4'd3: cap[3807 -: 544] <= p_d;
                        4'd4: cap[3263 -: 544] <= p_d;  4'd5: cap[2719 -: 544] <= p_d;
                        4'd6: cap[2175 -: 544] <= p_d;  4'd7: cap[1631 -: 544] <= p_d;
                        4'd8: cap[1087 -: 544] <= p_d;  4'd9: cap[543  -: 544] <= p_d;
                        default: ;
                    endcase
                    if (wc == 4'd0) begin
                        if (am_ok) miss <= 0;
                        else if (miss == 2'd3) begin lock <= 1'b0; cand <= 1'b0; miss <= 0; end
                        else miss <= miss + 1'b1;
                    end
                    if (wc == 4'd9) strobe <= 1'b1;
                    wc <= (wc == 4'd9) ? 4'd0 : wc + 1'b1;
                end
            end
        end
    // ---------------- syndromes: stage register sb (codeword) + running S over 10 cycles (sc = 0..9 after a strobe)
    reg  [5439:0] sb;
    reg  [9:0]    S [0:NT-1];
    reg  [3:0]    sc;
    reg           s_busy;
    wire [10 * NT - 1:0] nS_f;           // nS[j] at [10 j +: 10]
    // symbol p = 55 sc + k - 6 (6 leading zero symbols), p = 0 first (x^543): window = {60'b0, sb} << 550 sc, symbol k at
    // fixed bits [5499 - 10 k -: 10] (55 sc + k <= 549 < 550 = 6 + 544 always; sc > 9 never occurs while busy)
    wire [5499:0] swin = {60'b0, sb} << (10 * SPC * sc);
    // (ELEM-CENSUS S81-LINK 10-16, timing: the 55-step Horner chain of H-DIE 7a8b12424 -- nS_j = (..(S_j a^j ^ sym_0)
    // a^j ^ sym_1 ..) a^j ^ sym_54 -- was ~165 XOR levels a cycle.  It is GF(2)-linear in {S, window}, so the 55-symbol
    // advance is ONE GF(2) matrix: each next-syndrome bit is a balanced XOR of a fixed subset of {S_j, window}.
    // ot_s81_kp4_dec_syn_lin.svh is generated by tools/s81_link/gen_kp4_linear.py from the exact former chain and
    // self-checked against rs544.syndromes.)
    reg  [10 * NT - 1:0] S_f;
    integer sj;
    always @* for (sj = 0; sj < NT; sj = sj + 1) S_f[10 * sj +: 10] = S[sj];
    wire [849:0] syn_in = {S_f, swin[5499 -: 550]};
    wire [299:0] syn_out;
`include "ot_s81_kp4_dec_syn_lin.svh"
    assign nS_f = syn_out;
    genvar gj, gk, ga, gc;
    wire s_fin = s_busy && sc == 4'd9;   // nS = the codeword's syndromes (this cycle); the next strobe may coincide
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sc <= 0; s_busy <= 1'b0; end
        else begin
            if (s_busy) begin
                for (j = 0; j < NT; j = j + 1) S[j] <= nS_f[10 * j +: 10];
                sc <= sc + 1'b1;
                if (sc == 4'd9) s_busy <= 1'b0;
            end
            if (strobe) begin
                sb <= cap; s_busy <= 1'b1; sc <= 0;
                for (j = 0; j < NT; j = j + 1) S[j] <= 10'd0;
            end
        end
    // ---------------- Berlekamp-Massey units (round robin; unit bsel takes the codeword at s_fin, and its previous
    // codeword -- loaded NBM frames = 40 cycles ago, finished after 31 -- goes to the Chien stage in the same cycle)
    reg  [1:0]    bsel;
    reg  [5439:0] bcw  [0:NBM-1];
    reg  [9:0]    bS   [0:NBM-1][0:NT-1];
    reg  [9:0]    bC   [0:NBM-1][0:NT];
    reg  [9:0]    bB   [0:NBM-1][0:NT];  // x^m B
    reg  [9:0]    bW   [0:NBM-1][0:NT];  // syndrome window W[i] = S[n - i]
    reg  [9:0]    bb   [0:NBM-1];
    reg  [5:0]    bL   [0:NBM-1];
    reg  [5:0]    bn   [0:NBM-1];        // iteration 0..29, 30 = Omega, 31 = done
    reg           bact [0:NBM-1];
    reg           bany [0:NBM-1];        // a nonzero syndrome
    reg  [9:0]    bO   [0:NBM-1][0:NT-1];
    genvar u;
    generate for (u = 0; u < NBM; u = u + 1) begin : g_bm
        reg [9:0] d;
        wire [9:0] coef, ibb;
        reg [9:0] nC [0:NT];
        reg [9:0] oc_ [0:NT-1];
        reg       sany;
        integer a, c, f;
        // flattened unit state (constant-index reads) feeding the GF product instances
        reg  [10 * (NT + 1) - 1:0] fC, fB, fW;
        reg  [10 * NT - 1:0]       fS;
        wire [10 * (NT + 1) - 1:0] pd, pc;       // C_a W_a ; coef B_a
        wire [10 * (NT * (NT + 1) / 2) - 1:0] po; // C_c S_(a-c) at [10 (a (a + 1) / 2 + c) +: 10]
        always @* begin
            for (f = 0; f <= NT; f = f + 1) begin fC[10 * f +: 10] = bC[u][f]; fB[10 * f +: 10] = bB[u][f]; fW[10 * f +: 10] = bW[u][f]; end
            for (f = 0; f < NT; f = f + 1) fS[10 * f +: 10] = bS[u][f];
        end
        for (ga = 0; ga <= NT; ga = ga + 1) begin : g_d
            ot_s81_kp4_dec_vmul u_d (.a(fC[10 * ga +: 10]), .b(fW[10 * ga +: 10]), .y(pd[10 * ga +: 10]));
            ot_s81_kp4_dec_vmul u_c (.a(coef), .b(fB[10 * ga +: 10]), .y(pc[10 * ga +: 10]));
        end
        for (ga = 0; ga < NT; ga = ga + 1) begin : g_o
            for (gc = 0; gc <= ga; gc = gc + 1) begin : g_c
                ot_s81_kp4_dec_vmul u_o (.a(fC[10 * gc +: 10]), .b(fS[10 * (ga - gc) +: 10]),
                                         .y(po[10 * (ga * (ga + 1) / 2 + gc) +: 10]));
            end
        end
        ot_s81_kp4_dec_inv  u_i (.a(bb[u]), .y(ibb));
        ot_s81_kp4_dec_vmul u_k (.a(d), .b(ibb), .y(coef));
        always @* begin
            d = 10'd0;
            for (a = 0; a <= NT; a = a + 1) d = d ^ pd[10 * a +: 10];
            for (a = 0; a <= NT; a = a + 1) nC[a] = bC[u][a] ^ pc[10 * a +: 10];
            for (a = 0; a < NT; a = a + 1) begin
                oc_[a] = 10'd0;
                for (c = 0; c <= a; c = c + 1) oc_[a] = oc_[a] ^ po[10 * (a * (a + 1) / 2 + c) +: 10];
            end
            sany = 1'b0;
            for (a = 0; a < NT; a = a + 1) sany = sany | (nS_f[10 * a +: 10] != 10'd0);
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin bact[u] <= 1'b0; bn[u] <= 6'd31; end
            else if (s_fin && bsel == u) begin
                bcw[u] <= sb; bact[u] <= 1'b1; bn[u] <= 6'd0; bL[u] <= 6'd0; bb[u] <= 10'd1; bany[u] <= sany;
                for (a = 0; a < NT; a = a + 1) bS[u][a] <= nS_f[10 * a +: 10];
                for (a = 0; a <= NT; a = a + 1) begin
                    bC[u][a] <= (a == 0) ? 10'd1 : 10'd0;
                    bB[u][a] <= (a == 1) ? 10'd1 : 10'd0;       // x^1 * 1
                    bW[u][a] <= (a == 0) ? nS_f[9:0] : 10'd0;
                end
            end else if (bact[u] && bn[u] < 6'd30) begin
                // one BM iteration n = bn
                if (d == 10'd0) begin
                    for (a = NT; a >= 1; a = a - 1) bB[u][a] <= bB[u][a - 1];
                    bB[u][0] <= 10'd0;
                end else if (2 * bL[u] <= bn[u]) begin
                    for (a = 0; a <= NT; a = a + 1) bC[u][a] <= nC[a];
                    for (a = NT; a >= 1; a = a - 1) bB[u][a] <= bC[u][a - 1];   // x * C_old
                    bB[u][0] <= 10'd0;
                    bL[u] <= bn[u] + 6'd1 - bL[u];
                    bb[u] <= d;
                end else begin
                    for (a = 0; a <= NT; a = a + 1) bC[u][a] <= nC[a];
                    for (a = NT; a >= 1; a = a - 1) bB[u][a] <= bB[u][a - 1];
                    bB[u][0] <= 10'd0;
                end
                for (a = NT; a >= 1; a = a - 1) bW[u][a] <= bW[u][a - 1];
                bW[u][0] <= (bn[u] < 6'd29) ? bS[u][bn[u] + 1] : 10'd0;
                bn[u] <= bn[u] + 6'd1;
            end else if (bact[u] && bn[u] == 6'd30) begin
                for (a = 0; a < NT; a = a + 1) bO[u][a] <= oc_[a];   // Omega = S Lambda mod x^30
                bn[u] <= 6'd31;
            end
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) bsel <= 2'd0;
        else if (s_fin) bsel <= (bsel == NBM - 1) ? 2'd0 : bsel + 1'b1;
    wire c_take = s_fin && bact[bsel] && bn[bsel] == 6'd31;
    // ---------------- Chien + Forney (cc = 0..9 after c_take; c_fin = the last slice, the next take may coincide)
    reg  [5439:0] cw, orig;
    reg  [5:0]    cL;
    reg           c_bad, c_any;
    reg  [3:0]    cc;
    reg           c_busy;
    reg  [9:0]    Rl [0:15];             // lambda_i alpha^{-i 55 cc}
    reg  [9:0]    Ro [0:NT-1];           // omega_i alpha^{-i 55 cc}
    reg  [9:0]    Rx;                    // alpha^{55 cc}
    reg  [5:0]    nroot;
    reg  [5439:0] ncw;
    reg  [549:0]  corr;                  // symbol k of this slice at bits [10 k + 9 -: 10] (position 543 - (55 cc + k))
    reg  [5:0]    nr_add;
    integer e;
    // (H-DIE 10-16, yosys frontend) slice k: lv = Lambda(X^-1), ov = Omega(X^-1), dv = Lambda'(X^-1) = X * sum_{i odd}
    // lambda_i X^-i, ev = X ov / dv (MUT 2: without X); the odd lambda terms are the lv products themselves.
    reg  [159:0] fRl;
    reg  [10 * NT - 1:0] fRo;
    integer fi;
    always @* begin
        for (fi = 0; fi < 16; fi = fi + 1) fRl[10 * fi +: 10] = Rl[fi];
        for (fi = 0; fi < NT; fi = fi + 1) fRo[10 * fi +: 10] = Ro[fi];
    end
    wire [10 * SPC - 1:0] ch_ev;
    wire [SPC - 1:0]      ch_lz;
    generate for (gk = 0; gk < SPC; gk = gk + 1) begin : g_ch
        wire [159:0] pl;
        wire [10 * NT - 1:0] pw;
        reg  [9:0] lv, ov, dv0;
        wire [9:0] xe, dv, idv, q, ev;
        integer m;
        for (ga = 0; ga < 16; ga = ga + 1) begin : g_l
            ot_s81_kp4_dec_cmul #(.E((1023 - (ga * gk) % 1023) % 1023)) u_m (.a(fRl[10 * ga +: 10]), .y(pl[10 * ga +: 10]));
        end
        for (ga = 0; ga < NT; ga = ga + 1) begin : g_w
            ot_s81_kp4_dec_cmul #(.E((1023 - (ga * gk) % 1023) % 1023)) u_m (.a(fRo[10 * ga +: 10]), .y(pw[10 * ga +: 10]));
        end
        always @* begin
            lv = 10'd0; ov = 10'd0; dv0 = 10'd0;
            for (m = 0; m < 16; m = m + 1) lv = lv ^ pl[10 * m +: 10];
            for (m = 0; m < NT; m = m + 1) ov = ov ^ pw[10 * m +: 10];
            for (m = 1; m < 16; m = m + 2) dv0 = dv0 ^ pl[10 * m +: 10];
        end
        ot_s81_kp4_dec_cmul #(.E(gk)) u_x (.a(Rx), .y(xe));
        ot_s81_kp4_dec_vmul u_dv (.a(dv0), .b(xe), .y(dv));
        ot_s81_kp4_dec_inv  u_iv (.a(dv), .y(idv));
        ot_s81_kp4_dec_vmul u_q  (.a(ov), .b(idv), .y(q));
        if (MUT == 2) begin : g_mut
            assign ev = q;
        end else begin : g_ok
            ot_s81_kp4_dec_vmul u_e (.a(xe), .b(q), .y(ev));
        end
        assign ch_ev[10 * gk +: 10] = ev;
        assign ch_lz[gk] = (lv == 10'd0);
    end endgenerate
    always @* begin
        corr = 550'd0; nr_add = 0;
        for (k = 0; k < SPC; k = k + 1) begin
            e = SPC * cc + k;                       // degree: X = alpha^e, symbol position 543 - e
            if (e < 544 && ch_lz[k]) begin
                corr[10 * k + 9 -: 10] = ch_ev[10 * k +: 10];
                nr_add = nr_add + 1;
            end
        end
        ncw = cw ^ ({4890'd0, corr} << (10 * SPC * cc));   // symbol 543 - e sits at bits [10 e + 9 -: 10]
    end
    // slice advance: lambda_i, omega_i times alpha^(-55 i); X times alpha^55
    wire [159:0] nRl;
    wire [10 * NT - 1:0] nRo;
    wire [9:0] nRx;
    generate for (ga = 0; ga < NT; ga = ga + 1) begin : g_adv
        ot_s81_kp4_dec_cmul #(.E((1023 - (ga * SPC) % 1023) % 1023)) u_o (.a(fRo[10 * ga +: 10]), .y(nRo[10 * ga +: 10]));
        if (ga < 16) begin : g_l
            ot_s81_kp4_dec_cmul #(.E((1023 - (ga * SPC) % 1023) % 1023)) u_l (.a(fRl[10 * ga +: 10]), .y(nRl[10 * ga +: 10]));
        end
    end endgenerate
    ot_s81_kp4_dec_cmul #(.E(SPC)) u_adv_x (.a(Rx), .y(nRx));
    wire       c_fin  = c_busy && cc == 4'd9;
    wire [5:0] nr_fin = nroot + nr_add;
    wire       unc    = c_any && (c_bad || nr_fin != cL);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin c_busy <= 1'b0; cc <= 0; nroot <= 0; end
        else begin
            if (c_busy) begin
                cw <= ncw;
                nroot <= nr_fin;
                for (i = 0; i < 16; i = i + 1) Rl[i] <= nRl[10 * i +: 10];
                for (i = 0; i < NT; i = i + 1) Ro[i] <= nRo[10 * i +: 10];
                Rx <= nRx;
                cc <= cc + 1'b1;
                if (cc == 4'd9) c_busy <= 1'b0;
            end
            if (c_take) begin
                cw <= bcw[bsel]; orig <= bcw[bsel]; cL <= bL[bsel]; c_bad <= (bL[bsel] > 6'd15); c_any <= bany[bsel];
                c_busy <= 1'b1; cc <= 0; nroot <= 0; Rx <= 10'd1;
                for (i = 0; i < 16; i = i + 1) Rl[i] <= bC[bsel][i];
                for (i = 0; i < NT; i = i + 1) Ro[i] <= bO[bsel][i];
            end
        end
    // ---------------- emit (oc = 0..9 after c_fin; the last beat coincides with the next c_fin)
    reg  [5439:0] ob;
    reg  [3:0]    oc;
    reg           o_busy, o_unc;
    reg  [4:0]    o_ne;
    wire [5439:0] obsh  = ob << (512 * oc);
    wire [511:0]  obeat = obsh[5419 -: 512];       // = ob[5419 - 512 oc -: 512]
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_busy <= 1'b0; oc <= 0; q_v <= 1'b0; q_first <= 1'b0; q_unc <= 1'b0; q_nerr <= 0; n_corr <= 0; n_unc <= 0; end
        else begin
            q_v <= 1'b0; q_first <= 1'b0;
            if (o_busy) begin
                q_v <= 1'b1; q_first <= (oc == 0); q_unc <= o_unc; q_nerr <= o_ne; q_seq <= ob[5427:5420];
                q_d <= obeat;                              // beats follow the 20-b header
                oc <= oc + 1'b1;
                if (oc == 4'd9) o_busy <= 1'b0;
            end
            if (c_fin) begin
                o_unc <= unc;
                o_ne  <= (c_any && !unc) ? cL[4:0] : 5'd0;
                ob    <= unc ? orig : (c_bad ? cw : ncw);
                if (unc) n_unc <= n_unc + 1; else if (c_any) n_corr <= n_corr + cL;
                o_busy <= 1'b1; oc <= 0;
            end
        end
endmodule
// GF(2^10) product cells of the decoder (H-DIE 10-16, yosys frontend): a * alpha^E (one derivation per exponent),
// a * b, and a^-1 (0 -> 0) -- the same functions as the inlined forms they replace.
module ot_s81_kp4_dec_cmul #(parameter integer E = 0) (input wire [9:0] a, output wire [9:0] y);
`include "ot_s81_gf1024.svh"
    localparam [9:0] C = gf_alpha(E);
    assign y = gf_mul(a, C);
endmodule
module ot_s81_kp4_dec_vmul (input wire [9:0] a, input wire [9:0] b, output wire [9:0] y);
`include "ot_s81_gf1024.svh"
    assign y = gf_mul(a, b);
endmodule
module ot_s81_kp4_dec_inv (input wire [9:0] a, output reg [9:0] y);
`include "ot_s81_gf1024.svh"
    always @* y = gf_inv(a);
endmodule
