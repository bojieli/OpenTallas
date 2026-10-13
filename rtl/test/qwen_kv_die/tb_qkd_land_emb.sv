`timescale 1ns/1ps
// el1013-qwen-kvstrips 2026-10-13: exact bench of the chained embedding strip (qkd_land_emb + the 32 qkd_land_pc
// leaves of a strip in the die's permuted slot order) against the MONOLITHIC engine ot_qfd_emb_strip (the closed
// reference: direct ports to the 32 pseudo-channels).  Both sides get the same link words (boot writes, BOOT_END,
// fetches with and without the scale) under their own credits, and their own copy of the same behavioural static
// ports (SQD 4 credits a PC, in-order, random latency, data = f(pc, bank, column, row) or the boot-written sector,
// single-bit-corrected flags on some beats).  The transmitted link words must be the same sequence, word for word.
// PASS line "PASS qkd_land_emb ..."; MUT 1 / 2 = the engine's own mutants (wrong row / wrong scale lane), PM 2 = a PC
// leaf answers a POP with its newest beat: all must FAIL.
module emb_side #(parameter integer CHAIN = 0, MUT = 0, PM = 0, ST = 1, NB = 24, NF = 60) (input wire ck, input wire rst_n);
    // ---------------- link driver ----------------
    reg         i_v = 0; reg [522:0] i_d = 0; wire i_cr;
    wire        o_v; wire [522:0] o_d; reg o_cr = 0;
    reg [522:0] words [$];
    reg [522:0] outw [$];
    int icred = 4, opend = 0;
    reg [31:0] rnd = 32'h0badcafe;
    wire fault;
    always @(posedge ck) begin
        rnd = {rnd[30:0], rnd[31] ^ rnd[21] ^ rnd[1] ^ rnd[0]};
        if (i_cr) icred++;
        i_v <= 1'b0;
        if (rst_n && words.size() != 0 && icred > 0 && rnd[2:0] != 0) begin i_v <= 1'b1; i_d <= words.pop_front(); icred--; end
        o_cr <= 1'b0;
        if (o_v) begin outw.push_back(o_d); opend++; t_last = cyc; end
        if (opend > 0 && rnd[6:5] != 0) begin o_cr <= 1'b1; opend--; end
    end
    // ---------------- 32 behavioural static ports ----------------
    wire [31:0]  p_sv, p_we, p_wv;
    wire [4:0]   p_bank [0:31], p_col [0:31];
    wire [18:0]  p_row [0:31];
    wire [255:0] p_wd [0:31];
    reg  [31:0]  p_scr = 0, p_ev = 0;
    reg  [257:0] p_ed [0:31];
    reg  [255:0] mem [int];
    typedef struct { bit we; int key; reg [255:0] d; } cmd_t;
    cmd_t  cq [0:31][$];
    int    rdue [0:31][$]; reg [257:0] rdat [0:31][$];
    int    clog [0:31][$];                     // every command a PC got: {we, key}
    int    wait_n [0:31];
    longint cyc = 0, n_rd = 0, n_wr = 0, n_ce = 0, t_last = 0;
    function automatic [255:0] dflt(input integer key);
        integer k;
        begin for (k = 0; k < 8; k++) dflt[32*k +: 32] = (32'h9e3779b9 * (key + 11)) ^ (32'h85ebca6b * (k + 1)); end
    endfunction
    reg [31:0] prn = 32'h600dbeef;
    initial for (int p = 0; p < 32; p++) wait_n[p] = 0;
    always @(posedge ck) begin
        cyc++;
        p_scr <= 0; p_ev <= 0;
        for (int p = 0; p < 32; p++) begin
            prn = {prn[30:0], prn[31] ^ prn[21] ^ prn[1] ^ prn[0]};
            if (p_sv[p]) begin
                automatic cmd_t c;
                c.we = p_we[p]; c.key = (p << 26) | (int'(p_row[p] & 19'hff) << 10) | (int'(p_bank[p]) << 5) | int'(p_col[p]); c.d = p_wd[p];
                if (p_we[p] != p_wv[p]) $display("MISMATCH static command write flags pc %0d", p);
                c.key = c.key ^ (int'(p_row[p]) << 12);
                cq[p].push_back(c); clog[p].push_back(c.key ^ (c.we ? 32'h4000_0000 : 0));
            end
            if (wait_n[p] > 0) wait_n[p]--;
            else if (cq[p].size() != 0) begin
                automatic cmd_t c = cq[p].pop_front();
                p_scr[p] <= 1'b1; wait_n[p] = 1 + prn[1:0];
                if (c.we) begin mem[c.key] = c.d; n_wr++; end
                else begin
                    automatic reg [255:0] d = mem.exists(c.key) ? mem[c.key] : dflt(c.key);
                    automatic bit ce = (c.key % 7) == 3;
                    rdue[p].push_back(cyc + 6 + (c.key % 5)); rdat[p].push_back({1'b0, ce, d}); n_rd++; if (ce) n_ce++;
                end
            end
            if (rdue[p].size() != 0 && rdue[p][0] <= cyc) begin
                p_ev[p] <= 1'b1; p_ed[p] <= rdat[p].pop_front(); void'(rdue[p].pop_front());
            end
        end
    end
    // ---------------- the engine ----------------
    generate if (CHAIN == 0) begin : g_mono
        wire [31:0] s_m, w_m; wire s_we; wire [4:0] s_bank, s_col; wire [18:0] s_row; wire [255:0] w_d;
        wire [32*258-1:0] e_d;
        for (genvar p = 0; p < 32; p++) begin : pp
            assign p_sv[p] = s_m[p]; assign p_we[p] = s_we; assign p_wv[p] = w_m[p]; assign p_bank[p] = s_bank;
            assign p_col[p] = s_col; assign p_row[p] = s_row; assign p_wd[p] = w_d; assign e_d[258*p +: 258] = p_ed[p];
        end
        // PFD 8: with 4 tokens queued a PC that holds the scale of several of them keeps up to 8 beats; the monolith's
        // default PFD 4 overruns (fault code bit 2) under this bench's transmit back-pressure
        ot_qfd_emb_strip #(.STK(ST), .MUT(0), .PFD(8)) u (.clk(ck), .rst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_cr(i_cr), .o_v(o_v),
            .o_d(o_d), .o_cr(o_cr), .s_m(s_m), .s_we(s_we), .s_bank(s_bank), .s_col(s_col), .s_row(s_row), .s_cr(p_scr),
            .w_m(w_m), .w_d(w_d), .e_v(p_ev), .e_d(e_d), .fault(fault), .fault_code(), .ce_cnt(), .ue_info());
    end else begin : g_chain
        // chain position k = 0 is the leaf under the engine (strip slot 31); slot s hosts logical PC {s % 4, P[s / 4]}
        wire [297:0] dn [0:32];
        wire [261:0] up [0:32];
        wire [31:0]  cr [0:32];
        wire [32:0]  fc;
        wire [529:0] emr; wire mf;
        assign up[32] = 262'd0; assign cr[32] = 32'd0; assign fc[32] = 1'b0;
        qkd_land_emb #(.MUT(MUT)) u (.ck(ck), .rst_n(rst_n), .st(2'(ST)), .emf({o_cr, 5'd0, i_d, i_v}), .emr(emr),
            .dno(dn[0]), .upi(up[0]), .cri(cr[0]), .fi(fc[0]), .gfi(1'b0), .mf(mf));
        assign o_v = emr[0]; assign o_d = emr[523:1]; assign i_cr = emr[529]; assign fault = mf;
        for (genvar k = 0; k < 32; k++) begin : lf
            localparam integer SL = 31 - k;
            localparam integer GP = (SL / 4 == 0) ? 4 : (SL / 4 == 1) ? 5 : (SL / 4 == 2) ? 0 : (SL / 4 == 3) ? 1 :
                                    (SL / 4 == 4) ? 2 : (SL / 4 == 5) ? 3 : (SL / 4 == 6) ? 6 : 7;
            localparam integer LP = 8 * (SL % 4) + GP;
            wire [287:0] es; wire [260:0] er = {1'b0, p_scr[LP], p_ed[LP], p_ev[LP]};
            qkd_land_pc #(.MUT(LP == 9 ? PM : 0)) u (.ck(ck), .rst_n(rst_n), .lpc(5'(LP)), .li(282'd0), .lp(), .cf(1'b0), .gw(), .gc(1'b0),
                .es(es), .er(er), .dni(dn[k]), .dno(dn[k+1]), .upi(up[k+1]), .upo(up[k]), .cri(cr[k+1]), .cro(cr[k]),
                .fi(fc[k+1]), .fo(fc[k]));
            assign p_sv[LP] = es[0]; assign p_wd[LP] = es[256:1]; assign p_row[LP] = es[275:257]; assign p_col[LP] = es[280:276];
            assign p_bank[LP] = es[285:281]; assign p_we[LP] = es[286]; assign p_wv[LP] = es[287];
        end
    end endgenerate
    // ---------------- stimulus: the same word list on both sides ----------------
    localparam integer VOCAB = 151936;
    initial begin : stim
        automatic reg [31:0] r = 32'h51ed270b;
        automatic reg [522:0] w;
        for (int k = 0; k < NB; k++) begin
            automatic int t, e;
            r = {r[30:0], r[31] ^ r[21] ^ r[1] ^ r[0]};
            t = r % VOCAB; e = t * 128 + (ST << 5) + (r[20:16] % 32);         // a code sector of this stack
            w = 0; w[522] = 1'b1; w[521:520] = 2'd1; w[24:0] = 25'(e);
            for (int b = 0; b < 8; b++) w[25 + 32*b +: 32] = r ^ (32'h9e3779b9 * (b + k + 1));
            words.push_back(w);
        end
        w = 0; w[522] = 1'b1; w[521:520] = 2'd2; words.push_back(w);            // BOOT_END -> STATUS
        for (int k = 0; k < NF; k++) begin
            automatic int t;
            r = {r[30:0], r[31] ^ r[21] ^ r[1] ^ r[0]};
            t = r % VOCAB;
            if (k % 3 == 0) t = (t & ~(3 << 9)) | (ST << 9);                    // this stack holds the scale
            if (t >= VOCAB) t = t - 4096;
            w = 0; w[522] = 1'b1; w[521:520] = 2'd0; w[515:512] = 4'(k); w[17:0] = 18'(t);
            words.push_back(w);
        end
    end
endmodule

module tb_qkd_land_emb;
    parameter integer MUT = 0, PM = 0;
    reg ck = 0; always #0.416667 ck = ~ck;
    reg rst_n = 0;
    emb_side #(.CHAIN(0)) gold (.ck(ck), .rst_n(rst_n));
    emb_side #(.CHAIN(1), .MUT(MUT), .PM(PM)) dut (.ck(ck), .rst_n(rst_n));
    integer n_err = 0, n = 0, n_scale = 0, n_stat = 0;
    initial begin
        repeat (6) @(negedge ck); rst_n = 1;
        wait (gold.words.size() == 0 && dut.words.size() == 0);
        repeat (200) @(negedge ck);
        wait (gold.outw.size() == dut.outw.size() || $time > 3000000);
        repeat (4000) @(negedge ck);
        if (gold.outw.size() != dut.outw.size()) begin
            $display("MISMATCH word count: monolith %0d, chain %0d", gold.outw.size(), dut.outw.size()); n_err++;
        end
        n = (gold.outw.size() < dut.outw.size()) ? gold.outw.size() : dut.outw.size();
        for (int k = 0; k < n; k++) begin
            if (gold.outw[k] !== dut.outw[k]) begin
                if (n_err < 8) begin
                    automatic reg [522:0] x = gold.outw[k] ^ dut.outw[k];
                    automatic int lo = -1, hi = -1;
                    for (int i = 0; i < 523; i++) if (x[i]) begin if (lo < 0) lo = i; hi = i; end
                    $display("MISMATCH link word %0d: monolith kind %0d seq %0d, chain kind %0d seq %0d; differing bits %0d..%0d", k,
                             gold.outw[k][521:520], gold.outw[k][515:512], dut.outw[k][521:520], dut.outw[k][515:512], lo, hi);
                end
                n_err++;
            end
            if (gold.outw[k][521:520] == 2'd1) n_scale++;
            if (gold.outw[k][521:520] == 2'd2) n_stat++;
        end
        for (int p = 0; p < 32; p++) begin
            if (gold.clog[p].size() != dut.clog[p].size()) begin
                if (n_err < 8) $display("MISMATCH pc %0d got %0d static commands from the chain, %0d from the monolith", p, dut.clog[p].size(), gold.clog[p].size());
                n_err++;
            end else for (int k = 0; k < gold.clog[p].size(); k++) if (gold.clog[p][k] != dut.clog[p][k]) begin
                if (n_err < 8) $display("MISMATCH pc %0d static command %0d differs", p, k);
                n_err++;
            end
        end
        if (gold.fault || dut.fault) begin $display("MISMATCH fault monolith %0d chain %0d", gold.fault, dut.fault); n_err++; end
        if (n < 60 * 16 + 1 || n_scale < 10 || n_stat != 1 || gold.n_wr != 24 || dut.n_wr != 24 || gold.n_ce < 20) begin
            $display("MISMATCH coverage floor: words %0d scale %0d status %0d writes %0d / %0d ce %0d", n, n_scale, n_stat, gold.n_wr, dut.n_wr, gold.n_ce); n_err++;
        end
        if (n_err == 0)
            $display("PASS qkd_land_emb: %0d link words identical to ot_qfd_emb_strip (%0d scale, %0d status), %0d boot writes, %0d static reads (%0d corrected); last word at cycle %0d (chain) vs %0d (monolith) for 60 fetches",
                     n, n_scale, n_stat, dut.n_wr, dut.n_rd, dut.n_ce, dut.t_last, gold.t_last);
        else $display("FAIL qkd_land_emb mut=%0d pm=%0d: %0d mismatches", MUT, PM, n_err);
        $finish;
    end
    initial begin #12000000; $display("FAIL qkd_land_emb mut=%0d pm=%0d: watchdog (monolith %0d words, chain %0d words)", MUT, PM, gold.outw.size(), dut.outw.size()); $finish; end
endmodule
