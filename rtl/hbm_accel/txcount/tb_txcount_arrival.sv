`timescale 1ns/1ps
// Unit bench for ot_hbm_txcount_arrival: K participants, each with its own counter fed point-to-point
// through a per-pair registered delay D[i][j] in 1..DMAX (random, asymmetric), so fast participants
// reach the next barrier while slow consumers are still counting the current one.  Each participant
// works a random time after its own release, then arrives.  Checks: no consumer releases phase n before
// every participant has arrived at barrier n (early_release_errors), every barrier completes for every
// consumer (no deadlock), and the release follows the last arrival by exactly the slowest link + 1.
module tb_txcount_arrival;
    parameter integer K = 8, NBAR = 300, WMAX = 40, DMAX = 9, SEED = 7;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg  [K-1:0] sense = 0;                // participants' arrival senses
    reg  [K-1:0] hist [0:63];              // sense history ring (hist[t % 64])
    integer D [0:K-1][0:K-1];
    reg  [K-1:0] arr_in [0:K-1];
    wire [K-1:0] rel;
    integer cyc = 0, i, j, seed = SEED, errs = 0;
    integer narr [0:K-1];                  // arrivals made by participant i
    integer nrel [0:K-1];                  // releases seen by consumer j
    integer wake [0:K-1];
    integer t_arr [0:K-1][0:NBAR];
    reg [K-1:0] rel_q = 0;
    genvar g;
    for (g = 0; g < K; g = g + 1) begin : g_c
        ot_hbm_txcount_arrival #(.ENABLE(1), .K(K)) u (.clk(clk), .rst_n(rst_n), .arr(arr_in[g]), .rel(rel[g]));
    end
    always @* for (j = 0; j < K; j = j + 1) for (i = 0; i < K; i = i + 1) arr_in[j][i] = hist[(cyc - D[i][j] + 64) % 64][i];
    integer done_cnt, exp_lat, mind = 1 << 30, maxd = -(1 << 30);
    initial begin
        for (i = 0; i < K; i = i + 1) begin
            narr[i] = 0; nrel[i] = 0; wake[i] = 2 + $urandom(seed) % WMAX;
            for (j = 0; j < K; j = j + 1) D[i][j] = 1 + $urandom(seed) % DMAX;
        end
        for (i = 0; i < 64; i = i + 1) hist[i] = 0;
        repeat (3) @(posedge clk);
        rst_n = 1;
        forever begin
            @(negedge clk);
            // consumers: count releases, check them (cyc = cycle index of the last posedge's inputs)
            for (j = 0; j < K; j = j + 1) if (rel[j] != rel_q[j]) begin
                nrel[j] = nrel[j] + 1;
                for (i = 0; i < K; i = i + 1) if (narr[i] < nrel[j]) errs = errs + 1;
                exp_lat = 0;
                for (i = 0; i < K; i = i + 1) if (t_arr[i][nrel[j]] + D[i][j] > exp_lat) exp_lat = t_arr[i][nrel[j]] + D[i][j];
                if (cyc - exp_lat < mind) mind = cyc - exp_lat;
                if (cyc - exp_lat > maxd) maxd = cyc - exp_lat;
                if (nrel[j] < NBAR) wake[j] = cyc + 1 + $urandom(seed) % WMAX;
            end
            rel_q = rel;
            for (i = 0; i < K; i = i + 1)
                if (narr[i] == nrel[i] && narr[i] < NBAR && cyc >= wake[i]) begin
                    sense[i] = ~sense[i]; narr[i] = narr[i] + 1; t_arr[i][narr[i]] = cyc + 1;
                end
            cyc = cyc + 1;
            hist[cyc % 64] = sense;
            done_cnt = 0;
            for (j = 0; j < K; j = j + 1) if (nrel[j] == NBAR) done_cnt = done_cnt + 1;
            if (done_cnt == K || cyc > NBAR * (WMAX + 4 * DMAX + 10)) begin
                $display("TXCOUNT_ARRIVAL k=%0d barriers=%0d dmax=%0d completed_all=%0d early_release_errors=%0d release_minus_last_link_arrival_min=%0d max=%0d cycles=%0d %s",
                         K, NBAR, DMAX, done_cnt == K, errs, mind, maxd, cyc, (done_cnt == K && errs == 0 && mind == maxd) ? "PASS" : "FAIL");
                $finish;
            end
        end
    end
endmodule
