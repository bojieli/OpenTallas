`timescale 1ns/1ps
// Qwen ROM TP8 track B 2026-10-13: the qkd_seq CLUSTER (wires-only parent + 9 hardened leaves,
// rtl/physical/ot_qwen_kv_centre_slots.sv) against the FLAT merged-die sequencer (ot_qkvd_kv_seq_merged), cycle for
// cycle on every output bit, under credit-true random traffic on every bundle:
//   layers launched by the kvd descriptor or a dc ATTN word, 8 KVN (random order) + 32 Q x3 words per layer in a random
//   interleaving under the 40 x3 credits, a hub model (64 RES beats per start), a VM returning RES credits late, four
//   landing write queues returning row credits with their own delays (the credit join; per-copy outstanding rows are
//   checked against the 4 row credits), host words with program writes, token / CSR words, a fault at the end.
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
    reg          dc_v;  reg [W-1:0] dc_d;
    reg [43:0]   kvd;
    reg          ar_cr, dh_cr, tk_cr, hc_v, hf;
    reg [W-1:0]  hc_d;
    reg [519:0]  ar;
    reg [3:0]    kcr, af, mf;
    // ---- flat ----
    wire         f_x3cr, f_dccr, f_arv, f_dhv, f_pwv, f_rflt, f_hs, f_hccr, f_tokv, f_fault;
    wire [518:0] f_ard;  wire [W-1:0] f_dhd, f_tokd;  wire [9:0] f_pwa;  wire [63:0] f_pwd;  wire [7:0] f_rfc;
    wire [4*540-1:0] f_aq;  wire [4*1047-1:0] f_kvn;  wire [4*33-1:0] f_kc;  wire [8:0] f_fc;
    wire frr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_frr (.clk(clk), .rst_n_in(rst_n), .rst_n(frr));
    ot_qkvd_kv_seq_merged #(.MUT(FMUT)) u_flat (.clk(clk), .rst_n(frr), .x3_v(x3_v), .x3_tag(x3_tag), .x3_d(x3_d), .x3_cr(f_x3cr),
        .dc_v(dc_v), .dc_d(dc_d), .dc_cr(f_dccr), .kvd(kvd), .ar_v(f_arv), .ar_d(f_ard), .ar_cr(ar_cr), .dh_v(f_dhv),
        .dh_d(f_dhd), .dh_cr(dh_cr), .pw_v(f_pwv), .pw_addr(f_pwa), .pw_data(f_pwd), .rflt(f_rflt), .rflt_cause(f_rfc),
        .aq(f_aq), .kvn(f_kvn), .kvn_cr(kcr), .kc(f_kc), .af(af), .mf(mf), .hs(f_hs), .a_out_valid(ar[519]),
        .a_out_g(ar[518]), .a_out_beat(ar[517:512]), .a_out_data(ar[511:0]), .a_hub_fault(hf), .hc_v(hc_v), .hc_d(hc_d),
        .hc_cr(f_hccr), .tok_v(f_tokv), .tok_d(f_tokd), .tok_cr(tk_cr), .fault(f_fault), .fault_cause(f_fc));
    // ---- cluster ----
    wire         c_x3cr, c_dccr, c_hs, c_hccr;
    wire [519:0] c_tar;  wire [528:0] c_tds, c_tk;  wire [74:0] c_tpw;  wire [8:0] c_tflt;  wire [9:0] c_kst;
    wire [4*540-1:0] c_aq;  wire [4*1047-1:0] c_kvn;  wire [4*33-1:0] c_kc;
    qkd_seq u_cl (.ck(clk), .rst_n(rst_n), .r_x3({x3_v, x3_tag, x3_d}), .r_x3_cr(c_x3cr), .r_sd({dc_v, dc_d}), .r_sd_cr(c_dccr),
        .r_kvd(kvd), .t_ar(c_tar), .t_ar_cr(ar_cr), .t_ds(c_tds), .t_ds_cr(dh_cr), .t_pw(c_tpw), .t_flt(c_tflt),
        .aq_WS(c_aq[0 +: 540]), .aq_WN(c_aq[540 +: 540]), .aq_ES(c_aq[1080 +: 540]), .aq_EN(c_aq[1620 +: 540]),
        .kvn_WS(c_kvn[0 +: 1047]), .kvn_WN(c_kvn[1047 +: 1047]), .kvn_ES(c_kvn[2094 +: 1047]), .kvn_EN(c_kvn[3141 +: 1047]),
        .kvn_WS_cr(kcr[0]), .kvn_WN_cr(kcr[1]), .kvn_ES_cr(kcr[2]), .kvn_EN_cr(kcr[3]),
        .kc_WS(c_kc[0 +: 33]), .kc_WN(c_kc[33 +: 33]), .kc_ES(c_kc[66 +: 33]), .kc_EN(c_kc[99 +: 33]),
        .af_WS(af[0]), .af_WN(af[1]), .af_ES(af[2]), .af_EN(af[3]), .mf_WS(mf[0]), .mf_WN(mf[1]), .mf_ES(mf[2]), .mf_EN(mf[3]),
        .ar(ar), .hf(hf), .hs(c_hs), .hc({hc_v, hc_d}), .hc_cr(c_hccr), .tk(c_tk), .tk_cr(tk_cr), .kst(c_kst));
    // ---- compare: every output, every cycle ----
    integer nmis = 0, ncmp = 0;
    reg [255:0] first_bad;
    task bad(input [255:0] what); begin if (nmis == 0) begin first_bad = what; $display("MISMATCH %0s at cycle %0d", what, cyc); end nmis = nmis + 1; end endtask
    always @(negedge clk) if (rst_n && cyc > 12) begin
        ncmp = ncmp + 1;
        if (c_x3cr !== f_x3cr) bad("r_x3_cr");
        if (c_dccr !== f_dccr) bad("r_sd_cr");
        if (c_tar !== {f_arv, f_ard}) bad("t_ar");
        if (c_tds !== {f_dhv, f_dhd}) bad("t_ds");
        if (c_tpw !== {f_pwv, f_pwa, f_pwd}) bad("t_pw");
        if (c_tflt !== {f_rflt, f_rfc}) bad("t_flt");
        if (c_aq !== f_aq) bad("aq");
        if (c_kvn !== f_kvn) bad("kvn");
        if (c_kc !== f_kc) bad("kc");
        if (c_hs !== f_hs) bad("hs");
        if (c_hccr !== f_hccr) bad("hc_cr");
        if (c_tk !== {f_tokv, f_tokd}) bad("tk");
        if (c_kst !== {f_fault, f_fc}) bad("kst");
    end
    // ---- coverage ----
    integer n_layer = 0, n_kvdl = 0, n_dcl = 0, n_q = 0, n_kvn = 0, n_res = 0, n_dh = 0, n_pw = 0, n_tk = 0, n_kc = 0, n_x3cr = 0,
            n_join_wait = 0, n_flt = 0, n_prot = 0;
    reg [539:0] aq1 [0:3], aq0 [0:3];   reg [1046:0] kv1 [0:3], kv0 [0:3];   reg [32:0] kc1 [0:3], kc0 [0:3];
    reg [518:0] ar1, ar0;  reg [527:0] dh1, dh0, tk1, tk0;  reg [73:0] pw1, pw0;
    integer k;
    initial begin
        for (k = 0; k < 4; k = k + 1) begin aq1[k] = 0; aq0[k] = 0; kv1[k] = 0; kv0[k] = 0; kc1[k] = 0; kc0[k] = 0; end
        ar1 = 0; ar0 = 0; dh1 = 0; dh0 = 0; tk1 = 0; tk0 = 0; pw1 = 0; pw0 = 0;
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
        if (c_tds[528]) begin dh1 = dh1 | c_tds[527:0]; dh0 = dh0 | ~c_tds[527:0]; n_dh = n_dh + 1; end
        if (c_tk[528])  begin tk1 = tk1 | c_tk[527:0]; tk0 = tk0 | ~c_tk[527:0]; n_tk = n_tk + 1; end
        if (c_tpw[74])  begin pw1 = pw1 | c_tpw[73:0]; pw0 = pw0 | ~c_tpw[73:0]; n_pw = n_pw + 1; end
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
    integer xcred, dccred, hccred, lay_sent, lay_done, lay_x3, kv_left, q_left, q_next, launch_pending, vdesc_at, done_cyc, bt, flt_early;
    reg inj;
    reg [7:0]  kv_used;
    reg [13:0] cur_T;  reg [5:0] cur_L;
    integer hub_wait, hub_left, hub_gap, hub_q;      // hub model
    integer arc_pend, arc_tm, dhc_pend, dhc_tm, tkc_pend, tkc_tm;
    integer kc_pend [0:3], kc_tm [0:3];
    integer i, j, t;
    reg [W-1:0] w;
    initial begin
        if (!$value$plusargs("NL=%d", NL)) NL = 160;
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261013;
        for (k = 0; k < 4; k = k + 1) begin out_rows[k] = 0; kc_pend[k] = 0; kc_tm[k] = 0; end
        x3_v = 0; dc_v = 0; kvd = 0; ar_cr = 0; dh_cr = 0; tk_cr = 0; hc_v = 0; hf = 0; ar = 0; kcr = 0; af = 0; mf = 0;
        x3_tag = 0; x3_d = 0; dc_d = 0; hc_d = 0;
        xcred = 40; dccred = 4; hccred = 4; lay_sent = 0; lay_done = 0; lay_x3 = 0; kv_left = 0; q_left = 0; q_next = 0;
        launch_pending = 0; vdesc_at = -1; done_cyc = 0; flt_early = 0; inj = 0; cur_T = 14'd4321; cur_L = 6'd35; hub_wait = -1; hub_left = 0; hub_gap = 0; hub_q = 0;
        arc_pend = 0; arc_tm = 0; dhc_pend = 0; dhc_tm = 0; tkc_pend = 0; tkc_tm = 0; cyc = 0;
        repeat (4) @(posedge clk);
        rst_n = 1;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        x3_v <= 0; dc_v <= 0; kvd <= 0; ar_cr <= 0; dh_cr <= 0; tk_cr <= 0; hc_v <= 0; ar[519] <= 0; kcr <= 0; hf <= 0; af <= 0; mf <= inj ? 4'b0010 : 4'd0;
        if (rst_n && cyc >= 20) begin
            // credits back from the DUT (flat side; the cluster is compared against it)
            if (f_x3cr) xcred = xcred + 1;
            if (f_dccr) dccred = dccred + 1;
            if (f_hccr) hccred = hccred + 1;
            // a new layer: its launch (kvd or dc ATTN) and its 40 x3 words, at most two layers outstanding
            if (lay_sent < NL && kv_left == 0 && q_left == 0 && !launch_pending && (lay_sent - lay_done) < 2 && cyc > done_cyc + 8 && rnd(8) == 0) begin
                // first half: the real schedule (layers 0..35 of one token, then the next position): no fault may rise;
                // second half: random layer / position (every bit toggles; the descriptor issuer's mismatch fault is real)
                if (lay_sent < NL / 2) begin if (cur_L == 6'd35) begin cur_L = 6'd0; cur_T = cur_T + 14'd1; end else cur_L = cur_L + 6'd1; end
                else begin cur_T = 1 + rnd(16383); cur_L = rnd(36); end
                if (lay_sent == NL / 2 && f_fault) flt_early = 1; kv_left = 8; q_left = 32; q_next = 0; kv_used = 0;
                launch_pending = 1 + rnd(2);            // 1: kvd descriptor, 2: dc ATTN word
                lay_sent = lay_sent + 1;
            end
            t = 0;                                       // dc slot used this cycle
            if (launch_pending == 1 && rnd(4) == 0) begin
                kvd <= {1'b1, 1'b1, 4'd0, cur_T - 14'd1, 12'd0, cur_L, 6'd0}; launch_pending = 0; vdesc_at = cyc + 2 + rnd(6); n_kvdl = n_kvdl + 1;
            end else if (launch_pending == 2 && dccred > 0 && rnd(4) == 0) begin
                w = rw(0);
                w[527:524] = 4'd1; w[13:0] = cur_T; w[21:16] = cur_L;
                dc_v <= 1; dc_d <= w; dccred = dccred - 1; launch_pending = 0; t = 1; n_dcl = n_dcl + 1;
            end else if (cyc == vdesc_at) begin
                kvd <= {1'b1, 1'b0, 4'd0, cur_T - 14'd1, 11'd0, 1'b1, cur_L, 6'd0};      // the weighted-sum descriptor (V block)
            end
            if (!t && dccred > 0 && rnd(40) == 0) begin  // TOKEN / CSR_RSP words (any op but ATTN)
                w = rw(0);
                if (w[527:524] == 4'd1) w[527:524] = 4'd2;
                dc_v <= 1; dc_d <= w; dccred = dccred - 1;
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
            if (f_dhv) dhc_pend = dhc_pend + 1;
            if (dhc_tm > 0) dhc_tm = dhc_tm - 1;
            else if (dhc_pend > 0) begin dh_cr <= 1; dhc_pend = dhc_pend - 1; dhc_tm = rnd(40); end
            if (f_tokv) tkc_pend = tkc_pend + 1;
            if (tkc_tm > 0) tkc_tm = tkc_tm - 1;
            else if (tkc_pend > 0) begin tk_cr <= 1; tkc_pend = tkc_pend - 1; tkc_tm = rnd(40); end
            // four landing write queues: one credit per posted row, each with its own delay
            for (k = 0; k < 4; k = k + 1) begin
                if (f_kvn[1047*k + 1046]) kc_pend[k] = kc_pend[k] + 1;
                if (kc_tm[k] > 0) kc_tm[k] = kc_tm[k] - 1;
                else if (kc_pend[k] > 0) begin kcr[k] <= 1; kc_pend[k] = kc_pend[k] - 1; kc_tm[k] = (k == 3 && rnd(8) == 0) ? 500 + rnd(300) : 5 + rnd(40 + 20 * k); end
            end
            if (kc_pend[0] != kc_pend[3]) n_join_wait = n_join_wait + 1;
            // host words (program writes: op 5)
            if (hccred > 0 && rnd(25) == 0) begin
                w = rw(0);
                if (rnd(3) == 0) w[527:524] = 4'd5;
                hc_v <= 1; hc_d <= w; hccred = hccred - 1;
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
        while (!(lay_done >= NL && n_res >= 64 * NL) && lim < 4000000) begin @(posedge clk); lim = lim + 1; end
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
        if (&dh1 !== 1'b1 || &dh0 !== 1'b1) miss = miss + 1;
        if (&tk1 !== 1'b1 || &tk0 !== 1'b1) miss = miss + 1;
        if (&pw1 !== 1'b1 || &pw0 !== 1'b1) miss = miss + 1;
        ok = 1;
        if (n_layer < 100 || n_kvdl < 30 || n_dcl < 30 || n_q < 32 * 100 || n_kvn < 4 * 100 || n_res < 6400 || n_dh < 100 ||
            n_pw < 40 || n_tk < 60 || n_kc < 200 || n_x3cr < 4000 || n_join_wait < 1000 || n_flt < 10 || flt_early || miss != 0) ok = 0;
        $display("COUNTS cycles=%0d compared=%0d layers=%0d kvd_launch=%0d dc_launch=%0d q_words=%0d kvn_rows=%0d res=%0d dh=%0d pw=%0d tok=%0d kc=%0d x3_cr=%0d join_wait_cycles=%0d fault_cycles=%0d fault_in_real_schedule=%0d untoggled_bundles=%0d mismatches=%0d protocol=%0d",
                 cyc, ncmp, n_layer, n_kvdl, n_dcl, n_q, n_kvn, n_res, n_dh, n_pw, n_tk, n_kc, n_x3cr, n_join_wait, n_flt, flt_early, miss, nmis, n_prot);
        if (nmis != 0) $display("FAIL kv_centre seq_equiv %0d mismatching cycles, first %0s", nmis, first_bad);
        else if (n_prot != 0) $display("FAIL kv_centre seq_equiv protocol: row credit overrun (%0d cycles)", n_prot);
        else if (!ok) $display("FAIL kv_centre seq_equiv coverage refused: traffic too thin (layers=%0d untoggled_bundles=%0d)", n_layer, miss);
        else $display("PASS kv_centre seq_equiv cluster == flat on %0d cycles, %0d layers, every output bit toggled", ncmp, n_layer);
        $finish;
    end
endmodule
