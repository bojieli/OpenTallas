`timescale 1ns/1ps
// KVE-2/SEQ 2026-10-17: qkd_seq_static_p (attention RX taken from the attention programme, decision 0cx (3)) against
// qkd_seq_static (today's behaviour: att_rx_* + Q / CMD data on the KVN receiver wires), on the same layer traffic at the
// link compiler's slots (SEQ_GOLD from tools/qwen_static_kv/seq_static_golden.py, as tb_seq_static).
// The successor sees the ACTUAL qkd_native_attention_programme (descriptor producer + command guard + record codec +
// static ctl) fed with the static D2D end's 548-b attention RX records on the same edges; the programme's service face is
// closed by a loopback of its own reserved RESULT / STATUS slots (this bench proves the RX hand-off, not attention math).
// Checks per quadrant: aq words, kvn rows and kc descriptors bit-identical AND at a fixed edge offset from the reference:
// aq 0, kvn 0, kc DKC (= +1, priced).  Faults of both DUTs and of the programme must stay 0.
module tb_seq_static_prg #(parameter integer MUT = 0, parameter integer NL = 36, parameter integer P = 6836,
                           parameter integer DKC = 1) ();
`include "seq_gold.svh"
    reg ck = 0;
    always #0.5 ck = ~ck;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    localparam integer RXC = 4, TXF = 40, TEND = 74;   // programme compiled_rx_cmd / tx_first / end (ages after run)
    localparam [15:0] EP = 16'd17;
    reg         s_av = 0; reg [3:0] s_ak = 0; reg [4:0] s_ab = 0;
    reg         s_kv = 0; reg [10:0] s_kt = 0; reg [511:0] s_kd = 0;
    reg         s_lr = 0; reg [5:0] s_ll = 0; reg [13:0] s_lt = 0;
    reg         p_ev = 0; reg [547:0] p_pl = 0; reg p_issue = 0, p_run = 0;
    reg [5:0]   p_stage = 1; reg [17:0] p_pos = 0;
    integer B0 = 2000;
    function automatic [511:0] qword(input integer l, input integer b);
        qword = {16{8'(l), 8'(b), 16'h5a00 | 16'(l * 37 + b)}};
    endfunction
    function automatic [511:0] kword(input integer l, input integer k);
        kword = {16{8'(l), 8'(k), 16'hc300 | 16'(l * 11 + k)}};
    endfunction
    function automatic [2:0] ktag(input integer k);
        ktag = (k < 2) ? 3'(k) : 3'(k + 2);
    endfunction
    integer L, rel, T;
    always @(negedge ck) begin
        s_av = 0; s_ak = 0; s_ab = 0; s_kv = 0; s_kt = 0; s_lr = 0; p_ev = 0; p_issue = 0; p_run = 0;
        if (cyc >= B0) begin
            L = (cyc - B0) / P; rel = (cyc - B0) % P; T = 100 + L / 36;
            if (L < NL) begin
                s_ll = 6'(L); s_lt = 14'(T); p_stage = 6'(L + 1); p_pos = 18'(T - 1);
                if (rel == G_CMD - RXC - 8) p_issue = 1;
                if (rel == G_CMD - RXC - 1) p_run = 1;
                if (rel == G_CMD - G_LPRUN) s_lr = 1;
                if (rel == G_CMD) begin
                    s_av = 1; s_ak = 1;
                    p_ev = 1; p_pl = {5'd0, 4'd1, 6'(L), EP, 5'd0, 512'({18'(T - 1), 1'b1})};
                end
                if (rel == G_CMD + 1) s_kd = {493'd0, 18'(T - 1), 1'b1};
                if (rel >= G_Q0 && rel < G_Q0 + 32) begin
                    s_av = 1; s_ak = 2; s_ab = 5'(rel - G_Q0);
                    p_ev = 1; p_pl = {5'd0, 4'd2, 6'(L), EP, 5'(rel - G_Q0), qword(L, rel - G_Q0)};
                end
                if (rel >= G_Q0 + 1 && rel < G_Q0 + 33) s_kd = qword(L, rel - G_Q0 - 1);
                if (rel >= G_KV0 && rel < G_KV0 + 4) begin
                    s_kv = 1; s_kt = {3'b010, 5'd0, ktag(rel - G_KV0)}; s_kd = kword(L, rel - G_KV0);
                end
            end
        end
    end
    // ---------------- attention programme (actual RTL) + its service-face loopback ----------------
    wire        p_req, p_qv, p_busy, p_fault, p_resv, p_txv;
    wire [17:0] p_rpos; wire [4:0] p_qb; wire [511:0] p_qd; wire [15:0] p_age, p_rep; wire [5:0] p_rl;
    wire [547:0] p_txp;
    wire        lb_slot = p_resv || (p_busy && p_age == 16'(TXF + 33));
    wire        lb_stat = p_busy && p_age == 16'(TXF + 33);
    wire [4:0]  lb_beat = 5'(p_age - 16'(TXF));
    qkd_native_attention_programme u_prg (.ck(ck), .rst_n(rst_n), .issue(p_issue), .run(p_run),
        .fused_program_capability(1'b1), .authority_valid(1'b1), .authority_epoch(EP), .authority_token(18'd19),
        .authority_position(p_pos), .authority_stage(p_stage),
        .compiled_calendar(176'd0), .compiled_rx_cmd(16'(RXC)), .compiled_tx_first(16'(TXF)), .compiled_end(16'(TEND)),
        .rx_event(p_ev), .rx_payload(p_pl), .tx_slot(lb_slot), .tx_slot_kind(lb_stat ? 4'd4 : 4'd3),
        .tx_slot_beat(lb_stat ? 5'd0 : lb_beat), .tx_valid(p_txv), .tx_payload(p_txp),
        .request_valid(p_req), .request_ready(1'b1), .request_epoch(p_rep), .request_layer(p_rl),
        .request_position(p_rpos), .request_calendar(), .q_valid(p_qv), .q_beat(p_qb), .q_data(p_qd),
        .result_valid(p_resv), .result_beat(lb_beat), .result_data(512'd0), .result_epoch(p_rep), .result_layer(p_rl),
        .result_done(p_busy && p_age == 16'(TXF + 32)), .service_fault(1'b0), .result_reserved(p_resv),
        .busy(p_busy), .fault(p_fault), .age(p_age));
    // ---------------- DUTs ----------------
    wire [539:0] sa [0:3]; wire [1046:0] sk [0:3]; wire [32:0] sc [0:3]; wire shs; wire [92:0] stk; wire [9:0] skst;
    wire [539:0] ra [0:3]; wire [1046:0] rk [0:3]; wire [32:0] rc [0:3]; wire rhs; wire [92:0] rtk; wire [9:0] rkst;
    reg [519:0] s_ar = 0, r_ar = 0;
    reg [3:0] s_cr = 0, r_cr = 0;
    qkd_seq_static_p #(.MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .prg_req_v(p_req), .prg_req_pos(p_rpos),
        .prg_q_v(p_qv), .prg_q_beat(p_qb), .prg_q_data(p_qd),
        .kvn_word_valid(s_kv), .kvn_word_tag(s_kt), .kvn_word_data(s_kd), .lp_run(s_lr), .lp_layer(s_ll), .lp_ctx_t(s_lt),
        .svc(174'd0), .aq_WS(sa[0]), .aq_WN(sa[1]), .aq_ES(sa[2]), .aq_EN(sa[3]),
        .kvn_WS_d(sk[0]), .kvn_WN_d(sk[1]), .kvn_ES_d(sk[2]), .kvn_EN_d(sk[3]),
        .kvn_WS_cr(s_cr[0]), .kvn_WN_cr(s_cr[1]), .kvn_ES_cr(s_cr[2]), .kvn_EN_cr(s_cr[3]),
        .kc_WS(sc[0]), .kc_WN(sc[1]), .kc_ES(sc[2]), .kc_EN(sc[3]), .af_WS(1'b0), .af_WN(1'b0), .af_ES(1'b0), .af_EN(1'b0),
        .mf_WS(1'b0), .mf_WN(1'b0), .mf_ES(1'b0), .mf_EN(1'b0), .ar(s_ar), .hf(1'b0), .hs(shs), .tk(stk), .kst(skst));
    qkd_seq_static #(.MUT(0)) ref_ (.ck(ck), .rst_n(rst_n), .att_rx_v(s_av), .att_rx_kind(s_ak), .att_rx_beat(s_ab),
        .kvn_word_valid(s_kv), .kvn_word_tag(s_kt), .kvn_word_data(s_kd), .lp_run(s_lr), .lp_layer(s_ll), .lp_ctx_t(s_lt),
        .svc(174'd0), .aq_WS(ra[0]), .aq_WN(ra[1]), .aq_ES(ra[2]), .aq_EN(ra[3]),
        .kvn_WS_d(rk[0]), .kvn_WN_d(rk[1]), .kvn_ES_d(rk[2]), .kvn_EN_d(rk[3]),
        .kvn_WS_cr(r_cr[0]), .kvn_WN_cr(r_cr[1]), .kvn_ES_cr(r_cr[2]), .kvn_EN_cr(r_cr[3]),
        .kc_WS(rc[0]), .kc_WN(rc[1]), .kc_ES(rc[2]), .kc_EN(rc[3]), .af_WS(1'b0), .af_WN(1'b0), .af_ES(1'b0), .af_EN(1'b0),
        .mf_WS(1'b0), .mf_WN(1'b0), .mf_ES(1'b0), .mf_EN(1'b0), .ar(r_ar), .hf(1'b0), .hs(rhs), .tk(rtk), .kst(rkst));
    // hub model (each DUT its own): 32 RES words from 60 edges after its hs; landing row credit 6 edges after each row
    integer s_hs = -1, r_hs = -1;
    reg [3:0] s_crq [0:7]; reg [3:0] r_crq [0:7];
    integer k_;
    always @(posedge ck) begin
        if (shs) s_hs <= cyc; if (rhs) r_hs <= cyc;
        s_ar <= 0; r_ar <= 0;
        if (s_hs >= 0 && cyc - s_hs >= 60 && cyc - s_hs < 92) s_ar <= {1'b1, 1'b0, 6'(cyc - s_hs - 60), 512'(cyc)};
        if (r_hs >= 0 && cyc - r_hs >= 60 && cyc - r_hs < 92) r_ar <= {1'b1, 1'b0, 6'(cyc - r_hs - 60), 512'(cyc)};
        for (k_ = 7; k_ > 0; k_ = k_ - 1) begin s_crq[k_] <= s_crq[k_ - 1]; r_crq[k_] <= r_crq[k_ - 1]; end
        s_crq[0] <= {sk[3][1046], sk[2][1046], sk[1][1046], sk[0][1046]};
        r_crq[0] <= {rk[3][1046], rk[2][1046], rk[1][1046], rk[0][1046]};
        s_cr <= s_crq[5]; r_cr <= r_crq[5];
    end
    // ---------------- capture and compare (word AND edge) ----------------
    reg [539:0]  sa_q [0:3][$]; reg [539:0] ra_q [0:3][$];
    reg [1046:0] sk_q [0:3][$]; reg [1046:0] rk_q [0:3][$];
    reg [32:0]   sc_q [0:3][$]; reg [32:0]   rc_q [0:3][$];
    integer sa_t [0:3][$], ra_t [0:3][$], sk_t [0:3][$], rk_t [0:3][$], sc_t [0:3][$], rc_t [0:3][$];
    integer q, errs = 0, pf = 0;
    always @(posedge ck) if (rst_n) begin
        for (q = 0; q < 4; q = q + 1) begin
            if (sa[q][539] || sa[q][518]) begin sa_q[q].push_back(sa[q]); sa_t[q].push_back(cyc); end
            if (ra[q][539] || ra[q][518]) begin ra_q[q].push_back(ra[q]); ra_t[q].push_back(cyc); end
            if (sk[q][1046]) begin sk_q[q].push_back(sk[q]); sk_t[q].push_back(cyc); end
            if (rk[q][1046]) begin rk_q[q].push_back(rk[q]); rk_t[q].push_back(cyc); end
            if (sc[q][32]) begin sc_q[q].push_back(sc[q]); sc_t[q].push_back(cyc); end
            if (rc[q][32]) begin rc_q[q].push_back(rc[q]); rc_t[q].push_back(cyc); end
        end
        if (p_fault && pf == 0) begin pf = 1; errs = errs + 1; $display("ERR programme fault cyc %0d", cyc); end
        if (rkst[9] && errs < 1000) begin errs = errs + 1; if (errs < 4) $display("ERR reference fault cause %b cyc %0d", rkst[8:0], cyc); end
        if (skst[9] && errs < 1000) begin errs = errs + 1; if (errs < 4) $display("ERR successor fault cause %b cyc %0d", skst[8:0], cyc); end
    end
    integer i, n, da_min, da_max, dk_min, dk_max, dc_min, dc_max;
    initial begin
        repeat (10) @(posedge ck); rst_n = 1;
        wait (cyc > B0 + NL * P + 400);
        da_min = 1 << 30; da_max = -(1 << 30); dk_min = da_min; dk_max = da_max; dc_min = da_min; dc_max = da_max;
        for (q = 0; q < 4; q = q + 1) begin
            if (sa_q[q].size() != 33 * NL || ra_q[q].size() != 33 * NL) begin errs = errs + 1; $display("ERR aq count q%0d succ %0d ref %0d", q, sa_q[q].size(), ra_q[q].size()); end
            n = (sa_q[q].size() < ra_q[q].size()) ? sa_q[q].size() : ra_q[q].size();
            for (i = 0; i < n; i = i + 1) begin
                if (sa_q[q][i] !== ra_q[q][i]) begin errs = errs + 1; if (errs < 8) $display("ERR aq q%0d word %0d differs", q, i); end
                if (sa_t[q][i] - ra_t[q][i] < da_min) da_min = sa_t[q][i] - ra_t[q][i]; if (sa_t[q][i] - ra_t[q][i] > da_max) da_max = sa_t[q][i] - ra_t[q][i];
            end
            if (sk_q[q].size() != 2 * NL || rk_q[q].size() != 2 * NL) begin errs = errs + 1; $display("ERR kvn count q%0d succ %0d ref %0d", q, sk_q[q].size(), rk_q[q].size()); end
            n = (sk_q[q].size() < rk_q[q].size()) ? sk_q[q].size() : rk_q[q].size();
            for (i = 0; i < n; i = i + 1) begin
                if (sk_q[q][i] !== rk_q[q][i]) begin errs = errs + 1; if (errs < 8) $display("ERR kvn q%0d row %0d differs", q, i); end
                if (sk_t[q][i] - rk_t[q][i] < dk_min) dk_min = sk_t[q][i] - rk_t[q][i]; if (sk_t[q][i] - rk_t[q][i] > dk_max) dk_max = sk_t[q][i] - rk_t[q][i];
            end
            if (sc_q[q].size() != rc_q[q].size() || sc_q[q].size() == 0) begin errs = errs + 1; $display("ERR kc count q%0d succ %0d ref %0d", q, sc_q[q].size(), rc_q[q].size()); end
            n = (sc_q[q].size() < rc_q[q].size()) ? sc_q[q].size() : rc_q[q].size();
            for (i = 0; i < n; i = i + 1) begin
                if (sc_q[q][i] !== rc_q[q][i]) begin errs = errs + 1; if (errs < 8) $display("ERR kc q%0d word %0d differs", q, i); end
                if (sc_t[q][i] - rc_t[q][i] < dc_min) dc_min = sc_t[q][i] - rc_t[q][i]; if (sc_t[q][i] - rc_t[q][i] > dc_max) dc_max = sc_t[q][i] - rc_t[q][i];
            end
        end
        if (da_min != 0 || da_max != 0) begin errs = errs + 1; $display("ERR aq edge offset %0d..%0d (want 0)", da_min, da_max); end
        if (dk_min != 0 || dk_max != 0) begin errs = errs + 1; $display("ERR kvn edge offset %0d..%0d (want 0)", dk_min, dk_max); end
        if (dc_min != DKC || dc_max != DKC) begin errs = errs + 1; $display("ERR kc edge offset %0d..%0d (want %0d)", dc_min, dc_max, DKC); end
        $display("SEQ_PRG %s layers=%0d aq=%0d kvn=%0d kc=%0d errors=%0d mut=%0d aq_vs_ref=%0d..%0d kvn_vs_ref=%0d..%0d kc_vs_ref=%0d..%0d",
                 errs == 0 ? "PASS" : "FAIL", NL, sa_q[0].size(), sk_q[0].size(), sc_q[0].size(), errs, MUT,
                 da_min, da_max, dk_min, dk_max, dc_min, dc_max);
        $finish;
    end
    initial begin #4000000; $display("SEQ_PRG FAIL timeout"); $finish; end
endmodule
