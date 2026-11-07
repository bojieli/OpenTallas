`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// DIE-HEAD-76-SERDESRF 2026-11-06: hd_serdes SC form = RE-FORM after two strikes (vA TT -239.69, vB TT -211.35: enc
// ch_q -> pp1 and BM S_b -> dz, 400-450 ps of wire buffers each, 233.8k cells spread over the 150-um PHY shore strip).
// The partition keeps ONE KP4 link (OWNER 10-29 (A): one shared codeword, no decoder clones) and hardens two natural
// blocks as compact sub-cores inside the hd_serdes slot, like the signed u_chn (ot_s81_kp4_dchn) already is:
//   u_phy.u_link.u_tx              ot_s81hd_sc_tx  (1 instance): ck reset sync + KP4 encoder + PMA TX model.  Encoder =
//                                  ot_s81_kp4_enc_la LA = 2, FF = 1, the HBM serdes_tx form signed on HBM
//                                  (ot_pdie_serdes_tx ELA 2 / EFF 1, TT +168): pma_tx = the ot_s81_kp4_enc stream
//                                  delayed by exactly 2 ck edges (tb_kp4_enc_la / tb_kp4_enc_ff); e_flt unchanged.
//   u_phy.u_link.u_dec.u_syn.u_bm0..2  ot_s81hd_sc_bmq (3 instances, one type): the RXQ load / S copy registers (ldq,
//                                  S_b) + one RiBM unit (ot_s81_kp4_bm, THC 1).  0 added cycles: ldq / S_b are the RXQ
//                                  registers moved across the hierarchy, outputs leave the unit's own registers.
//   u_phy.u_link.u_dec.u_chn       ot_s81_kp4_dchn (unchanged signed child, default MUT 0).
// Everything else is ot_s81hd_serdes_rxq.sv (RXQ: RX +2 pma_rck edges, rate-match read +1 ck edge) byte for byte, plus
// a registered ck reset tree for the u_rm read side (every leaf == rs_t[1] on every edge).  Every child face is a
// register: tx -> d0, pma_tx <- u_ptx stage, e_flt <- flt; S_i -> S_b, ld_i -> ldq, lam/om/L/any/done <- RiBM registers.
// Children are in ot_s81hd_serdes_sc_cores.sv.  Cycle contract vs ot_s81hd_pdie_q (RXQ): pma_tx +2 ck edges, nothing else moves (tb_s81hd_serdes_sc_lockstep.sv).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_kp4_dsyn_sc #(parameter integer MUT = 0) (
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
    localparam integer NBM = 3;          // SC: three hard key-equation children u_bm0..2 (one type ot_s81hd_sc_bmq)
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
    // SC: the RXQ load / S copies (ldq, S_b) are the registered input face of each ot_s81hd_sc_bmq child
    always @(posedge clk)
        if (!rs_n[1]) begin
            g0 <= 0; g9 <= 0; g0s <= 0; bsel <= {{(NBM-1){1'b0}}, 1'b1};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= 4'd0;
        end else begin
            g0 <= {g0[1:0], xs[0][0]};
            g9 <= {g9[1:0], xs[0][9]};
            g0s <= {4{g0[0]}};
            for (i = 0; i < NBM; i = i + 1) ldr[i] <= {4{g9[1] && bsel[i]}};     // ldr at T + 12 (S final), unit load T + 13 (child face)
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
    // SC: explicit instance names (hard-core plan sites), rs_n[2] = the unit reset leaf (ldq used the equal leaf rs_n[1])
    ot_s81hd_sc_bmq u_bm0 (.clk(clk), .rs_n(rs_n[2]), .ld_i(ldr[0]), .S_i(S_q), .lam(u_lam[0]), .om(u_om[0]), .L(u_L[0]),
        .any(u_any[0]), .done(u_dn[0]));
    ot_s81hd_sc_bmq u_bm1 (.clk(clk), .rs_n(rs_n[2]), .ld_i(ldr[1]), .S_i(S_q), .lam(u_lam[1]), .om(u_om[1]), .L(u_L[1]),
        .any(u_any[1]), .done(u_dn[1]));
    ot_s81hd_sc_bmq u_bm2 (.clk(clk), .rs_n(rs_n[2]), .ld_i(ldr[2]), .S_i(S_q), .lam(u_lam[2]), .om(u_om[2]), .L(u_L[2]),
        .any(u_any[2]), .done(u_dn[2]));
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
module ot_s81hd_kp4_dec_sc #(parameter integer MUT = 0) (
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
    ot_s81hd_kp4_dsyn_sc #(.MUT(MUT)) u_syn (.clk(clk), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
    ot_s81_kp4_ddly #(.DD(55 + 2)) u_dly (.clk(clk), .rst_n(rst_n), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dchn u_chn (.clk(clk), .rst_n(rst_n), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
    ot_s81_kp4_dout u_out (.clk(clk), .rst_n(rst_n), .d_q(d_q), .cw(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
endmodule
// DIE-HEAD-77-SERDES conservative reset form: ot_s81hd_rate_match_q with a local read-side reset tree.  rrst_l[g] resets
// slice g (rsel copy g + r_d[32g+31:32g]); rrst_l[NRC] resets the read-side control.  Same behaviour when every leaf is equal.
module ot_s81hd_rate_match_sc (
    input  wire          wclk, wrst_n,
    input  wire          w_v,
    input  wire [511:0]  w_d,
    input  wire          rclk,
    input  wire [16:0]   rrst_l,
    output reg  [511:0]  r_d,
    output wire          fault
);
    reg  [511:0] mem [0:7];
    reg  [3:0] wp, rp, wp_g, rp_g;
    reg  [3:0] rp_g1, rp_g2, wp_g1, wp_g2;
    function automatic [3:0] g2b(input [3:0] g); begin g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; end endfunction
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_g; rp_g2 <= rp_g1; end
    always @(posedge rclk or negedge rrst_l[16]) if (!rrst_l[16]) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_g; wp_g2 <= wp_g1; end
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
    always @(posedge rclk or negedge rrst_l[16])
        if (!rrst_l[16]) begin rp <= 0; rp_g <= 0; ridl <= 1'b1; end
        else begin
            if (!empty) begin rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
            ridl <= empty;
        end
    genvar gs, gb;
    generate for (gs = 0; gs < NRC; gs = gs + 1) begin : g_sl
        always @(posedge rclk or negedge rrst_l[gs])
            if (!rrst_l[gs]) rsel[gs] <= 8'd0;
            else rsel[gs] <= empty ? 8'd0 : (8'd1 << rp[2:0]);
        for (gb = 0; gb < 32; gb = gb + 1) begin : g_b
            localparam integer cb = gs * 32 + gb;
            always @(posedge rclk or negedge rrst_l[gs])
                if (!rrst_l[gs]) r_d[cb] <= (cb == 1);   // reset value 512'd2
                else r_d[cb] <= ((cb == 1) & ridl) | (|({mem[7][cb], mem[6][cb], mem[5][cb], mem[4][cb], mem[3][cb], mem[2][cb], mem[1][cb], mem[0][cb]} & rsel[gs]));
        end
    end endgenerate
    reg f1, f2; always @(posedge rclk or negedge rrst_l[16]) if (!rrst_l[16]) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
endmodule
module ot_s81hd_pdie_sc #(parameter integer PMA_LAT = 4, parameter integer DMUT = 0) (
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
    // SC reset tree: the u_tx child has its own copy inside (ot_s81hd_sc_tx).  DIE-HEAD-77-SERDES conservative form: the
    // u_rm read side has a two-level registered tree with the same 2-edge release as rs_t (rst is synchronous to ck, so
    // every leaf == rs_t[1] on every edge, 0 added cycles): 3 root flops, fanout <= 6 each, 17 leaf flops, one per 32-bit
    // r_d slice (40 flops) plus one for the read-side control.
    (* keep *) reg [2:0]  rm_r;
    (* keep *) reg [16:0] rm_l;
    always @(posedge clk or negedge rst) if (!rst) rm_r <= 3'b000; else rm_r <= 3'b111;
    genvar gl;
    generate for (gl = 0; gl < 17; gl = gl + 1) begin : g_rml
        always @(posedge clk or negedge rst) if (!rst) rm_l[gl] <= 1'b0; else rm_l[gl] <= rm_r[gl / 6];
    end endgenerate
    always @(posedge pma_rck or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    // ---- transmit: FEC encoder (ck) -> PMA TX model
    wire e_flt;
    ot_s81hd_sc_tx u_tx (.clk(clk), .rst(rst), .tx(tx), .pma_tx(pma_tx), .e_flt(e_flt));   // hard child, pma_tx +2 edges
    assign pma_tck = clk;
    // ---- receive: PMA RX model (recovered clock) -> FEC decoder -> rate matcher -> ck
    wire [543:0] r_d;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx (.clk(pma_rck), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_corr, n_unc, n_rl;
    ot_s81hd_kp4_dec_sc #(.MUT(DMUT)) u_dec (.clk(pma_rck), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .q_v(q_v), .q_d(q_d),
        .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc),
        .n_relock(n_rl));
    reg unc_r; always @(posedge pma_rck or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81hd_rate_match_sc u_rm (.wclk(pma_rck), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_l(rm_l), .r_d(rx),
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
