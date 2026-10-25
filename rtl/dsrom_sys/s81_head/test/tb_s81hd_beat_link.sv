`timescale 1ns/1ps
// tb_s81hd_beat_link (S81-HEAD/ADAPT 2026-10-25): lockstep bench of ot_s81hd_beat_tx -> S plain relay registers ->
// ot_s81hd_beat_rx.  Phase A: NREC random words (all-0 / all-1 / random), back-to-back at the allowed rate (one word every
// N cycles) plus random gaps; every word must leave the RX exactly at t + N + 1 + S, bit-exact, in order, and no fault may
// rise.  Phase B (MUT 0): a word presented while beats are owed -> TX sticky fault, the dropped word never arrives.
// Phase C (MUT 0): direct RX injection (beat bi != 0 outside a word, dropped beat, beat-order swap, pad bit) -> RX fault
// sticky each time (RX reset between cases: control-only reset).  Prints one BEAT_LINK line: PASS / FAIL.
// A mutant run (MUT 1/2/3) must print FAIL (caught): phase A (MUT 1/2) or phase B (MUT 3) sees a mismatch, a missing
// word or an RX fault.
module tb_s81hd_beat_link;
    parameter integer W = 553, N = 2, S = 2, MUT = 0, NREC = 1200;
    localparam integer P = (W + N - 1) / N, BW = (N > 1) ? $clog2(N) : 1, PW = P + BW + 1;
    localparam integer LAT = N + 1 + S;
    reg ck = 0, rn = 0;
    always #1 ck = ~ck;
    reg tv; reg [W-1:0] td;
    wire [PW-1:0] to; wire tf;
    wire [PW-1:0] st [0:S];
    reg  inj; reg [PW-1:0] inj_w;
    wire [PW-1:0] ri = inj ? inj_w : st[S];
    wire rv; wire [W-1:0] rd; wire rf;
    ot_s81hd_beat_tx #(.W(W), .N(N), .MUT(MUT)) u_tx (.ck(ck), .rn(rn), .v(tv), .d(td), .o(to), .fault(tf));
    assign st[0] = to;
    genvar g;
    generate for (g = 1; g <= S; g = g + 1) begin : g_st   // plan relay stations (plain registers, no reset)
        reg [PW-1:0] q;
        always @(posedge ck) q <= st[g - 1];
        assign st[g] = q;
    end endgenerate
    ot_s81hd_beat_rx #(.W(W), .N(N)) u_rx (.ck(ck), .rn(rn), .i(ri), .v(rv), .d(rd), .fault(rf));

    reg [W-1:0] qw [0:65535]; integer qt [0:65535];
    integer qh = 0, qtl = 0, cyc = 0, errs = 0, got = 0, sent = 0, seed = 1, i, k, gap;
    reg chk_on = 1;
    // cyc = number of the rising edge about to come (updated on the falling edge: no race with the stimulus)
    always @(negedge ck) cyc <= cyc + 1;
    // a word presented (tv) before rising edge e is sampled by the TX at e; it must be the RX output word sampled at e + LAT
    reg dbg = 0;
    always @(posedge ck) if (dbg && cyc < 24) $display("DBG cyc %0d tv %b td0 %b to_v %b to_b %b ri_v %b rv %b rd0 %b rf %b", cyc, tv, td[0], to[P], to[P+1], ri[P], rv, rd[0], rf);
    always @(posedge ck) begin
        if (rn && chk_on && rv) begin
            if (qh == qtl) begin errs = errs + 1; if (errs < 5) $display("ERR unexpected word at %0d", cyc); end
            else begin
                if (rd !== qw[qh] || cyc != qt[qh]) begin
                    errs = errs + 1;
                    if (errs < 5) $display("ERR word %0d: cyc %0d want %0d data %s", qh, cyc, qt[qh], (rd === qw[qh]) ? "ok" : "BAD");
                end
                qh = qh + 1; got = got + 1;
            end
        end
    end
    function [W-1:0] rword(input integer kind);
        integer j; reg [W-1:0] x;
        begin
            for (j = 0; j < W; j = j + 32) x[j +: 32] = $random(seed);
            rword = (kind == 0) ? {W{1'b0}} : (kind == 1) ? {W{1'b1}} : x;
        end
    endfunction
    task send(input [W-1:0] w);
        begin
            tv <= 1; td <= w; qw[qtl] = w; qt[qtl] = cyc + 1 + LAT; qtl = qtl + 1; sent = sent + 1;
            @(posedge ck);      // tv stays 1 for a back-to-back word; the caller clears it on a gap
        end
    endtask
    reg [7:0] rxf;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if ($test$plusargs("dbg")) dbg = 1;
        tv = 0; td = 0; inj = 0; inj_w = 0;
        repeat (3) @(posedge ck); rn <= 1; repeat (2) @(posedge ck);
        // ---- phase A: lockstep exactness
        for (i = 0; i < NREC; i = i + 1) begin
            send(rword((i < 4) ? (i % 2) : 2));
            gap = ($random(seed) & 3) == 0 ? ($random(seed) & 7) : 0;
            if (N - 1 + gap > 0) begin tv <= 0; repeat (N - 1 + gap) @(posedge ck); end
        end
        tv <= 0;
        repeat (LAT + 4) @(posedge ck);
        if (got != NREC) begin errs = errs + 1; $display("ERR got %0d of %0d", got, NREC); end
        if (tf || rf) begin errs = errs + 1; $display("ERR fault in phase A tx %b rx %b", tf, rf); end
        rxf = 0;
        if (MUT == 0 || MUT == 3) begin
            // ---- phase B: TX rate violation (only meaningful for N > 1); MUT 3 (TX check removed): the RX must catch it
            chk_on = 0;
            if (N > 1) begin
                @(posedge ck); tv <= 1; td <= rword(2); @(posedge ck); tv <= 1; td <= rword(2); @(posedge ck); tv <= 0;
                repeat (LAT + 4) @(posedge ck);
                if (!tf) begin errs = errs + 1; $display("ERR TX rate violation not flagged"); end
                if (rf) begin errs = errs + 1; $display("ERR RX fault from a TX-dropped word"); end
            end
        end
        if (MUT == 0) begin
            // ---- phase C: RX injection, control-only reset between cases
            for (k = 0; k < 4; k = k + 1) begin
                rn <= 0; @(posedge ck); rn <= 1; @(posedge ck); inj <= 1; inj_w <= 0;
                case (k)
                  0: begin inj_w <= {BW'(N > 1 ? 1 : 0), 1'b1, P'(0)}; @(posedge ck); end                  // bi != 0 outside a word
                  1: begin inj_w <= {BW'(0), 1'b1, P'(0)}; @(posedge ck); inj_w <= 0; @(posedge ck); end    // dropped beat
                  2: begin inj_w <= {BW'(0), 1'b1, P'(0)}; @(posedge ck); inj_w <= {BW'(0), 1'b1, P'(0)}; @(posedge ck); end // order: 0,0
                  3: begin for (i = 0; i < N; i = i + 1) begin                                             // pad bit / last beat
                           inj_w <= {BW'(i), 1'b1, (i == N - 1) ? {1'b1, {(P-1){1'b0}}} : P'(0)}; @(posedge ck); end end
                endcase
                inj <= 0; inj_w <= 0; repeat (4) @(posedge ck);
                rxf[k] = rf;
            end
            // N = 1 has no order and no dropped-beat case; a pad bit exists only when N*P > W
            if (N > 1 && rxf[2:0] != 3'b111) begin errs = errs + 1; $display("ERR RX injection faults %b", rxf); end
            if ((N * P > W) && !rxf[3]) begin errs = errs + 1; $display("ERR RX pad fault missing"); end
        end
        $display("BEAT_LINK W=%0d N=%0d P=%0d S=%0d LAT=%0d MUT=%0d seed=%0d sent=%0d got=%0d txf=%b rxinj=%b errors=%0d %s",
                 W, N, P, S, LAT, MUT, seed, sent, got, tf, rxf, errs, errs == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
