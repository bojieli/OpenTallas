`timescale 1ns/1ps
// HBM-NEXT-SM4 leaf bench (Verilator 5.050, fleet): the P-lane leaf hnx_rp4lp4_lf against P PRODUCTION d4g leaves
// (ot_hbm_accel_smh_leafh from rtl/hbm_accel/sm/ot_hbm_accel_smh.sv, the closed design's source) driven by an
// independent spec model of the lane fan-out / lane-select protocol.
//   (1) LANE: every cycle after warm, lane p's leaf word {gv, gf, gy, gt} == production leaf p's word, bit for bit
//       (same rows, its own x-slot store contents) -> the golden reduction order is kept per lane;
//   (2) STREAM: the published gather word == the slot-major merge of the production words (lane p at +1 + p*LSKEW),
//       cycle for cycle; a collision must be flagged (gf) exactly where the model has two lanes in one cycle;
//   (3) PASS needs >0 words from every lane, no collision, no mismatch.
// Stimulus = production protocol: interleaved IL = 8 row chunks (first / last / tag {row, 0, slot}), random FP8/FP4/BF16
// words, chunk K in [KMIN, KMAX] beats, column switches spaced, concurrent random x-write beats + lane-select beats.
// THR = 1: throughput shape (back-to-back block-dot chunks, K = KMIN, no gaps): reports the issue span and publish span.
// MUT (negative controls): 1 lane alias (lane P-1 takes lane 0's x), 2 lane-select ignored, 3 lane 2 publishes in lane
// 1's slot.  Each must FAIL ("LANE MISMATCH" / "STREAM MISMATCH").
module tb_hnx_rp4lp4_leaf;
    parameter integer P = 4, MUT = 0, LSKEW = 8, NCYC = 6000, KMIN = 4, KMAX = 12, THR = 0, NCHUNK = 64;
    localparam integer IL = 8, WARM = 40;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [25:0] st;
    reg [817:0] rl1;
    reg [2068:0] bk1;
    wire [49:0] g;
`ifdef HNX_XS4
    // lever (a): the leaf on the shared P-lane x store hnx_xs4
    hnx_rp4lp4_lfx #(.P(P), .LSKEW(LSKEW), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .st(st), .rl1(rl1), .bk1(bk1), .g(g));
