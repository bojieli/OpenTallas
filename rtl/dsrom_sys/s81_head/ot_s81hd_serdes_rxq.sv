`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// DIE-HEAD-66 2026-11-05: hd_serdes RX timing form RXQ (HEAD only; the shared ot_pdie_serdes / ot_s81_kp4_dec / _dsyn /
// ot_s81_rate_match files are untouched, S81 keeps them).  Depth and distance read on the post-CTS paths of form
// dh64/serdes2, placement RC, pma_rck group:
//   u_rm rp_g2 -> mem 4,095 paths, -333: Gray decode, subtract, compare, push, then the write enable of 4,096 mem bits,
//     13 logic levels + 9 buffers.  Depth.  RXQ: full and fill >= 6 are flops, set from the next write pointer.  The read
//     pointer they use is one wclk edge older, so the writer only sees the FIFO fuller, never emptier: no overflow.
//     No data edge moves while the FIFO stays below the drop level [bench: rxq_bench.sh lockstep, slip benches].
//   u_syn S_q -> u_bm 1,292 paths, -230: one GF multiply + XOR, but one 300-bit S_q reaches 3 RiBM units, median 291 um,
//     7 buffers.  Distance.  RXQ: one S copy per unit, load one edge later.
//   u_syn done -> u_chn macro 320 paths, -605: 3 levels, 10 buffers, 661 um, against a macro clock about 200 ps early.
//     Distance.  RXQ: k_* registered in u_syn before the wire.
//   u_prx -> am_ok 1 path, -652: pop12 mapped to a full-adder chain.  RXQ: same function without adders, no new edge.
// Word path: u_dly DD 55 -> 57, so words and corrections meet as before.  Cost: RX +2 pma_rck edges (p_d -> q_d) + 1 ck edge
// (u_rm read stage: rp -> mem mux -> r_d, 169 endpoints -173, now one-hot copies), TX none; 900 + 320 + 129 flops + flags.  OWNER 10-29 (A): one shared KP4 codeword, no decoder clones,
// is kept: still 1 u_dec with 3 RiBM units.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_kp4_dsyn_q #(parameter integer MUT = 0, parameter integer NBM = 3) (
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
    // RXQ: at most 2 ones in 12 bits without an adder chain: nibble classes 0 / 1 / 2 ones, then the sum table
    function automatic [2:0] nb(input [3:0] x);   // one-hot {two, one, zero}; none set = 3 or 4 ones
        begin
            nb[0] = ~|x;
            nb[1] = (x == 4'b0001) | (x == 4'b0010) | (x == 4'b0100) | (x == 4'b1000);
            nb[2] = (x == 4'b0011) | (x == 4'b0101) | (x == 4'b0110) | (x == 4'b1001) | (x == 4'b1010) | (x == 4'b1100);
        end
    endfunction
    wire [2:0] n0 = nb(amx[3:0]), n1 = nb(amx[7:4]), n2 = nb(amx[11:8]);
    wire [1:0] sum01 = {(n0[1] & n1[1]) | (n0[2] & n1[0]) | (n0[0] & n1[2]), (n0[1] & n1[0]) | (n0[0] & n1[1])};  // [1] two, [0] one
    wire       zero01 = n0[0] & n1[0];
    wire       am_le2 = (zero01 & (n2[0] | n2[1] | n2[2])) | (sum01[0] & (n2[0] | n2[1])) | (sum01[1] & n2[0]);
    reg        am_ok, pv;
    always @(posedge clk) begin am_ok <= p_v && am_le2; pv <= p_v; end
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
    (* keep *) reg [3:0] ldq [0:NBM-1];  // RXQ: load one edge later, with S_b
    (* keep *) reg [299:0] S_b [0:NBM-1];  // RXQ: one S copy per unit, placed with it
    always @(posedge clk)
        if (!rs_n[1]) begin
            g0 <= 0; g9 <= 0; g0s <= 0; bsel <= {{(NBM-1){1'b0}}, 1'b1};
            for (i = 0; i < NBM; i = i + 1) begin ldr[i] <= 4'd0; ldq[i] <= 4'd0; end
        end else begin
            g0 <= {g0[1:0], xs[0][0]};
            g9 <= {g9[1:0], xs[0][9]};
            g0s <= {4{g0[0]}};
            for (i = 0; i < NBM; i = i + 1) begin ldr[i] <= {4{g9[1] && bsel[i]}}; ldq[i] <= ldr[i]; end     // ldr at T + 12 (S final), unit load T + 13
            if (g9[1]) bsel <= {bsel[NBM-2:0], bsel[NBM-1]};
        end
    generate for (gb = 0; gb < 300; gb = gb + 1) begin : g_S
        always @(posedge clk) S_q[gb] <= ((MUT != 3 && g0s[gb / 75]) ? 1'b0 : s_ar[gb]) ^ sp0[gb] ^ sp1[gb];  // MUT 3: no restart
    end endgenerate
    always @(posedge clk) for (i = 0; i < NBM; i = i + 1) S_b[i] <= S_q;
    // ================= key equation: NBM RiBM units
    wire [159:0] u_lam [0:NBM-1];
    wire [149:0] u_om  [0:NBM-1];
    wire [4:0]   u_L   [0:NBM-1];
    wire         u_any [0:NBM-1];
    wire [3:0]   u_dn  [0:NBM-1];
    generate for (gu = 0; gu < NBM; gu = gu + 1) begin : g_bm
        ot_s81_kp4_bm #(.NG(4), .NCD(4)) u_bm (.clk(clk), .rs_n(rs_n[2]), .ld(ldq[gu]), .S(S_b[gu]),
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
    // RXQ: k_* registered here, before the wire to the u_chn macro
    reg [309:0] k_lo_r;
    reg [3:0]   k_v_r;
    reg [4:0]   k_L_c;
    reg         k_any_c;
    always @* begin
        k_L_c = 5'd0; k_any_c = 1'b0;
        for (q = 0; q < NBM; q = q + 1) if (u_dn[q][0]) begin k_L_c = k_L_c | u_L[q]; k_any_c = k_any_c | u_any[q]; end
    end
    always @(posedge clk) begin k_lo_r <= lsel; k_v_r <= cl; k_L <= k_L_c; k_any <= k_any_c; end
    assign k_lo = k_lo_r;
    assign k_v  = k_v_r;
    assign x_q = x1;
endmodule
module ot_s81hd_kp4_dec_q #(parameter integer MUT = 0) (
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
    ot_s81hd_kp4_dsyn_q #(.MUT(MUT)) u_syn (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
    ot_s81_kp4_ddly #(.DD(55 + 2)) u_dly (.clk(clk), .rst_n(rst_n), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dchn #(.MUT(MUT)) u_chn (.clk(clk), .rst_n(rst_n), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
    ot_s81_kp4_dout u_out (.clk(clk), .rst_n(rst_n), .d_q(d_q), .cw(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
endmodule
module ot_s81hd_rate_match_q (
    input  wire          wclk, wrst_n,
    input  wire          w_v,
    input  wire [511:0]  w_d,
    input  wire          rclk, rrst_n,
    output reg  [511:0]  r_d,
    output wire          fault
);
    reg  [511:0] mem [0:7];
    reg  [3:0] wp, rp, wp_g, rp_g;
    reg  [3:0] rp_g1, rp_g2, wp_g1, wp_g2;
    function automatic [3:0] g2b(input [3:0] g); begin g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; end endfunction
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_g; rp_g2 <= rp_g1; end
    always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_g; wp_g2 <= wp_g1; end
    reg  full, ge6;                       // RXQ: flops, one read-pointer edge older than the combinational form
    wire idle = w_d[1] && !w_d[0];
    wire push = w_v && !full && !(idle && ge6);
    wire [3:0] wp_nx = wp + {3'd0, push};
    wire [3:0] fill_nx = wp_nx - g2b(rp_g2);
    reg flt;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; full <= 1'b0; ge6 <= 1'b0; end
        else begin
            full <= fill_nx == 4'd8; ge6 <= fill_nx >= 4'd6;
            if (push) begin mem[wp[2:0]] <= w_d; wp <= wp + 1'b1; wp_g <= (wp + 1'b1) ^ ((wp + 1'b1) >> 1); end
            if (w_v && full && !idle) flt <= 1'b1;
        end
    wire empty = g2b(wp_g2) == rp;
    // RXQ read stage: the pop decision is registered as one-hot select copies (32 data bits per copy), the mem mux and r_d
    // sit behind them: r_d one rclk edge later.  The popped slot stays valid for that edge: the writer sees the move of rp
    // only after rp_g and its 2-flop synchroniser.
    localparam integer NRC = 16;
    (* keep *) reg [7:0] rsel [0:NRC-1];
    (* keep *) reg       ridl;
    integer ci, cb;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin
            rp <= 0; rp_g <= 0; r_d <= 512'd2; ridl <= 1'b1;
            for (ci = 0; ci < NRC; ci = ci + 1) rsel[ci] <= 8'd0;
        end else begin
            if (!empty) begin rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
            ridl <= empty;
            for (ci = 0; ci < NRC; ci = ci + 1) rsel[ci] <= empty ? 8'd0 : (8'd1 << rp[2:0]);
            for (cb = 0; cb < 512; cb = cb + 1)
                r_d[cb] <= ((cb == 1) & ridl) | (|({mem[7][cb], mem[6][cb], mem[5][cb], mem[4][cb], mem[3][cb], mem[2][cb], mem[1][cb], mem[0][cb]} & rsel[cb / 32]));  // IDLE: bit 1 set, no marker, no reverse frame, no slot bits
        end
    reg f1, f2; always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
endmodule
module ot_s81hd_pdie_q #(parameter integer PMA_LAT = 4, parameter integer EMUT = 0, parameter integer DMUT = 0) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    // die pads (behavioural PMA lanes)
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    input  wire [543:0]  pma_rx,
    input  wire          pma_rck
);
    // ---- resets: one synchroniser per clock domain
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge pma_rck or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    // ---- transmit: FEC encoder (ck) -> PMA TX model
    wire e_v; wire [543:0] e_d; wire e_flt;
    ot_s81_kp4_enc #(.MUT(EMUT)) u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt));
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_ptx (.clk(clk), .d_v(e_v), .d(e_d), .q(pma_tx));
    assign pma_tck = clk;
    // ---- receive: PMA RX model (recovered clock) -> FEC decoder -> rate matcher -> ck
    wire [543:0] r_d;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
    ot_s81hd_kp4_dec_q #(.MUT(DMUT)) u_dec (.clk(pma_rck), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .q_v(q_v), .q_d(q_d),
        .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc),
        .n_relock(n_rl));
    reg unc_r; always @(posedge pma_rck or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81hd_rate_match_q u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rx),
        .fault(rm_flt));
    // ---- status (ck)
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt};
    assign st = st_q;
endmodule
