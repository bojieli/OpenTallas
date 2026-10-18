`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_bm (S81-KP4 2026-10-17): one key-equation unit of the S81 KP4 RS(544,514) decoder -- the reformulated
// inversionless Berlekamp-Massey algorithm (RiBM, Sarwate & Shanbhag, IEEE TVLSI 9(5) 2001): 3t + 1 = 46 identical
// processing elements, each iteration
//     delta_i <- gamma * delta_(i+1) ^ delta_0 * theta_i                       (i = 0..45, delta_46 = 0)
//     if (delta_0 != 0 && k >= 0): theta_i <- delta_(i+1), gamma <- delta_0, k <- -k - 1, L <- r + 1 - L
//     else                          k <- k + 1
// with delta = theta = {1 at 45, S_29..S_0 at 29..0} initially, gamma = 1, k = L = 0.  After 2t = 30 iterations
// lambda_i = delta_(15 + i) (i = 0..15) and omega_i = delta_i (i = 0..14).  Critical path = one GF(2^10) multiply + XOR
// (the 8cd04168b unit chained discrepancy -> inverse -> coefficient -> update, ~20 XOR levels a cycle).
// Exactness against tools/s81_link/rs544.py (classic BM with inversion): RiBM's lambda is the BM connection polynomial
// times a nonzero constant, with the same L sequence (k = r - 2L; delta_0 = the scaled discrepancy), so the Chien roots
// and the uncorrectable test (L > 15, roots != L) are unchanged.  RiBM's omega is the error evaluator in its x^(2t)
// form: the Forney value is omega(X^-1) X^-30 / lambda_odd(X^-1) -- the decoder evaluates omega_i against X^-(i + 30)
// (checked in Python against rs544.decode on 800 random patterns, 0..25 symbol errors: 0 mismatches).
// Schedule: ld (iteration r = 0, done here from S directly: delta / theta operands are muxed to the S image) at cycle
// t, iterations 1..29 at t + 1 .. t + 29, the result in delta during t + 30 (done = 1) -- the cycle the round robin
// reloads the unit with the frame 30 cycles later.  The datapath iterates every cycle (no enable); results are read only
// in the done cycle.  Control copies are kept per PE group (NG groups of <= 12 PEs: <= ~130 loads per copy).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_bm #(parameter integer NG = 4, parameter integer NCD = 4) (
    input  wire            clk,
    input  wire            rs_n,       // regional synchronous reset leaf
    input  wire [NG-1:0]   ld,         // load this cycle (NG identical copies, one per PE group)
    input  wire [299:0]    S,          // S_j at [10 j +: 10]
    output wire [159:0]    lam,        // lambda_i at [10 i +: 10], i = 0..15 (valid in the done cycle)
    output wire [149:0]    om,         // omega_i  at [10 i +: 10], i = 0..14
    output reg  [4:0]      L,
    output reg             any,        // a nonzero syndrome
    output reg  [NCD-1:0]  done        // NCD identical copies
);
    localparam integer NPE = 46, GS = 12;
    reg  [9:0] d  [0:NPE-1];
    reg  [9:0] th [0:NPE-1];
    (* keep *) reg [9:0] gm [0:NG-1];      // gamma copies
    (* keep *) reg [9:0] dz [0:NG-1];      // delta_0 copies
    (* keep *) reg [5:0] kc [0:NG-1];      // k copies (two's complement)
    reg  [4:0] n;                          // iteration index of the next update (0 = load)
    // initial image: delta_j(0) = theta_j(0) = S_j (j < 30), 1 (j = 45), else 0
    function automatic [9:0] dinit(input integer j);
        dinit = (j < 30) ? S[10 * j +: 10] : ((j == 45) ? 10'd1 : 10'd0);
    endfunction
    wire [9:0] nd [0:NPE-1];
    wire [NG-1:0] upd;
    genvar gi, gg;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_grp
        wire [9:0] G  = ld[gg] ? 10'd1 : gm[gg];
        wire [9:0] D0 = ld[gg] ? S[9:0] : dz[gg];
        wire [5:0] K  = ld[gg] ? 6'd0 : kc[gg];
        assign upd[gg] = (D0 != 10'd0) && !K[5];
        always @(posedge clk) begin
            gm[gg] <= upd[gg] ? D0 : G;
            kc[gg] <= upd[gg] ? (~K) : (K + 6'd1);      // -K - 1 = ~K
            dz[gg] <= nd[0];
        end
        for (gi = gg * GS; gi < ((gg == NG - 1) ? NPE : (gg + 1) * GS); gi = gi + 1) begin : g_pe
            wire [9:0] Dn = ld[gg] ? dinit(gi + 1) : ((gi + 1 < NPE) ? d[(gi + 1 < NPE) ? gi + 1 : 0] : 10'd0);
            wire [9:0] Th = ld[gg] ? dinit(gi) : th[gi];
            wire [9:0] pa, pb;
            ot_s81_kp4_vmul u_a (.a(G),  .b(Dn), .y(pa));
            ot_s81_kp4_vmul u_b (.a(D0), .b(Th), .y(pb));
            assign nd[gi] = pa ^ pb;
            always @(posedge clk) begin
                d[gi]  <= nd[gi];
                th[gi] <= upd[gg] ? Dn : Th;
            end
        end
    end endgenerate
    // L, iteration count, any, done (group-0 copies decide L)
    wire [4:0] Lc = ld[0] ? 5'd0 : L;
    wire [4:0] r  = ld[0] ? 5'd0 : n;
    always @(posedge clk) begin
        L <= upd[0] ? (r + 5'd1 - Lc) : Lc;
        if (ld[0]) any <= |S;
    end
    integer q;
    always @(posedge clk)
        if (!rs_n) begin n <= 5'd31; done <= {NCD{1'b0}}; end
        else begin
            if (ld[0]) n <= 5'd1;
            else if (n != 5'd31) n <= n + 5'd1;
            for (q = 0; q < NCD; q = q + 1) done[q] <= !ld[0] && (n == 5'd29);
        end
    genvar go;
    generate for (go = 0; go < 16; go = go + 1) begin : g_lam
        assign lam[10 * go +: 10] = d[15 + go];
        if (go < 15) begin : g_om
            assign om[10 * go +: 10] = d[go];
        end
    end endgenerate
endmodule
