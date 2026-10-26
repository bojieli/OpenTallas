`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dchn (S81-KP4 2026-10-17): Chien / Forney hard tile of the S81 KP4 RS(544,514) decoder cluster
// ot_s81_kp4_dec (frame / code: tools/s81_link/rs544.py; cluster structure and schedule: ot_s81_kp4_dec.sv).
//   forward Chien search + Forney over 55 lanes in two registered stages (E1: Lambda(X^-1), Omega(X^-1) X^-30,
//   Lambda_odd(X^-1); E2: e = Omega X^-30 / Lambda_odd with a kept-hierarchy inverse LUT, so yosys cannot fold the E1
//   register into an inferred ROM), a 64-leaf balanced root-count tree, the uncorrectable decision (L > 15 or roots
//   != L), and the correction masks re-cut to 544-bit PMA words (cw_q, to ot_s81_kp4_dout).  Every time is relative to
//   the k_v the tile sees: T' = that cycle - 42; chunk c is evaluated at T' + 43 + c, cw_q of word k at T' + 46 + k,
//   apply / o_unc / o_ne / fs at T' + 56.  Regional synchronous reset, no datapath reset.
// MUT 2: Forney value without the division (bench mutant).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dchn #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    k_v,
    input  wire [309:0]  k_lo,
    input  wire [4:0]    k_L,
    input  wire          k_any,
    output reg  [543:0]  cw_q,          // correction mask of PMA word k (to ot_s81_kp4_dout's SRAM delay)
    output reg  [7:0]    apply,         // the frame is corrected (8 identical copies, 68 mask bits each in dout)
    output reg           o_unc,         // the frame is uncorrectable
    output reg  [4:0]    o_ne,          // symbols corrected
    output reg           fs,            // frame start: beat 0 of the frame leaves dout's beat register next cycle
    output reg  [31:0]   n_corr, n_unc
);
`include "ot_s81_gf1024.svh"
    localparam integer NT = 30, SPC = 55;
    localparam integer NRL = 2;          // Chien lambda / omega register copies (lanes 0..27 / 28..54)
    localparam integer NRW = 17;         // corr-word select copies (32 bits each)
    wire [1:0] rs_n;
    ot_s81_kp4_rst #(.NL(2)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
    integer i, q;
    genvar gk, gb, gi, gu;
    wire [309:0] lsel = k_lo;
    wire [3:0]   cl = k_v;
    reg  [9:0] Rl [0:NRL-1][0:15];
    reg  [9:0] Ro [0:NRL-1][0:NT/2-1];
    generate for (gi = 0; gi < 16; gi = gi + 1) begin : g_rl
        wire [9:0] li, la [0:NRL-1];
        ot_s81_kp4_cmul #(.E(-543 * gi)) u_li (.a(lsel[10 * gi +: 10]), .y(li));
        for (gu = 0; gu < NRL; gu = gu + 1) begin : g_c
            ot_s81_kp4_cmul #(.E(55 * gi)) u_la (.a(Rl[gu][gi]), .y(la[gu]));
            always @(posedge clk) Rl[gu][gi] <= cl[(gi * 2 + gu) % 4] ? li : la[gu];
        end
    end endgenerate
    generate for (gi = 0; gi < NT / 2; gi = gi + 1) begin : g_ro
        wire [9:0] oi, oa [0:NRL-1];
        ot_s81_kp4_cmul #(.E(-543 * (gi + 30))) u_oi (.a(lsel[160 + 10 * gi +: 10]), .y(oi));
        for (gu = 0; gu < NRL; gu = gu + 1) begin : g_c
            ot_s81_kp4_cmul #(.E(55 * (gi + 30))) u_oa (.a(Ro[gu][gi]), .y(oa[gu]));
            always @(posedge clk) Ro[gu][gi] <= cl[(gi * 2 + gu + 1) % 4] ? oi : oa[gu];
        end
    end endgenerate
    // frame scalars: captured at load, copied to fin_* at chunk 9 (the root count is final at T + 55)
    reg  [4:0] cL, fin_L;
    reg        c_bad, c_any, fin_bad, fin_any;
    reg  [9:0] cc;                       // one-hot chunk index of the Chien evaluation (chunk c at T + 43 + c)
    reg  [9:0] ce1;                      // ... at E1 (T + 44 + c)
    reg  [9:0] ce2;                      // ... at E2 (T + 45 + c)
    reg        ce3_9;                    // chunk 9 at the root accumulator (T + 55)
    (* keep *) reg [9:0] cw_s [0:NRW-1]; // ce1 delayed: the corr-word select at E2, NRW copies
    always @(posedge clk) begin
        if (cl[0]) begin cL <= k_L; c_bad <= (k_L > 5'd15); c_any <= k_any; end
        if (cc[9]) begin fin_L <= cL; fin_bad <= c_bad; fin_any <= c_any; end
    end
    always @(posedge clk)
        if (!rs_n[0]) begin
            cc <= 0; ce1 <= 0; ce2 <= 0; ce3_9 <= 1'b0;
            for (i = 0; i < NRW; i = i + 1) cw_s[i] <= 10'd0;
        end else begin
            cc <= {cc[8:0], cl[0]};
            ce1 <= cc; ce2 <= ce1; ce3_9 <= ce2[9];
            for (i = 0; i < NRW; i = i + 1) cw_s[i] <= ce1;
        end
    // lanes
    reg  [SPC-1:0]   e1_lz;
    reg  [9:0]       e1_ov [0:SPC-1];
    reg  [9:0]       e1_dv [0:SPC-1];
    reg  [549:0]     crc;                // correction chunk (symbol k at [549 - 10 k -: 10], stream order)
    reg  [5:0]       nrc;                // roots in the chunk
    wire [SPC-1:0]   lzv;
    generate for (gk = 0; gk < SPC; gk = gk + 1) begin : g_ch
        localparam integer CP = (gk < 28) ? 0 : 1;
        wire [159:0] pl;
        wire [149:0] pw;
        reg  [9:0] lv, ov, dv0;
        integer m;
        for (gi = 0; gi < 16; gi = gi + 1) begin : g_l
            ot_s81_kp4_cmul #(.E(gi * gk)) u_m (.a(Rl[CP][gi]), .y(pl[10 * gi +: 10]));
        end
        for (gi = 0; gi < NT / 2; gi = gi + 1) begin : g_w
            ot_s81_kp4_cmul #(.E((gi + 30) * gk)) u_m (.a(Ro[CP][gi]), .y(pw[10 * gi +: 10]));
        end
        always @* begin
            lv = 10'd0; ov = 10'd0; dv0 = 10'd0;
            for (m = 0; m < 16; m = m + 1) lv = lv ^ pl[10 * m +: 10];
            for (m = 0; m < NT / 2; m = m + 1) ov = ov ^ pw[10 * m +: 10];
            for (m = 1; m < 16; m = m + 2) dv0 = dv0 ^ pl[10 * m +: 10];
        end
        always @(posedge clk) begin e1_lz[gk] <= (lv == 10'd0); e1_ov[gk] <= ov; e1_dv[gk] <= dv0; end
        // E2: e = Omega(X^-1) X^-30 / Lambda_odd(X^-1)  (b = 0: the X of X Omega / Lambda' cancels)
        wire [9:0] idv, ev;
        ot_s81_kp4_inv u_iv (.a(e1_dv[gk]), .y(idv));
        if (MUT == 2) begin : g_mut
            assign ev = e1_ov[gk];
        end else begin : g_ok
            ot_s81_kp4_vmul u_e (.a(e1_ov[gk]), .b(idv), .y(ev));
        end
        assign lzv[gk] = e1_lz[gk] && !(gk >= 49 && ce1[9]);     // positions 544..549 of chunk 9 do not exist
        always @(posedge clk) crc[549 - 10 * gk -: 10] <= lzv[gk] ? ev : 10'd0;
    end endgenerate
    // root count of the chunk: balanced adder tree (64 leaves, 6 levels)
    reg [6:0] pt [0:126];
    integer pa;
    always @* begin
        for (pa = 0; pa < 64; pa = pa + 1) pt[63 + pa] = (pa < SPC) ? {6'd0, lzv[pa]} : 7'd0;
        for (pa = 62; pa >= 0; pa = pa - 1) pt[pa] = pt[2 * pa + 1] + pt[2 * pa + 2];
    end
    always @(posedge clk) nrc <= pt[0][5:0];
    reg  [5:0] nacc;                     // roots of the frame so far (final at T + 55)
    always @(posedge clk) nacc <= (ce2[0] ? 6'd0 : nacc) + nrc;
    // correction words: word w = {chunk w-1, chunk w}[549 + 6 w -: 544] at T + 45 + w -> cw_q at T + 46 + w
    reg  [549:0] crp;
    always @(posedge clk) crp <= crc;
    wire [1099:0] wc2 = {crp, crc};
    wire [543:0]  csrc [0:9];
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_csrc
        assign csrc[gk] = wc2[549 + 6 * gk -: 544];
    end endgenerate
    generate for (gb = 0; gb < 544; gb = gb + 1) begin : g_cwm
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = csrc[gk][gb];
        end
        always @(posedge clk) cw_q[gb] <= |(s & cw_s[gb / 32]);
    end endgenerate
    // ================= decision (T' + 55 -> T' + 56): apply / o_unc / o_ne / fs to dout, counters
    wire unc_n = fin_any && (fin_bad || nacc != {1'b0, fin_L});
    reg  [12:0] pl;                      // cl delayed: fs at T' + 56
    always @(posedge clk)
        if (!rs_n[1]) begin
            pl <= 0; fs <= 1'b0; apply <= 0; o_unc <= 1'b0; o_ne <= 0; n_corr <= 0; n_unc <= 0;
        end else begin
            pl <= {pl[11:0], cl[1]};
            fs <= pl[12];
            if (ce3_9) begin
                apply <= {8{!unc_n}};
                o_unc <= unc_n;
                o_ne  <= (fin_any && !unc_n) ? fin_L : 5'd0;
                if (unc_n) n_unc <= n_unc + 1; else if (fin_any) n_corr <= n_corr + fin_L;
            end
        end
endmodule
