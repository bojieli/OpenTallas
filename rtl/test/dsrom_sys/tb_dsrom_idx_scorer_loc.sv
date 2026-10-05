`timescale 1ns/1ps
// Bench of ot_dsrom_idx_scorer_loc: IDX_SCORER_LOC = 0 (hub) and 1 (per HBM
// stack) instantiated side by side on the same per-stack key streams; both must
// return exactly the golden's selection: sorted(topk_lowest_index(s, min(K, n)))
// of tools/hdc_golden_v41.py (largest BF16 score, ties to the lower position,
// ascending position order) -- computed here by the golden's own hardware
// formulation, rank_i = #{j : s_j > s_i or (s_j == s_i and j < i)}, selected
// when rank_i < K.  Cases: random scores, heavy exact ties, +0/-0 and -inf,
// fewer keys than K, interleaved and block (imbalanced) sharding, empty shards,
// random output back-pressure.  Prints "CASE ..." lines and "IDXLOC PASS|FAIL".
// Mutants: +define+DSROM_IDX_MUTANT_TIE (ties to the higher position) must FAIL;
// +define+DSROM_IDX_MUTANT_QID (one stack tagged with a wrong query id) must
// raise the identity fault.
module tb_dsrom_idx_scorer_loc;
    localparam integer NS = 4, K = 16, PW = 12, QW = 8, NMAX = 400;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg start = 0; reg [QW-1:0] qid = 0;
    reg [NS-1:0] kv = 0, kl = 0; wire [NS-1:0] kr0, kr1;
    reg [NS*16-1:0] ks = 0; reg [NS*PW-1:0] kp = 0;
    wire sv0, sv1, sl0, sl1, f0, f1; wire [PW-1:0] sp0, sp1; wire [31:0] c0, c1;
    reg sr = 1;
    ot_dsrom_idx_scorer_loc #(.IDX_SCORER_LOC(0), .NS(NS), .K(K), .PW(PW), .QW(QW)) hub (
        .clk(clk), .rst_n(rst_n), .start(start), .qid(qid), .k_v(kv & kr0), .k_ready(kr0), .k_score(ks),
        .k_pos(kp), .k_last(kl & kr0), .sel_v(sv0), .sel_ready(sr), .sel_pos(sp0), .sel_last(sl0), .fault(f0),
        .st_cycles(c0));
    // the per-stack instance sees the same shards; each stack is fed independently
    reg [NS-1:0] kv1 = 0, kl1 = 0; reg [NS*16-1:0] ks1 = 0; reg [NS*PW-1:0] kp1 = 0;
    reg [QW-1:0] qid1;
    ot_dsrom_idx_scorer_loc #(.IDX_SCORER_LOC(1), .NS(NS), .K(K), .PW(PW), .QW(QW)) stk (
        .clk(clk), .rst_n(rst_n), .start(start), .qid(qid), .k_v(kv1), .k_ready(kr1), .k_score(ks1),
        .k_pos(kp1), .k_last(kl1), .sel_v(sv1), .sel_ready(sr), .sel_pos(sp1), .sel_last(sl1), .fault(f1),
        .st_cycles(c1));
`ifdef DSROM_IDX_MUTANT_QID
    initial force stk.g_stack.g_s[2].u_sel.q = 8'hEE;
