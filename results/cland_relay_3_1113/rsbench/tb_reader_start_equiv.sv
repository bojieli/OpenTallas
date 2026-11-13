// CLAND-RELAY-2 reader-START relay equivalence (the reach-default form of hd_turn_b t_i / hd_spn_wshim_rx link_i):
// CLAND-RELAY-3: RSN = RSTREP of A (default 19 = 1 + 2 x 9 chunks, RSTH-1 half-chunk copies; 10 = CLAND-RELAY-2 form)
// A = cas W568 D4 WREG1 DSREP8 RSTREP RSN PLACEREP1, rst_n and rst_xn from ot_dp_landing_relay_rep N RSN (d = START,
//     rst_raw_n = the ring reset relay), strap K-1 (reader_start_depth 1: K_adjustment -1);
// C = cas W568 D4 WREG1 DSREP8 (the rp18 kit form), rst_n = START raw, strap K.
// PASS: once both are ready, q(A) == q(C) on EVERY clk edge (same word on the same edge = 0 data cycles), no fault,
// for every case where C (the as-built form) arms without fault, A arms on the SAME edge without fault.  +define+TB_MUT_K: A keeps strap K (must FAIL).
`timescale 1ps/1ps
`ifndef RSN
`define RSN 19
`endif
module tb;
    localparam int W = 568, D = 4, KW = $clog2(D) + 4;
    int seed, ncase, phase, fs_at, rs_at, k, errs = 0, nready = 0, nmatch = 0, fra, frc, boot_ok = 0, nfa = 0, nfc = 0, nvalid = 0, cfa, cfc;
    logic fclk = 0, clk = 0, fstart = 0, start = 0, raw_n = 0;
    logic [W-1:0] d;
    wire [W-1:0] qa, qc; wire ra, rc, fa, fc;
    wire rs_q; wire [`RSN-1:0] rs_x;
    logic [KW-1:0] ka, kc;
    ot_dp_landing_relay_rep #(.N(`RSN)) u_rs (.clk(clk), .rst_raw_n(raw_n), .d(start), .q(rs_q), .qx(rs_x));
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(D), .WREG(1), .DSREP(8), .RSTREP(`RSN), .PLACEREP(1)) u_a (.fclk(fclk), .t_rst_n(fstart),
        .clk(clk), .rst_n(rs_q), .strap_k(ka), .rst_xn(rs_x), .d(d), .q(qa), .ready(ra), .fault(fa));
    ot_dp_clk_landing_cas #(.W(W), .DEPTH(D), .WREG(1), .DSREP(8)) u_c (.fclk(fclk), .t_rst_n(fstart),
        .clk(clk), .rst_n(start), .strap_k(kc), .d(d), .q(qc), .ready(rc), .fault(fc));
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("n=%d", ncase)) ncase = 200;
        for (int t = 0; t < ncase; t++) begin
            phase = 50 + $urandom(seed + t) % 700;
            fs_at = 2 + $urandom % 20; rs_at = $urandom % 2; k = 2 + $urandom % 3;
`ifdef TB_MUT_K
            ka = KW'(k);
`else
            ka = KW'(k - 1);
`endif
            kc = KW'(k);
            fstart = 0; start = 0; raw_n = 0; fra = -1; frc = -1; cfa = 0; cfc = 0;
            fork
                begin
                    for (int c = 0; c < 160; c++) begin
                        #416 fclk = 1;
                        #417 fclk = 0;
                        d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                             $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                        if (c == fs_at) fstart = 1;
                    end
                end
                begin
                    #(phase);
                    for (int c = 0; c < 160; c++) begin
                        #416 clk = 1;
                        #1;
                        if (ra && fra < 0) fra = c; if (rc && frc < 0) frc = c;
                        if (fa) begin nfa++; cfa++; end if (fc) begin nfc++; cfc++; end
                        if (ra && rc) begin
                            nready++;
                            if (qa === qc && !fa && !fc) nmatch++;
                            else begin if (errs < 5) $display("MISMATCH A/C case %0d cyc %0d", t, c); errs++; end
                        end
                        #416 clk = 0;
                        if (c == 1) raw_n = 1;
                        if (c == fs_at + rs_at) start = 1;
                    end
                end
            join
            if (frc >= 0 && cfc == 0) begin
                nvalid++;
                if (fra == frc && cfa == 0) boot_ok++;
                else begin if (errs < 8) $display("ARM case %0d firstA %0d firstC %0d faultsA %0d", t, fra, frc, cfa); errs++; end
            end
            if (t < 8) $display("case %0d k %0d phase %0d firstA %0d firstC %0d", t, k, phase, fra, frc);
            fstart = 0; start = 0; raw_n = 0;
            repeat (12) begin #416 fclk = 1; #1 clk = 1; #416 fclk = 0; clk = 0; end
        end
        $display("READER_START_EQUIV cases=%0d valid_C=%0d same_arm_A=%0d ready_cycles_AC=%0d match_AC=%0d fault_edges_A=%0d fault_edges_C=%0d errors=%0d %s",
                 ncase, nvalid, boot_ok, nready, nmatch, nfa, nfc, errs, (errs == 0 && nvalid > 0 && nready > 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
