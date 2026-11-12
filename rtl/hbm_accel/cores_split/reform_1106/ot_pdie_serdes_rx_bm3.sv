`timescale 1ns/1ps
// SOURCE-ONLY optional RX three-BM native cut. CUT_BM defaults 0; no canonical activation.
// Exact BMTHC1 frozen RX basis. Native S/ld and BM results retain existing registered cohorts.
// No internal face registers, clock/reset stages, arithmetic or cycles are added.
// Individual native/R2 helper views and parent geometry require separate adoption before GEN/P&R.
module ot_pdie_serdes_rx_bm_native #(parameter integer BMTHC=1) (
    input wire clk, rs_n, input wire [3:0] ld, input wire [299:0] S,
    output wire [159:0] lam, output wire [149:0] om,
    output wire [4:0] L, output wire any, output wire [3:0] done
);
    ot_s81_kp4_bm #(.NG(4), .NCD(4), .THC(BMTHC)) u_native (
        .clk(clk), .rs_n(rs_n), .ld(ld), .S(S), .lam(lam), .om(om), .L(L), .any(any), .done(done));
endmodule

module ot_s81_kp4_dsyn_bm3_rest #(parameter integer MUT = 0, parameter integer NBM = 3, parameter integer BMTHC = 0) (
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
    output reg  [31:0]   n_relock,
    output wire [299:0] bm_S, output wire [11:0] bm_ld, output wire bm_rs_n,
    input wire [479:0] bm_lam, input wire [449:0] bm_om, input wire [14:0] bm_L,
    input wire [2:0] bm_any, input wire [11:0] bm_done
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
`ifdef OT_RXBM3_SPCYC
    // CORES-HBM-1 rxbm3 11-12 (opt-in, default off): port of S81 dsyn SPCYC (S81-TYPES-9-RCK 11-08) to the HBM bm3_rest
    // syndrome tile.  M7T sign-off class: sc_q -> sp0/sp1 one-cycle dense GF(2) window matrix (296 of 389 TT setup
    // endpoints, WNS -171.7).  Four registered partial products (one per 138-bit sc_q select copy), pair XOR into sp0/sp1
    // one cycle later.  PIN CYCLE +1 rck on bm_ld (S final T + 13) and so on k_*; ddly DD +1 keeps words aligned at dout.
    wire [299:0] s_q0, s_q1, s_q2, s_q3;
`include "ot_s81_kp4_syn_mat_q4.svh"
    reg  [299:0] sq0, sq1, sq2, sq3;
    always @(posedge clk) begin
        sq0 <= s_q0; sq1 <= s_q1; sq2 <= s_q2; sq3 <= s_q3;
`ifdef RXBM3_MUT_SPCYC
        sp0 <= sq0 ^ sq1; sp1 <= sq2;        // bench mutant: partial 3 dropped
`else
        sp0 <= sq0 ^ sq1; sp1 <= sq2 ^ sq3;
`endif
    end
    reg  [3:0] g0, g9;                   // chunk-0 / chunk-9 flags: [0] sc stage (T + c + 1), [2] sp stage, [3] S final
