// tb_chip_v41_xcap_droop -- self-checking bench of the field-current controls (W18):
//  (1) ot_chip_v41_xcap + ot_chip_v41_xcap_take on a 4 x 4 checkerboard of pairs: every pair takes every word
//      exactly once and in order; a capped beat is taken by exactly half the pairs, an uncapped one by all;
//      random root stalls and spine back-pressure.
//  (2) ot_chip_v41_droop_ctrl on a random supply-code waveform: stretch is up within 2 cycles of a code below
//      the trip, is held >= cfg_min cycles, is released only after cfg_hold consecutive cycles at/above
//      cfg_release; the event counter matches; a sustained sag raises alarm.
`timescale 1ns/1ps
module tb_chip_v41_xcap_droop;
    localparam int W = 16, NP = 16, NW = 300;
    logic clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;                      // 1.2 GHz
    int errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    logic in_v = 0, in_rdy, in_cap = 0, xs_v, xs_sub, xs_cap, xs_rdy = 1;
    logic [W-1:0] in_d = 0, xs_d;
    ot_chip_v41_xcap #(.W(W)) u_cap (.clk, .rst_n, .in_v, .in_rdy, .in_cap, .in_d, .xs_v, .xs_sub, .xs_cap,
                                     .xs_d, .xs_rdy);
    logic [NP-1:0] take;
    genvar g;
    generate for (g = 0; g < NP; g++) begin : g_p
        ot_chip_v41_xcap_take u_t (.xs_v(xs_v && xs_rdy), .xs_sub, .cap(xs_cap), .ph(1'((g / 4 + g % 4) % 2)),
                                   .take(take[g]));
    end endgenerate
    logic [W-1:0] issued [$];
    int got [NP];
    int capped_beats = 0;
    always @(posedge clk) if (rst_n) begin
        if (in_v && in_rdy) issued.push_back(in_d);
        if (xs_v && xs_rdy) begin
            if (xs_cap && $countones(take) != NP / 2) begin errors++; $display("ERR capped beat %0d takers", $countones(take)); end
            if (!xs_cap && $countones(take) != NP) begin errors++; $display("ERR uncapped beat %0d takers", $countones(take)); end
            if (xs_cap) capped_beats++;
            for (int p = 0; p < NP; p++) if (take[p]) begin
                if (got[p] >= issued.size() || xs_d !== issued[got[p]]) begin
                    errors++; $display("ERR pair %0d word %h", p, xs_d); end
                got[p]++;
            end
        end
    end

    logic [7:0] code = 8'd200, cfg_trip = 8'd100, cfg_release = 8'd120, cfg_min = 8'd16, cfg_hold = 8'd8;
    logic [15:0] cfg_alarm = 16'd400, events, longest;
    logic stretch, alarm, en = 1;
    ot_chip_v41_droop_ctrl u_d (.clk, .rst_n, .en, .code, .cfg_trip, .cfg_release, .cfg_min, .cfg_hold, .cfg_alarm,
                                .stretch, .events, .longest, .alarm);
    logic [7:0] c1 = 8'd200, c2 = 8'd200;
    int st_len = 0, ok_run = 0, trips = 0;
    logic st_q = 0;
    always @(posedge clk) if (rst_n) begin
        c1 <= code; c2 <= c1;
        if (c2 < cfg_trip && !stretch && !st_q) begin errors++; $display("ERR no stretch 2 cycles after trip @%0d", cyc); end
        st_len <= stretch ? st_len + 1 : 0;
        if (st_q && !stretch) begin
            if (st_len < cfg_min) begin errors++; $display("ERR stretch %0d < min", st_len); end
            if (ok_run < cfg_hold) begin errors++; $display("ERR released after %0d ok cycles", ok_run); end
        end
        if (!st_q && stretch) trips++;
        ok_run <= (c1 >= cfg_release) ? ok_run + 1 : 0;
        st_q <= stretch;
    end

    int k = 0;
    initial begin
        foreach (got[p]) got[p] = 0;
        repeat (4) @(posedge clk); rst_n = 1;
        fork
            begin
                while (k < NW) begin
                    @(negedge clk);
                    if (!(in_v && !in_rdy)) begin              // hold a word until it is accepted
                        in_v = ($urandom_range(3) != 0);
                        if ((k % 20) == 0) in_cap = $urandom_range(1);
                        in_d = W'(k * 7 + 3);
                    end
                    @(posedge clk);
                    if (in_v && in_rdy) k++;
                end
                @(negedge clk) in_v = 0;
            end
            begin
                repeat (1500) begin @(negedge clk); xs_rdy = ($urandom_range(7) != 0); end
                xs_rdy = 1;
            end
            begin
                repeat (6000) begin
                    @(negedge clk);
                    if ($urandom_range(199) == 0) repeat ($urandom_range(40, 4)) begin
                        code = 8'($urandom_range(99, 60)); @(negedge clk); end
                    code = 8'($urandom_range(160, 118));
                end
                repeat (600) begin @(negedge clk); code = 8'd70; end
                code = 8'd200;
            end
        join
        repeat (20) @(posedge clk);
        for (int p = 0; p < NP; p++) if (got[p] != NW) begin errors++; $display("ERR pair %0d got %0d words", p, got[p]); end
        if (!alarm) begin errors++; $display("ERR sustained sag did not raise alarm"); end
        if (events != 16'(trips)) begin errors++; $display("ERR events %0d vs %0d", events, trips); end
        $display("W18_FIELD_RESULT words=%0d capped_beats=%0d stretch_events=%0d longest=%0d alarm=%0d errors=%0d",
                 NW, capped_beats, events, longest, alarm, errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
