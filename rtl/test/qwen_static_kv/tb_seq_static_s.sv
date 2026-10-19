`timescale 1ns/1ps
// RTL-BUILD-KV/SEQ 2026-10-18: qkd_seq_static_s (no legacy landing faces) LOCKSTEP against qkd_seq_static_p on the same
// link-slotted layer traffic as tb_seq_static_prg (SEQ_GOLD slots, the ACTUAL qkd_native_attention_programme feeding
// both).  The reference's kvn_<q>_cr is an always-available credit (a landing that returns every posted row 6 edges
// after it leaves the face) and mf_<q> = 0.  Every remaining output -- aq_<q> x4, kc_<q> x4, hs, tk, kst -- is compared
// on EVERY edge after reset (bit- and edge-identical).  svc is a per-edge pseudo-random word (tk host fields).
// After the last layer, a fault phase drives an off-slot KVN word, then an hf pulse and an af_EN pulse into both, so the
// fault / cause / drained bits are compared live too (before it, both must stay fault-free).
// A third instance qkd_seq_static_p with kvn_<q>_cr = 0 (= the die today: no producer) records where the live bug
// (row-credit check f_cr) raises its fault: DIE_CR0 line, layer of the first fault.
module tb_seq_static_s #(parameter integer MUT = 0, parameter integer NL = 36, parameter integer P = 6836) ();
`include "seq_gold.svh"
    reg ck = 0;
    always #0.5 ck = ~ck;
    reg rst_n = 0;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    localparam integer RXC = 4, TXF = 40, TEND = 74;
    localparam [15:0] EP = 16'd17;
    integer B0 = 2000;
    integer INJ;
    initial INJ = 2000 + NL * 6836 + 200;
    reg         s_kv = 0; reg [10:0] s_kt = 0; reg [511:0] s_kd = 0;
    reg         s_lr = 0; reg [5:0] s_ll = 0; reg [13:0] s_lt = 0;
    reg         p_ev = 0; reg [547:0] p_pl = 0; reg p_issue = 0, p_run = 0;
    reg [5:0]   p_stage = 1; reg [17:0] p_pos = 0;
    reg         s_hf = 0; reg [3:0] s_af = 0;
    reg [173:0] s_svc = 0;
    reg [31:0]  lfsr = 32'h1234_5678;
    function automatic [511:0] qword(input integer l, input integer b);
        qword = {16{8'(l), 8'(b), 16'h5a00 | 16'(l * 37 + b)}};
    endfunction
    function automatic [511:0] kword(input integer l, input integer k);
        kword = {16{8'(l), 8'(k), 16'hc300 | 16'(l * 11 + k)}};
    endfunction
    function automatic [2:0] ktag(input integer k);
        ktag = (k < 2) ? 3'(k) : 3'(k + 2);
    endfunction
    integer L, rel, T, j_;
    always @(negedge ck) begin
        s_kv = 0; s_kt = 0; s_lr = 0; p_ev = 0; p_issue = 0; p_run = 0; s_hf = 0; s_af = 0;
        lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
        for (j_ = 0; j_ < 6; j_ = j_ + 1) s_svc[32*j_ +: 32] = lfsr ^ 32'(j_ * 32'h9e37_79b9) ^ 32'(cyc);
        if (cyc >= B0) begin
            L = (cyc - B0) / P; rel = (cyc - B0) % P; T = 100 + L / 36;
            if (L < NL) begin
                s_ll = 6'(L); s_lt = 14'(T); p_stage = 6'(L + 1); p_pos = 18'(T - 1);
                if (rel == G_CMD - RXC - 8) p_issue = 1;
                if (rel == G_CMD - RXC - 1) p_run = 1;
                if (rel == G_CMD - G_LPRUN) s_lr = 1;
                if (rel == G_CMD) begin
                    p_ev = 1; p_pl = {5'd0, 4'd1, 6'(L), EP, 5'd0, 512'({18'(T - 1), 1'b1})};
                end
                if (rel >= G_Q0 && rel < G_Q0 + 32) begin
                    p_ev = 1; p_pl = {5'd0, 4'd2, 6'(L), EP, 5'(rel - G_Q0), qword(L, rel - G_Q0)};
                end
                if (rel >= G_KV0 && rel < G_KV0 + 4) begin
                    s_kv = 1; s_kt = {3'b010, 5'd0, ktag(rel - G_KV0)}; s_kd = kword(L, rel - G_KV0);
                end
            end
        end
        // fault phase (after every layer): off-slot KVN word, hub fault, attention-stack fault
        if (cyc == INJ)       begin s_kv = 1; s_kt = {3'b010, 8'd0}; end
        if (cyc == INJ + 100) s_hf = 1;
        if (cyc == INJ + 200) s_af = 4'b1000;
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
    wire [539:0] sa [0:3]; wire [32:0] sc [0:3]; wire shs; wire [92:0] stk; wire [9:0] skst;
    wire [539:0] ra [0:3]; wire [1046:0] rk [0:3]; wire [32:0] rc [0:3]; wire rhs; wire [92:0] rtk; wire [9:0] rkst;
    wire [539:0] za [0:3]; wire [1046:0] zk [0:3]; wire [32:0] zc [0:3]; wire zhs; wire [92:0] ztk; wire [9:0] zkst;
    reg [519:0] s_ar = 0, r_ar = 0, z_ar = 0;
    reg [3:0] r_cr = 0;
    qkd_seq_static_s #(.MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .prg_req_v(p_req), .prg_req_pos(p_rpos),
        .prg_q_v(p_qv), .prg_q_beat(p_qb), .prg_q_data(p_qd),
        .kvn_word_valid(s_kv), .kvn_word_tag(s_kt), .lp_run(s_lr), .lp_layer(s_ll), .lp_ctx_t(s_lt),
        .svc(s_svc), .aq_WS(sa[0]), .aq_WN(sa[1]), .aq_ES(sa[2]), .aq_EN(sa[3]),
        .kc_WS(sc[0]), .kc_WN(sc[1]), .kc_ES(sc[2]), .kc_EN(sc[3]),
        .af_WS(s_af[0]), .af_WN(s_af[1]), .af_ES(s_af[2]), .af_EN(s_af[3]),
        .ar_h(s_ar[519:512]), .hf(s_hf), .hs(shs), .tk(stk), .kst(skst));
    qkd_seq_static_p #(.MUT(0)) ref_ (.ck(ck), .rst_n(rst_n), .prg_req_v(p_req), .prg_req_pos(p_rpos),
        .prg_q_v(p_qv), .prg_q_beat(p_qb), .prg_q_data(p_qd),
        .kvn_word_valid(s_kv), .kvn_word_tag(s_kt), .kvn_word_data(s_kd), .lp_run(s_lr), .lp_layer(s_ll), .lp_ctx_t(s_lt),
        .svc(s_svc), .aq_WS(ra[0]), .aq_WN(ra[1]), .aq_ES(ra[2]), .aq_EN(ra[3]),
        .kvn_WS_d(rk[0]), .kvn_WN_d(rk[1]), .kvn_ES_d(rk[2]), .kvn_EN_d(rk[3]),
        .kvn_WS_cr(r_cr[0]), .kvn_WN_cr(r_cr[1]), .kvn_ES_cr(r_cr[2]), .kvn_EN_cr(r_cr[3]),
        .kc_WS(rc[0]), .kc_WN(rc[1]), .kc_ES(rc[2]), .kc_EN(rc[3]),
        .af_WS(s_af[0]), .af_WN(s_af[1]), .af_ES(s_af[2]), .af_EN(s_af[3]),
        .mf_WS(1'b0), .mf_WN(1'b0), .mf_ES(1'b0), .mf_EN(1'b0), .ar(r_ar), .hf(s_hf), .hs(rhs), .tk(rtk), .kst(rkst));
    qkd_seq_static_p #(.MUT(0)) die0 (.ck(ck), .rst_n(rst_n), .prg_req_v(p_req), .prg_req_pos(p_rpos),
        .prg_q_v(p_qv), .prg_q_beat(p_qb), .prg_q_data(p_qd),
        .kvn_word_valid(s_kv), .kvn_word_tag(s_kt), .kvn_word_data(s_kd), .lp_run(s_lr), .lp_layer(s_ll), .lp_ctx_t(s_lt),
        .svc(s_svc), .aq_WS(za[0]), .aq_WN(za[1]), .aq_ES(za[2]), .aq_EN(za[3]),
        .kvn_WS_d(zk[0]), .kvn_WN_d(zk[1]), .kvn_ES_d(zk[2]), .kvn_EN_d(zk[3]),
        .kvn_WS_cr(1'b0), .kvn_WN_cr(1'b0), .kvn_ES_cr(1'b0), .kvn_EN_cr(1'b0),
        .kc_WS(zc[0]), .kc_WN(zc[1]), .kc_ES(zc[2]), .kc_EN(zc[3]),
        .af_WS(1'b0), .af_WN(1'b0), .af_ES(1'b0), .af_EN(1'b0),
        .mf_WS(1'b0), .mf_WN(1'b0), .mf_ES(1'b0), .mf_EN(1'b0), .ar(z_ar), .hf(1'b0), .hs(zhs), .tk(ztk), .kst(zkst));
    // hub model (each DUT its own): 32 RES words from 60 edges after its hs; reference row credit 6 edges after each row
    integer s_hs = -1, r_hs = -1, z_hs = -1;
    reg [3:0] r_crq [0:7];
    integer k_;
    always @(posedge ck) begin
        if (shs) s_hs <= cyc; if (rhs) r_hs <= cyc; if (zhs) z_hs <= cyc;
        s_ar <= 0; r_ar <= 0; z_ar <= 0;
        if (s_hs >= 0 && cyc - s_hs >= 60 && cyc - s_hs < 92) s_ar <= {1'b1, 1'b0, 6'(cyc - s_hs - 60), 512'(cyc)};
        if (r_hs >= 0 && cyc - r_hs >= 60 && cyc - r_hs < 92) r_ar <= {1'b1, 1'b0, 6'(cyc - r_hs - 60), 512'(cyc)};
        if (z_hs >= 0 && cyc - z_hs >= 60 && cyc - z_hs < 92) z_ar <= {1'b1, 1'b0, 6'(cyc - z_hs - 60), 512'(cyc)};
        for (k_ = 7; k_ > 0; k_ = k_ - 1) r_crq[k_] <= r_crq[k_ - 1];
        r_crq[0] <= {rk[3][1046], rk[2][1046], rk[1][1046], rk[0][1046]};
        r_cr <= r_crq[5];
    end
    // ---------------- lockstep compare on every edge ----------------
    integer q, errs = 0, pf = 0, n_aq = 0, n_kc = 0, n_hs = 0, n_drn = 0, z_cyc = -1, s_flt = -1;
    reg [9:0] z_cause;
    reg tk_drn_q = 0;
    always @(posedge ck) tk_drn_q <= stk[89];
    always @(posedge ck) if (rst_n) begin
        for (q = 0; q < 4; q = q + 1) begin
            if (sa[q] !== ra[q]) begin errs = errs + 1; if (errs < 8) $display("ERR aq q%0d cyc %0d", q, cyc); end
            if (sc[q] !== rc[q]) begin errs = errs + 1; if (errs < 8) $display("ERR kc q%0d cyc %0d", q, cyc); end
            if (sa[q][539] || sa[q][518]) n_aq = n_aq + 1;
            if (sc[q][32]) n_kc = n_kc + 1;
        end
        if (shs !== rhs) begin errs = errs + 1; if (errs < 8) $display("ERR hs cyc %0d", cyc); end
        if (stk !== rtk) begin errs = errs + 1; if (errs < 8) $display("ERR tk cyc %0d succ %h ref %h", cyc, stk, rtk); end
        if (skst !== rkst) begin errs = errs + 1; if (errs < 8) $display("ERR kst cyc %0d succ %b ref %b", cyc, skst, rkst); end
        if (shs) n_hs = n_hs + 1;
        if (stk[89] != tk_drn_q) n_drn = n_drn + 1;                  // drained-bit transitions exercised
        if (p_fault && pf == 0) begin pf = 1; errs = errs + 1; $display("ERR programme fault cyc %0d", cyc); end
        if (cyc < INJ && rkst[9] && errs < 1000) begin errs = errs + 1; if (errs < 8) $display("ERR reference fault cause %b cyc %0d", rkst[8:0], cyc); end
        if (skst[9] && s_flt < 0) s_flt = cyc;
        if (zkst[9] && z_cyc < 0) begin z_cyc = cyc; z_cause = zkst; end
    end
    initial begin
        repeat (10) @(posedge ck); rst_n = 1;
        wait (cyc > INJ + 400);
        if (n_aq != 4 * 33 * NL) begin errs = errs + 1; $display("ERR aq word count %0d (want %0d)", n_aq, 4 * 33 * NL); end
        if (n_kc == 0) begin errs = errs + 1; $display("ERR no kc words"); end
        if (n_hs != NL) begin errs = errs + 1; $display("ERR hs count %0d", n_hs); end
        if (s_flt < INJ || !skst[9] || skst[8:0] != {1'b1, 4'b0, 1'b1, 3'b0}) begin
            errs = errs + 1; $display("ERR fault phase: first succ fault cyc %0d kst %b", s_flt, skst); end
        if (n_drn < 2 * NL) begin errs = errs + 1; $display("ERR drained bit toggled only %0d times", n_drn); end
        $display("DIE_CR0 qkd_seq_static_p with kvn_<q>_cr=0: first fault cyc %0d = layer %0d rel %0d kst %b",
                 z_cyc, (z_cyc - B0) / P, (z_cyc - B0) % P, z_cause);
        $display("SEQ_S %s layers=%0d aq=%0d kc=%0d hs=%0d drn_toggles=%0d errors=%0d mut=%0d lockstep_vs_p=every_edge",
                 errs == 0 ? "PASS" : "FAIL", NL, n_aq, n_kc, n_hs, n_drn, errs, MUT);
        $finish;
    end
    initial begin #4000000; $display("SEQ_S FAIL timeout"); $finish; end
endmodule