`else
    hnx_rp4lp4_lf #(.P(P), .LSKEW(LSKEW), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .st(st), .rl1(rl1), .bk1(bk1), .g(g));
`endif

    // ---- spec model of the lane fan-out (independent of the DUT RTL)
    wire m_sel = bk1[2068] && (bk1[2060:2048] == 13'd0);
    reg [P-1:0] m_tgt, m_act, m_bv;
    reg [817:0] m_rl;
    reg [2067:0] m_bd;
    integer q;
    always @(posedge clk) begin
        if (!rst_n) begin m_tgt <= 1; m_act <= 1; m_bv <= 0; end
        else begin
            if (m_sel) begin m_tgt <= bk1[P-1:0]; m_act <= bk1[8 +: P]; end
            for (q = 0; q < P; q = q + 1) m_bv[q] <= bk1[2068] && !m_sel && m_tgt[q];
        end
        m_rl <= rl1; m_bd <= bk1[2067:0];
    end
    // ---- P production leaves
    wire [P-1:0] r_gv, r_gf;
    wire [P*32-1:0] r_gy;
    wire [P*16-1:0] r_gt;
    wire [P*50-1:0] d_g;
    genvar gp;
    generate for (gp = 0; gp < P; gp = gp + 1) begin : g_ref
        ot_hbm_accel_smh_leafh u_ref (.clk(clk), .rst_n(rst_n), .xs_a1(st[8:0]), .xs_g1(st[13:9]), .xs_a2(st[20:14]),
            .xs_g2(st[25:21]), .rl1(m_rl), .bk1({m_bv[gp], m_bd}), .ohl1(m_bd[2060:2048]),
            .gv(r_gv[gp]), .gf(r_gf[gp]), .gy(r_gy[gp*32 +: 32]), .gt(r_gt[gp*16 +: 16]));
        assign d_g[gp*50 +: 50] = {dut.g_ln[gp].gv, dut.g_ln[gp].gf, dut.g_ln[gp].gy, dut.g_ln[gp].gt};
    end endgenerate

    // ---- stimulus
    integer cyc, k, r, K, row, gap, bf, fp4, chunks, nlane_bad, nstream_bad, ncoll_m, ncoll_d, nwords, t_first, t_last_issue,
            t_last_pub, i, sel_cnt;
    integer nw [0:P-1];
    reg [49:0] hist [0:P-1][0:127];
    reg [817:0] wrand;
    reg [2047:0] brand;
    reg [12:0] oh;
    reg [47:0] em;
    reg ev, ef, emulti;
    integer en;
    task automatic rand_rl(input integer kk, input integer rr, input integer KK, input integer rw);
        integer j;
        begin
            for (j = 0; j < 26; j = j + 1) wrand[j*32 +: 32] = $urandom;
            rl1 = wrand;
            rl1[817:796] = {(bf == 0), (bf != 0), (kk == 0), (kk == KK - 1), fp4[0], (bf != 0), rw[11:0], 1'b0, rr[2:0]};
            rl1[7] = 1'b1;                                   // x read enable
        end
    endtask
    task automatic beat;
        integer j, b;
        begin
            bk1 = 0;
            if (($urandom % 100) < (THR ? 40 : 30)) begin
                for (j = 0; j < 64; j = j + 1) brand[j*32 +: 32] = $urandom;
                if (($urandom % 12) == 0) begin                 // lane-select beat: one-hot beat field zero
                    bk1[2068] = 1'b1; bk1[2067:2061] = $urandom; bk1[2060:2048] = 13'd0; bk1[2047:0] = brand;
                    bk1[P-1:0] = ($urandom % ((1 << P) - 1)) + 1;  // target mask, non-zero
                    bk1[8 +: P] = (($urandom % 8) == 0 && !THR) ? (($urandom % ((1 << P) - 1)) + 1) : ((1 << P) - 1);
                    sel_cnt = sel_cnt + 1;
                end else begin
                    b = $urandom % 13; oh = 13'd1 << b;
                    bk1[2068] = 1'b1; bk1[2067:2061] = $urandom; bk1[2060:2048] = oh; bk1[2047:0] = brand;
                end
            end
        end
    endtask

    // row programme as a process: chunk after chunk
    reg run_rows;
    initial begin
        st = {$urandom} % (1 << 26);
        rl1 = 0; bk1 = 0; run_rows = 0;
        nlane_bad = 0; nstream_bad = 0; ncoll_m = 0; ncoll_d = 0; nwords = 0; t_first = -1; t_last_issue = 0; t_last_pub = 0;
        sel_cnt = 0;
        for (i = 0; i < P; i = i + 1) nw[i] = 0;
        cyc = 0;
        repeat (16) @(negedge clk);
        rst_n = 1'b1;
        // x preload: every lane, every address (production: the x load precedes the pass)
        @(negedge clk);
        bk1 = 0; bk1[2068] = 1'b1; bk1[8 +: P] = (1 << P) - 1; bk1[P-1:0] = 1;
        for (i = 0; i < P * 128 * 2; i = i + 1) begin
            @(negedge clk);
            if (i % 256 == 0) begin bk1 = 0; bk1[2068] = 1'b1; bk1[P-1:0] = 1 << (i / 256); bk1[8 +: P] = (1 << P) - 1; end
            else begin
                for (k = 0; k < 64; k = k + 1) brand[k*32 +: 32] = $urandom;
                bk1 = 0; bk1[2068] = 1'b1; bk1[2067:2061] = (i % 256) / 2; bk1[2060:2048] = 13'd1 << ($urandom % 13);
                bk1[2047:0] = brand;
            end
        end
        @(negedge clk); bk1 = 0;
        run_rows = 1;
        chunks = 0; row = 0; bf = 0;
        while ((THR ? (chunks < NCHUNK) : (cyc < NCYC - 200))) begin
            K = THR ? KMIN : (KMIN + ($urandom % (KMAX - KMIN + 1)));
            fp4 = THR ? 0 : ($urandom % 2);
            for (k = 0; k < K; k = k + 1)
                for (r = 0; r < IL; r = r + 1) begin
                    @(negedge clk);
                    beat();
                    rand_rl(k, r, K, row + r);
                    if (t_first < 0) t_first = cyc;
                    t_last_issue = cyc;
                end
            chunks = chunks + 1; row = (row + IL) % 4096;
            // gap: none in THR; else random, and a long one when the column type switches (static schedule rule)
            if (!THR) begin
                gap = $urandom % 6;
                if (($urandom % 4) == 0) begin bf = !bf; gap = 96; end
                for (i = 0; i < gap; i = i + 1) begin @(negedge clk); beat(); rl1 = 0; end
            end
        end
        @(negedge clk); rl1 = 0; bk1 = 0;
        repeat (200) @(negedge clk);
        // ---- verdict
        $display("HNX_RP4LP4 P=%0d MUT=%0d LSKEW=%0d chunks=%0d words=%0d sel_beats=%0d lane_bad=%0d stream_bad=%0d coll_model=%0d coll_dut=%0d",
                 P, MUT, LSKEW, chunks, nwords, sel_cnt, nlane_bad, nstream_bad, ncoll_m, ncoll_d);
        for (i = 0; i < P; i = i + 1) $display("  lane %0d words %0d", i, nw[i]);
        if (THR) $display("THROUGHPUT P=%0d chunks=%0d K=%0d rows=%0d issue_span=%0d first_issue=%0d last_pub=%0d publish_span=%0d words=%0d words_per_issue_cycle=%0.3f",
                 P, chunks, KMIN, chunks * IL, t_last_issue - t_first + 1, t_first, t_last_pub, t_last_pub - t_first + 1, nwords,
                 nwords * 1.0 / (t_last_issue - t_first + 1));
        if (nlane_bad != 0) $display("LANE MISMATCH count=%0d", nlane_bad);
        if (nstream_bad != 0) $display("STREAM MISMATCH count=%0d", nstream_bad);
        begin : verdict
            integer ok;
            ok = (nlane_bad == 0) && (nstream_bad == 0) && (ncoll_m == 0) && (nwords > 0);
            for (i = 0; i < P; i = i + 1) if (nw[i] == 0) ok = 0;
            if (ok) begin $display("PASS HNX-RP4LP4 P=%0d", P); $finish; end
            else begin $display("FAIL HNX-RP4LP4 P=%0d MUT=%0d", P, MUT); $fatal(1, "bench failed"); end
        end
    end

    // ---- checker (negedge: after every posedge update)
    integer p2;
    always @(negedge clk) begin
        cyc <= cyc + 1;
        for (p2 = 0; p2 < P; p2 = p2 + 1)
            hist[p2][cyc % 128] = {r_gv[p2] && m_act[p2], r_gf[p2] && m_act[p2], r_gy[p2*32 +: 32], r_gt[p2*16 +: 16]};
        if (rst_n && cyc > WARM) begin
            for (p2 = 0; p2 < P; p2 = p2 + 1)
                if (d_g[p2*50 +: 50] !== {r_gv[p2], r_gf[p2], r_gy[p2*32 +: 32], r_gt[p2*16 +: 16]}) begin
                    if (nlane_bad < 5) $display("LANE MISMATCH cyc %0d lane %0d dut %h ref %h", cyc, p2, d_g[p2*50 +: 50],
                        {r_gv[p2], r_gf[p2], r_gy[p2*32 +: 32], r_gt[p2*16 +: 16]});
                    nlane_bad = nlane_bad + 1;
                end
            // slot-major model: out(t) = merge_p lane_p(t - 1 - p*LSKEW)
            em = 0; ev = 0; ef = 0; en = 0;
            for (p2 = 0; p2 < P; p2 = p2 + 1) begin : mm
                reg [49:0] h;
                h = hist[p2][(cyc - 1 - p2 * LSKEW + 128) % 128];
                if (h[49]) begin em = em | h[47:0]; en = en + 1; ev = 1; end
                if (h[48]) ef = 1;                    // a lane fault propagates with or without a word (as the d4g leaf)
            end
            emulti = (en > 1);
            if (en > 1) ncoll_m = ncoll_m + 1;
            if (g[49] && g[48] && en > 1) ncoll_d = ncoll_d + 1;
            if (g !== {ev, ef | emulti, em}) begin
                if (nstream_bad < 5) $display("STREAM MISMATCH cyc %0d dut %h model %h", cyc, g, {ev, ef | emulti, em});
                nstream_bad = nstream_bad + 1;
            end
            if (g[49] && run_rows) begin
                nwords = nwords + 1; t_last_pub = cyc;
                for (p2 = 0; p2 < P; p2 = p2 + 1)
                    if (hist[p2][(cyc - 1 - p2 * LSKEW + 128) % 128] >> 49) nw[p2] = nw[p2] + 1;
            end
        end
    end
endmodule
