`timescale 1ns/1ps
// tb_hfd_lk_ep ([link] 2026-10-10): two hfd_lk_ep back to back over the 512-b lane, both directions loaded.
// Transaction-exact check: every flit sent by die A arrives at die B once, in order, bit-exact (and B -> A).
// Lane errors: +ERRP=<n> flips one random bit of a random beat about once per n beats, each way (frames hit are
// dropped by the CRC and replayed by the retry pipelines; reverse frames hit are dropped and repeated).
// Die receivers stall at random; they return r_cr per pop; their buffer (FCR deep) must never overflow (credit check).
// PASS needs: N flits each way delivered, replays > 0 when ERRP > 0, no fault.
module tb_hfd_lk_ep;
    parameter integer NS = 3;
    localparam integer W = 545, TXQ = 8, FCR = 16;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer N, ERRP, seed, cyc;
    // ---- DUTs
    reg            a_tv, b_tv; reg [W-1:0] a_tf, b_tf;
    wire           a_tcr, b_tcr, a_rv, b_rv, a_f, b_f, a_l, b_l;
    wire [W-1:0]   a_rf, b_rf;
    reg            a_rcr, b_rcr;
    wire [511:0]   a_x, b_x;
    reg  [511:0]   a2b, b2a;
    wire [31:0]    a_rep, b_rep; wire [15:0] a_dr, b_dr;
    hfd_lk_ep #(.NS(NS), .TXQ(TXQ), .FCR(FCR)) A (.clk(clk), .rst_n(rst_n), .session(24'h5A), .t_v(a_tv), .t_flit(a_tf),
        .t_cr(a_tcr), .r_v(a_rv), .r_flit(a_rf), .r_cr(a_rcr), .x_tx(a_x), .x_rx_v(1'b1), .x_rx(b2a), .fault(a_f),
        .locked(a_l), .st_replays(a_rep), .st_drops(a_dr));
    hfd_lk_ep #(.NS(NS), .TXQ(TXQ), .FCR(FCR)) B (.clk(clk), .rst_n(rst_n), .session(24'h5A), .t_v(b_tv), .t_flit(b_tf),
        .t_cr(b_tcr), .r_v(b_rv), .r_flit(b_rf), .r_cr(b_rcr), .x_tx(b_x), .x_rx_v(1'b1), .x_rx(a2b), .fault(b_f),
        .locked(b_l), .st_replays(b_rep), .st_drops(b_dr));
    // ---- lane with bit errors (one register each way, like the PHY)
    integer bi1, bi2;
    always @(posedge clk) begin
        a2b <= a_x; b2a <= b_x;
        if (ERRP > 0 && cyc > 200) begin
            if (($random(seed) & 32'h7fffffff) % ERRP == 0) begin bi1 = ($random(seed) & 32'h7fffffff) % 512; a2b[bi1] <= ~a_x[bi1]; end
            if (($random(seed) & 32'h7fffffff) % ERRP == 0) begin bi2 = ($random(seed) & 32'h7fffffff) % 512; b2a[bi2] <= ~b_x[bi2]; end
        end
    end
    function [W-1:0] pay(input integer dir, input integer n);
        integer j; begin for (j = 0; j < W; j = j + 1) pay[j] = ((j * 13 + n * 7 + dir * 5) ^ (n >> (j % 9))) & 1;
            pay[31:0] = n; pay[33:32] = dir; end
    endfunction
    // ---- die senders (TXQ credits each)
    integer a_sent, b_sent, a_cred, b_cred;
    always @(posedge clk) if (rst_n) begin
        a_cred <= a_cred + (a_tcr ? 1 : 0) - (a_tv ? 1 : 0);
        b_cred <= b_cred + (b_tcr ? 1 : 0) - (b_tv ? 1 : 0);
    end
    always @(negedge clk) begin
        a_tv = rst_n && cyc > 20 && a_sent < N && (a_cred - (a_tv ? 1 : 0)) > 0 && (($random(seed) & 32'h7fffffff) % 8 != 0);
        b_tv = rst_n && cyc > 20 && b_sent < N && (b_cred - (b_tv ? 1 : 0)) > 0 && (($random(seed) & 32'h7fffffff) % 5 != 0);
        a_tf = pay(0, a_sent); b_tf = pay(1, b_sent);
    end
    always @(posedge clk) begin if (a_tv) a_sent <= a_sent + 1; if (b_tv) b_sent <= b_sent + 1; end
    // ---- die receivers: FCR-deep buffer, random pops, credit per pop
    integer a_occ, b_occ, a_seen, b_seen;
    reg a_pop, b_pop;
    always @(negedge clk) begin
        a_pop = (a_occ > 0) && (($random(seed) & 32'h7fffffff) % 3 == 0);
        b_pop = (b_occ > 0) && (($random(seed) & 32'h7fffffff) % 4 != 0);
        a_rcr = a_pop; b_rcr = b_pop;
    end
    always @(posedge clk) if (rst_n) begin
        a_occ <= a_occ + (a_rv ? 1 : 0) - (a_pop ? 1 : 0);
        b_occ <= b_occ + (b_rv ? 1 : 0) - (b_pop ? 1 : 0);
        if (a_occ > FCR || b_occ > FCR) $fatal(1, "die receive buffer overflow (credit violation) a%0d b%0d", a_occ, b_occ);
        if (b_rv) begin
            if (b_rf !== pay(0, b_seen)) $fatal(1, "A->B flit %0d mismatch (got %0d)", b_seen, b_rf[31:0]);
            b_seen <= b_seen + 1;
        end
        if (a_rv) begin
            if (a_rf !== pay(1, a_seen)) $fatal(1, "B->A flit %0d mismatch (got %0d)", a_seen, a_rf[31:0]);
            a_seen <= a_seen + 1;
        end
        if (a_f || b_f) $fatal(1, "fault a%0d b%0d", a_f, b_f);
    end
    integer k;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 3000;
        if (!$value$plusargs("ERRP=%d", ERRP)) ERRP = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        cyc = 0; a_sent = 0; b_sent = 0; a_cred = TXQ; b_cred = TXQ; a_occ = 0; b_occ = 0; a_seen = 0; b_seen = 0;
        a_tv = 0; b_tv = 0; a_rcr = 0; b_rcr = 0; a2b = 0; b2a = 0;
        repeat (5) @(posedge clk); rst_n = 1;
        for (k = 0; k < 400 * N + 200000 && !(a_seen == N && b_seen == N); k = k + 1) begin @(posedge clk); cyc = cyc + 1; end
        if (a_seen != N || b_seen != N) $fatal(1, "TIMEOUT delivered A->B %0d B->A %0d of %0d (locked %0d %0d)", b_seen, a_seen, N, a_l, b_l);
        if (ERRP > 0 && a_rep + b_rep == 0) $fatal(1, "no replay with lane errors");
        $display("LKEP_BENCH PASS NS %0d N %0d ERRP %0d cycles %0d replays %0d/%0d drops %0d/%0d (%.3f flits/cycle A->B)",
                 NS, N, ERRP, cyc, a_rep, b_rep, a_dr, b_dr, N * 1.0 / cyc);
        $finish;
    end
endmodule
