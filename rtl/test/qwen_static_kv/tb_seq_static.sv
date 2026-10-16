`timescale 1ns/1ps
// Q-KVSYS PVJOIN 2026-10-16: qkd_seq_static (static formatter) against the legacy credit/event sequencer qkd_seq
// (HEADS 1, Q FP32: the die's profile), both on the same layer traffic placed at the link compiler's slots
// (tools/qwen_split/d2d_link_calendar.py --profile program: CMD rx_out 616, Q 617..648, KVN 650..653 in each layer run;
// SEQ_GOLD include from tools/qwen_static_kv/seq_static_golden.py).  The static DUT sees the static D2D end's pins
// (att_rx_*, kvn_word_* with the payload one edge after its event, the end's PR stage included) and the layer programme's
// attention_run / layer / ctx_t; the legacy DUT sees the same words as x3 / kvd with prompt RES and row credits.
// Checks: per quadrant the sequence of aq words (start + 32 Q beats), kvn rows and kc descriptors is IDENTICAL between
// the two (bit-exact), counts = NL layers, static fault 0, and the static edges sit at ONE offset from the CMD slot in
// every layer.  Prints SEQ_STATIC ... with the per-face latency delta static - legacy (edges) for the cost ledger.
module tb_seq_static #(parameter integer MUT = 0, parameter integer NL = 36, parameter integer P = 6836) ();
`include "seq_gold.svh"
    reg ck = 0;
    always #0.5 ck = ~ck;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    // ---------------- stimulus (driven on negedge from cycle-indexed schedules) ----------------
    reg         s_av = 0; reg [3:0] s_ak = 0; reg [4:0] s_ab = 0;
    reg         s_kv = 0; reg [10:0] s_kt = 0; reg [511:0] s_kd = 0;
    reg         s_lr = 0; reg [5:0] s_ll = 0; reg [13:0] s_lt = 0;
    reg [523:0] l_x3 = 0; reg [43:0] l_kvd = 0;
    integer B0 = 2000;
    function automatic [511:0] qword(input integer l, input integer b);
        qword = {16{8'(l), 8'(b), 16'h5a00 | 16'(l * 37 + b)}};
    endfunction
    function automatic [511:0] kword(input integer l, input integer k);
        kword = {16{8'(l), 8'(k), 16'hc300 | 16'(l * 11 + k)}};
    endfunction
    function automatic [2:0] ktag(input integer k);
        ktag = (k < 2) ? 3'(k) : 3'(k + 2);       // 0, 1, 4, 5
    endfunction
    integer L, rel, T;
    always @(negedge ck) begin
        s_av = 0; s_ak = 0; s_ab = 0; s_kv = 0; s_kt = 0; s_lr = 0; l_x3 = 0; l_kvd = 0;
        if (cyc >= B0) begin
            L = (cyc - B0) / P; rel = (cyc - B0) % P; T = 100 + L / 36;
            if (L < NL) begin
                s_ll = 6'(L); s_lt = 14'(T);
                if (rel == G_CMD - G_LPRUN) s_lr = 1;
                if (rel == G_CMD) begin s_av = 1; s_ak = 1; end
                if (rel == G_CMD + 1) s_kd = {493'd0, 18'(T - 1), 1'b1};
                if (rel >= G_Q0 && rel < G_Q0 + 32) begin s_av = 1; s_ak = 2; s_ab = 5'(rel - G_Q0); end
                if (rel >= G_Q0 + 1 && rel < G_Q0 + 33) begin
                    s_kd = qword(L, rel - G_Q0 - 1);
                    l_x3 = {1'b1, 3'b001, 2'b00, 6'(rel - G_Q0 - 1), qword(L, rel - G_Q0 - 1)};
                end
                if (rel >= G_KV0 && rel < G_KV0 + 4) begin
                    s_kv = 1; s_kt = {3'b010, 5'd0, ktag(rel - G_KV0)}; s_kd = kword(L, rel - G_KV0);
                    l_x3 = {1'b1, 3'b010, 5'd0, ktag(rel - G_KV0), kword(L, rel - G_KV0)};
                end
                if (rel == G_CMD + 1) l_kvd = {1'b1, 1'b1, 18'(T - 1), 12'd0, 6'(L), 6'd0};
            end
        end
    end
    // ---------------- DUTs ----------------
    wire [539:0] sa [0:3]; wire [1046:0] sk [0:3]; wire [32:0] sc [0:3]; wire shs; wire [92:0] stk; wire [9:0] skst;
    wire [539:0] la [0:3]; wire [1046:0] lk [0:3]; wire [32:0] lc [0:3]; wire lhs; wire [92:0] ltk; wire [9:0] lkst;
    reg [519:0] s_ar = 0, l_ar = 0;
    reg [3:0] s_cr = 0, l_cr = 0, l_rescr = 0;
    wire [519:0] l_tar; wire l_x3cr; wire [186:0] l_ds; wire [74:0] l_pw;
    qkd_seq_static #(.MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .att_rx_v(s_av), .att_rx_kind(s_ak), .att_rx_beat(s_ab),
        .kvn_word_valid(s_kv), .kvn_word_tag(s_kt), .kvn_word_data(s_kd), .lp_run(s_lr), .lp_layer(s_ll), .lp_ctx_t(s_lt),
        .svc(174'd0), .aq_WS(sa[0]), .aq_WN(sa[1]), .aq_ES(sa[2]), .aq_EN(sa[3]),
        .kvn_WS_d(sk[0]), .kvn_WN_d(sk[1]), .kvn_ES_d(sk[2]), .kvn_EN_d(sk[3]),
        .kvn_WS_cr(s_cr[0]), .kvn_WN_cr(s_cr[1]), .kvn_ES_cr(s_cr[2]), .kvn_EN_cr(s_cr[3]),
        .kc_WS(sc[0]), .kc_WN(sc[1]), .kc_ES(sc[2]), .kc_EN(sc[3]), .af_WS(1'b0), .af_WN(1'b0), .af_ES(1'b0), .af_EN(1'b0),
        .mf_WS(1'b0), .mf_WN(1'b0), .mf_ES(1'b0), .mf_EN(1'b0), .ar(s_ar), .hf(1'b0), .hs(shs), .tk(stk), .kst(skst));
    qkd_seq #(.HEADS(1), .Q_FP32(1)) ref_ (.ck(ck), .rst_n(rst_n), .r_x3_d(l_x3), .r_x3_cr(l_x3cr), .r_sd(56'd0), .r_kvd(l_kvd),
        .t_ar_d(l_tar), .t_ar_cr(l_rescr[0]), .t_ds(l_ds), .t_pw(l_pw), .aq_WS(la[0]), .aq_WN(la[1]), .aq_ES(la[2]), .aq_EN(la[3]),
        .kvn_WS_d(lk[0]), .kvn_WN_d(lk[1]), .kvn_ES_d(lk[2]), .kvn_EN_d(lk[3]),
        .kvn_WS_cr(l_cr[0]), .kvn_WN_cr(l_cr[1]), .kvn_ES_cr(l_cr[2]), .kvn_EN_cr(l_cr[3]),
        .kc_WS(lc[0]), .kc_WN(lc[1]), .kc_ES(lc[2]), .kc_EN(lc[3]), .af_WS(1'b0), .af_WN(1'b0), .af_ES(1'b0), .af_EN(1'b0),
        .mf_WS(1'b0), .mf_WN(1'b0), .mf_ES(1'b0), .mf_EN(1'b0), .ar(l_ar), .hf(1'b0), .hs(lhs), .hc(182'd0), .tk(ltk), .kst(lkst));
    // hub model (each DUT its own): 32 RES words beats 0..31 from 60 edges after its hs (after the 32 Q beats); landing row credit 6 edges after
    // each row leaves a fan; legacy RES credit 3 edges after each t_ar_d word
    integer s_hs = -1, l_hs = -1;
    reg [3:0] s_crq [0:7]; reg [3:0] l_crq [0:7]; reg [7:0] l_rq;
    integer k_;
    always @(posedge ck) begin
        if (shs) s_hs <= cyc; if (lhs) l_hs <= cyc;
        s_ar <= 0; l_ar <= 0;
        if (s_hs >= 0 && cyc - s_hs >= 60 && cyc - s_hs < 92) s_ar <= {1'b1, 1'b0, 6'(cyc - s_hs - 60), 512'(cyc)};
        if (l_hs >= 0 && cyc - l_hs >= 60 && cyc - l_hs < 92) l_ar <= {1'b1, 1'b0, 6'(cyc - l_hs - 60), 512'(cyc)};
        for (k_ = 7; k_ > 0; k_ = k_ - 1) begin s_crq[k_] <= s_crq[k_ - 1]; l_crq[k_] <= l_crq[k_ - 1]; end
        s_crq[0] <= {sk[3][1046], sk[2][1046], sk[1][1046], sk[0][1046]};
        l_crq[0] <= {lk[3][1046], lk[2][1046], lk[1][1046], lk[0][1046]};
        s_cr <= s_crq[5]; l_cr <= l_crq[5];
        l_rq <= {l_rq[6:0], l_tar[519]}; l_rescr <= {3'd0, l_rq[2]};
    end
    // ---------------- capture and compare ----------------
    reg [539:0]  sa_q [0:3][$]; reg [539:0] la_q [0:3][$];
    reg [1046:0] sk_q [0:3][$]; reg [1046:0] lk_q [0:3][$];
    reg [32:0]   sc_q [0:3][$]; reg [32:0]   lc_q [0:3][$];
    integer s_ast [$], l_ast [$], s_krow [$], l_krow [$], cmd_t [$];
    integer q, errs = 0;
    always @(posedge ck) if (rst_n) begin
        if (s_av && s_ak == 1) cmd_t.push_back(cyc);
        for (q = 0; q < 4; q = q + 1) begin
            if (sa[q][539] || sa[q][518]) sa_q[q].push_back(sa[q]);
            if (la[q][539] || la[q][518]) la_q[q].push_back(la[q]);
            if (sk[q][1046]) sk_q[q].push_back(sk[q]);
            if (lk[q][1046]) lk_q[q].push_back(lk[q]);
            if (sc[q][32]) sc_q[q].push_back(sc[q]);
            if (lc[q][32]) lc_q[q].push_back(lc[q]);
        end
        if (sa[0][539]) s_ast.push_back(cyc); if (la[0][539]) l_ast.push_back(cyc);
        if (sk[0][1046] && sk[0][1045:1044] == 2'b00) s_krow.push_back(cyc);
        if (lk[0][1046] && lk[0][1045:1044] == 2'b00) l_krow.push_back(cyc);
        if (lkst[9] && errs < 1000) begin errs = errs + 1; if (errs < 4) $display("ERR legacy fault cause %b cyc %0d", lkst[8:0], cyc); end
        if (skst[9] && errs < 1000) begin errs = errs + 1; if (errs < 4) $display("ERR static fault cause %b cyc %0d", skst[8:0], cyc); end
    end
    integer i, n, d_min, d_max, o_min, o_max, k_min, k_max;
    initial begin
        repeat (10) @(posedge ck); rst_n = 1;
        wait (cyc > B0 + NL * P + 400);
        for (q = 0; q < 4; q = q + 1) begin
            if (sa_q[q].size() != 33 * NL || la_q[q].size() != 33 * NL) begin errs = errs + 1; $display("ERR aq count q%0d static %0d legacy %0d", q, sa_q[q].size(), la_q[q].size()); end
            n = (sa_q[q].size() < la_q[q].size()) ? sa_q[q].size() : la_q[q].size();
            for (i = 0; i < n; i = i + 1) if (sa_q[q][i] !== la_q[q][i]) begin errs = errs + 1; if (errs < 8) $display("ERR aq q%0d word %0d differs", q, i); end
            if (sk_q[q].size() != 2 * NL || lk_q[q].size() != 2 * NL) begin errs = errs + 1; $display("ERR kvn count q%0d static %0d legacy %0d", q, sk_q[q].size(), lk_q[q].size()); end
            n = (sk_q[q].size() < lk_q[q].size()) ? sk_q[q].size() : lk_q[q].size();
            for (i = 0; i < n; i = i + 1) if (sk_q[q][i] !== lk_q[q][i]) begin errs = errs + 1; if (errs < 8) $display("ERR kvn q%0d row %0d differs", q, i); end
            if (sc_q[q].size() != lc_q[q].size() || sc_q[q].size() == 0) begin errs = errs + 1; $display("ERR kc count q%0d static %0d legacy %0d", q, sc_q[q].size(), lc_q[q].size()); end
            n = (sc_q[q].size() < lc_q[q].size()) ? sc_q[q].size() : lc_q[q].size();
            for (i = 0; i < n; i = i + 1) if (sc_q[q][i] !== lc_q[q][i]) begin errs = errs + 1; if (errs < 8) $display("ERR kc q%0d word %0d differs", q, i); end
        end
        d_min = 1 << 30; d_max = -(1 << 30); o_min = d_min; o_max = d_max; k_min = d_min; k_max = d_max;
        for (i = 0; i < s_ast.size() && i < l_ast.size() && i < cmd_t.size(); i = i + 1) begin
            if (s_ast[i] - l_ast[i] < d_min) d_min = s_ast[i] - l_ast[i]; if (s_ast[i] - l_ast[i] > d_max) d_max = s_ast[i] - l_ast[i];
            if (s_ast[i] - cmd_t[i] < o_min) o_min = s_ast[i] - cmd_t[i]; if (s_ast[i] - cmd_t[i] > o_max) o_max = s_ast[i] - cmd_t[i];
        end
        for (i = 0; i < s_krow.size() && i < l_krow.size(); i = i + 1) begin
            if (s_krow[i] - l_krow[i] < k_min) k_min = s_krow[i] - l_krow[i]; if (s_krow[i] - l_krow[i] > k_max) k_max = s_krow[i] - l_krow[i];
        end
        if (o_min != o_max || o_min != G_AQ) begin errs = errs + 1; $display("ERR static aq start not at the compiled CMD offset %0d: %0d..%0d", G_AQ, o_min, o_max); end
        $display("SEQ_STATIC %s layers=%0d aq=%0d kvn=%0d kc=%0d errors=%0d mut=%0d aq_start_from_cmd=%0d aq_start_vs_legacy=%0d..%0d row_vs_legacy=%0d..%0d",
                 errs == 0 ? "PASS" : "FAIL", NL, sa_q[0].size(), sk_q[0].size(), sc_q[0].size(), errs, MUT, o_min, d_min, d_max, k_min, k_max);
        $finish;
    end
    initial begin #4000000; $display("SEQ_STATIC FAIL timeout"); $finish; end
endmodule
