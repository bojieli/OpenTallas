`timescale 1ns/1ps
// tb_hfd_lk_ep ([link] 2026-10-10): two hfd_lk_ep back to back over the 512-b lane, both directions loaded.
// Transaction-exact check: every flit sent by die A arrives at die B once, in order, bit-exact (and B -> A).
// Lane errors: +ERRP=<n> flips one random bit of a random beat about once per n beats, each way (frames hit are
// dropped by the CRC and replayed by the retry pipelines; reverse frames hit are dropped and repeated).
// Die receivers stall at random; they return r_cr per pop; their buffer (FCR deep) must never overflow (credit check).
// PASS needs: N flits each way delivered, replays > 0 when ERRP > 0, no fault.
module tb_hbm_endpoint_kp4;
 parameter integer MUT_FACE=0;
    parameter integer NS = 3;
    parameter integer FCR = 256;
    parameter integer TXQ = 32;
    localparam integer W = 545;
    reg clk = 0; always #0.41667 clk = ~clk;
    reg rst_n = 0;
    integer N, ERRP, seed, cyc, maxcyc, lostrp, lr_until;
    // el1011-hbm-lkep: own xorshift32 stream (Verilator ignores the seed argument of $random(seed), so +SEED had no
    // effect: every seed gave the same error pattern).
    reg [31:0] rs_x;
    function automatic integer rnd(input integer dummy);
        begin rs_x = rs_x ^ (rs_x << 13); rs_x = rs_x ^ (rs_x >> 17); rs_x = rs_x ^ (rs_x << 5); rnd = rs_x & 32'h7fffffff; end
    endfunction
    // ---- DUTs
    reg            a_tv, b_tv; reg [W-1:0] a_tf, b_tf;
    wire           a_tcr, b_tcr, a_rv, b_rv, a_f, b_f, a_l, b_l;
    wire [W-1:0]   a_rf, b_rf;
    reg            a_rcr, b_rcr;
    localparam integer LW = 487;
    wire [LW-1:0]  a_x, b_x;
    wire [LW-1:0] a2b,b2a;
    wire [31:0]    a_rep = A.u.st_replays, b_rep = B.u.st_replays; wire [15:0] a_dr = A.u.st_drops, b_dr = B.u.st_drops;
    tri[1119:0]fa,fb;tri[973:0]pya,pyb;
    assign fa[0]=a_tv;assign fa[545:1]=a_tf;assign fa[546]=a_rcr;assign fa[1117:1094]=24'h5a;
    assign {a_l,a_f}=fa[1119:1118];assign a_tcr=fa[1093];assign a_rf=fa[1092:548];assign a_rv=fa[547];
    assign fb[0]=b_tv;assign fb[545:1]=b_tf;assign fb[546]=b_rcr;assign fb[1117:1094]=24'h5a;
    assign {b_l,b_f}=fb[1119:1118];assign b_tcr=fb[1093];assign b_rf=fb[1092:548];assign b_rv=fb[547];
    hfd_lk_ep #(.HARD_CLOCKS(1),.MUT_FACE(MUT_FACE))A(.clk(clk),.clk_face(clk),.clk_sub({12{clk}}),.clk_tx_shared(clk),.clk_rx_shared(clk),.clk_status_shared(clk),.rst_n(rst_n),.f_lk(fa),.phy(pya));
    hfd_lk_ep #(.HARD_CLOCKS(1))B(.clk(clk),.clk_face(clk),.clk_sub({12{clk}}),.clk_tx_shared(clk),.clk_rx_shared(clk),.clk_status_shared(clk),.rst_n(rst_n),.f_lk(fb),.phy(pyb));
    wire[543:0]pa,pb;wire ca,cb;wire[1:0]sa,sb;wire pfa,pfb;
    hfd_serdes487 sa_phy(.clk(clk),.rst_n(rst_n),.tx(pya[486:0]),.rx(pya[973:487]),.st(sa),.padding_fault(pfa),.pma_tx(pa),.pma_tck(ca),.pma_rx(pb),.pma_rck(cb));
    hfd_serdes487 sb_phy(.clk(clk),.rst_n(rst_n),.tx(pyb[486:0]),.rx(pyb[973:487]),.st(sb),.padding_fault(pfb),.pma_tx(pb),.pma_tck(cb),.pma_rx(pa),.pma_rck(ca));
    // ---- lane with bit errors (one register each way, like the PHY)
    integer bi1, bi2;
    // +LOSTRP=<n>: directed LOST REPLAY, forced (not left to the random pattern): the first n rewinds of A's retry pipelines
    // open a 40-edge window in which every A->B beat carries a bit error, so the replay that rewind launches is lost too
    // and B keeps NAKing that sequence.  NAK_HOLD replays again one round trip later; the pre-fix pipeline
    // (OT_LKEP_MUT_NAKHOLD) waits for the 8,192-edge TIMEOUT, which +MAXCYC catches.
    wire [NS-1:0] a_rw;
    genvar gq;
    generate for (gq = 0; gq < NS; gq = gq + 1) begin : g_rw
        assign a_rw[gq] = A.u.g_t[gq].u_t.u_rp.g_on.rinc;
    end endgenerate
    always @(posedge clk) if (rst_n && lostrp > 0 && (|a_rw) && cyc >= lr_until) begin lr_until <= cyc + 40; lostrp <= lostrp - 1; end
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
        a_tv = rst_n && cyc > 500 && a_sent < N && (a_cred - (a_tv ? 1 : 0)) > 0 && (FCR > 64 || rnd(0) % 8 != 0);
        b_tv = rst_n && cyc > 500 && b_sent < N && (b_cred - (b_tv ? 1 : 0)) > 0 && (FCR > 64 || rnd(0) % 5 != 0);
        a_tf = pay(0, a_sent); b_tf = pay(1, b_sent);
    end
    always @(posedge clk) begin if (a_tv) a_sent <= a_sent + 1; if (b_tv) b_sent <= b_sent + 1; end
    // ---- die receivers: FCR-deep buffer, random pops, credit per pop
    integer a_occ, b_occ, a_seen, b_seen;
    reg a_pop, b_pop;
    always @(negedge clk) begin
        a_pop = (a_occ > 0) && (FCR > 64 || rnd(0) % 3 == 0);
        b_pop = (b_occ > 0) && (FCR > 64 || rnd(0) % 4 != 0);
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
        if (a_f || b_f || pfa || pfb) $fatal(1, "fault a%0d b%0d", a_f, b_f);
    end
    integer k;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 128;
        if (!$value$plusargs("ERRP=%d", ERRP)) ERRP = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 0;   // recovery-time bound (0 = none)
        if (!$value$plusargs("LOSTRP=%d", lostrp)) lostrp = 0;
        lr_until = 0; rs_x = 32'h9E3779B9 ^ seed; if (rs_x == 0) rs_x = 1;
        cyc = 0; a_sent = 0; b_sent = 0; a_cred = TXQ; b_cred = TXQ; a_occ = 0; b_occ = 0; a_seen = 0; b_seen = 0;
        a_tv = 0; b_tv = 0; a_rcr = 0; b_rcr = 0; 
        repeat (5) @(posedge clk); rst_n = 1;
        for (k = 0; k < 400 * N + 200000 && !(a_seen == N && b_seen == N); k = k + 1) begin @(posedge clk); cyc = cyc + 1; end
        if (a_seen != N || b_seen != N) $fatal(1, "TIMEOUT delivered A->B %0d B->A %0d of %0d (locked %0d %0d)", b_seen, a_seen, N, a_l, b_l);
        if (ERRP > 0 && a_rep + b_rep == 0) $fatal(1, "no replay with lane errors");
        if (lostrp > 0) $fatal(1, "LOSTRP: %0d directed lost-replay windows never opened", lostrp);
        if (maxcyc > 0 && cyc > maxcyc) $fatal(1, "recovery too slow: %0d cycles > MAXCYC %0d (a lost replay waited for TIMEOUT?)", cyc, maxcyc);
        $display("HBM_ENDPOINT_KP4_PASS NS %0d N %0d ERRP %0d cycles %0d replays %0d/%0d drops %0d/%0d (%.3f flits/cycle A->B)",
                 NS, N, ERRP, cyc, a_rep, b_rep, a_dr, b_dr, N * 1.0 / cyc);
        $finish;
    end
endmodule
