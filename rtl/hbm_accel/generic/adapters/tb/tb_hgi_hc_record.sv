`timescale 1ns/1ps
// hgi-adapters (2026-10-09): bench of ot_hgi_hc_record (stub HC unit; MUT_NF must FAIL).  Vectors: tools/hgi_adapters/hc_bench.py (+DIR=).
//  RUN cases: records -> adapter (stub mover: random ready, done after a random latency; fence done after a random
//    latency): every move word at issue == the reference, every FENCE reaches the fence port, each record retires once,
//    in order, only after the mover's done.  NEGATIVE cases: rec_fault, nothing issued, halted.
//  LEGACY: a second adapter with hgi_en 0: mover / fence ports == the legacy ports every cycle (random legacy traffic).
// Prints HGI_HC PASS / FAIL.
module tb_hgi_hc_record;
`ifdef MUT_NF
    localparam integer MS = 1;
`else
    localparam integer MS = 0;
`endif
`ifdef MUT_EARLY
    localparam integer ME = 1;
`else
    localparam integer ME = 0;
`endif
    `include "hc_sizes.svh"
    reg clk = 0;
    always #1 clk = ~clk;
    reg [937:0] recm [0:NREC-1];
    reg [230:0] refm [0:NREC-1];
    reg [95:0]  casem [0:NCASE-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/hc_rec.mem"}, recm); $readmemh({dir, "/hc_ref.mem"}, refm); $readmemh({dir, "/hc_case.mem"}, casem);
    end
    integer errors = 0, cyc = 0, seed = 7;
    always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted, mv_v; wire [228:0] mv;
    reg mv_rdy = 0, mv_done = 0, fence_rdy = 0, fence_done = 0;
    ot_hgi_hc_record #(.MUT_NF(MS)) u_h (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .cfg_hc_eps(EPS), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]),
        .rec_n_a(cur[916:896]), .rec_n_o(cur[937:917]), .rec_done(done), .rec_fault(fault), .halted(halted),
        .lg_v(1'b0), .lg_rdy(), .lg_job(229'd0), .job_v(mv_v), .job_rdy(mv_rdy), .job(mv), .job_done(mv_done), .job_fault(1'b0));
    wire fence_v = 1'b0;
    // legacy identity
    reg [228:0] lmv; reg lv, lf, lr, lfr; integer q, lock_n = 0;
    wire l_mv_v, l_lr, l_rdy, l_done, l_fault; wire [228:0] l_mv;
    ot_hgi_hc_record #(.MUT_NF(MS)) u_l (.clk(clk), .rst_n(rst_n), .hgi_en(1'b0), .cfg_hc_eps(EPS), .rec_v(1'b1),
        .rec_rdy(l_rdy), .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]),
        .rec_n_a(cur[916:896]), .rec_n_o(cur[937:917]), .rec_done(l_done), .rec_fault(l_fault), .halted(),
        .lg_v(lv), .lg_rdy(l_lr), .lg_job(lmv), .job_v(l_mv_v), .job_rdy(lr), .job(l_mv), .job_done(1'b0), .job_fault(1'b0));
    wire l_f_v = lf; wire l_lfr = lfr;
    always @(posedge clk) begin
        for (q = 0; q < 229; q = q + 32) lmv[q +: 32] <= $random(seed);
        {lv, lf, lr, lfr} <= $random(seed);
        if (rst_n) begin
            lock_n = lock_n + 1;
            if (l_mv !== lmv || l_mv_v !== lv || l_f_v !== lf || l_lr !== lr || l_lfr !== lfr || l_rdy || l_done || l_fault) begin
                if (errors < 10) $display("ERR legacy identity at %0d", cyc); errors = errors + 1; end
        end
    end
    // stub mover
    integer k = 0, base = 0, issued = 0, lat = -1, flat = -1, nfault = 0;
    reg [230:0] rw;
    always @(posedge clk) begin
        rw = refm[base + k];
        mv_rdy <= $random(seed) & 1; fence_rdy <= $random(seed) & 1; mv_done <= 0; fence_done <= 0;
        if (rst_n && mv_v && mv_rdy) begin
            issued = issued + 1; lat = 2 + ($random(seed) & 15);
            if (rw[230:229] != 2'd0 || mv !== rw[228:0]) begin
                $display("ERR job mismatch at record %0d: %h vs %h", base + k, mv, rw[228:0]); errors = errors + 1; end
        end else if (lat > 0) lat = lat - 1;
        else if (lat == 0) begin mv_done <= 1; lat = -1; end
        if (rst_n && fence_v && fence_rdy) begin
            issued = issued + 1; flat = 2 + ($random(seed) & 7);
            if (1) begin $display("ERR fence issued for record %0d", base + k); errors = errors + 1; end
        end else if (flat > 0) flat = flat - 1;
        else if (flat == 0) begin fence_done <= 1; flat = -1; end
        if (rst_n && done) begin
            if (lat != -1 || flat != -1 || mv_done || fence_done) begin
                $display("ERR record %0d retired before the mover completed", base + k); errors = errors + 1; end
            k = k + 1;
        end
        if (rst_n && fault) nfault = nfault + 1;
    end
    integer c, j, kind, r0, nr, t, runs = 0, negs = 0;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][95:64]; r0 = casem[c][63:32]; nr = casem[c][31:0];
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; @(posedge clk);
            base = r0; k = 0; issued = 0; nfault = 0; lat = -1; flat = -1;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 20000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nfault == 0 && t < 20000) begin @(posedge clk); t = t + 1; end
            repeat (30) @(posedge clk);
            if (kind == 0) begin
                if (k != nr || nfault != 0 || issued != nr) begin
                    $display("ERR run case %0d: retired %0d issued %0d of %0d, faults %0d", c, k, issued, nr, nfault); errors = errors + 1; end
                runs = runs + nr;
            end else if (nfault != 1 || k != 0 || issued != 0 || !halted) begin
                $display("ERR negative case %0d", c); errors = errors + 1;
            end else negs = negs + 1;
        end
        $display("summary: %0d records run, %0d negatives refused, %0d legacy identity cycles", runs, negs, lock_n);
        if (errors == 0) $display("HGI_HC PASS"); else $display("HGI_HC FAIL errors=%0d", errors);
        $finish;
    end
endmodule
