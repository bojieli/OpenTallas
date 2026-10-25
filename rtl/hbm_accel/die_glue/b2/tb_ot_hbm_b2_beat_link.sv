`timescale 1ns/1ps
`default_nettype none
// HBM-BIND2 (2026-10-25) bench of the scheduled multi-beat lane (run_b2_beat_link.sh):
//   tb_b2_beat_link : ot_hbm_b2_beat_tx -> LANE-cycle registered lane -> ot_hbm_b2_beat_rx.  Random words, random
//                     valid bits, random spacing >= BEATS; every word must come out exactly BEATS + 1 + LANE edges after
//                     it went in, bit-exact, and v must be low elsewhere; no fault.  Then one close pair (spacing
//                     BEATS - 1, BEATS > 1): tx AND rx must raise fault.
// Prints "<NAME> ... checks=N errors=E PASS|FAIL".
module tb_b2_beat_link;
    parameter integer W = 320, NV = 3, BEATS = 3, LANE = 4, MUT = 0, N = 4000;
    localparam integer LW = (W + BEATS - 1) / BEATS;
    localparam integer LAT = BEATS + 1 + LANE;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg [NV-1:0] vin; reg [W-1:0] d;
    wire lv; wire [LW-1:0] ld; wire tf, rf, v; wire [W-1:0] q;
    ot_hbm_b2_beat_tx #(.W(W), .NV(NV), .BEATS(BEATS), .MUT(MUT)) tx (.clk(clk), .rst_n(rst_n), .vin(vin), .d(d), .lv(lv), .ld(ld), .fault(tf));
    // the plan lane: LANE registered stations (valid reset, data not)
    reg [LANE:0] lvp; reg [LW-1:0] ldp [0:LANE];
    integer k;
    always @(*) begin lvp[0] = lv; ldp[0] = ld; end
    always @(posedge clk) for (k = 1; k <= LANE; k = k + 1) begin lvp[k] <= rst_n ? lvp[k-1] : 1'b0; ldp[k] <= ldp[k-1]; end
    ot_hbm_b2_beat_rx #(.W(W), .BEATS(BEATS), .MUT(MUT)) rx (.clk(clk), .rst_n(rst_n), .lv(lvp[LANE]), .ld(ldp[LANE]), .v(v), .d(q), .fault(rf));
    // expected outputs by edge index
    reg [W-1:0] exp_d [0:N+LAT+8]; reg exp_v [0:N+LAT+8];
    integer t, gap, errs = 0, checks = 0, words = 0;
    function automatic [W-1:0] rnd_w(input integer u); reg [W+31:0] x; integer j; begin x = 0; for (j = 0; j < W; j = j + 32) x[j +: 32] = $random; rnd_w = x[W-1:0]; end endfunction
    initial begin
        for (t = 0; t <= N + LAT + 8; t = t + 1) exp_v[t] = 0;
        vin = 0; d = 0;
        repeat (3) @(posedge clk);
        #0.2 rst_n = 1;
        gap = 0;
        for (t = 0; t < N + LAT + 4; t = t + 1) begin
            @(negedge clk);
            // the DUT now shows edge t's result
            if (t >= 1) begin
                checks = checks + 1;
                if (v !== exp_v[t] || (exp_v[t] && q !== exp_d[t]) || tf !== 1'b0 || rf !== 1'b0) begin
                    errs = errs + 1;
                    if (errs < 6) $display("MISMATCH t=%0d v=%b exp=%b tf=%b rf=%b", t, v, exp_v[t], tf, rf);
                end
            end
            // drive edge t+1's inputs: a word every >= BEATS edges, random
            vin = 0; d = rnd_w(0);
            if (t < N && gap <= 0 && ($random & 1)) begin
                vin = $random; if (vin == 0) vin = 1;
                d[NV-1:0] = vin;
                exp_v[t + LAT] = 1; exp_d[t + LAT] = d;
                gap = BEATS - 1 + ($random & 3); words = words + 1;
            end else gap = gap - 1;
        end
        // close pair: must fault on both ends (BEATS > 1)
        if (BEATS > 1) begin
            @(negedge clk); vin = 1; d = rnd_w(0);
            @(negedge clk); vin = 0;
            repeat (BEATS - 2) @(negedge clk);
            vin = 1; d = rnd_w(0);
            @(negedge clk); vin = 0;
            repeat (LAT + 4) @(negedge clk);
            checks = checks + 1;
            if (tf !== 1'b1 || rf !== 1'b1) begin errs = errs + 1; $display("CLOSE PAIR not faulted tf=%b rf=%b", tf, rf); end
        end
        $display("B2_BEAT_LINK W=%0d NV=%0d BEATS=%0d LANE=%0d MUT=%0d words=%0d checks=%0d errors=%0d %s", W, NV, BEATS, LANE,
                 MUT, words, checks, errs, errs == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
`default_nettype wire
