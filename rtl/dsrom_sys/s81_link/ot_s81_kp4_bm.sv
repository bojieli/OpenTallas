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
// THC (opt-in, default 0 = the signed form): theta_45 in its reachable form.  theta_45 is 1 at the load and takes
// delta_46 = 0 on an update, so after a load it is 0 or 1: with THC = 1 its bits [9:1] are read as constant 0.  Same
// values from the first load on; before it the unloaded unit's X bits read 0 (no reset there; results are read only
// in the done cycle after a load).  Synthesis folds those bits anyway; THC = 1 states it in the RTL so the X power-up
// and the folded netlist agree under equivalence checking (HBM ot_pdie_serdes_rx LEC, th[45][9:1]).
// ---------------------------------------------------------------------------------------------------------------
// PREL (opt-in, default 0): the load is taken one cycle earlier, into the state registers (d, th, dz, gm, kc) at the end of
// the ldp cycle, so iteration 0 runs in the ld cycle from registers like every other iteration and the load muxes leave
// the GF multiply cone (S81-TYPES-10-RCK: vD routed TT -64 ps on ld2/Sl -> operand mux -> multiply -> 46 dz copies, the
// remaining BM class after SPCYC).  The delta state is then overwritten one cycle early, so lam/om come from result
// registers fed by nd: same value in every cycle.  ld (one cycle after ldp) stays the control timing: L, any, n, done,
// the reload cadence and all external cycles are unchanged; PIN CYCLES +0.
module ot_s81_kp4_bm #(parameter integer NG = 4, parameter integer NCD = 4, parameter integer THC = 0, parameter integer PREL = 0) (
    input  wire            clk,
    input  wire            rs_n,       // regional synchronous reset leaf
    input  wire [NG-1:0]   ld,         // load this cycle (NG identical copies, one per PE group)
    input  wire [299:0]    S,          // S_j at [10 j +: 10]
    output wire [159:0]    lam,        // lambda_i at [10 i +: 10], i = 0..15 (valid in the done cycle)
    output wire [149:0]    om,         // omega_i  at [10 i +: 10], i = 0..14
    output reg  [4:0]      L,
    output reg             any,        // a nonzero syndrome
    output reg  [NCD-1:0]  done,       // NCD identical copies
    input  wire [NG-1:0]   ldp,        // PREL: the load, one cycle before ld (one copy per PE group); else tied 0
    input  wire [299:0]    Sp          // PREL: the S image, one cycle before S; else tied 0
);
    localparam integer NPE = 46, GS = (NPE + NG - 1) / NG;   // 12 at NG 4 (unchanged); 6 at NG 8 (S81-RCK-10 vJ)
    reg  [9:0] d  [0:NPE-1];
    reg  [9:0] th [0:((THC != 0) ? NPE-2 : NPE-1)];
    // Reachable theta45 stores only bit0: upper bits are always zero after the first load.
    // No never-reset constant-D tail flops exist in this opt-in form.
    reg th_last;
    (* keep *) reg [9:0] gm [0:NG-1];      // gamma copies
    (* keep *) reg [9:0] dz [0:NG-1];      // delta_0 copies
    (* keep *) reg [5:0] kc [0:NG-1];      // k copies (two's complement)
    reg  [4:0] n;                          // iteration index of the next update (0 = load)
    // initial image: delta_j(0) = theta_j(0) = S_j (j < 30), 1 (j = 45), else 0
    function automatic [9:0] dinit(input integer j);
        dinit = (j < 30) ? S[10 * j +: 10] : ((j == 45) ? 10'd1 : 10'd0);
    endfunction
    function automatic [9:0] dinitp(input integer j);
        dinitp = (j < 30) ? Sp[10 * j +: 10] : ((j == 45) ? 10'd1 : 10'd0);
    endfunction
    wire [9:0] nd [0:NPE-1];
    wire [NG-1:0] upd;
    // PREL: PE0's next value, including the load, one shared mux per bit (S0 fans out to one load, not to 46 dz copies)
    wire [9:0] nd0p = (PREL != 0 && ldp[0]) ? Sp[9:0] : nd[0];
    genvar gi, gg;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_grp
        wire [9:0] G  = (PREL != 0) ? gm[gg] : (ld[gg] ? 10'd1 : gm[gg]);
        wire [9:0] D0 = (PREL != 0) ? dz[gg] : (ld[gg] ? S[9:0] : dz[gg]);
        wire [5:0] K  = (PREL != 0) ? kc[gg] : (ld[gg] ? 6'd0 : kc[gg]);
        assign upd[gg] = (D0 != 10'd0) && !K[5];
        always @(posedge clk) begin
            if (PREL != 0 && ldp[gg]) begin
`ifdef OT_BM_PREL_MUT
                gm[gg] <= 10'd1; kc[gg] <= 6'd1;        // bench mutant: wrong k at the load
`else
                gm[gg] <= 10'd1; kc[gg] <= 6'd0;
`endif
            end else begin
                gm[gg] <= upd[gg] ? D0 : G;
                kc[gg] <= upd[gg] ? (~K) : (K + 6'd1);      // -K - 1 = ~K
            end
            dz[gg] <= nd0p;
        end
        for (gi = gg * GS; gi < ((gg == NG - 1) ? NPE : (gg + 1) * GS); gi = gi + 1) begin : g_pe
            wire [9:0] Dn = (PREL == 0 && ld[gg]) ? dinit(gi + 1) : ((gi + 1 < NPE) ? d[(gi + 1 < NPE) ? gi + 1 : 0] : 10'd0);
            wire [9:0] thq;
            if (THC != 0 && gi == NPE-1) begin:g_tail_read
                assign thq={9'd0,th_last};
            end else begin:g_normal_read
                assign thq=th[gi];
            end
            wire [9:0] Th = (PREL == 0 && ld[gg]) ? dinit(gi) : thq;
            wire [9:0] pa, pb;
            ot_s81_kp4_vmul u_a (.a(G),  .b(Dn), .y(pa));
            ot_s81_kp4_vmul u_b (.a(D0), .b(Th), .y(pb));
            assign nd[gi] = pa ^ pb;
            always @(posedge clk) d[gi] <= (gi == 0) ? nd0p : ((PREL != 0 && ldp[gg]) ? dinitp(gi) : nd[gi]);
            if (THC != 0 && gi == NPE-1) begin:g_tail_write
                always @(posedge clk) th_last <= (PREL != 0 && ldp[gg]) ? 1'b1 : (upd[gg] ? Dn[0] : Th[0]);
            end else begin:g_normal_write
                always @(posedge clk) th[gi] <= (PREL != 0 && ldp[gg]) ? dinitp(gi) : (upd[gg] ? Dn : Th);
            end
        end
    end endgenerate
    // L, iteration count, any, done (group-0 copies decide L)
    reg anyp;                              // PREL: |S, registered from the early image
    always @(posedge clk) anyp <= |Sp;
    wire [4:0] Lc = ld[0] ? 5'd0 : L;
    wire [4:0] r  = ld[0] ? 5'd0 : n;
    always @(posedge clk) begin
        L <= upd[0] ? (r + 5'd1 - Lc) : Lc;
        if (ld[0]) any <= (PREL != 0) ? anyp : |S;
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
    generate if (PREL != 0) begin : g_resq
        // result registers: the same value as d in every cycle; d itself may already hold the next frame's load
        reg [9:0] lq [0:15];
        reg [9:0] oq [0:14];
        integer qi;
        always @(posedge clk) begin
            for (qi = 0; qi < 16; qi = qi + 1) lq[qi] <= nd[15 + qi];
            for (qi = 0; qi < 15; qi = qi + 1) oq[qi] <= nd[qi];
        end
        for (go = 0; go < 16; go = go + 1) begin : g_lam
            assign lam[10 * go +: 10] = lq[go];
            if (go < 15) begin : g_om
                assign om[10 * go +: 10] = oq[go];
            end
        end
    end else begin : g_resd
        for (go = 0; go < 16; go = go + 1) begin : g_lam
            assign lam[10 * go +: 10] = d[15 + go];
            if (go < 15) begin : g_om
                assign om[10 * go +: 10] = d[go];
            end
        end
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_bm_it2 (HARD-S81-SERDES-1 2026-11-13; used only under `define OT_S81_KP4_BM_IT2, so every other form is
// unchanged): the same RiBM unit with a TWO-CYCLE iteration, the standard folded form of a recurrence whose loop is one
// GF(2^10) multiply + XOR.  serdes__t2 kitC2 (template island, placement): u_syn.Sl -> operand mux -> multiply -> XOR ->
// u_bm.d was 12 cells + 21 wire buffers, 3.2 ns, 2247 endpoints; the loop cannot take a register without taking time.
//   ld (cycle t)      : state <= the S image (delta = theta = {1 at 45, S_29..S_0}, gamma = 1, k = 0); no multiply.
//   M phase (t+1+2r)  : pa_q <= gamma * delta_(i+1), pb_q <= delta_0 * theta_i, upd_q <= (delta_0 != 0 && k >= 0).
//   U phase (t+2+2r)  : delta_i <= pa_q ^ pb_q; theta / gamma / k / L update from upd_q exactly as ot_s81_kp4_bm.
//   r = 0..29; done is high in cycle t + 61 with the result in delta (ot_s81_kp4_bm: t + 30).  PIN CYCLES: k_* +31 rck.
// The unit is busy 61 cycles, so the syndrome tile runs NBM = 7 units (one frame every 10 cycles: reload after 70) and
// ot_s81_kp4_ddly delays the words 31 more (a 31-word register line before the 64-word delay memory).
// Same arithmetic, same L / any / lam / om values as ot_s81_kp4_bm for every S (bench: KP4 gate vs rs544.py + column
// lock-step).  `define OT_BM_IT2_MUT (bench only): 29 iterations instead of 30 -> must FAIL the KP4 gate.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_bm_it2 #(parameter integer NG = 4, parameter integer NCD = 4) (
    input  wire            clk,
    input  wire            rs_n,
    input  wire [NG-1:0]   ld,
    input  wire [299:0]    S,
    output wire [159:0]    lam,
    output wire [149:0]    om,
    output reg  [4:0]      L,
    output reg             any,
    output reg  [NCD-1:0]  done
);
    localparam integer NPE = 46, GS = (NPE + NG - 1) / NG;
`ifdef OT_BM_IT2_MUT
    localparam [4:0] LAST = 5'd28;
`else
    localparam [4:0] LAST = 5'd29;
`endif
    reg  [9:0] d  [0:NPE-1];
    reg  [9:0] th [0:NPE-1];
    reg  [9:0] pa_q [0:NPE-1];
    reg  [9:0] pb_q [0:NPE-1];
    (* keep *) reg [9:0] gm [0:NG-1];
    (* keep *) reg [9:0] dz [0:NG-1];
    (* keep *) reg [5:0] kc [0:NG-1];
    (* keep *) reg [NG-1:0] upd_q, ph_m, ph_u;      // phase copies, one per PE group
    reg  [4:0] n;
    function automatic [9:0] dinit(input integer j);
        dinit = (j < 30) ? S[10 * j +: 10] : ((j == 45) ? 10'd1 : 10'd0);
    endfunction
    wire [9:0] nd0 = pa_q[0] ^ pb_q[0];
    genvar gi, gg;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_grp
        always @(posedge clk) begin
            if (ld[gg]) begin gm[gg] <= 10'd1; kc[gg] <= 6'd0; dz[gg] <= S[9:0]; end
            else if (ph_u[gg]) begin
                gm[gg] <= upd_q[gg] ? dz[gg] : gm[gg];
                kc[gg] <= upd_q[gg] ? (~kc[gg]) : (kc[gg] + 6'd1);
                dz[gg] <= nd0;
            end
            if (ph_m[gg]) upd_q[gg] <= (dz[gg] != 10'd0) && !kc[gg][5];
            if (!rs_n) begin ph_m[gg] <= 1'b0; ph_u[gg] <= 1'b0; end
            else if (ld[gg]) begin ph_m[gg] <= 1'b1; ph_u[gg] <= 1'b0; end
            else begin ph_m[gg] <= ph_u[gg] && (n != LAST); ph_u[gg] <= ph_m[gg]; end
        end
        for (gi = gg * GS; gi < ((gg == NG - 1) ? NPE : (gg + 1) * GS); gi = gi + 1) begin : g_pe
            wire [9:0] Dn = (gi + 1 < NPE) ? d[(gi + 1 < NPE) ? gi + 1 : 0] : 10'd0;
            wire [9:0] pa, pb;
            ot_s81_kp4_vmul u_a (.a(gm[gg]), .b(Dn),     .y(pa));
            ot_s81_kp4_vmul u_b (.a(dz[gg]), .b(th[gi]), .y(pb));
            always @(posedge clk) begin
                if (ph_m[gg]) begin pa_q[gi] <= pa; pb_q[gi] <= pb; end
                if (ld[gg]) begin d[gi] <= dinit(gi); th[gi] <= dinit(gi); end
                else if (ph_u[gg]) begin
                    d[gi]  <= pa_q[gi] ^ pb_q[gi];
                    th[gi] <= upd_q[gg] ? Dn : th[gi];
                end
            end
        end
    end endgenerate
    integer q;
    always @(posedge clk) begin
        if (ld[0]) begin L <= 5'd0; any <= |S; end
        else if (ph_u[0]) L <= upd_q[0] ? (n + 5'd1 - L) : L;
        if (!rs_n) begin n <= 5'd31; done <= {NCD{1'b0}}; end
        else begin
            if (ld[0]) n <= 5'd0;
            else if (ph_u[0] && n != 5'd31) n <= (n == LAST) ? 5'd31 : n + 5'd1;
            for (q = 0; q < NCD; q = q + 1) done[q] <= !ld[0] && ph_u[0] && (n == LAST);
        end
    end
    genvar go;
    generate for (go = 0; go < 16; go = go + 1) begin : g_lam
        assign lam[10 * go +: 10] = d[15 + go];
        if (go < 15) begin : g_om
            assign om[10 * go +: 10] = d[go];
        end
    end endgenerate
endmodule
