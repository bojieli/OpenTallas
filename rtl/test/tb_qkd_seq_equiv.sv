`timescale 1ns/1ps
// Qwen ROM TP8 track B 2026-10-13: the qkd_seq CLUSTER (wires-only parent + 9 hardened leaves,
// rtl/physical/ot_qwen_kv_centre_slots.sv) against the FLAT merged-die sequencer (ot_qkvd_kv_seq_merged), cycle for
// cycle on every output bit, under credit-true random traffic on every bundle:
//   layers launched by the kvd descriptor, 8 KVN (random order) + 32 Q x3 words per layer in a random interleaving
//   under the 40 x3 credits, a hub model (64 RES beats per start), a VM returning RES credits late, four landing write
//   queues returning row credits with their own delays (the credit join; per-copy outstanding rows are checked against
//   the 4 row credits), decode steps from the host (d_start {token, pos, gen}) against a ROM-sequencer model (s_done
//   per stage after a random time, {token, logit} at the head stage; stage order, token / position and the reported
//   result are checked), host program / descriptor writes (checked on both program copies), and at the end one step
//   per stepper fault kind (sequencer, core, ROM, vocabulary, start while busy) and a landing-merge fault.
// COVERAGE REFUSAL: the run passes only if every bundle carried traffic and every data bit of every output bundle was
// seen at 0 and at 1 while valid (minimum counts below); a run that is too short is a FAIL, not a pass (+NL=<layers>).
// OT_QKD_SEQ_MUT: the parent's wiring mutant.  FMUT (parameter): a control mutant in the flat side (4: credit join OR).
module tb_qkd_seq_equiv;
    parameter integer FMUT = 0;
    localparam integer W = 528;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    integer NL, cyc, seed;
    // ---- stimulus ----
    reg          x3_v;  reg [10:0] x3_tag;  reg [511:0] x3_d;
    reg [55:0]   sd;
    reg [43:0]   kvd;
    reg          ar_cr, hf;
    reg [181:0]  hc, hc1, hc2;
    reg [519:0]  ar;
    reg [3:0]    kcr, af, mf;
    // ---- flat ----
    wire         f_x3cr, f_arv, f_hs, f_fault;
    wire [518:0] f_ard;  wire [186:0] f_ds;  wire [74:0] f_pw;  wire [92:0] f_tk;
    wire [4*540-1:0] f_aq;  wire [4*1047-1:0] f_kvn;  wire [4*33-1:0] f_kc;  wire [8:0] f_fc;
    wire frr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_frr (.clk(clk), .rst_n_in(rst_n), .rst_n(frr));
    ot_qkvd_kv_seq_merged #(.MUT(FMUT)) u_flat (.clk(clk), .rst_n(frr), .x3_v(x3_v), .x3_tag(x3_tag), .x3_d(x3_d), .x3_cr(f_x3cr),
        .sd(sd), .kvd(kvd), .ar_v(f_arv), .ar_d(f_ard), .ar_cr(ar_cr), .ds(f_ds), .pw(f_pw),
        .aq(f_aq), .kvn(f_kvn), .kvn_cr(kcr), .kc(f_kc), .af(af), .mf(mf), .hs(f_hs), .a_out_valid(ar[519]),
        .a_out_g(ar[518]), .a_out_beat(ar[517:512]), .a_out_data(ar[511:0]), .a_hub_fault(hf), .hc(hc), .tk(f_tk),
        .fault(f_fault), .fault_cause(f_fc));
    // ---- cluster ----
    wire         c_x3cr, c_hs;
    wire [519:0] c_tar;  wire [186:0] c_tds;  wire [92:0] c_tk;  wire [74:0] c_tpw;  wire [9:0] c_kst;
    wire [4*540-1:0] c_aq;  wire [4*1047-1:0] c_kvn;  wire [4*33-1:0] c_kc;
    qkd_seq u_cl (.ck(clk), .rst_n(rst_n), .r_x3_d({x3_v, x3_tag, x3_d}), .r_x3_cr(c_x3cr), .r_sd(sd),
        .r_kvd(kvd), .t_ar_d(c_tar), .t_ar_cr(ar_cr), .t_ds(c_tds), .t_pw(c_tpw),
        .aq_WS(c_aq[0 +: 540]), .aq_WN(c_aq[540 +: 540]), .aq_ES(c_aq[1080 +: 540]), .aq_EN(c_aq[1620 +: 540]),
        .kvn_WS_d(c_kvn[0 +: 1047]), .kvn_WN_d(c_kvn[1047 +: 1047]), .kvn_ES_d(c_kvn[2094 +: 1047]), .kvn_EN_d(c_kvn[3141 +: 1047]),
        .kvn_WS_cr(kcr[0]), .kvn_WN_cr(kcr[1]), .kvn_ES_cr(kcr[2]), .kvn_EN_cr(kcr[3]),
        .kc_WS(c_kc[0 +: 33]), .kc_WN(c_kc[33 +: 33]), .kc_ES(c_kc[66 +: 33]), .kc_EN(c_kc[99 +: 33]),
        .af_WS(af[0]), .af_WN(af[1]), .af_ES(af[2]), .af_EN(af[3]), .mf_WS(mf[0]), .mf_WN(mf[1]), .mf_ES(mf[2]), .mf_EN(mf[3]),
        .ar(ar), .hf(hf), .hs(c_hs), .hc(hc), .tk(c_tk), .kst(c_kst));
    // ---- compare: every output, every cycle ----
    integer nmis = 0, ncmp = 0;
    reg [255:0] first_bad;
    task bad(input [255:0] what); begin if (nmis == 0) begin first_bad = what; $display("MISMATCH %0s at cycle %0d", what, cyc); end nmis = nmis + 1; end endtask
    always @(negedge clk) if (rst_n && cyc > 12) begin
        ncmp = ncmp + 1;
        if (c_x3cr !== f_x3cr) bad("r_x3_cr");
        if (c_tar !== {f_arv, f_ard}) bad("t_ar");
        if (c_tds !== f_ds) bad("t_ds");
        if (c_tpw !== f_pw) bad("t_pw");
        if (c_aq !== f_aq) bad("aq");
        if (c_kvn !== f_kvn) bad("kvn");
        if (c_kc !== f_kc) bad("kc");
        if (c_hs !== f_hs) bad("hs");
        if (c_tk !== f_tk) bad("tk");
        if (c_kst !== {f_fault, f_fc}) bad("kst");
    end
    // ---- coverage ----
    integer n_layer = 0, n_kvdl = 0, n_q = 0, n_kvn = 0, n_res = 0, n_hst = 0, n_pw = 0, n_dw = 0, n_step = 0, n_fstep = 0, n_kc = 0, n_x3cr = 0,
            n_join_wait = 0, n_flt = 0, n_prot = 0, n_sprot = 0, n_drain_wait = 0;
    reg [539:0] aq1 [0:3], aq0 [0:3];   reg [1046:0] kv1 [0:3], kv0 [0:3];   reg [32:0] kc1 [0:3], kc0 [0:3];
    reg [518:0] ar1, ar0;  reg [186:0] ds1, ds0;  reg [92:0] tk1, tk0;  reg [73:0] pw1, pw0;  reg [3:0] codes;
    integer k;
    initial begin
        for (k = 0; k < 4; k = k + 1) begin aq1[k] = 0; aq0[k] = 0; kv1[k] = 0; kv0[k] = 0; kc1[k] = 0; kc0[k] = 0; end
        ar1 = 0; ar0 = 0; ds1 = 0; ds0 = 0; tk1 = 0; tk0 = 0; pw1 = 0; pw0 = 0; codes = 0;
    end
    integer out_rows [0:3];
    always @(negedge clk) if (rst_n && cyc > 12) begin
        for (k = 0; k < 4; k = k + 1) begin
            if (c_aq[540*k + 539]) begin aq1[k][539:519] = aq1[k][539:519] | c_aq[540*k + 519 +: 21]; aq0[k][539:519] = aq0[k][539:519] | ~c_aq[540*k + 519 +: 21]; end
            if (c_aq[540*k + 518]) begin aq1[k][518:0] = aq1[k][518:0] | c_aq[540*k +: 519]; aq0[k][518:0] = aq0[k][518:0] | ~c_aq[540*k +: 519]; end
            if (c_kvn[1047*k + 1046]) begin kv1[k] = kv1[k] | c_kvn[1047*k +: 1047]; kv0[k] = kv0[k] | ~c_kvn[1047*k +: 1047]; end
            if (c_kc[33*k + 32]) begin kc1[k] = kc1[k] | c_kc[33*k +: 33]; kc0[k] = kc0[k] | ~c_kc[33*k +: 33]; end
        end
        if (c_tar[519]) begin ar1 = ar1 | c_tar[518:0]; ar0 = ar0 | ~c_tar[518:0]; n_res = n_res + 1; end
        ds1 = ds1 | c_tds; ds0 = ds0 | ~c_tds; tk1 = tk1 | c_tk; tk0 = tk0 | ~c_tk;
        if (c_tds[42]) n_hst = n_hst + 1;
        if (c_tds[186]) n_dw = n_dw + 1;
        if (c_tpw[74])  begin pw1 = pw1 | c_tpw[73:0]; pw0 = pw0 | ~c_tpw[73:0]; n_pw = n_pw + 1; end
        // the write relay: both program copies and the descriptor write are the host's words, two edges later
        if (f_pw !== hc2[113:39] || f_ds[118:44] !== hc2[113:39] || f_ds[186:119] !== hc2[181:114]) begin
            if (n_sprot == 0) $display("PROTOCOL write relay differs from the host word at cycle %0d", cyc); n_sprot = n_sprot + 1; end
        if (c_aq[518]) n_q = n_q + 1;
        if (c_kvn[1046]) n_kvn = n_kvn + 1;
        if (c_kc[32]) n_kc = n_kc + 1;
        if (c_x3cr) n_x3cr = n_x3cr + 1;
        if (c_kst[9]) n_flt = n_flt + 1;
        // protocol: a landing write queue never holds more than its 4 row credits (the credit join)
        for (k = 0; k < 4; k = k + 1) begin
            if (f_kvn[1047*k + 1046]) out_rows[k] = out_rows[k] + 1;
            if (kcr[k]) out_rows[k] = out_rows[k] - 1;
            if (out_rows[k] > 4) begin if (n_prot == 0) $display("PROTOCOL row credit overrun quadrant %0d at cycle %0d", k, cyc); n_prot = n_prot + 1; end
        end
    end
    // ---- traffic generators (credit-true) ----
    function integer rnd(input integer n); reg [31:0] u; begin u = $urandom(seed); rnd = u % n; end endfunction
    function [W-1:0] rw(input integer dummy); integer ii; begin for (ii = 0; ii < 17; ii = ii + 1) if (ii == 16) rw[527:512] = $urandom(seed); else rw[32*ii +: 32] = $urandom(seed); end endfunction
    integer xcred, lay_sent, lay_done, lay_x3, kv_left, q_left, q_next, launch_pending, vdesc_at, done_cyc, bt, flt_early;
    reg inj;
    reg [7:0]  kv_used;
    reg [13:0] cur_T;  reg [5:0] cur_L;
    integer hub_wait, hub_left, hub_gap, hub_q;      // hub model
    integer arc_pend, arc_tm;
    // decode steps: host model + ROM-sequencer model
    integer stp_busy, stp_stage, stp_wait, stp_kind, stp_fat, stp_n, stp_dn, stp_fk, stp_done_q, stp_bz;
    reg [17:0] stp_tok, stp_pos, stp_ntok;  reg [31:0] stp_nval;  reg [1:0] stp_gen;
    integer kc_pend [0:3], kc_tm [0:3];
    integer i, j, t;
    reg [W-1:0] w;
    initial begin
        if (!$value$plusargs("NL=%d", NL)) NL = 160;
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261013;
        for (k = 0; k < 4; k = k + 1) begin out_rows[k] = 0; kc_pend[k] = 0; kc_tm[k] = 0; end
        x3_v = 0; sd = 0; kvd = 0; ar_cr = 0; hc = 0; hc1 = 0; hc2 = 0; hf = 0; ar = 0; kcr = 0; af = 0; mf = 0;
        x3_tag = 0; x3_d = 0;
        stp_busy = 0; stp_stage = 0; stp_wait = -1; stp_kind = 0; stp_fat = 0; stp_n = 0; stp_dn = 0; stp_fk = 0; stp_done_q = 0; stp_bz = 0; stp_gen = 0;
        xcred = 40; lay_sent = 0; lay_done = 0; lay_x3 = 0; kv_left = 0; q_left = 0; q_next = 0;
        launch_pending = 0; vdesc_at = -1; done_cyc = 0; flt_early = 0; inj = 0; cur_T = 14'd4321; cur_L = 6'd35; hub_wait = -1; hub_left = 0; hub_gap = 0; hub_q = 0;
        arc_pend = 0; arc_tm = 0; cyc = 0;
        repeat (4) @(posedge clk);
        rst_n = 1;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        hc1 <= hc; hc2 <= hc1;
        x3_v <= 0; kvd <= 0; ar_cr <= 0; hc[38] <= 0; hc[113] <= 0; hc[181] <= 0; ar[519] <= 0; kcr <= 0; hf <= 0; af <= 0; mf <= inj ? 4'b0010 : 4'd0;
        if (rst_n && cyc >= 20) begin
            // credits back from the DUT (flat side; the cluster is compared against it)
            if (f_x3cr) xcred = xcred + 1;
            // a new layer: its launch (the kvd score descriptor) and its 40 x3 words, at most two layers outstanding
            // (no layer is launched while a step waits for its KV rows to drain: the ROM sequencer launches inside stages)
            if (lay_sent < NL && kv_left == 0 && q_left == 0 && !launch_pending && (lay_sent - lay_done) < 2 && cyc > done_cyc + 8 && rnd(8) == 0 &&
                !(stp_busy && stp_stage == 38)) begin
                // first half: the real schedule (layers 0..35 of one token, then the next position): no fault may rise;
                // second half: random layer / position (every bit toggles; the descriptor issuer's mismatch fault is real)
                if (lay_sent < NL / 2) begin if (cur_L == 6'd35) begin cur_L = 6'd0; cur_T = cur_T + 14'd1; end else cur_L = cur_L + 6'd1; end
                else begin cur_T = 1 + rnd(16383); cur_L = rnd(36); end
                if (lay_sent == NL / 2 && f_fault) flt_early = 1; kv_left = 8; q_left = 32; q_next = 0; kv_used = 0;
                launch_pending = 1;
                lay_sent = lay_sent + 1;
            end
            if (launch_pending == 1 && rnd(4) == 0) begin
                kvd <= {1'b1, 1'b1, 4'd0, cur_T - 14'd1, 12'd0, cur_L, 6'd0}; launch_pending = 0; vdesc_at = cyc + 2 + rnd(6); n_kvdl = n_kvdl + 1;
            end else if (cyc == vdesc_at) begin
                kvd <= {1'b1, 1'b0, 4'd0, cur_T - 14'd1, 11'd0, 1'b1, cur_L, 6'd0};      // the weighted-sum descriptor (V block)
            end
            // x3 words of the current layer: KVN tags in random order, Q beats in order, interleaved at random
            if ((kv_left > 0 || q_left > 0) && xcred > 0 && rnd(3) != 0) begin
                for (i = 0; i < 16; i = i + 1) x3_d[32*i +: 32] <= $urandom(seed);
                if (kv_left > 0 && (q_left == 0 || rnd(5) < 2)) begin
                    j = rnd(8); while (kv_used[j]) j = (j + 1) % 8;
                    kv_used[j] = 1'b1; kv_left = kv_left - 1;
                    x3_tag <= {3'b010, 5'd0, j[2:0]};
                end else begin
                    x3_tag <= {3'b001, 2'd0, q_next[5:0]}; q_next = q_next + 1; q_left = q_left - 1;
                end
                x3_v <= 1; xcred = xcred - 1;
            end
            // attention hub model: 64 RES beats per start
            if (f_hs) hub_q = hub_q + 1;
            if (hub_left == 0 && hub_q > 0 && hub_wait < 0) begin hub_wait = 20 + rnd(60); hub_q = hub_q - 1; end
            if (hub_wait > 0) hub_wait = hub_wait - 1;
            else if (hub_wait == 0) begin hub_left = 64; hub_wait = -1; end
            if (hub_left > 0) begin
                if (hub_gap > 0) hub_gap = hub_gap - 1;
                else begin
                    for (i = 0; i < 16; i = i + 1) ar[32*i +: 32] <= $urandom(seed);
                    bt = 64 - hub_left; ar[519:512] <= {1'b1, bt[0], bt[5:0]};
                    hub_left = hub_left - 1; hub_gap = (rnd(6) == 0) ? rnd(3) : 0;
                    if (hub_left == 0) begin lay_done = lay_done + 1; n_layer = n_layer + 1; done_cyc = cyc; end
                end
            end
            // the VM returns one RES credit per word, late (sometimes very late)
            if (f_arv) arc_pend = arc_pend + 1;
            if (arc_tm > 0) arc_tm = arc_tm - 1;
            else if (arc_pend > 0) begin ar_cr <= 1; arc_pend = arc_pend - 1; arc_tm = (rnd(50) == 0) ? 40 + rnd(200) : rnd(3); end
            // four landing write queues: one credit per posted row, each with its own delay
            for (k = 0; k < 4; k = k + 1) begin
                if (f_kvn[1047*k + 1046]) kc_pend[k] = kc_pend[k] + 1;
                if (kc_tm[k] > 0) kc_tm[k] = kc_tm[k] - 1;
                else if (kc_pend[k] > 0) begin kcr[k] <= 1; kc_pend[k] = kc_pend[k] - 1; kc_tm[k] = (k == 3 && rnd(8) == 0) ? 500 + rnd(300) : 5 + rnd(40 + 20 * k); end
            end
            if (kc_pend[0] != kc_pend[3]) n_join_wait = n_join_wait + 1;
            // host writes (posted): program write, descriptor write
            if (rnd(25) == 0) begin hc[113] <= 1; hc[112:103] <= $urandom(seed); hc[102:71] <= $urandom(seed); hc[70:39] <= $urandom(seed); end
            if (rnd(60) == 0) begin hc[181] <= 1; hc[180:178] <= $urandom(seed); hc[177:146] <= $urandom(seed); hc[145:114] <= $urandom(seed); end
            sd[53] <= (rnd(7) == 0); sd[54] <= (rnd(5) == 0);          // coll_busy, kv_write_flush (status levels)
            // ---- decode steps.  Kinds: 0 good | 1 sequencer fault | 2 core fault | 3 ROM fault | 4 token out of
            //      vocabulary | 5 a start while busy.  The fault kinds run once each after the layers are done. ----
            if (stp_done_q) begin
                // the done level of the flat side, with the step's generation: result check
                stp_done_q = 0; stp_busy = 0; stp_dn = stp_dn + 1; codes = codes | (4'd1 << f_tk[87:84]);
                if (stp_kind == 0) begin
                    n_step = n_step + 1;
                    if (f_tk[91:90] !== stp_gen || f_tk[88] !== 1'b0 || f_tk[89] !== 1'b1 || f_tk[81:64] !== stp_ntok || f_tk[63:32] !== stp_nval) begin
                        if (n_sprot == 0) $display("PROTOCOL step result wrong at cycle %0d", cyc); n_sprot = n_sprot + 1; end
                end else begin
                    n_fstep = n_fstep + 1;
                    if (f_tk[88] !== 1'b1 || f_tk[87:84] !== ((stp_kind == 4) ? 4'd5 : (stp_kind == 5) ? 4'd6 : stp_kind[3:0])) begin
                        if (n_sprot == 0) $display("PROTOCOL fault step kind %0d reported code %0d at cycle %0d", stp_kind, f_tk[87:84], cyc); n_sprot = n_sprot + 1; end
                end
            end
            if (stp_busy && f_tk[92] && stp_bz > 8) stp_done_q = 1;
            if (stp_busy) stp_bz = stp_bz + 1;
            if (stp_busy && stp_kind == 0 && stp_stage == 38 && stp_wait < 0 && !f_tk[92]) n_drain_wait = n_drain_wait + 1;
            if (!stp_busy && !stp_done_q && rnd(40) == 0 && (lay_done < NL ? 1 : stp_fk < 5)) begin
                stp_kind = (lay_done < NL) ? 0 : stp_fk + 1;
                if (lay_done >= NL) stp_fk = stp_fk + 1;
                stp_tok = $urandom(seed); stp_pos = $urandom(seed); stp_gen = stp_gen + 2'd1;
                hc[38] <= 1; hc[37:36] <= stp_gen; hc[35:18] <= stp_tok; hc[17:0] <= stp_pos;
                stp_busy = 1; stp_stage = 0; stp_wait = -1; stp_n = stp_n + 1; stp_bz = 0; stp_fat = 2 + rnd(30);
                sd[51] <= 0; sd[52] <= 0; sd[55] <= 0;
            end else if (stp_busy && stp_kind == 5 && stp_bz == 60) begin
                hc[38] <= 1;                                         // a second start while the step runs
            end
            // the ROM-sequencer model: h_start -> done low -> the stage's time -> done high (level)
            if (f_ds[42]) begin
                if (f_ds[41:36] !== stp_stage[5:0] || f_ds[35:18] !== stp_tok || f_ds[17:0] !== stp_pos) begin
                    if (n_sprot == 0) $display("PROTOCOL h_start stage %0d (expected %0d) / token / position wrong at cycle %0d", f_ds[41:36], stp_stage, cyc); n_sprot = n_sprot + 1; end
                sd[50] <= 0; stp_wait = 2 + rnd(12); stp_stage = stp_stage + 1;
            end else if (stp_wait > 0) begin
                stp_wait = stp_wait - 1;
                if (stp_kind >= 1 && stp_kind <= 3 && stp_stage == stp_fat && stp_wait == 1) sd[(stp_kind == 1) ? 51 : (stp_kind == 2) ? 52 : 55] <= 1;
            end else if (stp_wait == 0) begin
                stp_wait = -1; sd[50] <= 1;
                if (stp_stage == 38) begin
                    stp_ntok = (stp_kind == 4) ? 18'd151936 + rnd(1000) : rnd(151936); stp_nval = $urandom(seed);
                    sd[49:32] <= stp_ntok; sd[31:0] <= stp_nval;
                end else begin sd[49:32] <= $urandom(seed); sd[31:0] <= $urandom(seed); end
            end
        end
    end
    // ---- end of run ----
    integer miss;
    reg ok;
    initial begin : fin
        integer lim;
        @(posedge rst_n);
        lim = 0;
        while (!(lay_done >= NL && n_res >= 64 * NL && stp_fk >= 5 && !stp_busy) && lim < 4000000) begin @(posedge clk); lim = lim + 1; end
        repeat (400) @(posedge clk);
        // a landing-merge fault of quadrant WN must reach both fault words
        @(negedge clk); inj = 1; @(negedge clk); inj = 0;
        repeat (40) @(posedge clk);
        miss = 0;
        for (k = 0; k < 4; k = k + 1) begin
            if (&(aq1[k] | (540'd1 << 517)) !== 1'b1 || &(aq0[k] | (540'd1 << 539) | (540'd1 << 518)) !== 1'b1) miss = miss + 1;   // beat < 32; valid bits
            if (&kv1[k] !== 1'b1 || &(kv0[k] | (1047'd1 << 1046)) !== 1'b1) miss = miss + 1;
            // kc word {v, op 2, 10 zero, layer 6, T 14}: op bit 31 and the ten zero bits are constant by format
            if (&(kc1[k] | 33'h0_BFF0_0000) !== 1'b1 || &(kc0[k] | 33'h1_0000_0000) !== 1'b1) miss = miss + 1;
        end
        if (&ar1 !== 1'b1 || &ar0 !== 1'b1) miss = miss + 1;
        if (&ds1 !== 1'b1 || &ds0 !== 1'b1) miss = miss + 1;
        // tk: the cycle counter's bits 31:11 and fault-code bit 3 (codes are 1..6) are constant in a run of this length
        if (&(tk1 | {5'd0, 4'h8, 2'd0, 18'd0, 32'd0, 32'hFFFF_F800}) !== 1'b1 || &tk0 !== 1'b1) miss = miss + 1;
        if (codes !== 4'b0000 && codes[0] !== 1'b1) miss = miss + 1;
        if (&pw1 !== 1'b1 || &pw0 !== 1'b1) miss = miss + 1;
        ok = 1;
        if (n_layer < 100 || n_kvdl < 100 || n_q < 32 * 100 || n_kvn < 4 * 100 || n_res < 6400 || n_step < 20 || n_hst < 38 * 20 ||
            n_fstep != 5 || n_pw < 40 || n_dw < 20 || n_kc < 200 || n_x3cr < 4000 || n_join_wait < 1000 || n_drain_wait < 20 ||
            n_flt < 10 || flt_early || miss != 0) ok = 0;
        $display("COUNTS cycles=%0d compared=%0d layers=%0d kvd_launch=%0d q_words=%0d kvn_rows=%0d res=%0d steps=%0d h_starts=%0d fault_steps=%0d drain_wait_cycles=%0d pw=%0d dw=%0d kc=%0d x3_cr=%0d join_wait_cycles=%0d fault_cycles=%0d fault_in_real_schedule=%0d untoggled_bundles=%0d mismatches=%0d protocol=%0d step_protocol=%0d",
                 cyc, ncmp, n_layer, n_kvdl, n_q, n_kvn, n_res, n_step, n_hst, n_fstep, n_drain_wait, n_pw, n_dw, n_kc, n_x3cr, n_join_wait, n_flt, flt_early, miss, nmis, n_prot, n_sprot);
        if (nmis != 0) $display("FAIL kv_centre seq_equiv %0d mismatching cycles, first %0s", nmis, first_bad);
        else if (n_prot != 0) $display("FAIL kv_centre seq_equiv protocol: row credit overrun (%0d cycles)", n_prot);
        else if (n_sprot != 0) $display("FAIL kv_centre seq_equiv protocol: stepper / write relay (%0d events)", n_sprot);
        else if (!ok) $display("FAIL kv_centre seq_equiv coverage refused: traffic too thin (layers=%0d untoggled_bundles=%0d)", n_layer, miss);
        else $display("PASS kv_centre seq_equiv cluster == flat on %0d cycles, %0d layers, %0d decode steps + %0d fault steps, every output bit toggled", ncmp, n_layer, n_step, n_fstep);
        $finish;
    end
endmodule
