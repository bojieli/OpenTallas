`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dec_b (S81-KP4 2026-10-17): BACK hard sub-tile of the S81 KP4 RS(544,514) decoder cluster ot_s81_kp4_dec
// (frame / code: tools/s81_link/rs544.py; structure and schedule: ot_s81_kp4_dec.sv).  East tile, core side:
//   forward Chien search + Forney (55 lanes, two registered stages; e = Omega(X^-1) X^-30 / Lambda_odd(X^-1)), root
//   count and the uncorrectable decision, correction masks re-cut to PMA words and delayed in u_cmem (32 x 546), the
//   corrected word d_q ^ mask and the lane beats.  From the front tile (west face): d_q (received words) and the
//   key-equation result k_* -- both through the same seam, so every time here is relative to k_v: with T' = the cycle
//   k_v is seen minus 42, chunk c is evaluated at T' + 43 + c and beat k leaves q_d at T' + 58 + k.
// The Forney inverse cell is a kept-hierarchy LUT (ot_s81_kp4_inv): yosys must not fold the E1 register into an
// inferred ROM read port (that moved the 1024-entry decode into the Lambda-evaluation stage: 17 levels, 683 ps).
// Regional synchronous reset, no datapath reset.  MUT 2: Forney value without the division (bench mutant).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dec_b #(parameter integer MUT = 0) (
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
