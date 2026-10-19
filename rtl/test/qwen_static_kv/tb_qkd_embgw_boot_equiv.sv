`timescale 1ns/1ps
// KVJ-C (a) 2026-10-17: the boot-only embedding gateway qkd_embgw_boot is cycle-for-cycle equal to qkd_embgw_splitboot
// with its SU face idle (r_ea = 0), on every output it keeps (emf_<q>, emf_<q>_cr, hb_cr, est).
//   phase R: random legal stimulus on both cells' shared inputs (hb words with random credit discipline, strip STATUS
//            words and credits at random, reset pulses every RLEN cycles) for NRAND cycles: any output differing = FAIL.
//   phase B: the 4-strip boot bench of tb_qkd_embgw_splitboot (ot_qfd_emb_strip x4 behind LD relays, per-PC models):
//            the boot cell drives the strips, the splitboot cell shadows the same inputs; emb_ready must rise with no
//            fault and every output must match.
// The splitboot cell's dropped outputs t_ecr / t_eq must stay 0 (they would be the removed face's only activity).
// Mutant: compile with -DOT_KVJ_EMBGW_MUT=5 (BOOT_WR to stack + 1) or =6 (BOOT_END does not clear emb_ready): FAIL.
// Prints "PASS kvjc embgw_boot ..." or "FAIL kvjc embgw_boot ...".
`ifndef OT_KVJ_EMBGW_MUT
`define OT_KVJ_EMBGW_MUT 0
`endif
module tb_qkd_embgw_boot_equiv;
    parameter integer NT    = 12;
    parameter integer LD    = 3;
    parameter integer NRAND = 60000;
    parameter integer RLEN  = 3000;
    localparam [24:0] E_SCALE = 25'd19447808;
    localparam integer NPC = 32;
    reg ck = 0, rst_n = 0;
    always #0.4165 ck = ~ck;
    integer cyc = 0;
    always @(posedge ck) cyc = cyc + 1;
    function automatic [255:0] gsec(input [24:0] e);
        reg [31:0] x; integer j;
        begin
            for (j = 0; j < 8; j = j + 1) begin
                x = {7'd0, e} * 32'h9E3779B1 + j * 32'h85EBCA6B + 32'h1234567;
                x = x ^ (x >> 15); x = x * 32'h2C1B3C6D; x = x ^ (x >> 12); x = x * 32'h297A2D39; x = x ^ (x >> 15);
                gsec[32*j +: 32] = x;
            end
        end
    endfunction
    function automatic [31:0] crc_sector(input [24:0] e, input [255:0] d);
        reg [287:0] m; reg [31:0] c; integer i;
        begin
            m = {d, 7'd0, e}; c = 32'hffffffff;
            for (i = 0; i < 288; i = i + 1) c = (c >> 1) ^ ((c[0] ^ m[i]) ? 32'hedb88320 : 32'h0);
            crc_sector = ~c;
        end
    endfunction
    // ---- shared inputs ----
    reg          phase_b = 1'b0;
    reg  [282:0] hb = 0;
    reg  [519:0] r_emr [0:3];
    reg  [3:0]   r_emr_cr = 0;
    wire [519:0] s_emr [0:3];
    wire [3:0]   s_emr_cr;
    wire [519:0] emr [0:3];
    wire [3:0]   emr_cr = phase_b ? s_emr_cr : r_emr_cr;
    genvar k, p;
    generate for (k = 0; k < 4; k = k + 1) begin : g_in
        assign emr[k] = phase_b ? s_emr[k] : r_emr[k];
    end endgenerate
    // ---- the two cells ----
    wire [287:0] nf [0:3], of [0:3];
    wire [3:0]   nf_cr, of_cr;
    wire         n_hbcr, o_hbcr, o_ecr;
    wire [12:0]  n_est, o_est;
    wire [512:0] o_eq;
    qkd_embgw_boot #(.MUT(`OT_KVJ_EMBGW_MUT)) dut (.ck(ck), .rst_n(rst_n),
        .emr_WS(emr[0]), .emr_WS_cr(emr_cr[0]), .emf_WS(nf[0]), .emf_WS_cr(nf_cr[0]),
        .emr_WN(emr[1]), .emr_WN_cr(emr_cr[1]), .emf_WN(nf[1]), .emf_WN_cr(nf_cr[1]),
        .emr_ES(emr[2]), .emr_ES_cr(emr_cr[2]), .emf_ES(nf[2]), .emf_ES_cr(nf_cr[2]),
        .emr_EN(emr[3]), .emr_EN_cr(emr_cr[3]), .emf_EN(nf[3]), .emf_EN_cr(nf_cr[3]),
        .hb(hb), .hb_cr(n_hbcr), .est(n_est));
    qkd_embgw_splitboot ref_ (.ck(ck), .rst_n(rst_n), .r_ea(26'd0), .t_ecr(o_ecr), .t_eq(o_eq),
        .emr_WS(emr[0]), .emr_WS_cr(emr_cr[0]), .emf_WS(of[0]), .emf_WS_cr(of_cr[0]),
        .emr_WN(emr[1]), .emr_WN_cr(emr_cr[1]), .emf_WN(of[1]), .emf_WN_cr(of_cr[1]),
        .emr_ES(emr[2]), .emr_ES_cr(emr_cr[2]), .emf_ES(of[2]), .emf_ES_cr(of_cr[2]),
        .emr_EN(emr[3]), .emr_EN_cr(emr_cr[3]), .emf_EN(of[3]), .emf_EN_cr(of_cr[3]),
        .hb(hb), .hb_cr(o_hbcr), .est(o_est));
    // ---- lock-step compare (emf data bits are don't-care while v = 0 in both: the registers hold the last word in
    //      both cells, compared too) ----
    integer mism = 0, cmp = 0, emf_words = 0, st_words = 0;
    integer q;
    always @(negedge ck) if (rst_n) begin
        cmp = cmp + 1;
        for (q = 0; q < 4; q = q + 1) begin
            if (nf[q] !== of[q] || nf_cr[q] !== of_cr[q]) begin
                mism = mism + 1;
                if (mism < 6) $display("MISMATCH cyc %0d emf[%0d] v %b/%b k %h/%h cr %b/%b", cyc, q, nf[q][0], of[q][0],
                                       nf[q][287:286], of[q][287:286], nf_cr[q], of_cr[q]);
            end
            if (nf[q][0]) emf_words = emf_words + 1;
        end
        if (n_hbcr !== o_hbcr || n_est !== o_est) begin
            mism = mism + 1;
            if (mism < 6) $display("MISMATCH cyc %0d hb_cr %b/%b est %h/%h", cyc, n_hbcr, o_hbcr, n_est, o_est);
        end
        if (o_ecr !== 1'b0 || o_eq[0] !== 1'b0) begin mism = mism + 1; $display("MISMATCH removed face active cyc %0d", cyc); end
    end
    // ---- phase B: four strips behind LD relay stages, driven by the boot cell ----
    wire [3:0] strip_fault;
    generate for (k = 0; k < 4; k = k + 1) begin : g_stk
        reg [288:0] dn [0:LD-1];
        reg [520:0] up [0:LD-1];
        integer j;
        wire        o_v, i_cr;
        wire [522:0] o_d;
        wire [287:0] f = dn[LD-1][287:0];
        initial for (j = 0; j < LD; j = j + 1) begin dn[j] = 0; up[j] = 0; end
        always @(posedge ck) begin
            dn[0] <= {nf_cr[k], nf[k]};
            up[0] <= {i_cr, o_d[521:520], o_d[519], o_d[515:512], o_d[511:0], o_v};
            for (j = 1; j < LD; j = j + 1) begin dn[j] <= dn[j-1]; up[j] <= up[j-1]; end
        end
        assign s_emr[k] = up[LD-1][519:0];
        assign s_emr_cr[k] = up[LD-1][520];
        wire [NPC-1:0] s_m, s_cr, w_m, e_rv; wire s_we; wire [4:0] s_bank, s_col; wire [18:0] s_row; wire [255:0] w_d;
        wire [NPC*258-1:0] e_rd;
        ot_qfd_emb_strip #(.STK(k)) u_strip (.clk(ck), .rst_n(rst_n & phase_b),
            .i_v(f[0] & phase_b), .i_d({1'b1, f[287:286], 1'b0, 3'b000, f[285:282], 231'd0, f[281:1]}), .i_cr(i_cr),
            .o_v(o_v), .o_d(o_d), .o_cr(dn[LD-1][288]),
            .s_m(s_m), .s_we(s_we), .s_bank(s_bank), .s_col(s_col), .s_row(s_row), .s_cr(s_cr), .w_m(w_m), .w_d(w_d),
            .e_v(e_rv), .e_d(e_rd), .fault(strip_fault[k]), .fault_code(), .ce_cnt(), .ue_info());
        for (p = 0; p < NPC; p = p + 1) begin : g_pc
            tb_emb_pc_model #(.DLY(7 + (p % 5))) u_pc (.clk(ck), .rst_n(rst_n & phase_b), .s_v(s_m[p]), .s_we(s_we),
                .s_key({s_bank, s_col, s_row}), .w_d(w_d), .s_cr(s_cr[p]), .e_v(e_rv[p]), .e_d(e_rd[p*258 +: 258]));
        end
    end endgenerate
    // ---- drivers ----
    integer seed = 20261017;
    integer errors = 0, i, j, c, hbc = 4, boot_n = 0, resets = 0, rfaults = 0, rready = 0;
    reg [31:0] csum = 0;
    reg [17:0] toks [0:NT-1];
    reg        scale_done [0:9495];
    always @(posedge ck) if (rst_n && phase_b && n_hbcr) hbc = hbc + 1;
    task automatic hb_send(input en, input [24:0] e, input [255:0] d);
        begin
            @(negedge ck); while (hbc == 0) @(negedge ck);
            hb = {d, e, en, 1'b1}; hbc = hbc - 1;
            @(negedge ck); hb[0] = 1'b0;
        end
    endtask
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261017;
        for (i = 0; i < 9496; i = i + 1) scale_done[i] = 1'b0;
        for (i = 0; i < 4; i = i + 1) r_emr[i] = 0;
        // ---- phase R ----
        repeat (4) @(negedge ck); rst_n = 1;
        for (c = 0; c < NRAND; c = c + 1) begin
            @(negedge ck);
            if (c % RLEN == RLEN - 1) begin
                if (o_est[1]) rfaults = rfaults + 1; if (o_est[0]) rready = rready + 1;
                rst_n = 0; resets = resets + 1; @(negedge ck); rst_n = 1;
            end
            // host words: mostly within the 4-word skid, sometimes over-run (both cells must latch cause[9] together)
            hb = {gsec(25'($random(seed))), 25'(($random(seed) & 1) ? E_SCALE + 25'($random(seed) & 16'h3fff) : 25'($random(seed))),
                  (($random(seed) & 15) == 0), (($random(seed) & 3) == 0)};
            // strip words: STATUS only (kind 2; no FETCH is ever sent, so CODE / SCALE cannot legally occur), random data
            for (i = 0; i < 4; i = i + 1) begin
                r_emr[i] = {2'd2, 1'b0, 4'($random(seed)), {16{$random(seed)}}, (($random(seed) & 7) == 0)};
                r_emr_cr[i] = (($random(seed) & 3) == 0);
            end
        end
        hb = 0; r_emr_cr = 0; for (i = 0; i < 4; i = i + 1) r_emr[i] = 0;
        $display("PHASE R cycles=%0d resets=%0d windows_faulted=%0d windows_ready=%0d mismatches=%0d", NRAND, resets, rfaults, rready, mism);
        // ---- phase B ----
        rst_n = 0; repeat (4) @(negedge ck); phase_b = 1; repeat (4) @(negedge ck); rst_n = 1; repeat (12) @(negedge ck);
        for (i = 0; i < NT; i = i + 1) toks[i] = (i == 0) ? 18'd0 : (i == 1) ? 18'd151935 : 18'(($random(seed) & 32'h7fffffff) % 151936);
        for (i = 0; i < NT; i = i + 1) begin
            for (j = 0; j < 128; j = j + 1) begin
                hb_send(1'b0, {toks[i], 7'd0} + 25'(j), gsec({toks[i], 7'd0} + 25'(j)));
                csum = csum + crc_sector({toks[i], 7'd0} + 25'(j), gsec({toks[i], 7'd0} + 25'(j))); boot_n = boot_n + 1;
            end
            if (!scale_done[toks[i] >> 4]) begin
                scale_done[toks[i] >> 4] = 1'b1;
                hb_send(1'b0, E_SCALE + 25'(toks[i] >> 4), gsec(E_SCALE + 25'(toks[i] >> 4)));
                csum = csum + crc_sector(E_SCALE + 25'(toks[i] >> 4), gsec(E_SCALE + 25'(toks[i] >> 4))); boot_n = boot_n + 1;
            end
        end
        hb_send(1'b1, 25'd0, {192'd0, csum, 32'(boot_n)});
        i = 0; while (!n_est[0] && !n_est[1] && i < 200000) begin @(negedge ck); i = i + 1; end
        $display("BOOT sectors=%0d emb_ready=%0d/%0d fault=%0d/%0d cause=%h/%h at cycle %0d", boot_n, n_est[0], o_est[0],
                 n_est[1], o_est[1], n_est[12:2], o_est[12:2], cyc);
        // a second load (BOOT_END clears emb_ready until the new check passes)
        hb_send(1'b1, 25'd0, {192'd0, csum, 32'(boot_n)});
        repeat (3) @(negedge ck);
        if (n_est[0]) begin errors = errors + 1; $display("FAIL emb_ready not cleared by a new BOOT_END"); end
        i = 0; while (!n_est[0] && !n_est[1] && i < 200000) begin @(negedge ck); i = i + 1; end
        repeat (100) @(negedge ck);
        if (!n_est[0] || n_est[1] || n_est[12:2] != 0) begin errors = errors + 1; $display("FAIL boot status %h", n_est); end
        if (|strip_fault) begin errors = errors + 1; $display("FAIL strip fault %b", strip_fault); end
        if (mism != 0) begin errors = errors + 1; $display("FAIL %0d lock-step mismatches", mism); end
        if (errors == 0)
            $display("PASS kvjc embgw_boot equal to splitboot(r_ea idle): random_cycles=%0d boot_sectors=%0d compared_cycles=%0d emf_words=%0d (LD %0d)",
                     NRAND, boot_n, cmp, emf_words, LD);
        else $display("FAIL kvjc embgw_boot errors=%0d mismatches=%0d", errors, mism);
        $finish;
    end
    initial begin #80000000; $display("FAIL kvjc embgw_boot timeout"); $finish; end
endmodule
