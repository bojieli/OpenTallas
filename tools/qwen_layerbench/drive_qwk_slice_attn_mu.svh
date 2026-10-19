// MU-TOK-KV 10-19: the KV-die ATTENTION STEP, single user AND 4 users on the mixed-user calendar, on the qwk_slice_attn
// vehicle (slice_cut.py of a KV die netlist; the release die is the MU GEN kvs14r-bce531645-mu, OT_KV_MU=1).
// Successor of drive_qwk_slice_attn.svh (QW-KVATTN2): same slice edges, same KV store-path model, same checks, but N
// attention STEPS (one per user-layer kvs window of tools/qwen_static_schedule/mu_calendar.py), each with its own
//   user u, layer l, epoch {seq14, u2} (the MU epoch convention: epoch[1:0] = user, MU-ADOPT-KV), token, REAL operands
//   (q / K,V history / gold of its own vector dir), and run edge A_k = A_0 + REL_k (the calendar's kvs window offsets).
// Slice-edge neighbours, driven on the compiled static schedule (no ready, no credit, nothing waits):
//   kvs_ctl.o_attn / lp, d2d rx records, RESULT slots, KVN words, hroot kgo: as drive_qwk_slice_attn.svh, per step.
//   slg_<s>_<i> = the KV STORE PATH (landing ring <- PC <- HBM).  The MU read map (qkd_static_kv_pc_path_nc MU 1 =
//   qkd_kv_mu_rrow: row[9:8] = static_epoch[1:0]) puts user u, layer l at HBM row 64 + l + 256 u.  The model keys its
//   store by that row: a K request carries {layer, epoch} at the group pin -> row = 64 + layer + 256 * epoch[1:0] -> the
//   history of the step whose (u, l) has that row; a V request carries only t, so the model takes the row of the step
//   whose window [A_k, A_k+1) holds the request edge (the PC calendar is stage-latched the same way).  Every K request's
//   row is checked against the row of the step whose window holds it (KVA_ROW errors).
// Checks per step: 512 RESULT words at the d2d face bit-exact against that step's gold, the RESULT/STATUS record header
// epoch / layer = the step's, STATUS = {done 1, ready 1}, no fault anywhere (first fault cycle + cause printed).
// Measured per step (KVA_STEP lines): issue / run -> start_qk -> start_pv -> pvfin beat 0 -> RESULT beat 0 / 31 at the d2d
// face, K / V request spans; KVA_DIE_ATTN_CYCLES issue -> last RESULT word.
// Plusargs: +NSTEP=n (<= 8) and per step k: +VEC<k>=dir +U<k>=user +L<k>=layer +REL<k>=run-edge offset from step 0
//   (default k * 3283); +CTX=<T> +KVA_LG=8 +KVA_KGO=200 +KVA_AGE0=1 +KVA_KVN=34 +KVA_HCKC (DIAGNOSTIC: HBM-clock pins on
//   the core clock); +KVA_MUT=n: 1 CMD record one edge late (step 0), 2 group slg_WS_5 one edge late, 3 group 0 K row t^1,
//   4 RESULT slots one edge late (step 0), 5 USER-ROW SWAP (the store serves user 1's requests from user 2's rows and v.v.,
//   K and V: a wrong row map), 6 SLOT LATE (user 2's RESULT slots one edge late), 7 USER TAG (user 3's CMD/Q records carry
//   user 0's epoch at the seam).
// MU-TOK-KV2 10-19: (a) the seam epoch follows the MU-DQ-D2DUSER contract (c93aee75b): epoch = {seq14[u], u} with a
//   PER-USER sequence -- seq14[u] = KVA_SEQ0 (+SEQ0=, default 9) at the user's first L0 step, +1 at each later L0 step of
//   that user; every layer of one token carries its token's epoch (was: a global 9+k per step).
// (b) PER-STACK vehicles (kv_attn_grp_map.py --stacks: `define KVA_PARTIAL, KVA_NG = 8 groups, KVA_NV = 4 V ports):
//   one attention stack + the shared control; the absent stacks' partials are not driven, so RESULT exactness is not
//   judged (reported only); measured per step and stack (KVA_STACK lines): K / V request spans at the stack's landing
//   groups, the stack's partial (astk.ap) first..last non-zero edge, its V ports' out_valid span; faults judged only for
//   the stack's own ECTLs / V ports / strip.
`include "kva_grp_map.svh"
`include "kva_ports.svh"
`include "kva_hier_refs.svh"   // MU-TOK-KV3: port nets of hier-block instances (no refs into a hier block)
    localparam integer KMAX = 8, KV_ROWS = 16384;
    reg [1023:0] kva_kv [0:KMAX*KV_ROWS-1];
    reg [31:0] kva_q [0:KMAX*512-1], kva_gold [0:KMAX*512-1];
    integer kva_n = 1, kva_T = 8192, kva_go = 0, kva_lg = 8, kva_kgo = 200, kva_age0 = 1, kva_kvn = 34;
    integer kva_mut = 0, kva_hckc = 0, kva_txfirst = 1750, kva_rxcmd = 2, kva_seq0 = 9;
    integer kva_A [0:KMAX-1], kva_u [0:KMAX-1], kva_l [0:KMAX-1], kva_rel [0:KMAX-1];
    reg [15:0] kva_ep [0:KMAX-1]; reg [17:0] kva_tok [0:KMAX-1];
    string kva_vec [0:KMAX-1];
    // ---- HBM clock pins: free-running 976.6 MHz (1024 ps, the die's HBM clock) or (DIAGNOSTIC) the core clock ----
    reg kva_hfree = 0; always #0.512 kva_hfree = ~kva_hfree;
    always @* hck = (kva_hckc != 0) ? ck : kva_hfree;
`define KVA_ARGS(K) begin void'($value$plusargs(`"VEC``K=%s`", kva_vec[K])); void'($value$plusargs(`"U``K=%d`", kva_u[K])); \
        void'($value$plusargs(`"L``K=%d`", kva_l[K])); void'($value$plusargs(`"REL``K=%d`", kva_rel[K])); end
    function automatic integer kva_row(input integer u, input integer l); kva_row = 64 + l + 256 * u; endfunction
    initial begin : cfg
        integer k; string s;
        void'($value$plusargs("NSTEP=%d", kva_n)); if (kva_n < 1 || kva_n > KMAX) $fatal(1, "NSTEP 1..8");
        void'($value$plusargs("KVA_LG=%d", kva_lg)); void'($value$plusargs("KVA_KGO=%d", kva_kgo));
        void'($value$plusargs("KVA_AGE0=%d", kva_age0)); void'($value$plusargs("KVA_KVN=%d", kva_kvn));
        void'($value$plusargs("KVA_MUT=%d", kva_mut));
        if ($test$plusargs("KVA_HCKC")) kva_hckc = 1;
        if (!$value$plusargs("CTX=%d", kva_T)) kva_T = 8192;
        void'($value$plusargs("SEQ0=%d", kva_seq0));
        for (k = 0; k < KMAX; k = k + 1) begin
            kva_A[k] = -1000000; kva_u[k] = 0; kva_l[k] = 0; kva_rel[k] = 3283 * k;
            if (k < kva_n) begin
                case (k)
                    0: `KVA_ARGS(0)  1: `KVA_ARGS(1)  2: `KVA_ARGS(2)  3: `KVA_ARGS(3)
                    4: `KVA_ARGS(4)  5: `KVA_ARGS(5)  6: `KVA_ARGS(6)  default: `KVA_ARGS(7)
                endcase
                if (kva_vec[k] == "") $fatal(1, "+VEC%0d required", k);
                begin : seq   // per-user token sequence (MU-DQ-D2DUSER): +1 at each later L0 of the same user
                    integer j, n; n = 0;
                    for (j = 0; j <= k; j = j + 1) if (kva_u[j] == kva_u[k] && kva_l[j] == 0) n = n + 1;
                    kva_ep[k] = {14'(kva_seq0 + ((n > 0) ? n - 1 : 0)), 2'(kva_u[k])};   // epoch {seq14[u], user2}
                end
                kva_tok[k] = 18'(50994 + 64 * kva_ep[k][15:2] + kva_u[k]);
                $readmemh({kva_vec[k], "/q.hex"}, kva_q, 512 * k, 512 * k + 511);
                $readmemh({kva_vec[k], "/gold.hex"}, kva_gold, 512 * k, 512 * k + 511);
                $readmemh({kva_vec[k], "/kv.hex"}, kva_kv, KV_ROWS * k, KV_ROWS * k + 2 * kva_T - 1);
                $display("KVA_STEPCFG %0d vec %0s user %0d layer %0d epoch %04h row %0d rel %0d", k, kva_vec[k], kva_u[k], kva_l[k],
                         kva_ep[k], kva_row(kva_u[k], kva_l[k]), kva_rel[k]);
            end
        end
        for (k = 0; k < kva_n; k = k + 1) begin : uniq
            integer j; for (j = 0; j < k; j = j + 1)
                if (kva_row(kva_u[j], kva_l[j]) == kva_row(kva_u[k], kva_l[k])) $fatal(1, "steps %0d / %0d share a KV row", j, k);
        end
        $display("KVA_CFG nstep %0d T %0d LG %0d KGO %0d AGE0 %0d KVN %0d MUT %0d HCKC %0d", kva_n, kva_T, kva_lg, kva_kgo,
                 kva_age0, kva_kvn, kva_mut, kva_hckc);
        kva_ectl_cfg();
        kva_kg({6'(kva_l[0]), kva_ep[0], 1'b0});
    end
    // the step whose window holds edge p (latest A_k - lead <= p), -1 before the first
    function automatic integer kva_cur(input integer p, input integer lead);
        integer k; begin kva_cur = -1;
            if (kva_go) for (k = 0; k < kva_n; k = k + 1) if (p >= kva_A[k] - lead) kva_cur = k;
        end endfunction
    function automatic integer kva_step_of_row(input integer r);
        integer k; begin kva_step_of_row = -1;
            for (k = 0; k < kva_n; k = k + 1) if (kva_row(kva_u[k], kva_l[k]) == r) kva_step_of_row = k; end endfunction
    function automatic integer kva_step_of_ep(input [15:0] e, input [5:0] l);
        integer k; begin kva_step_of_ep = -1;
            for (k = 0; k < kva_n; k = k + 1) if (kva_ep[k] == e && 6'(kva_l[k]) == l) kva_step_of_ep = k; end endfunction
    initial begin : uniq_ep   // (epoch, layer) must name one step: the RESULT header check keys on it
        integer j, k; #1;
        for (k = 0; k < kva_n; k = k + 1) for (j = 0; j < k; j = j + 1)
            if (kva_ep[j] == kva_ep[k] && kva_l[j] == kva_l[k]) $fatal(1, "steps %0d / %0d share epoch %04h layer %0d", j, k, kva_ep[k], kva_l[k]);
    end
    // ---- the compiled edge-relative events at the consumer pins (p = consumer pin cycle) ----
    function automatic [76:0] kva_ctl(input integer p);
        integer k; reg go, iss, run; begin
            k = kva_cur(p, 40); kva_ctl = 77'd0;
            if (k >= 0) begin
                go = (p == kva_A[k] - 30); iss = (p == kva_A[k] - 8); run = (p == kva_A[k]);
                kva_ctl = {kva_tok[k], go, 6'(kva_l[k] + 1), 18'(kva_T - 1), kva_ep[k], 14'(kva_T), run, iss, 1'b1, 1'b1};
            end
        end endfunction
    function automatic [20:0] kva_lp(input integer p);
        integer k; begin k = kva_cur(p, 40); kva_lp = 21'd0;
            if (k >= 0) kva_lp = {14'(kva_T), 6'(kva_l[k]), p == kva_A[k] - 8}; end endfunction
    function automatic [547:0] kva_rec(input integer p);   // the RX record at the attention programme's rx pin
        integer k, g, b, j; reg [511:0] d; reg [15:0] e; begin
            kva_rec = 548'd0;
            for (k = 0; k < kva_n; k = k + 1) if (kva_go) begin
                g = p - (kva_A[k] + kva_age0) - ((kva_mut == 1 && k == 0) ? 1 : 0);
                e = (kva_mut == 7 && kva_u[k] == 3) ? {kva_ep[k][15:2], 2'd0} : kva_ep[k];
                if (g == kva_rxcmd) kva_rec = {5'd0, 4'd1, 6'(kva_l[k]), e, 5'd0, {493'd0, 5'd0, 13'(kva_T - 1), 1'b1}};
                else if (g > kva_rxcmd && g <= kva_rxcmd + 32) begin
                    b = g - kva_rxcmd - 1;
                    for (j = 0; j < 16; j = j + 1) d[32*j +: 32] = kva_q[512 * k + 16*b + j];
                    kva_rec = {5'd0, 4'd2, 6'(kva_l[k]), e, 5'(b), d};
                end
            end
        end endfunction
    function automatic [9:0] kva_txs(input integer p);      // {beat 5, kind 4, slot}
        integer k, g; begin kva_txs = 10'd0;
            for (k = 0; k < kva_n; k = k + 1) if (kva_go) begin
                g = p - (kva_A[k] + kva_age0) - kva_txfirst - (((kva_mut == 4 && k == 0) || (kva_mut == 6 && kva_u[k] == 2)) ? 1 : 0);
                if (g >= 0 && g < 32) kva_txs = {5'(g), 4'd3, 1'b1};
                else if (g == 33) kva_txs = {5'd0, 4'd4, 1'b1};
            end
        end endfunction
    // ---- the KVN words on the sequencer's compiled check edges (k-th rising seq request = step k) ----
    integer kva_seqreq [0:KMAX-1]; integer kva_nsr = 0; reg kva_sr_q = 0;
    initial for (int k = 0; k < KMAX; k++) kva_seqreq[k] = -1;
    always @(negedge ck) begin
        if (dut.seq.prg_req_v === 1'b1 && !kva_sr_q && kva_nsr < KMAX) begin kva_seqreq[kva_nsr] = cyc; kva_nsr = kva_nsr + 1; end
        kva_sr_q <= (dut.seq.prg_req_v === 1'b1);
    end
    function automatic [11:0] kva_skw(input integer p);
        integer k, j; begin kva_skw = 12'd0;
            for (k = 0; k < KMAX; k = k + 1) if (kva_seqreq[k] >= 0) begin
                j = p - (kva_seqreq[k] + kva_kvn);
                if (j >= 0 && j < 4) kva_skw = {3'b010, 5'd0, 1'(j / 2), 1'b0, 1'(j % 2), 1'b1};
            end
        end endfunction
    // ---- slice-edge drive: every input S edges before its consumer-pin event ----
    always @(negedge ck) begin : edge_drive
        integer k;
        drv_i_n_ks_kvs_ctl__o_attn = kva_ctl(cyc + S_CTL);
        drv_i_n_ks_seq_lp = kva_lp(cyc + S_LP);
        begin : rx
            reg [547:0] r; r = kva_rec(cyc + S_RXP);
            drv_i_n_ks_d2d_kv__rx_payload = r;
            r = kva_rec(cyc + S_SRX);
            drv_i_n_seqst_rx = {512'd0, 5'd0, 4'd0, |r[542:539]};
        end
        begin : tx
            reg [9:0] t; t = kva_txs(cyc + S_TXS);
            drv_i_n_ks_d2d_kv__att_tx_slot = t[0]; drv_i_n_ks_d2d_kv__att_tx_kind = t[4:1]; drv_i_n_ks_d2d_kv__att_tx_beat = t[9:5];
        end
        drv_i_n_seqst_kw = kva_skw(cyc + S_SKW);
        begin : kg
            reg hit; hit = 0;
            for (k = 0; k < kva_n; k = k + 1) if (kva_go && cyc == kva_A[k] - kva_kgo) begin kva_kg({6'(kva_l[k]), kva_ep[k], 1'b1}); hit = 1; end
            if (!hit) begin k = kva_cur(cyc, kva_kgo); if (k < 0) k = 0; kva_kg({6'(kva_l[k]), kva_ep[k], 1'b0}); end
        end
    end
    // ---- the KV store path at the 32 landing-group pins: request sampled at edge c -> response visible KVA_LG edges later --
    reg [37:0] kva_pk [0:KVA_NG-1][0:63]; reg [14:0] kva_pv [0:KVA_NG-1][0:63]; integer kva_pvk [0:KVA_NG-1][0:63];
    integer kva_g, kva_i, kva_coll = 0, kva_rowerr = 0;
    integer kva_nk [0:KMAX-1], kva_nv [0:KMAX-1], kva_k0 [0:KMAX-1], kva_v0 [0:KMAX-1], kva_klast [0:KMAX-1], kva_vlast [0:KMAX-1];
    initial begin
        for (kva_g = 0; kva_g < KVA_NG; kva_g = kva_g + 1) for (kva_i = 0; kva_i < 64; kva_i = kva_i + 1) begin
            kva_pk[kva_g][kva_i] = 0; kva_pv[kva_g][kva_i] = 0; kva_pvk[kva_g][kva_i] = 0; end
        for (kva_i = 0; kva_i < KMAX; kva_i = kva_i + 1) begin
            kva_nk[kva_i] = 0; kva_nv[kva_i] = 0; kva_k0[kva_i] = -1; kva_v0[kva_i] = -1; kva_klast[kva_i] = -1; kva_vlast[kva_i] = -1; end
    end
    // per step and stack: K / V request spans, partial (astk.ap) non-zero span, V-port out_valid span
    integer kva_sk0 [0:KMAX-1][0:3], kva_skl [0:KMAX-1][0:3], kva_sv0 [0:KMAX-1][0:3], kva_svl [0:KMAX-1][0:3];
    integer kva_sa0 [0:KMAX-1][0:3], kva_sal [0:KMAX-1][0:3], kva_so0 [0:KMAX-1][0:3], kva_sol [0:KMAX-1][0:3];
    initial for (int k = 0; k < KMAX; k++) for (int s = 0; s < 4; s++) begin
        kva_sk0[k][s] = -1; kva_skl[k][s] = -1; kva_sv0[k][s] = -1; kva_svl[k][s] = -1;
        kva_sa0[k][s] = -1; kva_sal[k][s] = -1; kva_so0[k][s] = -1; kva_sol[k][s] = -1; end
    always @(negedge ck) begin : stk_spans
        integer s, w, v; w = kva_cur(cyc, 30);
        if (w >= 0) begin
            for (s = 0; s < KVA_NSTK; s = s + 1) if (|kva_ap[s] === 1'b1) begin
                if (kva_sa0[w][s] < 0) kva_sa0[w][s] = cyc; kva_sal[w][s] = cyc; end
            for (v = 0; v < KVA_NV; v = v + 1) if (kva_vport_ov[v] === 1'b1) begin
                if (kva_so0[w][v / 4] < 0) kva_so0[w][v / 4] = cyc; kva_sol[w][v / 4] = cyc; end
        end
    end
    // the HBM row map as the store sees it (mutant 5 = a wrong map: users 1 and 2 exchanged)
    function automatic integer kva_map_user(input integer u);
        kva_map_user = (kva_mut == 5 && u == 1) ? 2 : (kva_mut == 5 && u == 2) ? 1 : u; endfunction
    always @(negedge ck) begin : grp_model
        integer g, d, t, lg, s, sk, w, wr; reg [37:0] ek; reg [14:0] ev; reg [1023:0] row;
        for (g = 0; g < KVA_NG; g = g + 1) begin
            d = cyc % 64; ek = kva_pk[g][d]; ev = kva_pv[g][d]; s = kva_pvk[g][d]; kva_pk[g][d] = 0; kva_pv[g][d] = 0;
            kva_krsp[g] = 1062'd0; kva_rsp[g] = 1056'd0;
            if (ek[0] && ev[0]) begin kva_coll = kva_coll + 1; smoke_err("landing group: K and V response in one edge"); end
            if (ek[0]) begin
                t = ek[14:1];
                sk = kva_step_of_row(kva_row(kva_map_user(ek[17:16]), ek[37:32]));
                row = (sk >= 0) ? kva_kv[KV_ROWS * sk + t] : {32{32'hdead0bad}};
                if (kva_mut == 3 && g == 0 && sk >= 0) row = kva_kv[KV_ROWS * sk + (t ^ 1)];
                kva_krsp[g] = {ek[37:32], ek[31:16], 1'b0, 14'(t), row, 1'b1};
                kva_rsp[g] = {row, ek[31:16], 14'(t), 1'b0, 1'b1};
            end else if (ev[0]) begin
                t = ev[14:1];
                sk = (s >= 0) ? kva_step_of_row(kva_row(kva_map_user(kva_u[s]), kva_l[s])) : -1;
                row = (sk >= 0) ? kva_kv[KV_ROWS * sk + kva_T + t] : {32{32'hdead0bad}};
                w = (s >= 0) ? s : 0;
                kva_krsp[g] = {6'(kva_l[w]), kva_ep[w], 1'b1, 14'(t), row, 1'b1};
                kva_rsp[g] = {row, kva_ep[w], 14'(t), 1'b1, 1'b1};
            end
            lg = kva_lg + ((kva_mut == 2 && g == 5) ? 1 : 0);
            w = kva_cur(cyc, 30);
            if (kva_kreq[g][0] === 1'b1) begin
                kva_pk[g][(cyc + lg) % 64] = kva_kreq[g];
                wr = kva_row(kva_kreq[g][17:16], kva_kreq[g][37:32]);
                if (w < 0 || wr != kva_row(kva_u[w], kva_l[w])) begin
                    kva_rowerr = kva_rowerr + 1;
                    if (kva_rowerr <= 4) $display("KVA_ROW_ERR cyc %0d group %0d K request row %0d (epoch %04h layer %0d), window step %0d row %0d",
                        cyc, g, wr, kva_kreq[g][31:16], kva_kreq[g][37:32], w, (w < 0) ? -1 : kva_row(kva_u[w], kva_l[w]));
                end
                if (w >= 0) begin kva_nk[w] = kva_nk[w] + 1; if (kva_k0[w] < 0) kva_k0[w] = cyc; kva_klast[w] = cyc;
                    if (kva_sk0[w][g / 8] < 0) kva_sk0[w][g / 8] = cyc; kva_skl[w][g / 8] = cyc; end
            end
            if (kva_vreq[g][0] === 1'b1) begin
                kva_pv[g][(cyc + lg) % 64] = kva_vreq[g]; kva_pvk[g][(cyc + lg) % 64] = w;
                if (w >= 0) begin kva_nv[w] = kva_nv[w] + 1; if (kva_v0[w] < 0) kva_v0[w] = cyc; kva_vlast[w] = cyc;
                    if (kva_sv0[w][g / 8] < 0) kva_sv0[w][g / 8] = cyc; kva_svl[w][g / 8] = cyc; end
            end
        end
    end
    // ---- the d2d face (slice output): RESULT beats vs the step's gold, STATUS ----
    wire [547:0] kva_tp = `KVA_TXP;
    wire kva_tv = `KVA_TXV;
    integer kva_words [0:KMAX-1], kva_derr [0:KMAX-1], kva_r0 [0:KMAX-1], kva_r31 [0:KMAX-1], kva_st [0:KMAX-1];
    integer kva_nrec = 0, kva_hdrerr = 0, kva_nst = 0;
    initial for (int k = 0; k < KMAX; k++) begin kva_words[k] = 0; kva_derr[k] = 0; kva_r0[k] = -1; kva_r31[k] = -1; kva_st[k] = -1; end
    always @(negedge ck) if (kva_tv === 1'b1) begin : face
        integer j, b, k; kva_nrec = kva_nrec + 1;
        k = kva_step_of_ep(kva_tp[532:517], kva_tp[538:533]);
        if (kva_tp[542:539] == 4'd3) begin
            b = kva_tp[516:512];
            if (k < 0) begin kva_hdrerr = kva_hdrerr + 1; smoke_err("RESULT epoch / layer of no step");
                if (kva_hdrerr <= 4) $display("KVA_HDR_ERR cyc %0d epoch %04h layer %0d beat %0d", cyc, kva_tp[532:517], kva_tp[538:533], b); end
            else begin
                if (b == 0) kva_r0[k] = cyc; if (b == 31) kva_r31[k] = cyc;
                for (j = 0; j < 16; j = j + 1) begin
                    if (kva_tp[32*j +: 32] !== kva_gold[512 * k + 16*b + j]) begin
                        if (kva_derr[k] < 4) $display("KVA_MISMATCH step %0d user %0d word %0d got %08h want %08h", k, kva_u[k], 16*b + j,
                                                      kva_tp[32*j +: 32], kva_gold[512 * k + 16*b + j]);
                        kva_derr[k] = kva_derr[k] + 1;
                    end
                    kva_words[k] = kva_words[k] + 1;
                end
            end
        end else if (kva_tp[542:539] == 4'd4) begin
            if (k < 0) k = (kva_nst < kva_n) ? kva_nst : 0;
            kva_st[k] = cyc; kva_nst = kva_nst + 1;
            if (kva_tp[511:0] !== {507'd0, 5'b01001}) begin smoke_err("STATUS word != {done 1, ready 1}"); $display("KVA_STATUS step %0d %h", k, kva_tp[31:0]); end
        end else begin smoke_err("unexpected record kind at the d2d face"); $display("KVA_REC kind %0d", kva_tp[542:539]); end
    end
    // ---- fault probes (first cycle + cause) and per-step event cycles (k-th rising edge = step k) ----
    wire kva_f_prog = dut.kvs_attn.w_attn__fault, kva_f_face = dut.kvs_attn.w_attn_face__result_fault,
         kva_f_svc = dut.kvs_attn.w_attn_face__service_fault, kva_f_rl = dut.kvs_attn.w_attn_root__local_fault,
         kva_f_ri = dut.kvs_attn.w_attn_root__io_fault, kva_f_cal = dut.kvs_attn.w_attn_cal__fault,
         kva_f_fin = dut.pvfin.fault, kva_f_pw0 = `KVA_PW0_F, kva_f_pw1 = `KVA_PW1_F, kva_f_hub = dut.ahub.hf;
    wire [KVA_NSTK-1:0] kva_f_stk = `KVA_STK_F;
    wire [9:0] kva_f_unit = dut.kvs_attn.w_afr__unit_fault;
    wire [5:0] kva_ev = {dut.kvs_attn.w_attn_face__result_valid === 1'b1, dut.kvs_attn.fin[0] === 1'b1,
                         dut.kvs_attn.w_attn_root__start_pv === 1'b1, dut.kvs_attn.w_attn_root__start_qk === 1'b1,
                         dut.kvs_attn.attn__run === 1'b1, dut.kvs_attn.attn__issue === 1'b1};
    reg [5:0] kva_ev_q = 0;
    integer kva_evc [0:5][0:KMAX-1]; integer kva_evn [0:5]; integer kva_flast [0:KMAX-1];
    initial begin for (int e = 0; e < 6; e++) begin kva_evn[e] = 0; for (int k = 0; k < KMAX; k++) kva_evc[e][k] = -1; end
        for (int k = 0; k < KMAX; k++) kva_flast[k] = -1; end
    integer kva_ff = -1, kva_fe = -1, kva_fv = -1, kva_fs = -1;
    always @(negedge ck) if (trace_on) begin : evs
        integer e;
        for (e = 0; e < 6; e = e + 1) if (kva_ev[e] && !kva_ev_q[e] && kva_evn[e] < KMAX) begin
            kva_evc[e][kva_evn[e]] = cyc; kva_evn[e] = kva_evn[e] + 1;
            if (e == 4) $display("KVA_FIN step %0d beat0 at kvs_attn.fin: cyc %0d root age %0d", kva_evn[e] - 1, cyc, dut.kvs_attn.w_attn_root__age);
        end
        if (kva_ev[5] && kva_evn[5] > 0) kva_flast[kva_evn[5] - 1] = cyc;
        kva_ev_q <= kva_ev;
        if (kva_fe < 0 && |kva_ectl_f) begin kva_fe = cyc;
            for (kva_i = 0; kva_i < KVA_NG; kva_i = kva_i + 1) if (kva_ectl_f[kva_i])
                $display("KVA_FAULT ECTL issuer of %0s cyc %0d (rel run0 %0d)", kva_gname(kva_i), cyc, cyc - kva_A[0]); end
        if (kva_fv < 0 && |kva_vport_f) begin kva_fv = cyc;
            for (kva_i = 0; kva_i < KVA_NV; kva_i = kva_i + 1) if (kva_vport_f[kva_i])
                $display("KVA_FAULT V port %0s cyc %0d (rel run0 %0d)", kva_vname(kva_i), cyc, cyc - kva_A[0]); end
`ifdef KVA_PARTIAL
        if (kva_fs < 0 && (|kva_f_stk || |kva_ectl_f || |kva_vport_f)) begin kva_fs = cyc;
            $display("KVA_FAULT_STACK first cyc %0d step %0d strips %b ECTL %h Vport %h", cyc, kva_cur(cyc, 0), kva_f_stk, kva_ectl_f, kva_vport_f); end
`endif
        if (kva_ff < 0 && (kva_f_prog || kva_f_face || kva_f_svc || kva_f_rl || kva_f_ri || kva_f_cal || kva_f_fin || kva_f_pw0 ||
                           kva_f_pw1 || kva_f_hub || |kva_f_stk || |kva_ectl_f || |kva_vport_f)) begin
            kva_ff = cyc;
            $display("KVA_FAULT first cyc %0d step %0d rel run %0d root age %0d: programme %0d (ctl local %0d record %0d codec cause %b slot %0d) face result %0d service %0d | root local %0d io %0d | cal %0d | pvfin %0d pvw0 %0d pvw1 %0d hub %0d strips %b ECTL %h Vport %h unit %b",
                cyc, kva_cur(cyc, 0), (kva_cur(cyc, 0) < 0) ? 0 : cyc - kva_A[kva_cur(cyc, 0)], dut.kvs_attn.w_attn_root__age, kva_f_prog,
                dut.kvs_attn.u_attn.ctl.local_fault, dut.kvs_attn.u_attn.ctl.record_fault, dut.kvs_attn.u_attn.ctl.codec.fault_cause,
                dut.kvs_attn.u_attn.ctl.slot_fault, kva_f_face, kva_f_svc, kva_f_rl, kva_f_ri, kva_f_cal, kva_f_fin, kva_f_pw0,
                kva_f_pw1, kva_f_hub, kva_f_stk, kva_ectl_f, kva_vport_f, kva_f_unit);
        end
    end
    task automatic slice_programme(); begin : prog
        integer k, ok, all, dc, a;
        for (k = 0; k < kva_n; k = k + 1) kva_A[k] = cyc + 400 + kva_rel[k] - kva_rel[0];
        kva_go = 1;
        for (k = 0; k < kva_n; k = k + 1) $display("KVA_RUN_AT step %0d cyc %0d", k, kva_A[k]);
        while (cyc < kva_A[kva_n - 1] + kva_txfirst + 400 && kva_nst < kva_n) @(negedge ck);
        repeat (40) @(negedge ck);
        all = 1;
        for (k = 0; k < kva_n; k = k + 1) begin
            a = kva_A[k];
            $display("KVA_STEP %0d user %0d layer %0d epoch %04h row %0d | issue %0d run %0d start_qk %0d start_pv %0d | K req %0d..%0d (%0d) | V req %0d..%0d (%0d) | pvfin beat0 %0d | face RESULT %0d..%0d | d2d RESULT beat0 %0d beat31 %0d STATUS %0d | seq request %0d",
                k, kva_u[k], kva_l[k], kva_ep[k], kva_row(kva_u[k], kva_l[k]), kva_evc[0][k] - a, kva_evc[1][k] - a, kva_evc[2][k] - a,
                kva_evc[3][k] - a, kva_k0[k] - a, kva_klast[k] - a, kva_nk[k], kva_v0[k] - a, kva_vlast[k] - a, kva_nv[k],
                kva_evc[4][k] - a, kva_evc[5][k] - a, kva_flast[k] - a, kva_r0[k] - a, kva_r31[k] - a, kva_st[k] - a, kva_seqreq[k] - a);
            if (kva_evc[0][k] >= 0 && kva_r31[k] >= 0)
                $display("KVA_DIE_ATTN_CYCLES step %0d user %0d issue->last RESULT word at the d2d face %0d (run->last %0d)", k, kva_u[k],
                         kva_r31[k] - kva_evc[0][k], kva_r31[k] - kva_A[k]);
            for (int s = 0; s < KVA_NSTK; s++)
                $display("KVA_STACK step %0d user %0d layer %0d stack %0s | K req %0d..%0d | V req %0d..%0d | partial ap %0d..%0d | Vport out %0d..%0d",
                    k, kva_u[k], kva_l[k], kva_sname(s), kva_sk0[k][s] - a, kva_skl[k][s] - a, kva_sv0[k][s] - a, kva_svl[k][s] - a,
                    kva_sa0[k][s] - a, kva_sal[k][s] - a, kva_so0[k][s] - a, kva_sol[k][s] - a);
            ok = (kva_words[k] == 512 && kva_derr[k] == 0 && kva_st[k] >= 0);
            if (!ok) all = 0;
            $display("KVA_STEP_RESULT %0d user %0d exact %0d words %0d data_errors %0d status %0d", k, kva_u[k], ok, kva_words[k],
                     kva_derr[k], kva_st[k] >= 0);
        end
`ifdef KVA_PARTIAL
        // per-stack vehicle: the absent stacks' partials are undriven -> RESULT / shared-unit faults are not judged
        if (kva_rowerr != 0) smoke_err("K request row != the row of the step whose window holds it");
        if (kva_fs >= 0) smoke_err("stack fault (own ECTL / V port / strip)");
        for (k = 0; k < kva_n; k = k + 1) for (int s = 0; s < KVA_NSTK; s++)
            `ifdef KVA_QK_ONLY
            if (kva_sk0[k][s] < 0 || kva_sa0[k][s] < 0) smoke_err("QK strip produced no K request or partial in a step");
        $display("KVA_QK_ONLY: PV pairs outside cut; no PV completion or RESULT claim");
`else
            if (kva_sk0[k][s] < 0 || kva_sv0[k][s] < 0 || kva_sa0[k][s] < 0) smoke_err("a stack produced no K / V request or partial in a step");
`endif
        $display("KVA_PARTIAL stacks %0d: RESULT exactness not judged (absent stacks undriven)", KVA_NSTK);
`else
        if (!all) smoke_err("a step's RESULT is not exact / complete");
        if (kva_rowerr != 0) smoke_err("K request row != the row of the step whose window holds it");
        if (kva_ff >= 0) smoke_err("attention fault");
`endif
        dc = 0; for (k = 0; k < kva_n; k = k + 1) dc = dc + kva_derr[k];
        $display("KVA_RESULT exact %0d steps %0d data_errors %0d row_errors %0d hdr_errors %0d records %0d first_fault %0d seq_kst %h",
            (all && kva_rowerr == 0 && kva_ff < 0 && kva_hdrerr == 0), kva_n, dc, kva_rowerr, kva_hdrerr, kva_nrec,
            (kva_ff < 0) ? -1 : kva_ff - kva_A[0], `KVA_KST);
    end endtask
