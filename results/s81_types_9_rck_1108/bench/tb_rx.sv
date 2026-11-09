`timescale 1ns/1ps
// S81-TYPES-9-RCK 11-08: RX decoder (RX-SYN + RX-BACK cores in ot_s81_rck_dec) new forms vs the current RTL, lock-step.
// The PMA stream is a real KP4 frame stream (ot_s81_kp4_enc, current RTL) with injected symbol errors: 0..12 symbol
// errors per frame (correctable), bursts of 16..40 (uncorrectable), and AM slips (bit shifts: relock).  All four region
// clocks are one clock (single-clock cores).  SHIFT = the expected q_* latency change in clocks (1 with
// OT_S81_RCK_RX_SPCYC, 0 otherwise): q_v/q_d/q_first/q_unc/q_nerr/q_seq/n_corr/n_unc of the new decoder equal the current
// decoder's SHIFT clocks later; lock/n_relock equal on the same clock.  A window of 16 clocks after each rst_n edge is
// not compared.
`ifndef SHIFT
`define SHIFT 0
`endif
module tb;
    reg clk = 0;
    always #0.4165 clk = ~clk;
    reg rst_n = 0, tx_v = 0, erst_n = 0;
    reg [511:0] tx_d = 0;
    wire e_v; wire [543:0] e_d; wire e_f;
    ot_s81_kp4_enc_r G (.clk(clk), .rst_n(erst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(e_v), .p_d(e_d), .fault(e_f));
    reg [543:0] err = 0, p_d = 0, slipbuf = 0; reg p_v = 0;
    integer nerr = 0, mode = 0, slip = 0, b, s;
    // error pattern for the current word: in mode 1 each word gets a symbol error with probability ~1/1 per 10 symbols...
    always @(posedge clk) begin
        err = 0;
        if (mode == 1) begin for (b = 0; b < 2; b = b + 1) if (($urandom % 100) < 45) begin s = $urandom % 54; err[s * 10 +: 10] = $urandom; end end
        if (mode == 2) begin for (b = 0; b < 4; b = b + 1) begin s = $urandom % 54; err[s * 10 +: 10] = $urandom | 1; end end
        slipbuf <= e_d;
        p_v <= e_v;
        p_d <= ((slip != 0) ? {e_d[542:0], slipbuf[543]} : e_d) ^ err;
    end
    wire qv_r, qv_n, qf_r, qf_n, qu_r, qu_n, lk_r, lk_n;
    wire [511:0] qd_r, qd_n; wire [4:0] ne_r, ne_n; wire [7:0] sq_r, sq_n;
    wire [31:0] nc_r, nc_n, nu_r, nu_n, nr_r, nr_n;
    ot_s81_rck_dec_r R (.rst_n(rst_n), .p_v(p_v), .p_d(p_d), .q_v(qv_r), .q_d(qd_r), .q_first(qf_r), .q_unc(qu_r), .q_nerr(ne_r),
        .q_seq(sq_r), .lock(lk_r), .n_corr(nc_r), .n_unc(nu_r), .n_relock(nr_r), .ck_syn(clk), .ck_dly(clk), .ck_chn(clk), .ck_out(clk));
    ot_s81_rck_dec_n N (.rst_n(rst_n), .p_v(p_v), .p_d(p_d), .q_v(qv_n), .q_d(qd_n), .q_first(qf_n), .q_unc(qu_n), .q_nerr(ne_n),
        .q_seq(sq_n), .lock(lk_n), .n_corr(nc_n), .n_unc(nu_n), .n_relock(nr_n), .ck_syn(clk), .ck_dly(clk), .ck_chn(clk), .ck_out(clk));
    // the current decoder's q-side outputs delayed by SHIFT clocks
    localparam integer QW = 1 + 512 + 1 + 1 + 5 + 8 + 32 + 32;
    wire [QW-1:0] q_r = {qv_r, qd_r, qf_r, qu_r, ne_r, sq_r, nc_r, nu_r};
    wire [QW-1:0] q_n = {qv_n, qd_n, qf_n, qu_n, ne_n, sq_n, nc_n, nu_n};
    reg  [QW-1:0] q_d1 = 0, q_d2 = 0;
    always @(posedge clk) begin q_d1 <= q_r; q_d2 <= q_d1; end
    wire [QW-1:0] q_ref = (`SHIFT == 0) ? q_r : (`SHIFT == 1) ? q_d1 : q_d2;
    reg rst_q = 0;
    integer mask = 0, checks = 0, bad = 0, nqv = 0, nunc = 0, nfix = 0, nlock = 0, cyc = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        rst_q <= rst_n;
        if (rst_q != rst_n) mask <= 16; else if (mask > 0) mask <= mask - 1;
        if (mask == 0 && rst_n && cyc > 8) begin
            checks <= checks + 1;
            if (q_n !== q_ref || lk_n !== lk_r || nr_n !== nr_r) begin
                bad = bad + 1;
                if (bad < 10) $display("BAD cyc=%0d qv %b/%b qd %0d meta %0d lock %b/%b nrel %0d/%0d", cyc, qv_n, q_ref[QW-1],
                    qd_n !== q_ref[QW-2 -: 512], q_n[QW-514:0] !== q_ref[QW-514:0], lk_n, lk_r, nr_n, nr_r);
            end
            if (qv_r) nqv <= nqv + 1;
            if (qv_r && qu_r) nunc <= nunc + 1;
            if (qv_r && !qu_r && ne_r != 0) nfix <= nfix + 1;
            if (lk_r) nlock <= nlock + 1;
        end
    end
    integer ph;
    initial begin
        for (ph = 0; ph < 5; ph = ph + 1) begin
            @(negedge clk); rst_n = 0; erst_n = 0; tx_v = 0; mode = 0; slip = 0;
            repeat (12) @(negedge clk);
            erst_n = 1; rst_n = 1;
            repeat (2 * ph) @(negedge clk);
            tx_v = 1;
            repeat (1500) begin @(negedge clk); tx_d = {16{$urandom}}; end
            mode = 1; repeat (2000) begin @(negedge clk); tx_d = {16{$urandom}}; end
            mode = 2; repeat (400) begin @(negedge clk); tx_d = {16{$urandom}}; end
            mode = 1; repeat (800) begin @(negedge clk); tx_d = {16{$urandom}}; end
            if (ph == 2 || ph == 4) begin slip = 1; repeat (300) begin @(negedge clk); tx_d = {16{$urandom}}; end slip = 0; end
            mode = 0; repeat (1200) begin @(negedge clk); tx_d = {16{$urandom}}; end
        end
        $display("RX_RESULT shift=%0d checks=%0d errors=%0d q_v=%0d corrected=%0d uncorrectable=%0d locked=%0d n_relock=%0d n_corr=%0d n_unc=%0d",
                 `SHIFT, checks, bad, nqv, nfix, nunc, nlock, nr_r, nc_r, nu_r);
        if (bad != 0 || nqv < 5000 || nfix < 100 || nunc < 20 || nlock < 5000) $fatal(1, "RX lockstep FAILED");
        $display("RX lockstep PASS");
        $finish;
    end
endmodule
