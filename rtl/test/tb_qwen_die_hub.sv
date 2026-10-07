// ot_qwen_die_hub scoreboard bench.  Four remote link endpoints (models) on their own clocks fck[k] (same period,
// different phases): each sends N words on its link obeying 4 credits returned through the hub's tx Gray count, and
// receives the hub's x3 words, returning a credit per word through its own Gray count.  The SU model sends x3 words
// with random link selects obeying 2 credits (x3_cr); the VM model takes ar words, returning ar_cr after random
// delays.  Checks: every link word reaches ar exactly once, in per-link order, bit-exact; every x3 word reaches its
// selected link, in order, bit-exact; no fault.  NEG = 1: the remotes ignore credits (must FAIL).
`timescale 1ns/1ps
module tb_qwen_die_hub;
    parameter integer N = 600, NEG = 0;
    localparam integer NL = 4, LW = 528;
    reg ck = 0, rst_n = 0; reg [NL-1:0] fck = 0;
    always #1.0 ck = ~ck;
    initial begin #0.3 forever #1.0 fck[0] = ~fck[0]; end
    initial begin #0.7 forever #1.0 fck[1] = ~fck[1]; end
    initial begin #1.1 forever #1.0 fck[2] = ~fck[2]; end
    initial begin #1.6 forever #1.0 fck[3] = ~fck[3]; end
    reg [NL*LW-1:0] l_i = 0; wire [NL*LW-1:0] l_o;
    reg x3_v = 0; reg [511:0] x3_d = 0; reg [10:0] x3_tag = 0; wire x3_cr, ar_v, fault; wire [511:0] ar_d; reg ar_cr = 0;
    ot_qwen_die_hub u (.ck(ck), .rst_n(rst_n), .fck(fck), .l_i(l_i), .l_o(l_o), .x3_v(x3_v), .x3_d(x3_d),
        .x3_tag(x3_tag), .x3_cr(x3_cr), .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr), .fault(fault));
    function [3:0] g2b(input [3:0] g); g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; endfunction
    reg go = 0; integer bad = 0, seed = 9;
    // ---- remotes ----
    reg [511:0] lsent [0:NL-1][0:N-1]; integer lns [0:NL-1]; integer lnr [0:NL-1];   // link -> hub words
    reg [509:0] xsent [0:NL-1][0:4*N-1]; integer xns [0:NL-1]; integer xnr [0:NL-1]; // x3 -> link words
    genvar k;
    generate for (k = 0; k < NL; k = k + 1) begin : g_rem
        integer cred = 4; reg [3:0] seen = 0, mycnt = 0; reg [3:0] s1 = 0, s2 = 0; integer j;
        reg [LW-1:0] w;
        initial begin lns[k] = 0; lnr[k] = 0; xns[k] = 0; xnr[k] = 0; end
        always @(posedge fck[k]) if (go) begin
            s1 <= l_o[k*LW + 1 +: 4]; s2 <= s1;                      // hub's returned-credit Gray count
            cred = cred + ((g2b(s2) - g2b(seen)) & 15); seen = s2;
            w = 0;
            if (lns[k] < N && (NEG || cred > 0) && ($random(seed) % 2)) begin
                for (j = 0; j < 16; j = j + 1) w[16 + 32*j +: 32] = $random(seed);
                w[15:5] = lns[k]; w[0] = 1'b1;
                lsent[k][lns[k]] = w[LW-1:16]; lns[k] = lns[k] + 1; cred = cred - 1;
            end
            if (l_o[k*LW]) begin                                     // a word from the hub (sampled in fck: same period)
                if (l_o[k*LW + 18 +: 510] !== xsent[k][xnr[k]]) bad = bad + 1;
                xnr[k] = xnr[k] + 1; mycnt = mycnt + 1;
            end
            w[4:1] = mycnt ^ (mycnt >> 1);
            l_i[k*LW +: LW] <= w;
        end
    end endgenerate
    // ---- SU (x3) and VM (ar) ----
    integer xc = 2, xtot = 0, owe = 0, k2, got = 0; integer m;
    always @(posedge ck) if (go) begin
        xc = xc + x3_cr;
        x3_v <= 1'b0;
        if (xtot < 4*N && (NEG || xc > 0) && ($random(seed) % 3 == 0)) begin
            for (k2 = 0; k2 < 16; k2 = k2 + 1) x3_d[32*k2 +: 32] <= $random(seed);
            x3_v <= 1'b1; xc = xc - 1; xtot = xtot + 1;
        end
        if (ar_v) begin
            // the word's link: search the oldest outstanding word of each link
            m = -1;
            for (k2 = 0; k2 < NL; k2 = k2 + 1) if (m < 0 && lnr[k2] < lns[k2] && ar_d === lsent[k2][lnr[k2]]) m = k2;
            if (m < 0) bad = bad + 1; else lnr[m] = lnr[m] + 1;
            got = got + 1; owe = owe + 1;
        end
        ar_cr <= 1'b0;
        if (owe > 0 && ($random(seed) & 1)) begin ar_cr <= 1'b1; owe = owe - 1; end
    end
    always @(posedge ck) if (x3_v) begin xsent[x3_d[511:510]][xns[x3_d[511:510]]] = x3_d[509:0]; xns[x3_d[511:510]] = xns[x3_d[511:510]] + 1; end
    initial begin
        repeat (5) @(posedge ck); rst_n = 1; repeat (10) @(posedge ck); go = 1;
        repeat (40 * N) @(posedge ck);
        if (bad == 0 && !fault && got == NL * N && xnr[0] == xns[0] && xnr[1] == xns[1] && xnr[2] == xns[2] && xnr[3] == xns[3])
            $display("PASS hub ar_words=%0d x3_words=%0d", got, xtot);
        else $display("FAIL hub NEG=%0d: bad %0d fault %0d ar %0d of %0d x3 %0d/%0d/%0d/%0d of %0d", NEG, bad, fault, got, NL * N,
                      xnr[0], xnr[1], xnr[2], xnr[3], xtot);
        $finish;
    end
endmodule
