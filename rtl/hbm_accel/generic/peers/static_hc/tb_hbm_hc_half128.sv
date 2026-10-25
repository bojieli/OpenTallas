`timescale 1ns/1ps
// HBM-HC 2026-10-24: the B2 128-lane HALF engine vs its golden composition.
// DUT  = ot_hbm_hc_qeng_static #(W 128, TERM7 1, CPR 1, DRLY 2): the half hub centre ot_hbm_hc_qcen_static W 128 + 8 W 128
//        bank tiles (bankq0 / ft / plain / terminal bank 7, die parameters), 7-level subtree.
// REF  = two UNCHANGED 64-lane quarter engines (ot_hbm_hc_qeng_static_orig = the fc76a2c42 originals, CPR 1, DRLY 2):
//        quarter 0 = half lanes 0..63, quarter 1 = half lanes 64..127, + the 7th level ot_hdc_fp32_add_lat #(LAT 7)
//        (q0 + q1) on the quarters' registered sums: the golden pairwise order of the 256-leaf csum tree (a half sum is
//        the aligned 128-leaf subtree (q_2h + q_2h+1)).  Equal latency: REF = level 6 -> ps flop -> add (TLA) ; DUT =
//        level 6 -> level 7 add (TLA) -> ps flop, so the two outputs are compared on the SAME edge, bit for bit.
// Load phase (static, no backpressure): weight slot 0 rows 0..23 and x positions 0..7 at K 20,480 (R 10 runs) through the
// x-wave ports, one wave every 4 edges (beats 0..3), ingest event 2 edges before beat 0's landing edge.  DUT half wave lw
// (40 a row / position) = run lw / 4, slice lw % 4 (lanes 32 (lw % 4) .. +31); REF quarter q wave lw' (20) = run lw' / 2,
// slice lw' % 2 (half lanes 64 q + 32 (lw' % 2) ..).  Weights: random binary32 (moderate exponents, signs, zeros); x:
// BF16-valued.  Compute phase: NT random descriptors (valid ~70 % of edges, ss ~15 %, nv 0..128 biased to 128; REF
// quarter lane counts min(nv, 64) / max(nv - 64, 0) exactly as the root clamps per slot), wa / xa over the loaded words.
// Checks every edge: DUT {ps_v, ps} == REF {v, y}; DUT ps_f == 0, REF ps_f == 0, every fault == 0; all NT sums seen.
// MUT (DUT): 1 bank 3 weight slice rotated, 3 x landing one run off, 4 level-1 pairs (0,2),(1,3), 5 level-1 pairs
// (i, i + 64) (reordered accumulation), 6 write slice j = i_w[0] (wrong j), 7 top level dropped.  All must FAIL.
module tb_hbm_hc_half128;
    parameter integer MUT = 0;
    parameter integer NT = 3000;
    localparam integer K = 20480, R = 10, TLA = 7;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0;
    // ---------------------------------------------------------------- data
    reg [31:0] wv_m [0:24*R*128*8-1];    // [o][r][lane][k]
    reg [31:0] xv_m [0:8*R*128*8-1];     // [p][r][lane][k]
    function automatic [31:0] rw(input integer dummy);
        reg [31:0] r; r = $urandom;
        if (r[4:0] == 0) rw = 32'd0; else rw = {r[31], 8'(112 + ($urandom % 24)), r[22:0]};
    endfunction
    // ---------------------------------------------------------------- DUT / REF ports
    reg d_v = 0, d_ss = 0; reg [7:0] d_nv = 0; reg [9:0] d_wa = 0, d_xa = 0;
    reg [1:0] i_v = 0, i_kind = 0;                  // [0] DUT, REF quarters below
    reg ri_v0 = 0, ri_v1 = 0, ri_kind = 0; reg di_v = 0, di_kind = 0;
    reg [11:0] di_cnt = 0, ri_cnt = 0; reg [9:0] di_word = 0, ri_word = 0;
    reg dx_v = 0, rx_v = 0; reg [1:0] dx_b = 0, rx_b = 0; reg [9:0] dx_w = 0, rx_w = 0;
    reg [2047:0] dx_d = 0, rx_d0 = 0, rx_d1 = 0;
    wire dps_v, dps_f, dfault; wire [31:0] dps;
    ot_hbm_hc_qeng_static #(.K(K), .DRLY(2), .CPR(1), .W(128), .TERM7(1), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n),
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa),
        .i_v(di_v), .i_kind(di_kind), .i_slot(2'd0), .i_lo(5'd0), .i_w(6'd0), .i_cnt(di_cnt), .i_word(di_word),
        .x_wave_v(dx_v), .x_wave_beat(dx_b), .x_wave_word(dx_w), .x_wave(dx_d), .ps_v(dps_v), .ps(dps), .ps_f(dps_f), .fault(dfault));
    wire [6:0] nv0 = (d_nv >= 8'd64) ? 7'd64 : d_nv[6:0];
    wire [6:0] nv1 = (d_nv <= 8'd64) ? 7'd0 : 7'(d_nv - 8'd64);
    wire [1:0] rps_v, rps_f, rfault; wire [63:0] rps;
    ot_hbm_hc_qeng_static_orig #(.K(K), .DRLY(2), .CPR(1)) ref0 (.clk(clk), .rst_n(rst_n),
        .d_v(d_v), .d_ss(d_ss), .d_nv(nv0), .d_wa(d_wa), .d_xa(d_xa),
        .i_v(ri_v0), .i_kind(ri_kind), .i_slot(2'd0), .i_lo(5'd0), .i_w(5'd0), .i_cnt(ri_cnt), .i_word(ri_word),
        .x_wave_v(rx_v), .x_wave_beat(rx_b), .x_wave_word(rx_w), .x_wave(rx_d0), .ps_v(rps_v[0]), .ps(rps[31:0]),
        .ps_f(rps_f[0]), .fault(rfault[0]));
    ot_hbm_hc_qeng_static_orig #(.K(K), .DRLY(2), .CPR(1)) ref1 (.clk(clk), .rst_n(rst_n),
        .d_v(d_v), .d_ss(d_ss), .d_nv(nv1), .d_wa(d_wa), .d_xa(d_xa),
        .i_v(ri_v1), .i_kind(ri_kind), .i_slot(2'd0), .i_lo(5'd0), .i_w(5'd0), .i_cnt(ri_cnt), .i_word(ri_word),
        .x_wave_v(rx_v), .x_wave_beat(rx_b), .x_wave_word(rx_w), .x_wave(rx_d1), .ps_v(rps_v[1]), .ps(rps[63:32]),
        .ps_f(rps_f[1]), .fault(rfault[1]));
    wire [31:0] ry; wire [1:0] re; wire rv;
    ot_hdc_fp32_add_lat #(.LAT(TLA), .DRST(0)) u_l7 (.clk(clk), .rst_n(rst_n), .valid_in(rps_v[0]), .a(rps[31:0]),
        .b(rps[63:32]), .y(ry), .err(re), .valid_out(rv));
    // ---------------------------------------------------------------- wave content
    // beat b of a wave: x_wave[256 i + 32 k] = term k of chunk m = 8 b + i; chunk m = lane base + m
    task automatic fill_beat(input integer kind, input integer unit, input integer r, input integer lane0, input integer b,
                             output reg [2047:0] d);
        for (integer i = 0; i < 8; i = i + 1) for (integer k = 0; k < 8; k = k + 1) begin
            integer idx; idx = ((unit * R + r) * 128 + lane0 + 8 * b + i) * 8 + k;
            d[i*256 + k*32 +: 32] = kind ? wv_m[idx] : xv_m[idx];
        end
    endtask
    // stream state: DUT (40 waves a unit) and REF (20 waves a unit, both quarters in parallel)
    integer d_n = -1, d_tot = 0, d_t0 = 0, d_kind = 0, r_n = -1, r_tot = 0, r_t0 = 0, r_kind = 0;
    integer d_word0 = 0, r_word0 = 0;
    always @(negedge clk) begin
        di_v <= 0; ri_v0 <= 0; ri_v1 <= 0; dx_v <= 0; rx_v <= 0;
        // ingest events 2 edges before beat 0 of wave 0 is on the pins + 3 (beat 3 lands one edge after the event)
        if (d_tot > 0 && cyc == d_t0 + 2) begin di_v <= 1; di_kind <= d_kind[0]; di_cnt <= 12'(d_tot); di_word <= 10'(d_word0); end
        if (r_tot > 0 && cyc == r_t0 + 2) begin ri_v0 <= 1; ri_v1 <= 1; ri_kind <= r_kind[0]; ri_cnt <= 12'(r_tot); ri_word <= 10'(r_word0); end
        if (d_tot > 0 && cyc >= d_t0 && (cyc - d_t0) / 4 < d_tot) begin : dw
            integer n, b, unit, lw; reg [2047:0] d;
            n = (cyc - d_t0) / 4; b = (cyc - d_t0) % 4; unit = n / 40; lw = n % 40;
            fill_beat(d_kind, unit, lw / 4, 32 * (lw % 4), b, d);
            dx_v <= 1; dx_b <= 2'(b); dx_w <= 10'(d_word0 + n); dx_d <= d;
        end
        if (r_tot > 0 && cyc >= r_t0 && (cyc - r_t0) / 4 < r_tot) begin : rw_
            integer n, b, unit, lw; reg [2047:0] d0, d1;
            n = (cyc - r_t0) / 4; b = (cyc - r_t0) % 4; unit = n / 20; lw = n % 20;
            fill_beat(r_kind, unit, lw / 2, 32 * (lw % 2), b, d0);
            fill_beat(r_kind, unit, lw / 2, 64 + 32 * (lw % 2), b, d1);
            rx_v <= 1; rx_b <= 2'(b); rx_w <= 10'(r_word0 + n); rx_d0 <= d0; rx_d1 <= d1;
        end
    end
    // ---------------------------------------------------------------- checks
    integer nseen = 0, nbad = 0, nzero = 0, nflt = 0, ntask = 0, phase = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n && cyc > 20) begin
            if (dps_v !== rv || (rv && dps !== ry)) begin
                nbad = nbad + 1;
                if (nbad < 8) $display("MISMATCH cyc=%0d dut v=%0d ps=%08x  ref v=%0d y=%08x", cyc, dps_v, dps, rv, ry);
            end
            if (rv) begin nseen = nseen + 1; if (ry == 0) nzero = nzero + 1; end
            if (dps_f || (|rps_f) || dfault || (|rfault) || (rv && (|re))) begin
                nflt = nflt + 1;
                if (nflt < 4) $display("FAULT cyc=%0d dut ps_f=%0d fault=%0d ref ps_f=%b fault=%b err=%b", cyc, dps_f, dfault,
                    rps_f, rfault, re);
            end
        end
    end
    // ---------------------------------------------------------------- programme
    initial begin
        integer seed, t;
        if (!$value$plusargs("SEED=%d", seed)) seed = 7;
        void'($urandom(seed));
        for (integer i = 0; i < 24*R*128*8; i = i + 1) wv_m[i] = rw(0);
        for (integer i = 0; i < 8*R*128*8; i = i + 1) begin xv_m[i] = rw(0); xv_m[i][15:0] = 16'd0; end
        repeat (10) @(posedge clk); rst_n = 1;
        repeat (20) @(posedge clk);
        // weights: DUT 24 rows x 40 waves, REF 24 rows x 20 waves (both quarters)
        d_kind = 1; d_tot = 24 * 40; d_word0 = 5; d_t0 = cyc + 4;
        r_kind = 1; r_tot = 24 * 20; r_word0 = 9; r_t0 = cyc + 4;
        wait (cyc > d_t0 + 4 * d_tot + 40);
        d_kind = 0; d_tot = 8 * 40; d_word0 = 300; d_t0 = cyc + 4;
        r_kind = 0; r_tot = 8 * 20; r_word0 = 700; r_t0 = cyc + 4;
        wait (cyc > d_t0 + 4 * d_tot + 40);
        d_tot = 0; r_tot = 0;
        repeat (40) @(posedge clk);
        phase = 1;
        // compute: NT descriptors
        while (ntask < NT) begin
            @(negedge clk);
            if (($urandom % 10) < 7) begin
                integer u; u = $urandom % 8;
                d_v <= 1; d_ss <= (($urandom % 7) == 0);
                d_nv <= (u < 5) ? 8'd128 : (u == 5) ? 8'($urandom % 129) : (u == 6) ? 8'(64 + $urandom % 2) : 8'($urandom % 64);
                d_wa <= 10'(($urandom % 24) * R + ($urandom % R)); d_xa <= 10'(($urandom % 8) * R + ($urandom % R));
                ntask = ntask + 1;
            end else d_v <= 0;
        end
        @(negedge clk); d_v <= 0;
        repeat (400) @(posedge clk);
        $display("HC_HALF128 MUT=%0d tasks=%0d sums_checked=%0d (zero %0d) mismatches=%0d faults=%0d %s", MUT, ntask, nseen,
            nzero, nbad, nflt, (nbad == 0 && nflt == 0 && nseen == NT) ? "PASS" : "FAIL");
        $finish;
    end
    initial begin #4000000; $display("HC_HALF128 MUT=%0d watchdog FAIL", MUT); $finish; end
endmodule
