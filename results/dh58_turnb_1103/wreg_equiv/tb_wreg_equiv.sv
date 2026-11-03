// DH58-TURNB WREG-1/DSREP-1 equivalence: A = cas WREG=1 DSREP=4 (strap K), B = cas WREG=0 DSREP=1 fed by t_rst_n through
// one wclk flop (strap K): q/ready/fault must be equal on every clk edge (exact).  C = cas WREG=0 with the raw t_rst_n and
// strap K-1 (the W1 bind rule K_new = K_old + 1): once both are ready, q(A) == q(C) and neither faults.
`timescale 1ps/1ps
module tb;
    localparam int W = 568, D = 4, KW = $clog2(D) + 4;
    int fra, frc, nrc = 0, nfa = 0, nfc = 0, nra = 0, seed, ncase, phase, fs_at, rs_at, k, errs = 0, cyc, nready = 0, nmatch = 0;
    logic fclk = 0, clk = 0, fstart = 0, rst_n = 0, fs_d = 0;
    logic [W-1:0] d;
    wire [W-1:0] qa, qb, qc; wire ra, rb, rc, fa, fb, fc;
    logic [KW-1:0] ka, kc;
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(D), .WREG(1), .DSREP(4)) u_a (.fclk(fclk), .t_rst_n(fstart), .clk(clk), .rst_n(rst_n),
        .strap_k(ka), .d(d), .q(qa), .ready(ra), .fault(fa));
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(D)) u_b (.fclk(fclk), .t_rst_n(fs_d), .clk(clk), .rst_n(rst_n),
        .strap_k(ka), .d(d), .q(qb), .ready(rb), .fault(fb));
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(D)) u_c (.fclk(fclk), .t_rst_n(fstart), .clk(clk), .rst_n(rst_n),
        .strap_k(kc), .d(d), .q(qc), .ready(rc), .fault(fc));
    always @(posedge fclk) fs_d <= fstart;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("n=%d", ncase)) ncase = 200;

        for (int t = 0; t < ncase; t++) begin
            phase = 50 + $urandom(seed + t) % 700;          // clk lags fclk by phase ps (period 833)
            fs_at = 2 + $urandom % 20; rs_at = $urandom % 2; k = 1 + $urandom % 3;
            ka = KW'(k); kc = KW'(k - 1);
            fstart = 0; rst_n = 0; fs_d = 0; fra = -1; frc = -1;
            // run both clocks for 140 cycles
            fork
                begin
                    for (int c = 0; c < 140; c++) begin
                        #416 fclk = 1;
                        #417 fclk = 0; d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                                            $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                                            $urandom, $urandom};
                        if (c == fs_at) fstart = 1;
                    end
                end
                begin
                    #(phase);
                    for (int c = 0; c < 140; c++) begin
                        #416 clk = 1;
                        #1;
                        if (qa !== qb || ra !== rb || fa !== fb) begin
                            if (errs < 5) $display("MISMATCH A/B case %0d cyc %0d ready %b/%b fault %b/%b", t, c, ra, rb, fa, fb);
                            errs++;
                        end
                        if (ra && fra < 0) fra = c; if (rc && frc < 0) frc = c;
                        if (ra) nra++; if (rc) nrc++; if (fa) nfa++; if (fc) nfc++;
                        if (t == 0 && (c == 45 || c == 100)) $display("c%0d ra %b rc %b fa %b fc %b qa==qc %b", c, ra, rc, fa, fc, qa === qc);
                        if (ra && rc) begin
                            nready++;
                            if (qa === qc && !fa && !fc) nmatch++;
                            else begin if (errs < 5) $display("MISMATCH A/C case %0d cyc %0d", t, c); errs++; end
                        end
                        #416 clk = 0;
                        if (c == fs_at + rs_at) rst_n = 1;
                    end
                end
            join
            if (t < 12) $display("case %0d k %0d phase %0d rs %0d firstA %0d firstC %0d", t, k, phase, rs_at, fra, frc);
            // reset state between cases: hold starts low for a few cycles
            fstart = 0; rst_n = 0;
            repeat (12) begin #416 fclk = 1; #1 clk = 1; #416 fclk = 0; clk = 0; end
        end
        $display("ready_A=%0d ready_C=%0d fault_A=%0d fault_C=%0d", nra, nrc, nfa, nfc);
        $display("WREG_EQUIV cases=%0d ready_cycles_AC=%0d match_AC=%0d errors=%0d %s", ncase, nready, nmatch, errs,
                 (errs == 0 && nready > 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