`endif

    reg [15:0] sc [0:NMAX-1];
    integer n, i, j, r, fails = 0, seed = 11, cs;
    reg [NMAX-1:0] want;
    integer shard [0:NMAX-1];
    // BF16 -> real, independent of the RTL's ordering key (no subnormals are generated)
    function automatic real bf(input [15:0] b);
        reg [63:0] d;
        begin
            if (b[14:7] == 0) d = 64'd0;                                      // +0 and -0 -> 0.0
            else if (b[14:7] == 8'hFF) d = {b[15], 11'h7FF, 52'd0};             // +-inf
            else d = {b[15], 11'(b[14:7] - 127 + 1023), b[6:0], 45'd0};
            bf = $bitstoreal(d);
        end
    endfunction
    integer got0 [0:NMAX-1], got1 [0:NMAX-1];
    integer n0, n1, d0, d1;
    always @(posedge clk) begin
        sr <= ($urandom(seed) % 100) >= 40;
        if (sv0 && sr) begin got0[n0] = sp0; n0 = n0 + 1; if (sl0) d0 = 1; end
        if (sv1 && sr) begin got1[n1] = sp1; n1 = n1 + 1; if (sl1) d1 = 1; end
    end

    task automatic run_case(input string name, input integer nk, input integer mode, input integer block);
        integer s, cnt, ok, idx0, idx1, wantn, t;
        integer q0 [0:NS-1];
        begin
            n = nk;
            // shard assignment: block (imbalanced: first shards larger) or interleaved
            for (i = 0; i < n; i = i + 1) shard[i] = block ? ((i * NS) / (n > 0 ? n : 1) + (i % 7 == 0)) % NS : i % NS;
            for (i = 0; i < n; i = i + 1)
                case (mode)
                    0: sc[i] = {1'b0, 8'(120 + ($urandom(seed) % 16)), 7'($urandom(seed))};            // random positive
                    1: sc[i] = {1'b0, 8'd127, 7'($urandom(seed) % 3)};                                // heavy ties
                    default: case ($urandom(seed) % 5)                                                 // zeros, -0, -inf
                        0: sc[i] = 16'h0000; 1: sc[i] = 16'h8000; 2: sc[i] = 16'hFF80;
                        default: sc[i] = {1'b0, 8'd126, 7'($urandom(seed) % 2)};
                    endcase
                endcase
            // golden selection by rank
            want = 0; wantn = 0;
            for (i = 0; i < n; i = i + 1) begin
                r = 0;
                for (j = 0; j < n; j = j + 1)
                    if (bf(sc[j]) > bf(sc[i]) || (bf(sc[j]) == bf(sc[i]) && j < i)) r = r + 1;
                if (r < K) begin want[i] = 1; wantn = wantn + 1; end
            end
            n0 = 0; n1 = 0; d0 = 0; d1 = 0;
            @(negedge clk); start = 1; qid = qid + 1; @(negedge clk); start = 0;
            // stream: hub instance gets each shard's keys through k_ready; stack instance in parallel
            for (s = 0; s < NS; s = s + 1) q0[s] = 0;
            fork
                begin : feed_hub
                    integer ss, ii, any;
                    for (ss = 0; ss < NS; ss = ss + 1) begin
                        any = 0;
                        for (ii = 0; ii < n; ii = ii + 1) if (shard[ii] == ss) any = ii + 1;
                        if (any == 0) begin
                            @(negedge clk); kv[ss] = 0; kl[ss] = 1;
                            @(posedge clk); while (!kr0[ss]) @(posedge clk);
                            @(negedge clk); kl[ss] = 0;
                        end else
                            for (ii = 0; ii < n; ii = ii + 1) if (shard[ii] == ss) begin
                                @(negedge clk); kv[ss] = 1; ks[ss*16 +: 16] = sc[ii]; kp[ss*PW +: PW] = ii;
                                kl[ss] = (ii == any - 1);
                                @(posedge clk); while (!kr0[ss]) @(posedge clk);
                                @(negedge clk); kv[ss] = 0; kl[ss] = 0;
                            end
                    end
                end
                begin : feed_stk
                    integer ii, ss, last [0:NS-1], done;
                    for (ss = 0; ss < NS; ss = ss + 1) last[ss] = -1;
                    for (ii = 0; ii < n; ii = ii + 1) last[shard[ii]] = ii;
                    // all stacks in parallel, one key a cycle each, in position order within a shard
                    for (ss = 0; ss < NS; ss = ss + 1) q0[ss] = 0;
                    done = 0;
                    while (!done) begin
                        @(negedge clk);
                        done = 1;
                        for (ss = 0; ss < NS; ss = ss + 1) begin
                            kv1[ss] = 0; kl1[ss] = 0;
                            while (q0[ss] < n && shard[q0[ss]] != ss) q0[ss] = q0[ss] + 1;
                            if (last[ss] < 0 && q0[ss] != -5) begin kl1[ss] = 1; q0[ss] = -5; done = 0; end
                            else if (q0[ss] >= 0 && q0[ss] < n) begin
                                kv1[ss] = 1; ks1[ss*16 +: 16] = sc[q0[ss]]; kp1[ss*PW +: PW] = q0[ss];
                                kl1[ss] = (q0[ss] == last[ss]); q0[ss] = q0[ss] + 1; done = 0;
                            end
                        end
                    end
                    @(negedge clk); kv1 = 0; kl1 = 0;
                end
            join
            t = 0;
            while ((!d0 || !d1) && t < 20000) begin @(posedge clk); t = t + 1; end
            ok = (n0 == wantn) && (n1 == wantn) && !f0 && !f1;
            cnt = 0;
            for (i = 0; i < n; i = i + 1) if (want[i]) begin
                if (cnt < n0 && got0[cnt] != i) ok = 0;
                if (cnt < n1 && got1[cnt] != i) ok = 0;
                cnt = cnt + 1;
            end
            $display("CASE %s n=%0d k=%0d want=%0d hub=%0d stack=%0d hub_cycles=%0d stack_cycles=%0d fault=%0d/%0d %s",
                     name, n, K, wantn, n0, n1, c0, c1, f0, f1, ok ? "PASS" : "FAIL");
            if (!ok) fails = fails + 1;
        end
    endtask

    initial begin
        repeat (3) @(posedge clk); rst_n = 1;
        run_case("random_interleaved", 200, 0, 0);
        run_case("random_block", 300, 0, 1);
        run_case("ties_interleaved", 250, 1, 0);
        run_case("ties_block", 400, 1, 1);
        run_case("zeros_negzero_neginf", 180, 2, 0);
        run_case("fewer_than_k", 11, 0, 0);
        run_case("exactly_k", 16, 1, 1);
        run_case("empty_shards", 3, 0, 0);
        $display("IDXLOC %s fails=%0d", fails == 0 ? "PASS" : "FAIL", fails);
        $finish;
    end
endmodule
