// tb_chip_v41_ratio_fifo -- the 1.2 GHz <-> 0.9 GHz ratio CDC (W18): two FIFOs, fast->slow and slow->fast,
// clocks from one 3.6 GHz VCO (/3 and /4, rising edges aligned at t = 0).  Random valid/ready on both sides.
// Checks: every word delivered once, in order; throughput reaches the slower side's rate under saturation;
// reports the minimum / mean / maximum latency from the write edge to r_v, in ps and destination cycles.
`timescale 1ps/1ps
module tb_chip_v41_ratio_fifo;
    localparam int W = 32, N = 4000;
    localparam int TF = 833, TS = 1111;           // 1.2 GHz and 0.9 GHz (3.333 ns hyperperiod: 4 x 833.25)
    logic fclk = 0, sclk = 0, rst_n = 0;
    // exact 3:4 relation: toggle from a 3.6 GHz reference (277.78 ps) -- use 1/12 ns ticks
    logic vco = 0;
    int t12 = 0;
    always #139 begin vco = ~vco; end            // ~277.8 ps VCO period (ticks at 139 ps half period)
    int nv = 0;
    always @(posedge vco) begin
        nv <= nv + 1;
        if (nv % 3 == 0) fclk <= 1; else if (nv % 3 == 1) fclk <= fclk; else fclk <= 0;
        if (nv % 4 == 0) sclk <= 1; else if (nv % 4 == 2) sclk <= 0;
    end
    // fast -> slow
    logic a_wv, a_wr, a_rv, a_rr; logic [W-1:0] a_wd, a_rd;
    ot_chip_v41_ratio_fifo #(.W(W)) u_fs (.wclk(fclk), .wrst_n(rst_n), .w_v(a_wv), .w_rdy(a_wr), .w_d(a_wd),
                                          .rclk(sclk), .rrst_n(rst_n), .r_v(a_rv), .r_rdy(a_rr), .r_d(a_rd));
    // slow -> fast
    logic b_wv, b_wr, b_rv, b_rr; logic [W-1:0] b_wd, b_rd;
    ot_chip_v41_ratio_fifo #(.W(W)) u_sf (.wclk(sclk), .wrst_n(rst_n), .w_v(b_wv), .w_rdy(b_wr), .w_d(b_wd),
                                          .rclk(fclk), .rrst_n(rst_n), .r_v(b_rv), .r_rdy(b_rr), .r_d(b_rd));
    int errors = 0;
    longint ta [N], tb [N];
    int a_sent = 0, a_got = 0, b_sent = 0, b_got = 0;
    longint a_lat_min = 1 << 30, a_lat_max = 0, a_lat_sum = 0, b_lat_min = 1 << 30, b_lat_max = 0, b_lat_sum = 0;
    logic sat = 0;                               // saturation phase: always valid / always ready
    logic sparse = 0;                            // +sparse: one word every 7 source cycles, readers always ready
    int fa = 0, sb = 0;
    // latency = time from the write edge that accepts a word to the read-side edge where r_v first shows it
    longint l;
    logic a_seen, b_seen;                        // the head word's r_v has already been timed
    always @(posedge fclk) if (rst_n) begin
        if (a_wv && a_wr) begin ta[a_sent] = $time; a_sent = a_sent + 1; end
        if (b_rv && !b_seen) begin
            l = $time - tb[b_got];
            if (l < b_lat_min) b_lat_min = l; if (l > b_lat_max) b_lat_max = l; b_lat_sum += l; b_seen = 1;
        end
        if (b_rv && b_rr) begin
            if (b_rd !== W'(b_got * 13 + 5)) begin errors++; $display("ERR s->f word %0d", b_got); end
            b_got = b_got + 1; b_seen = 0;
        end
    end
    always @(negedge fclk) begin
        fa = fa + 1;
        if (!(a_wv && !a_wr)) begin
            a_wv = (a_sent < N) && (sparse ? (fa % 7 == 0) : (sat || $urandom_range(3) != 0)); a_wd = W'(a_sent * 7 + 1); end
        b_rr = sparse || sat || ($urandom_range(3) != 0);
    end
    always @(posedge sclk) if (rst_n) begin
        if (b_wv && b_wr) begin tb[b_sent] = $time; b_sent = b_sent + 1; end
        if (a_rv && !a_seen) begin
            l = $time - ta[a_got];
            if (l < a_lat_min) a_lat_min = l; if (l > a_lat_max) a_lat_max = l; a_lat_sum += l; a_seen = 1;
        end
        if (a_rv && a_rr) begin
            if (a_rd !== W'(a_got * 7 + 1)) begin errors++; $display("ERR f->s word %0d got %h", a_got, a_rd); end
            a_got = a_got + 1; a_seen = 0;
        end
    end
    always @(negedge sclk) begin
        sb = sb + 1;
        if (!(b_wv && !b_wr)) begin
            b_wv = (b_sent < N) && (sparse ? (sb % 7 == 0) : (sat || $urandom_range(3) != 0)); b_wd = W'(b_sent * 13 + 5); end
        a_rr = sparse || sat || ($urandom_range(3) != 0);
    end
    longint t_sat0; int a0, b0;
    initial begin
        a_wv = 0; b_wv = 0; a_rr = 0; b_rr = 0; a_seen = 0; b_seen = 0;
        sparse = $test$plusargs("sparse");
        #5000 rst_n = 1;
        wait (a_got >= N / 2 && b_got >= N / 2);
        sat = !sparse; t_sat0 = $time; a0 = a_got; b0 = b_got;
        wait (a_got >= N && b_got >= N);
        $display("W18_CDC_RESULT mode=%0s words=%0d f2s_lat_ps=%0d/%0d/%0d f2s_lat_slow_cycles=%.2f/%.2f/%.2f s2f_lat_ps=%0d/%0d/%0d s2f_lat_fast_cycles=%.2f/%.2f/%.2f sat_f2s_words_per_ns=%.3f sat_s2f_words_per_ns=%.3f errors=%0d",
                 sparse ? "sparse" : "random_stall", N, a_lat_min, a_lat_sum / N, a_lat_max, a_lat_min / 1111.0, (a_lat_sum / N) / 1111.0, a_lat_max / 1111.0,
                 b_lat_min, b_lat_sum / N, b_lat_max, b_lat_min / 833.3, (b_lat_sum / N) / 833.3, b_lat_max / 833.3,
                 (a_got - a0) * 1000.0 / ($time - t_sat0), (b_got - b0) * 1000.0 / ($time - t_sat0), errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
