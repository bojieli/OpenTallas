// FROZEN REFERENCE (S81-TILES2 2026-10-17): the two-tile KP4 decoder ot_s81_kp4_dec (dec_a + dec_b) of commit 33a35eb7d,
// modules renamed *_r33, for the bit-exact equivalence bench tb_s81_kp4_eq.sv of the four-tile re-split.  Not synthesised.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dec_a_r33 (S81-KP4 2026-10-17): FRONT hard sub-tile of the S81 KP4 RS(544,514) decoder cluster ot_s81_kp4_dec_r33
// (frame / code: tools/s81_link/rs544.py; structure and schedule: ot_s81_kp4_dec_r33.sv).  West tile, PMA side:
//   codeword alignment (AM hunt / lock, as 8cd04168b) on REGISTERED port data (am_ok and p_v are registered before the
//   FSM: no popcount -> FSM -> 32-bit counter path from the pins), syndromes on the arriving stream, NBM = 3 RiBM
//   key-equation units (round robin), and the received-word SRAM delay line u_dmem (64 x 546, written at T + k, read
//   at T + 55 + k).  To the back tile (east face): the delayed words d_q (straight from the macro read port into the
//   output pin registers) and the key-equation result of the unit that finishes (k_v x 4 copies, k_lo = {omega,
//   lambda}, k_L, k_any) -- both cross the same seam, so the back tile's fixed schedule is unchanged by its latency.
//   T = the cycle word 0 of a frame sits in x1.  Regional synchronous reset, no datapath reset.
// MUT 3: the syndrome loop is not restarted at chunk 0 (stale syndromes) -- bench mutant of this tile.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dec_a_r33 #(parameter integer MUT = 0, parameter integer NBM = 3) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          p_v,
    input  wire [543:0]  p_d,
    output wire [543:0]  d_q,           // received word k of a frame at T + 56 + k (macro read port)
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
    localparam integer DD = 55;          // data SRAM delay (write T + k, read T + 55 + k)
    wire [3:0] rs_n;
    ot_s81_kp4_rst #(.NL(4)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
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
    // ================= received-word SRAM delay line (write and read every cycle; fixed distance DD)
    reg  [5:0] ptr;
    always @(posedge clk) if (!rs_n[3]) ptr <= 6'd0; else ptr <= ptr + 6'd1;
    wire [5:0] rd_d = ptr - DD[5:0];
    wire [545:0] d_rd;
    ot_sram_1r1w2c_64x546_m1 u_dmem (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in(rd_d), .rd_out(d_rd),
        .w_ce_in(1'b1), .w_addr_in(ptr), .wd_in({2'b00, x1}), .w_mask_in({546{1'b1}}));
    assign d_q = d_rd[543:0];
endmodule
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dec_b_r33 (S81-KP4 2026-10-17): BACK hard sub-tile of the S81 KP4 RS(544,514) decoder cluster ot_s81_kp4_dec_r33
// (frame / code: tools/s81_link/rs544.py; structure and schedule: ot_s81_kp4_dec_r33.sv).  East tile, core side:
//   forward Chien search + Forney (55 lanes, two registered stages; e = Omega(X^-1) X^-30 / Lambda_odd(X^-1)), root
//   count and the uncorrectable decision, correction masks re-cut to PMA words and delayed in u_cmem (32 x 546), the
//   corrected word d_q ^ mask and the lane beats.  From the front tile (west face): d_q (received words) and the
//   key-equation result k_* -- both through the same seam, so every time here is relative to k_v: with T' = the cycle
//   k_v is seen minus 42, chunk c is evaluated at T' + 43 + c and beat k leaves q_d at T' + 58 + k.
// The Forney inverse cell is a kept-hierarchy LUT (ot_s81_kp4_inv): yosys must not fold the E1 register into an
// inferred ROM read port (that moved the 1024-entry decode into the Lambda-evaluation stage: 17 levels, 683 ps).
// Regional synchronous reset, no datapath reset.  MUT 2: Forney value without the division (bench mutant).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dec_b_r33 #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [543:0]  d_q,
    input  wire [3:0]    k_v,
    input  wire [309:0]  k_lo,
    input  wire [4:0]    k_L,
    input  wire          k_any,
    output reg           q_v,
    output reg  [511:0]  q_d,
    output reg           q_first,
    output reg           q_unc,
    output reg  [4:0]    q_nerr,
    output reg  [7:0]    q_seq,
    output reg  [31:0]   n_corr, n_unc
);
`include "ot_s81_gf1024.svh"
    localparam integer NT = 30, SPC = 55;
    localparam integer NRL = 2;          // Chien lambda / omega register copies (lanes 0..27 / 28..54)
    localparam integer NRW = 17;         // corr-word select copies (32 bits each)
    localparam integer NRA = 8;          // apply copies (68 bits each)
    localparam integer NRO = 16;         // beat select copies (32 bits each)
    localparam integer DC = 9;           // corr SRAM delay (write T' + 46 + k, read T' + 55 + k)
    wire [2:0] rs_n;
    ot_s81_kp4_rst #(.NL(3)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
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
    reg  [543:0] cw_q;
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
    // ================= correction-mask SRAM delay (write and read every cycle; fixed distance DC)
    reg  [4:0] ptr;                      // free-running cycle pointer
    always @(posedge clk) if (!rs_n[1]) ptr <= 5'd0; else ptr <= ptr + 5'd1;
    wire [4:0] rd_c = ptr - DC[4:0];
    wire [545:0] c_rd;
    ot_sram_1r1w_32x546_m1 u_cmem (.clk(clk), .r_ce_in(1'b1), .r_addr_in(rd_c), .rd_out(c_rd),
        .w_ce_in(1'b1), .w_addr_in(ptr), .wd_in({2'b00, cw_q}), .w_mask_in({546{1'b1}}));
    // ================= decision (T + 55 -> T + 56), corrected words (T + 57 + k), beats (q_d at T + 58 + k)
    wire unc_n = fin_any && (fin_bad || nacc != {1'b0, fin_L});
    reg  o_unc;
    reg  [4:0] o_ne;
    (* keep *) reg [NRA-1:0] apply;
    reg  [13:0] pl;                      // cl delayed: pl[13] at T + 56
    (* keep *) reg [9:0] os [0:NRO-1];   // one-hot beat index: os[*][k] at T + 57 + k
    always @(posedge clk)
        if (!rs_n[2]) begin
            pl <= 0; apply <= 0; o_unc <= 1'b0; o_ne <= 0; n_corr <= 0; n_unc <= 0;
            for (i = 0; i < NRO; i = i + 1) os[i] <= 10'd0;
        end else begin
            pl <= {pl[12:0], cl[1]};
            for (i = 0; i < NRO; i = i + 1) os[i] <= {os[i][8:0], pl[13]};
            if (ce3_9) begin
                apply <= {NRA{!unc_n}};
                o_unc <= unc_n;
                o_ne  <= (fin_any && !unc_n) ? fin_L : 5'd0;
                if (unc_n) n_unc <= n_unc + 1; else if (fin_any) n_corr <= n_corr + fin_L;
            end
        end
    reg  [543:0] cwo, cwp;
    generate for (gb = 0; gb < 544; gb = gb + 1) begin : g_cor
        always @(posedge clk) cwo[gb] <= d_q[gb] ^ (apply[gb / 68] & c_rd[gb]);
    end endgenerate
    always @(posedge clk) cwp <= cwo;
    wire [1087:0] w2 = {cwp, cwo};
    wire [511:0]  bsrc [0:9];
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_bsrc
        assign bsrc[gk] = w2[523 + 32 * gk -: 512];
    end endgenerate
    generate for (gb = 0; gb < 512; gb = gb + 1) begin : g_bm_o
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = bsrc[gk][gb];
        end
        always @(posedge clk) q_d[gb] <= |(s & os[gb / 32]);
    end endgenerate
    always @(posedge clk)
        if (!rs_n[2]) begin q_v <= 1'b0; q_first <= 1'b0; q_unc <= 1'b0; q_nerr <= 0; q_seq <= 0; end
        else begin
            q_v <= |os[0];
            q_first <= os[0][0];
            if (os[0][0]) begin q_unc <= o_unc; q_nerr <= o_ne; q_seq <= cwo[531:524]; end
        end
endmodule
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dec_r33 (s81-die-rtl-bind 2026-10-14, die item F10; STREAMING rewrite S81-KP4 2026-10-17): the receive FEC of
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
//   u_a = ot_s81_kp4_dec_a_r33 (west, PMA side): alignment, syndromes on the arriving stream, 3 RiBM key-equation units,
//         the 64 x 546 received-word SRAM delay line;
//   u_b = ot_s81_kp4_dec_b_r33 (east, core side): forward Chien / Forney, root count + decision, the 32 x 546 correction-mask
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
module ot_s81_kp4_dec_r33 #(parameter integer MUT = 0) (
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
    ot_s81_kp4_dec_a_r33 #(.MUT(MUT)) u_a (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .d_q(d_q), .k_v(k_v), .k_lo(k_lo), .k_L(k_L),
        .k_any(k_any), .lock(lock), .n_relock(n_relock));
    ot_s81_kp4_dec_b_r33 #(.MUT(MUT)) u_b (.clk(clk), .rst_n(rst_n), .d_q(d_q), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .n_corr(n_corr), .n_unc(n_unc));
endmodule
