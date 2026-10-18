`timescale 1ns/1ps
// S81U-1 bench for ot_dsdv_vstop: a statically scheduled V-rung trace in both directions, checked cycle-exactly against
// an independent model of the rung contract (ot_s81sl_rstop V format: header bit 0 valid, kind [3:1], XQ/XB = 4
// fragments, other kinds 1 beat).  The "compiler" builds the whole schedule up front: arrivals on vi_s / vi_n, then
// injections only into slots it knows are free (idle or a sunk header; 4 consecutive free slots for an XQ/XB beat).
// Expected vo at t+2 = injection ? injected : (free ? 0 : arrival); expected dl at t+2 = tapped/sunk single-beat header.
// Phase 2 injects into an occupied slot and requires the sticky fault.
// Prints VSTOP PASS / VSTOP FAIL <n>.  +seed=<n>, +n=<cycles>, +tap=<hex>, +sink=<hex>.
module tb_dsdv_vstop;
    localparam integer V = 276;
`ifndef MUT
    localparam integer MUT = 0;
`else
    localparam integer MUT = `MUT;
`endif
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [7:0] tap_k, sink_k;
    reg [V-1:0] vi_s, vi_n, in_n, in_s; reg in_nv, in_sv;
    wire [V-1:0] vo_n, vo_s, dl_n, dl_s; wire dl_nv, dl_sv, fault;
    ot_dsdv_vstop #(.V(V), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .dl_nv(dl_nv), .dl_n(dl_n), .dl_sv(dl_sv), .dl_s(dl_s),
        .in_nv(in_nv), .in_n(in_n), .in_sv(in_sv), .in_s(in_s), .fault(fault));

    localparam integer NMAX = 20000;
    // per direction d (0 = northbound, 1 = southbound): arrival, free, header-kind, inject valid / data
    reg [V-1:0] A [0:1][0:NMAX+7]; reg [V-1:0] I [0:1][0:NMAX+7];
    reg fr [0:1][0:NMAX+7]; reg iv [0:1][0:NMAX+7]; reg tp [0:1][0:NMAX+7];
    integer seed, seed0, n, d, t, k, r, errs, ninj, ntap, nsink, nfrag;
    function [V-1:0] rnd_v(input integer dummy);
        integer q; begin for (q = 0; q < V; q = q + 32) rnd_v[q +: 32] = $random(seed); end
    endfunction
    function [V-1:0] hdr(input [V-1:0] b, input [2:0] kd);
        begin hdr = b; hdr[0] = 1'b1; hdr[3:1] = kd; end
    endfunction
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1; seed0 = seed;
        if (!$value$plusargs("n=%d", n)) n = 12000;
        if (!$value$plusargs("tap=%h", tap_k)) tap_k = 8'h21;     // CTL (0) + SC (5)
        if (!$value$plusargs("sink=%h", sink_k)) sink_k = 8'h20;  // SC sunk (router scores end at the G-unit)
        errs = 0; ninj = 0; ntap = 0; nsink = 0; nfrag = 0;
        // ------------------------------------------------ the compiler's schedule
        for (d = 0; d < 2; d = d + 1) begin
            t = 0;
            while (t < n + 8) begin
                r = $random(seed) & 255;
                if (r < 100 || t >= n) begin A[d][t] = {V{1'b0}}; fr[d][t] = 1; tp[d][t] = 0; t = t + 1; end
                else if (r < 190) begin                              // single-beat header, kinds 0,3..7
                    k = $random(seed) & 7; if (k == 1 || k == 2) k = k + 4;
                    A[d][t] = hdr(rnd_v(0), k[2:0]);
                    fr[d][t] = sink_k[k]; tp[d][t] = tap_k[k] | sink_k[k]; t = t + 1;
                end else begin                                       // XQ / XB: header + 3 raw fragments
                    A[d][t] = hdr(rnd_v(0), (r & 1) ? 3'd1 : 3'd2); fr[d][t] = 0; tp[d][t] = 0;
                    for (k = 1; k < 4; k = k + 1) begin A[d][t + k] = rnd_v(0); fr[d][t + k] = 0; tp[d][t + k] = 0; end
                    t = t + 4; nfrag = nfrag + 1;
                end
            end
            for (t = 0; t < n + 8; t = t + 1) begin iv[d][t] = 0; I[d][t] = {V{1'b0}}; end
            t = 0;
            while (t < n - 4) begin
                r = $random(seed) & 255;
                if (fr[d][t] && fr[d][t+1] && fr[d][t+2] && fr[d][t+3] && r < 40) begin
                    I[d][t] = hdr(rnd_v(0), 3'd2); iv[d][t] = 1;
                    for (k = 1; k < 4; k = k + 1) begin I[d][t + k] = rnd_v(0); iv[d][t + k] = 1; end
                    t = t + 4; ninj = ninj + 1;
                end else begin
                    if (fr[d][t] && r < 120) begin k = $random(seed) & 7; if (k == 1 || k == 2) k = 0;
                        I[d][t] = hdr(rnd_v(0), k[2:0]); iv[d][t] = 1; ninj = ninj + 1; end
                    t = t + 1;
                end
            end
        end
        // ------------------------------------------------ drive + check (inputs change at negedge t, outputs checked at negedge t+2)
        vi_s = 0; vi_n = 0; in_n = 0; in_s = 0; in_nv = 0; in_sv = 0;
        repeat (3) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);
        for (t = 0; t < n + 2; t = t + 1) begin
            if (t < n) begin
                vi_s = A[0][t]; vi_n = A[1][t]; in_nv = iv[0][t]; in_n = I[0][t]; in_sv = iv[1][t]; in_s = I[1][t];
            end else begin vi_s = 0; vi_n = 0; in_nv = 0; in_sv = 0; end
            if (t >= 2) chk(t - 2);
            @(negedge clk);
        end
        if (fault) begin errs = errs + 1; $display("ERR fault raised on a legal schedule"); end
        // ------------------------------------------------ phase 2: illegal injection into an occupied slot
        vi_s = hdr(rnd_v(0), 3'd1); in_nv = 1; in_n = hdr(rnd_v(0), 3'd0);
        @(negedge clk); vi_s = 0; in_nv = 0; repeat (3) @(negedge clk);
        if (!fault) begin errs = errs + 1; $display("ERR collision not flagged"); end
        if (errs == 0) $display("VSTOP PASS seed=%0d n=%0d tap=%h sink=%h inj=%0d xbeats=%0d taps=%0d", seed0, n, tap_k, sink_k, ninj, nfrag, ntap);
        else $display("VSTOP FAIL %0d (MUT=%0d)", errs, MUT);
        $finish;
    end
    task chk(input integer u);
        reg [V-1:0] en, es; reg etn, ets;
        begin
            en = iv[0][u] ? I[0][u] : fr[0][u] ? {V{1'b0}} : A[0][u];
            es = iv[1][u] ? I[1][u] : fr[1][u] ? {V{1'b0}} : A[1][u];
            etn = (u < n) && tp[0][u]; ets = (u < n) && tp[1][u];
            if (u >= n) begin en = 0; es = 0; end
            if (vo_n !== en) begin errs = errs + 1; if (errs < 6) $display("ERR t=%0d vo_n", u); end
            if (vo_s !== es) begin errs = errs + 1; if (errs < 6) $display("ERR t=%0d vo_s", u); end
            if (dl_nv !== etn || (etn && dl_n !== A[0][u])) begin errs = errs + 1; if (errs < 6) $display("ERR t=%0d dl_n", u); end
            if (dl_sv !== ets || (ets && dl_s !== A[1][u])) begin errs = errs + 1; if (errs < 6) $display("ERR t=%0d dl_s", u); end
            ntap = ntap + etn + ets;
        end
    endtask
endmodule
