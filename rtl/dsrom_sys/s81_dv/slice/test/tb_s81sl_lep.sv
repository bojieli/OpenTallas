`timescale 1ns/1ps
// RTL-BUILD-S81 (2026-10-18): link-port bench of the end-slice master.  Two dies, each = ot_s81sl_lep + the two
// hardened link lane tiles (die A: dsfd_coll_lane_w = a W end, die B: dsfd_coll_lane_e = an E end) + two ot_pdie_ucie
// (behavioural PMA; lane 1 has a longer PMA latency than lane 0 so the two halves of a beat arrive skewed).
// Both directions run at once: random 1,104-b ring beats (bit 0 = valid) are presented on each die's outward port
// `ro` at a Bernoulli rate below the lane rate plus back-to-back bursts; every beat must leave the peer's `ri`
// bit-exact and in order, with no fault.  Then an over-rate burst must raise A's sticky fault (landing overflow).
// +define+TB_LEP_NH (S81-LEPV): both dies use the host-less leaf top ot_s81sl_lep_nh (HOST_EN 0, no host ports).
// Verdict: "PASS lep ..." or "FAIL lep ...".
`ifdef TB_LEP_NH
`define TB_LEP_M ot_s81sl_lep_nh
`define TB_LEP_HOST
`define TB_LEP_ST(a, b)
`else
`define TB_LEP_M ot_s81sl_lep
`define TB_LEP_HOST .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
`define TB_LEP_ST(a, b) .l0_st(a), .l1_st(b),
`endif
module tb_s81sl_lep #(parameter integer N = 1000, parameter integer SEED = 1, parameter integer WAIT = 8000);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    reg [1103:0] a_ro = 0, b_ro = 0; wire [1103:0] a_ri, b_ri; wire a_f, b_f;
    // ---- die A (W end)
    wire a0v, a0r, a1v, a1r, ai0v, ai0r, ai1v, ai1r; wire [552:0] a0d, a1d, ai0d, ai1d; wire [2:0] af0, af1; wire [1:0] arxv;
    wire b0v, b0r, b1v, b1r, bi0v, bi0r, bi1v, bi1r; wire [552:0] b0d, b1d, bi0d, bi1d; wire [2:0] bf0, bf1; wire [1:0] brxv;
    wire [511:0] atx0, atx1, btx0, btx1, arx0, arx1, brx0, brx1; wire [1:0] ast0, ast1, bst0, bst1;
    wire [512:0] pa0, pa1, pb0, pb1; wire ta0, ta1, tb0, tb1;
    `TB_LEP_M la (.clk(clk), .rst_n(rst_n), .ro(a_ro), .ri(a_ri),
        .lo0_v(a0v), .lo0_r(a0r), .lo0_d(a0d), .lo1_v(a1v), .lo1_r(a1r), .lo1_d(a1d),
        .li0_v(ai0v), .li0_r(ai0r), .li0_d(ai0d), .li1_v(ai1v), .li1_r(ai1r), .li1_d(ai1d), .rxv(arxv),
        .sl_f(1'b0), .l0_f(af0), .l1_f(af1), `TB_LEP_ST(ast0, ast1)
        `TB_LEP_HOST .fault(a_f));
    dsfd_coll_lane_w #(.LCR(1)) a_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({ast0[0], ast0[1], arx0, arxv[0]}), .tx(atx0), .tf(),
        .lo_v(a0v), .lo_r(a0r), .lo_d(a0d), .li_v(ai0v), .li_r(ai0r), .li_d(ai0d), .flt(af0));
    dsfd_coll_lane_w #(.LCR(1)) a_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({ast1[0], ast1[1], arx1, arxv[1]}), .tx(atx1), .tf(),
        .lo_v(a1v), .lo_r(a1r), .lo_d(a1d), .li_v(ai1v), .li_r(ai1r), .li_d(ai1d), .flt(af1));
    `TB_LEP_M lb (.clk(clk), .rst_n(rst_n), .ro(b_ro), .ri(b_ri),
        .lo0_v(b0v), .lo0_r(b0r), .lo0_d(b0d), .lo1_v(b1v), .lo1_r(b1r), .lo1_d(b1d),
        .li0_v(bi0v), .li0_r(bi0r), .li0_d(bi0d), .li1_v(bi1v), .li1_r(bi1r), .li1_d(bi1d), .rxv(brxv),
        .sl_f(1'b0), .l0_f(bf0), .l1_f(bf1), `TB_LEP_ST(bst0, bst1)
        `TB_LEP_HOST .fault(b_f));
    dsfd_coll_lane_e #(.LCR(1)) b_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({bst0[0], bst0[1], brx0, brxv[0]}), .tx(btx0), .tf(),
        .lo_v(b0v), .lo_r(b0r), .lo_d(b0d), .li_v(bi0v), .li_r(bi0r), .li_d(bi0d), .flt(bf0));
    dsfd_coll_lane_e #(.LCR(1)) b_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({bst1[0], bst1[1], brx1, brxv[1]}), .tx(btx1), .tf(),
        .lo_v(b1v), .lo_r(b1r), .lo_d(b1d), .li_v(bi1v), .li_r(bi1r), .li_d(bi1d), .flt(bf1));
    // UCIe macros: lane 0 PMA latency 2, lane 1 PMA latency 9 (lane skew 14 cycles round trip)
    ot_pdie_ucie #(.PMA_LAT(2)) ua0 (.clk(clk), .rst(rst_n), .tx(atx0), .rx(arx0), .st(ast0), .pma_tx(pa0), .pma_tck(ta0), .pma_rx(pb0), .pma_rck(tb0));
    ot_pdie_ucie #(.PMA_LAT(2)) ub0 (.clk(clk), .rst(rst_n), .tx(btx0), .rx(brx0), .st(bst0), .pma_tx(pb0), .pma_tck(tb0), .pma_rx(pa0), .pma_rck(ta0));
    ot_pdie_ucie #(.PMA_LAT(9)) ua1 (.clk(clk), .rst(rst_n), .tx(atx1), .rx(arx1), .st(ast1), .pma_tx(pa1), .pma_tck(ta1), .pma_rx(pb1), .pma_rck(tb1));
    ot_pdie_ucie #(.PMA_LAT(9)) ub1 (.clk(clk), .rst(rst_n), .tx(btx1), .rx(brx1), .st(bst1), .pma_tx(pb1), .pma_tck(tb1), .pma_rx(pa1), .pma_rck(ta1));

    // ---- scoreboards
    reg [1103:0] qa [0:4095]; reg [1103:0] qb [0:4095];   // A->B beats sent / B->A beats sent
    integer na = 0, nb = 0, ra = 0, rb = 0, bad = 0, cyc = 0, last_rx = 0;
    integer seed; reg chk = 1;
    function automatic [1103:0] rbeat(input integer dummy);
        integer i; reg [1103:0] b;
        begin for (i = 0; i < 34; i = i + 1) b[i * 32 +: 32] = $urandom; b[1103:1088] = $urandom; b[0] = 1'b1; rbeat = b; end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (b_ri[0]) begin
            if (ra >= na || b_ri !== qa[ra]) begin
                bad = bad + 1;
                if (bad < 6 && chk) $display("MISMATCH A->B beat %0d at cycle %0d: got %h.. exp %h..", ra, cyc, b_ri[63:0], qa[ra][63:0]);
            end
            ra = ra + 1; last_rx = cyc;
        end
        if (a_ri[0]) begin
            if (rb >= nb || a_ri !== qb[rb]) begin
                bad = bad + 1;
                if (bad < 6 && chk) $display("MISMATCH B->A beat %0d at cycle %0d: got %h.. exp %h..", rb, cyc, a_ri[63:0], qb[rb][63:0]);
            end
            rb = rb + 1; last_rx = cyc;
        end
    end
    integer k, burst, f_main, ofl_seen, bad_main, ra_m, rb_m;
    initial begin
        seed = SEED; void'($urandom(seed));
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);                     // link-up: gearbox lock + first reverse frames
        // main phase: rate 0.55 + one back-to-back burst a direction (400 A->B, 200 B->A: ~95 / ~48 flits staged)
        burst = 0;
        while (na < N || nb < N) begin
            @(negedge clk);
            a_ro = 0; b_ro = 0;
            if (na < N && (na >= 200 && na < 600 || ($urandom % 100) < 55)) begin a_ro = rbeat(0); qa[na] = a_ro; na = na + 1; end
            if (nb < N && (nb >= 500 && nb < 700 || ($urandom % 100) < 55)) begin b_ro = rbeat(0); qb[nb] = b_ro; nb = nb + 1; end
        end
        @(negedge clk); a_ro = 0; b_ro = 0;
        while (cyc - last_rx < 3000 && (ra < na || rb < nb)) @(posedge clk);
        repeat (50) @(posedge clk);
        f_main = a_f | b_f; bad_main = bad; ra_m = ra; rb_m = rb; chk = 0;
        // overflow phase: 3000 back-to-back beats A->B (1.0 > 0.764 sustained; 512-flit landing): overflow must be flagged
        for (k = 0; k < 3000; k = k + 1) begin @(negedge clk); a_ro = rbeat(0); end
        @(negedge clk); a_ro = 0;
        repeat (2000) @(posedge clk);
        ofl_seen = a_f;
        $display("LEP_STATS sent A->B %0d recv %0d, B->A %0d recv %0d, mismatches %0d, fault_main %0d, overflow_fault %0d, lane_flt A %b%b B %b%b",
            na, ra_m, nb, rb_m, bad_main, f_main, ofl_seen, af0, af1, bf0, bf1);
        if (bad_main == 0 && ra_m == N && rb_m == N && !f_main && ofl_seen)
            $display("PASS lep: %0d + %0d beats bit-exact in order across 2 x 2 UCIe lanes (lane skew 7 PMA cycles, SRAM landing wrapped); overflow flagged", ra_m, rb_m);
        else
            $display("FAIL lep: mismatches %0d recv %0d/%0d %0d/%0d fault_main %0d overflow_fault %0d", bad_main, ra_m, N, rb_m, N, f_main, ofl_seen);
        $finish;
    end
    initial begin #(0.8333 * (WAIT + 40 * N + 20000)); $display("FAIL lep: TIMEOUT recv %0d/%0d %0d/%0d", ra, na, rb, nb); $finish; end
endmodule
