// QW-KVATTN2 10-19: the KV-die ATTENTION STEP of one decode layer on the kvs14p GEN netlist slice qwk_slice_attn
// (tools/qwen_layerbench/slice_cut.py: qkd_kvs_attn (programme + cal_gen + service root + result face + fault root),
// qkd_seq_static_s, 4 attention strips qkd_astk_strip_er_die + every expanded head leaf (frontq / lane8 / stin / stk /
// ktree / score4 / gather / sstage), 32 ECTL A + static K issuers qkd_ectl3_kiss_st, the hub qkd_ahub_static_dw, the PV
// wide pair qkd_pvw_die_t x2, 16 PV16 V ports qkd_pv16_vport, the final join qkd_pv_fin_s, and every die relay /
// landing / reset region between them, verbatim from the die netlist).
// Slice-edge neighbours, driven by this bench on the compiled static schedule (no ready, no credit, nothing waits):
//   kvs_ctl.o_attn  -> kvs_attn.i_ctl   go A-30 / issue A-8 / run A (the as-built layer programme's relative edges, as the
//                                       QXF vehicle K_REAL=3); authority epoch / token / stage / position T-1, ctx T
//   kvs_ctl.lp      -> seq.lp           lp_run at A-8, layer, ctx T
//   d2d_kv.srx / rx_payload -> kvs_attn the CMD record at programme age RX_CMD (2), Q beats 0..31 at ages 3..34
//                                       (record {5'd0, kind, layer, epoch, beat, data}: CMD kind 1 data {.., POS, 1},
//                                       Q kind 2 = the REAL q operand, 16 fp32 words a beat)
//   d2d_kv.att_tx_* -> kvs_attn         the RESULT slots (kind 3, beat b) at age TX_FIRST + b, STATUS (kind 4) at +33
//   d2d_kv.skw      -> seq              the 4 KVN words on the sequencer's compiled check edges (check only)
//   hroot_<s>.o_c<e> / o_kg -> ECTL     cfg = 4 e + stack (the sealed G-K1 boot values); kgo KVA_KGO edges before A
//   slg_<s>_<i> (32 static landing groups, NOT in the slice) = the KV STORE PATH (landing ring <- PC <- HBM): modelled
//                                       at the group pins by its RTL latency qkd_static_kv_landing_seg (request ->
//                                       response KVA_LG = 8 edges) returning the REAL history row: K row t = kv[t],
//                                       V row t = kv[T + t] (1024 b FP8 rows; tools/qwen_layerbench/kv_attn_vectors.py),
//                                       one response stream per group on both faces (krsp to the ECTL, rsp to the V port).
// Every event time below is at the CONSUMER pin; the bench drives the slice input S edges earlier, S = the die's relay
// stages of that bus (case_kv/relay_stages.json of kvs14p, the table RELAY_CHECK passed on).
// Checks: the 32 RESULT words x 16 at the d2d face bit-exact against gold.hex (the TP8 P.V reference the qualified
// service unit matches 16/16), STATUS = {done 1, ready 1}, no fault anywhere (programme / root / face / cal / pvfin / pvw /
// V ports / ECTL issuers / strips / hub); every first-fault cycle and cause is printed (KVA_FAULT lines).
// Measured (KVA_CYC lines): issue / run -> start_qk -> start_pv -> pvfin beat 0 -> RESULT beat 0 / 31 at the face pin and
// at the d2d face (slice output), the service root's own cycles counter.
// Plusargs: +VEC=<dir> (q.hex kv.hex gold.hex) +CTX=<T> +KVA_LAYER=<n> +KVA_LG=<8> +KVA_KGO=<200> +KVA_AGE0=<1> (pin
// cycle of programme age 0 after the run cycle) +KVA_KVN=<34> (KVN word 0 edges after the seq request pin) +KVA_HCKC
// (DIAGNOSTIC: the HBM-clock pins run on the core clock) +KVA_MUT=n: 1 = CMD record one edge late, 2 = group slg_WS_5
// returns one edge late (KVA_LG + 1), 3 = every K row of group slg_WS_0 replaced by row t^1 (data), 4 = RESULT slots one
// edge late.
`include "kva_grp_map.svh"
    localparam integer S_CTL = 6, S_LP = 1, S_SRX = 11, S_RXP = 11, S_TXS = 9, S_SKW = 4;   // die relay stages (kvs14p)
    localparam [15:0] KVA_EP = 16'd9;
    localparam [17:0] KVA_TOK = 18'd50994;
    reg [1023:0] kva_kv [0:16383];
    reg [31:0] kva_q [0:511], kva_gold [0:511];
    string kva_vec;
    integer kva_T = 8192, kva_A = -1000000, kva_layer = 0, kva_lg = 8, kva_kgo = 200, kva_age0 = 1, kva_kvn = 34;
    integer kva_mut = 0, kva_hckc = 0, kva_txfirst = 1750, kva_rxcmd = 2;
    // ---- HBM clock pins: free-running 976.6 MHz (1024 ps, the die's HBM clock) or (DIAGNOSTIC) the core clock ----
    reg kva_hfree = 0; always #0.512 kva_hfree = ~kva_hfree;
    always @* hck = (kva_hckc != 0) ? ck : kva_hfree;
    initial begin
        if (!$value$plusargs("VEC=%s", kva_vec)) $fatal(1, "+VEC required");
        void'($value$plusargs("KVA_LAYER=%d", kva_layer)); void'($value$plusargs("KVA_LG=%d", kva_lg));
        void'($value$plusargs("KVA_KGO=%d", kva_kgo)); void'($value$plusargs("KVA_AGE0=%d", kva_age0));
        void'($value$plusargs("KVA_KVN=%d", kva_kvn)); void'($value$plusargs("KVA_MUT=%d", kva_mut));
        if ($test$plusargs("KVA_HCKC")) kva_hckc = 1;
        if (!$value$plusargs("CTX=%d", kva_T)) kva_T = 8192;
        $readmemh({kva_vec, "/q.hex"}, kva_q); $readmemh({kva_vec, "/gold.hex"}, kva_gold);
        $readmemh({kva_vec, "/kv.hex"}, kva_kv, 0, 2 * kva_T - 1);
        $display("KVA_CFG vec %0s T %0d layer %0d LG %0d KGO %0d AGE0 %0d KVN %0d MUT %0d HCKC %0d", kva_vec, kva_T, kva_layer,
                 kva_lg, kva_kgo, kva_age0, kva_kvn, kva_mut, kva_hckc);
        kva_ectl_cfg();
        kva_kg({6'(kva_layer), KVA_EP, 1'b0});
    end
    // ---- the compiled edge-relative events at the consumer pins (p = consumer pin cycle) ----
    function automatic [76:0] kva_ctl(input integer p);
        reg go, iss, run; begin
            go = (p == kva_A - 30); iss = (p == kva_A - 8); run = (p == kva_A);
            kva_ctl = {KVA_TOK, go, 6'(kva_layer + 1), 18'(kva_T - 1), KVA_EP, 14'(kva_T), run, iss, 1'b1, 1'b1};
        end endfunction
    function automatic [20:0] kva_lp(input integer p);
        kva_lp = {14'(kva_T), 6'(kva_layer), p == kva_A - 8}; endfunction
    // programme age of a pin cycle: age 0 = the cycle kva_age0 after the run cycle
    function automatic integer kva_age(input integer p); kva_age = p - (kva_A + kva_age0); endfunction
    function automatic [547:0] kva_rec(input integer p);   // the RX record at the attention programme's rx pin
        integer g, b, j; reg [511:0] d; begin
            g = kva_age(p) - ((kva_mut == 1) ? 1 : 0); kva_rec = 548'd0;
            if (g == kva_rxcmd) kva_rec = {5'd0, 4'd1, 6'(kva_layer), KVA_EP, 5'd0, {493'd0, 5'd0, 13'(kva_T - 1), 1'b1}};
            else if (g > kva_rxcmd && g <= kva_rxcmd + 32) begin
                b = g - kva_rxcmd - 1;
                for (j = 0; j < 16; j = j + 1) d[32*j +: 32] = kva_q[16*b + j];
                kva_rec = {5'd0, 4'd2, 6'(kva_layer), KVA_EP, 5'(b), d};
            end
        end endfunction
    function automatic [9:0] kva_txs(input integer p);      // {beat 5, kind 4, slot}
        integer g; begin
            g = kva_age(p) - kva_txfirst - ((kva_mut == 4) ? 1 : 0); kva_txs = 10'd0;
            if (g >= 0 && g < 32) kva_txs = {5'(g), 4'd3, 1'b1};
            else if (g == 33) kva_txs = {5'd0, 4'd4, 1'b1};
        end endfunction
    // ---- the KVN words on the sequencer's check edges (seq core: a = 0 two edges after its request pin; a 32..35) ----
    integer kva_seqreq = -1;
    always @(negedge ck) if (kva_seqreq < 0 && dut.seq.prg_req_v === 1'b1) kva_seqreq = cyc;
    function automatic [11:0] kva_skw(input integer p);
        integer j; begin j = p - (kva_seqreq + kva_kvn); kva_skw = 12'd0;
            if (kva_seqreq >= 0 && j >= 0 && j < 4) kva_skw = {3'b010, 5'd0, 1'(j / 2), 1'b0, 1'(j % 2), 1'b1};
        end endfunction
    // ---- slice-edge drive: every input S edges before its consumer-pin event ----
    always @(negedge ck) begin
        drv_i_n_ks_kvs_ctl__o_attn = (kva_A > -1000000) ? kva_ctl(cyc + S_CTL) : 77'd0;
        drv_i_n_ks_seq_lp = (kva_A > -1000000) ? kva_lp(cyc + S_LP) : 21'd0;
        begin : rx
            reg [547:0] r; r = (kva_A > -1000000) ? kva_rec(cyc + S_RXP) : 548'd0;
            drv_i_n_ks_d2d_kv__rx_payload = r;
            r = (kva_A > -1000000) ? kva_rec(cyc + S_SRX) : 548'd0;
            drv_i_n_seqst_rx = {512'd0, 5'd0, 4'd0, |r[542:539]};
        end
        begin : tx
            reg [9:0] t; t = (kva_A > -1000000) ? kva_txs(cyc + S_TXS) : 10'd0;
            drv_i_n_ks_d2d_kv__att_tx_slot = t[0]; drv_i_n_ks_d2d_kv__att_tx_kind = t[4:1]; drv_i_n_ks_d2d_kv__att_tx_beat = t[9:5];
        end
        drv_i_n_seqst_kw = kva_skw(cyc + S_SKW);
        if (kva_A > -1000000 && cyc == kva_A - kva_kgo) kva_kg({6'(kva_layer), KVA_EP, 1'b1});
        else kva_kg({6'(kva_layer), KVA_EP, 1'b0});
    end
    // ---- the KV store path at the 32 landing-group pins: request sampled at edge c -> response visible KVA_LG edges later --
    reg [37:0] kva_pk [0:31][0:63]; reg [14:0] kva_pv [0:31][0:63];
    integer kva_g, kva_i, kva_nk = 0, kva_nv = 0, kva_k0 = -1, kva_v0 = -1, kva_klast = -1, kva_vlast = -1, kva_coll = 0;
    initial for (kva_g = 0; kva_g < 32; kva_g = kva_g + 1) for (kva_i = 0; kva_i < 64; kva_i = kva_i + 1) begin
        kva_pk[kva_g][kva_i] = 0; kva_pv[kva_g][kva_i] = 0; end
    always @(negedge ck) begin : grp_model
        integer g, d, t, lg; reg [37:0] ek; reg [14:0] ev; reg [1023:0] row;
        for (g = 0; g < 32; g = g + 1) begin
            d = cyc % 64; ek = kva_pk[g][d]; ev = kva_pv[g][d]; kva_pk[g][d] = 0; kva_pv[g][d] = 0;
            kva_krsp[g] = 1062'd0; kva_rsp[g] = 1056'd0;
            if (ek[0] && ev[0]) begin kva_coll = kva_coll + 1; smoke_err("landing group: K and V response in one edge"); end
            if (ek[0]) begin
                t = ek[14:1]; row = kva_kv[t];
                if (kva_mut == 3 && g == 0) row = kva_kv[t ^ 1];
                kva_krsp[g] = {ek[37:32], ek[31:16], 1'b0, 14'(t), row, 1'b1};
                kva_rsp[g] = {row, ek[31:16], 14'(t), 1'b0, 1'b1};
            end else if (ev[0]) begin
                t = ev[14:1]; row = kva_kv[kva_T + t];
                kva_krsp[g] = {6'(kva_layer), KVA_EP, 1'b1, 14'(t), row, 1'b1};
                kva_rsp[g] = {row, KVA_EP, 14'(t), 1'b1, 1'b1};
            end
            lg = kva_lg + ((kva_mut == 2 && g == 5) ? 1 : 0);
            if (kva_kreq[g][0] === 1'b1) begin kva_pk[g][(cyc + lg) % 64] = kva_kreq[g]; kva_nk = kva_nk + 1;
                if (kva_k0 < 0) kva_k0 = cyc; kva_klast = cyc; end
            if (kva_vreq[g][0] === 1'b1) begin kva_pv[g][(cyc + lg) % 64] = kva_vreq[g]; kva_nv = kva_nv + 1;
                if (kva_v0 < 0) kva_v0 = cyc; kva_vlast = cyc; end
        end
    end
    // ---- the d2d face (slice output): RESULT beats vs gold, STATUS ----
    wire [547:0] kva_tp = o_n_ks_kvs_attn__attn__tx_payload__r9__pinfix1;
    wire kva_tv = o_n_ks_kvs_attn__attn__tx_valid__r6__beq5;
    integer kva_words = 0, kva_derr = 0, kva_r0 = -1, kva_r31 = -1, kva_st = -1, kva_nrec = 0;
    always @(negedge ck) if (kva_tv === 1'b1) begin : face
        integer j, b; kva_nrec = kva_nrec + 1;
        if (kva_tp[542:539] == 4'd3) begin
            b = kva_tp[516:512]; if (b == 0) kva_r0 = cyc; if (b == 31) kva_r31 = cyc;
            if (kva_tp[532:517] != KVA_EP || kva_tp[538:533] != 6'(kva_layer)) begin kva_derr = kva_derr + 1; smoke_err("RESULT epoch / layer"); end
            for (j = 0; j < 16; j = j + 1) begin
                if (kva_tp[32*j +: 32] !== kva_gold[16*b + j]) begin
                    if (kva_derr < 8) $display("KVA_MISMATCH word %0d got %08h want %08h", 16*b + j, kva_tp[32*j +: 32], kva_gold[16*b + j]);
                    kva_derr = kva_derr + 1;
                end
                kva_words = kva_words + 1;
            end
        end else if (kva_tp[542:539] == 4'd4) begin
            kva_st = cyc;
            if (kva_tp[511:0] !== {507'd0, 5'b01001}) begin smoke_err("STATUS word != {done 1, ready 1}"); $display("KVA_STATUS %h", kva_tp[31:0]); end
        end else begin smoke_err("unexpected record kind at the d2d face"); $display("KVA_REC kind %0d", kva_tp[542:539]); end
    end
    // ---- fault probes (first cycle + cause) and event cycles ----
    wire kva_f_prog = dut.kvs_attn.w_attn__fault, kva_f_face = dut.kvs_attn.w_attn_face__result_fault,
         kva_f_svc = dut.kvs_attn.w_attn_face__service_fault, kva_f_rl = dut.kvs_attn.w_attn_root__local_fault,
         kva_f_ri = dut.kvs_attn.w_attn_root__io_fault, kva_f_cal = dut.kvs_attn.w_attn_cal__fault,
         kva_f_fin = dut.pvfin.fault, kva_f_pw0 = dut.pvw_0.fault, kva_f_pw1 = dut.pvw_1.fault, kva_f_hub = dut.ahub.hf;
    wire [3:0] kva_f_stk = {dut.astk_EN.af, dut.astk_ES.af, dut.astk_WN.af, dut.astk_WS.af};
    wire [9:0] kva_f_unit = dut.kvs_attn.w_afr__unit_fault;
    integer kva_ff = -1, kva_sqk = -1, kva_spv = -1, kva_fin0 = -1, kva_iss = -1, kva_run = -1, kva_fres0 = -1, kva_fres31 = -1;
    integer kva_fe = -1, kva_fv = -1;
    always @(negedge ck) if (trace_on) begin
        if (dut.kvs_attn.attn__issue === 1'b1 && kva_iss < 0) kva_iss = cyc;
        if (dut.kvs_attn.attn__run === 1'b1 && kva_run < 0) kva_run = cyc;
        if (dut.kvs_attn.w_attn_root__start_qk === 1'b1 && kva_sqk < 0) kva_sqk = cyc;
        if (dut.kvs_attn.w_attn_root__start_pv === 1'b1 && kva_spv < 0) kva_spv = cyc;
        if (dut.kvs_attn.fin[0] === 1'b1 && kva_fin0 < 0) begin kva_fin0 = cyc;
            $display("KVA_FIN beat0 at kvs_attn.fin: cyc %0d root age %0d (cal PV %0d P0 %0d P1 %0d R %0d) face RESULT_AGE (F_DLY 1) expects PV + max(P0,P1,R) + 17",
                cyc, dut.kvs_attn.w_attn_root__age, dut.kvs_attn.w_attn_root__cal[127:112], dut.kvs_attn.w_attn_root__cal[143:128],
                dut.kvs_attn.w_attn_root__cal[159:144], dut.kvs_attn.w_attn_root__cal[175:160]); end
        if (dut.kvs_attn.w_attn_face__result_valid === 1'b1) begin
            if (kva_fres0 < 0) kva_fres0 = cyc; kva_fres31 = cyc; end
        if (kva_fe < 0 && |kva_ectl_f) begin kva_fe = cyc;
            for (kva_i = 0; kva_i < 32; kva_i = kva_i + 1) if (kva_ectl_f[kva_i])
                $display("KVA_FAULT ECTL issuer of %0s cyc %0d (rel run %0d)", kva_gname(kva_i), cyc, cyc - kva_A); end
        if (kva_fv < 0 && |kva_vport_f) begin kva_fv = cyc;
            for (kva_i = 0; kva_i < 16; kva_i = kva_i + 1) if (kva_vport_f[kva_i])
                $display("KVA_FAULT V port %0s cyc %0d (rel run %0d)", kva_vname(kva_i), cyc, cyc - kva_A); end
        if (kva_ff < 0 && (kva_f_prog || kva_f_face || kva_f_svc || kva_f_rl || kva_f_ri || kva_f_cal || kva_f_fin || kva_f_pw0 ||
                           kva_f_pw1 || kva_f_hub || |kva_f_stk || |kva_ectl_f || |kva_vport_f)) begin
            kva_ff = cyc;
            $display("KVA_FAULT first cyc %0d rel run %0d root age %0d: programme %0d (ctl local %0d record %0d codec cause %b slot %0d) face result %0d service %0d | root local %0d io %0d | cal %0d | pvfin %0d pvw0 %0d pvw1 %0d hub %0d strips %b ECTL %h Vport %h unit %b",
                cyc, cyc - kva_A, dut.kvs_attn.w_attn_root__age, kva_f_prog, dut.kvs_attn.u_attn.ctl.local_fault,
                dut.kvs_attn.u_attn.ctl.record_fault, dut.kvs_attn.u_attn.ctl.codec.fault_cause, dut.kvs_attn.u_attn.ctl.slot_fault,
                kva_f_face, kva_f_svc, kva_f_rl, kva_f_ri, kva_f_cal, kva_f_fin, kva_f_pw0, kva_f_pw1, kva_f_hub, kva_f_stk,
                kva_ectl_f, kva_vport_f, kva_f_unit);
        end
    end
    task automatic slice_programme(); begin
        kva_A = cyc + 400;                                   // the run edge at the kvs_attn pin
        $display("KVA_RUN_AT cyc %0d", kva_A);
        while (cyc < kva_A + kva_txfirst + 400 && !(kva_st >= 0)) @(negedge ck);
        repeat (40) @(negedge ck);
        $display("KVA_CYC issue %0d run %0d start_qk %0d start_pv %0d | first K req %0d last %0d (%0d) | first V req %0d last %0d (%0d) | pvfin beat0 at fin pin %0d | face RESULT beat0 %0d beat31 %0d | d2d face RESULT beat0 %0d beat31 %0d STATUS %0d | seq request %0d | root cycles %0d",
            kva_iss - kva_A, kva_run - kva_A, kva_sqk - kva_A, kva_spv - kva_A, kva_k0 - kva_A, kva_klast - kva_A, kva_nk,
            kva_v0 - kva_A, kva_vlast - kva_A, kva_nv, kva_fin0 - kva_A, kva_fres0 - kva_A, kva_fres31 - kva_A,
            kva_r0 - kva_A, kva_r31 - kva_A, kva_st - kva_A, kva_seqreq - kva_A, dut.kvs_attn.w_attn_root__cycles);
        if (kva_iss >= 0 && kva_r31 >= 0)
            $display("KVA_DIE_ATTN_CYCLES issue->last RESULT word at the d2d face %0d (run->last %0d)", kva_r31 - kva_iss, kva_r31 - kva_run);
        if (kva_words != 512) smoke_err("RESULT words at the d2d face != 512");
        if (kva_derr != 0) smoke_err("RESULT data != gold");
        if (kva_st < 0) smoke_err("no STATUS record");
        if (kva_ff >= 0) smoke_err("attention fault");
        $display("KVA_RESULT exact %0d words %0d data_errors %0d records %0d first_fault %0d seq_kst %h",
            (kva_words == 512 && kva_derr == 0 && kva_ff < 0 && kva_st >= 0), kva_words, kva_derr, kva_nrec,
            (kva_ff < 0) ? -1 : kva_ff - kva_A, o_n_kst__r2__pinfix1);
    end endtask