`else
    always @(posedge clk) begin sp0 <= s_p0; sp1 <= s_p1; end
    reg  [2:0] g0, g9;                   // chunk-0 / chunk-9 flags: [0] sc stage (T + c + 1), [1] sp stage, [2] S final
`endif
    (* keep *) reg [3:0] g0s;            // chunk-0 flag at the sp stage, 4 copies (75 S bits each)
    reg  [NBM-1:0] bsel;                 // round robin: the unit that takes the next frame
    (* keep *) reg [3:0] ldr [0:NBM-1];  // unit load, one copy per PE group
    always @(posedge clk)
        if (!rs_n[1]) begin
            g0 <= 0; g9 <= 0; g0s <= 0; bsel <= {{(NBM-1){1'b0}}, 1'b1};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= 4'd0;
        end else begin
`ifdef OT_RXBM3_SPCYC
            g0 <= {g0[2:0], xs[0][0]};
            g9 <= {g9[2:0], xs[0][9]};
            g0s <= {4{g0[1]}};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= {4{g9[2] && bsel[i]}};     // ld at T + 13 (S final, +1 SPCYC)
            if (g9[2]) bsel <= {bsel[NBM-2:0], bsel[NBM-1]};
`else
            g0 <= {g0[1:0], xs[0][0]};
            g9 <= {g9[1:0], xs[0][9]};
            g0s <= {4{g0[0]}};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= {4{g9[1] && bsel[i]}};     // ld at T + 12 (S final)
            if (g9[1]) bsel <= {bsel[NBM-2:0], bsel[NBM-1]};
`endif
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
    assign bm_S = S_q;
    assign bm_rs_n = rs_n[2];
    generate for (gu = 0; gu < NBM; gu = gu + 1) begin : g_bm_return
        assign bm_ld[4*gu+:4] = ldr[gu];
        assign u_lam[gu] = bm_lam[160*gu+:160];
        assign u_om[gu] = bm_om[150*gu+:150];
        assign u_L[gu] = bm_L[5*gu+:5];
        assign u_any[gu] = bm_any[gu];
        assign u_dn[gu] = bm_done[4*gu+:4];
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

module ot_pdie_serdes_rx_bm3_legacy #(parameter integer PMA_LAT = 4, parameter integer DMUT = 0, parameter integer SEAM = 2,
    parameter integer BMTHC = 0) (
    input  wire          clk,
    input  wire          rck_clk,
    input  wire          rst,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    input  wire [543:0]  pma_rx,
    input  wire          e_flt_i,
    output wire [3:0]    k_v,
    output wire [309:0]  k_lo,
    output wire [4:0]    k_L,
    output wire          k_any,
    input  wire [543:0]  cw_q,
    input  wire [7:0]    apply,
    input  wire          o_unc,
    input  wire [4:0]    o_ne,
    input  wire          fs
);
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge rck_clk or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    wire [543:0] r_d, x_q, d_q;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx (.clk(rck_clk), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_rl;
    ot_s81_kp4_dsyn #(.MUT(DMUT), .BMTHC(BMTHC)) u_syn (.clk(rck_clk), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_rl));
    ot_s81_kp4_ddly #(.DD(55 + SEAM)) u_dly (.clk(rck_clk), .rst_n(rn_r), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dout u_out (.clk(rck_clk), .rst_n(rn_r), .d_q(d_q), .cw(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
    reg unc_r; always @(posedge rck_clk or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(rck_clk), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rx),
        .fault(rm_flt));
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt_i};
    assign st = st_q;
endmodule
module ot_pdie_serdes_rx_bm3_rest #(parameter integer PMA_LAT = 4, parameter integer DMUT = 0, parameter integer SEAM = 2,
    parameter integer BMTHC = 0) (
    input  wire          clk,
    input  wire          rck_clk,
    input  wire          rst,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    input  wire [543:0]  pma_rx,
    input  wire          e_flt_i,
    output wire [3:0]    k_v,
    output wire [309:0]  k_lo,
    output wire [4:0]    k_L,
    output wire          k_any,
    input  wire [543:0]  cw_q,
    input  wire [7:0]    apply,
    input  wire          o_unc,
    input  wire [4:0]    o_ne,
    input  wire          fs,
    output wire [299:0] bm_S, output wire [11:0] bm_ld, output wire bm_rs_n,
    input wire [479:0] bm_lam, input wire [449:0] bm_om, input wire [14:0] bm_L,
    input wire [2:0] bm_any, input wire [11:0] bm_done
);
`ifdef OT_RXBM3_SPCYC
    localparam integer RXB_SPCYC = 1;    // words wait one more rck (k_* +1 under OT_RXBM3_SPCYC)
`else
    localparam integer RXB_SPCYC = 0;
`endif
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge rck_clk or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    wire [543:0] r_d, x_q, d_q;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx (.clk(rck_clk), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_rl;
    ot_s81_kp4_dsyn_bm3_rest #(.MUT(DMUT), .BMTHC(BMTHC)) u_syn (.clk(rck_clk), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_rl), .bm_S(bm_S), .bm_ld(bm_ld), .bm_rs_n(bm_rs_n), .bm_lam(bm_lam), .bm_om(bm_om), .bm_L(bm_L), .bm_any(bm_any), .bm_done(bm_done));
`ifdef OT_RXBM3_SRAM_SPLIT
    ot_s81_kp4_ddly_sp #(.DD(55 + SEAM + RXB_SPCYC)) u_dly (.clk(rck_clk), .rst_n(rn_r), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dout_sp u_out (.clk(rck_clk), .rst_n(rn_r), .d_q(d_q), .cw(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
`else
    ot_s81_kp4_ddly #(.DD(55 + SEAM + RXB_SPCYC)) u_dly (.clk(rck_clk), .rst_n(rn_r), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dout u_out (.clk(rck_clk), .rst_n(rn_r), .d_q(d_q), .cw(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
`endif
    reg unc_r; always @(posedge rck_clk or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(rck_clk), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rx),
        .fault(rm_flt));
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt_i};
    assign st = st_q;
endmodule
// GENERATED by face_shell.py (HBM-FACE): face-register shell of ot_pdie_serdes_rx__fcore.  Every signal pin bit has its own
// flop at the face (+1 cycle in, +1 cycle out); clock / reset pins pass through; dropped unread input bits are
// driven 0 at the core port (never read by the core: yosys analysis, bench-verified).  Do not edit.
`default_nettype none
module ot_pdie_serdes_rx_bm3_legacy_family (
    input wire clk,
    input wire rck_clk,
    input wire rst,
    output wire [511:0] rx,
    output wire [1:0] st,
    input wire [543:0] pma_rx,
    input wire e_flt_i,
    output wire [3:0] k_v,
    output wire [309:0] k_lo,
    output wire [4:0] k_L,
    output wire k_any,
    input wire [543:0] cw_q,
    input wire [7:0] apply,
    input wire o_unc,
    input wire fs
);
    wire [511:0] rx__fc;
    (* keep *) ot_hbm_face_reg #(.W(512)) u_bout_rx (.clk(clk), .d(rx__fc), .q(rx));
    wire [1:0] st__fc;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bout_st (.clk(clk), .d(st__fc), .q(st));
    wire [543:0] pma_rx__fq;
    (* keep *) ot_hbm_face_reg #(.W(544)) u_bin_pma_rx (.clk(clk), .d(pma_rx), .q(pma_rx__fq));
    wire [0:0] e_flt_i__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_e_flt_i (.clk(clk), .d(e_flt_i), .q(e_flt_i__fq));
    wire [3:0] k_v__fc;
    (* keep *) ot_hbm_face_reg #(.W(4)) u_bout_k_v (.clk(clk), .d(k_v__fc), .q(k_v));
    wire [309:0] k_lo__fc;
    (* keep *) ot_hbm_face_reg #(.W(310)) u_bout_k_lo (.clk(clk), .d(k_lo__fc), .q(k_lo));
    wire [4:0] k_L__fc;
    (* keep *) ot_hbm_face_reg #(.W(5)) u_bout_k_L (.clk(clk), .d(k_L__fc), .q(k_L));
    wire [0:0] k_any__fc;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bout_k_any (.clk(clk), .d(k_any__fc), .q(k_any));
    wire [543:0] cw_q__fq;
    (* keep *) ot_hbm_face_reg #(.W(544)) u_bin_cw_q (.clk(clk), .d(cw_q), .q(cw_q__fq));
    wire [7:0] apply__fq;
    (* keep *) ot_hbm_face_reg #(.W(8)) u_bin_apply (.clk(clk), .d(apply), .q(apply__fq));
    wire [0:0] o_unc__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_o_unc (.clk(clk), .d(o_unc), .q(o_unc__fq));
    wire [0:0] fs__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_fs (.clk(clk), .d(fs), .q(fs__fq));
    ot_pdie_serdes_rx_bm3_legacy #(.BMTHC(1)) u_fcore (
        .clk(clk),
        .rck_clk(rck_clk),
        .rst(rst),
        .rx(rx__fc),
        .st(st__fc),
        .pma_rx(pma_rx__fq),
        .e_flt_i(e_flt_i__fq),
        .k_v(k_v__fc),
        .k_lo(k_lo__fc),
        .k_L(k_L__fc),
        .k_any(k_any__fc),
        .cw_q(cw_q__fq),
        .apply(apply__fq),
        .o_unc(o_unc__fq),
        .o_ne(5'd0),
        .fs(fs__fq)
    );
endmodule
`default_nettype wire

// GENERATED by face_shell.py (HBM-FACE): face-register shell of ot_pdie_serdes_rx__fcore.  Every signal pin bit has its own
// flop at the face (+1 cycle in, +1 cycle out); clock / reset pins pass through; dropped unread input bits are
// driven 0 at the core port (never read by the core: yosys analysis, bench-verified).  Do not edit.
`default_nettype none
module ot_pdie_serdes_rx_bm3_residual (
    input wire clk,
    input wire rck_clk,
    input wire rst,
    output wire [511:0] rx,
    output wire [1:0] st,
    input wire [543:0] pma_rx,
    input wire e_flt_i,
    output wire [3:0] k_v,
    output wire [309:0] k_lo,
    output wire [4:0] k_L,
    output wire k_any,
    input wire [543:0] cw_q,
    input wire [7:0] apply,
    input wire o_unc,
    input wire fs,
    output wire [299:0] bm_S, output wire [11:0] bm_ld, output wire bm_rs_n,
    input wire [479:0] bm_lam, input wire [449:0] bm_om, input wire [14:0] bm_L,
    input wire [2:0] bm_any, input wire [11:0] bm_done
);
    wire [511:0] rx__fc;
    (* keep *) ot_hbm_face_reg #(.W(512)) u_bout_rx (.clk(clk), .d(rx__fc), .q(rx));
    wire [1:0] st__fc;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bout_st (.clk(clk), .d(st__fc), .q(st));
    wire [543:0] pma_rx__fq;
    (* keep *) ot_hbm_face_reg #(.W(544)) u_bin_pma_rx (.clk(clk), .d(pma_rx), .q(pma_rx__fq));
    wire [0:0] e_flt_i__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_e_flt_i (.clk(clk), .d(e_flt_i), .q(e_flt_i__fq));
    wire [3:0] k_v__fc;
    (* keep *) ot_hbm_face_reg #(.W(4)) u_bout_k_v (.clk(clk), .d(k_v__fc), .q(k_v));
    wire [309:0] k_lo__fc;
    (* keep *) ot_hbm_face_reg #(.W(310)) u_bout_k_lo (.clk(clk), .d(k_lo__fc), .q(k_lo));
    wire [4:0] k_L__fc;
    (* keep *) ot_hbm_face_reg #(.W(5)) u_bout_k_L (.clk(clk), .d(k_L__fc), .q(k_L));
    wire [0:0] k_any__fc;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bout_k_any (.clk(clk), .d(k_any__fc), .q(k_any));
    wire [543:0] cw_q__fq;
    (* keep *) ot_hbm_face_reg #(.W(544)) u_bin_cw_q (.clk(clk), .d(cw_q), .q(cw_q__fq));
    wire [7:0] apply__fq;
    (* keep *) ot_hbm_face_reg #(.W(8)) u_bin_apply (.clk(clk), .d(apply), .q(apply__fq));
    wire [0:0] o_unc__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_o_unc (.clk(clk), .d(o_unc), .q(o_unc__fq));
    wire [0:0] fs__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_fs (.clk(clk), .d(fs), .q(fs__fq));
    ot_pdie_serdes_rx_bm3_rest #(.BMTHC(1)) u_fcore (
        .clk(clk),
        .rck_clk(rck_clk),
        .rst(rst),
        .rx(rx__fc),
        .st(st__fc),
        .pma_rx(pma_rx__fq),
        .e_flt_i(e_flt_i__fq),
        .k_v(k_v__fc),
        .k_lo(k_lo__fc),
        .k_L(k_L__fc),
        .k_any(k_any__fc),
        .cw_q(cw_q__fq),
        .apply(apply__fq),
        .o_unc(o_unc__fq),
        .o_ne(5'd0),
        .fs(fs__fq), .bm_S(bm_S), .bm_ld(bm_ld), .bm_rs_n(bm_rs_n), .bm_lam(bm_lam), .bm_om(bm_om), .bm_L(bm_L), .bm_any(bm_any), .bm_done(bm_done)
    );
endmodule
`default_nettype wire

module ot_pdie_serdes_rx_bm3_family #(parameter integer CUT_BM=0) (
    input wire clk,
    input wire rck_clk,
    input wire rst,
    output wire [511:0] rx,
    output wire [1:0] st,
    input wire [543:0] pma_rx,
    input wire e_flt_i,
    output wire [3:0] k_v,
    output wire [309:0] k_lo,
    output wire [4:0] k_L,
    output wire k_any,
    input wire [543:0] cw_q,
    input wire [7:0] apply,
    input wire o_unc,
    input wire fs
);
    generate if (CUT_BM == 0) begin : g_default
        ot_pdie_serdes_rx_bm3_legacy_family u_legacy (.clk(clk), .rck_clk(rck_clk), .rst(rst), .rx(rx), .st(st), .pma_rx(pma_rx), .e_flt_i(e_flt_i), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any), .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .fs(fs));
    end else begin : g_native
        wire [299:0] bm_S;
        wire [11:0] bm_ld, bm_done;
        wire bm_rs_n;
        wire [479:0] bm_lam;
        wire [449:0] bm_om;
        wire [14:0] bm_L;
        wire [2:0] bm_any;
        ot_pdie_serdes_rx_bm3_residual u_rest (.clk(clk), .rck_clk(rck_clk), .rst(rst), .rx(rx), .st(st), .pma_rx(pma_rx), .e_flt_i(e_flt_i), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any), .cw_q(cw_q), .apply(apply), .o_unc(o_unc), .fs(fs), .bm_S(bm_S), .bm_ld(bm_ld), .bm_rs_n(bm_rs_n), .bm_lam(bm_lam), .bm_om(bm_om), .bm_L(bm_L), .bm_any(bm_any), .bm_done(bm_done));
        for (genvar engine=0; engine<3; engine=engine+1) begin : g_bm
            ot_pdie_serdes_rx_bm_native #(.BMTHC(1)) u_bm (
                .clk(rck_clk), .rs_n(bm_rs_n), .ld(bm_ld[4*engine+:4]), .S(bm_S),
                .lam(bm_lam[160*engine+:160]), .om(bm_om[150*engine+:150]),
                .L(bm_L[5*engine+:5]), .any(bm_any[engine]), .done(bm_done[4*engine+:4]));
        end
    end endgenerate
endmodule
`default_nettype wire
