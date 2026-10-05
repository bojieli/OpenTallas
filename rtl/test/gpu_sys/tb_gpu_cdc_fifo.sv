`timescale 1ps/1ps
// ---------------------------------------------------------------------------
// tb_gpu_cdc_fifo: self-checking bench of ot_gpu_cdc_fifo #(.ENABLE(1)).
//
// For each of five clock pairs (write/read ps: 833/1000, 1000/833, 833/900,
// 4000/833, 833/4000) and each depth 4, 8, 16 (AW 2..4), two FIFOs run
// concurrently on that pair's two free-running clocks:
//   * integrity: NENT entries of a sequence-derived 64-bit word, random valid
//     (held while !ready) and random ready, with the backpressure probability
//     of each side (5..100%) changing every 256 cycles; the FIFO must be seen full; the reader checks every popped
//     word against the next expected one (ordering + data integrity);
//   * throughput: always-valid writer, always-ready reader; pops are counted
//     over NWIN slower-side cycles after a warm-up and reported as entries per
//     slower-clock cycle.
// Checks: (a) integrity, (b) throughput >= 0.99 at the depth predicted by
// tools/gpu_sys/cdc_sizing.py (PRED_AW_<pair>), and the prediction is the
// smallest measured depth reaching 0.99, (c) ovf_fault never rises, (d) an
// ENABLE=0 instance keeps every output 0 under toggling inputs.
// ---------------------------------------------------------------------------
module tb_gpu_cdc_fifo_unit #(
    parameter integer WPER = 833,
    parameter integer RPER = 1000,
    parameter integer AW   = 3,
    parameter integer NENT = 20000,
    parameter integer NWIN = 20000,
    parameter integer SEED = 1
) (
    input  wire  wrst_n,
    input  wire  rrst_n,
    output reg   int_done,
    output reg   int_err,
    output reg   thr_done,
    output reg [31:0] thr_ppm,       // entries per slower cycle x 1e6
    output reg   ovf_seen,
    output integer full_cycles        // integrity FIFO: write cycles stalled on full (backpressure reached)
);
    localparam integer W = 64;
    localparam integer TSLOW = (WPER > RPER) ? WPER : RPER;
    reg wclk = 1'b0, rclk = 1'b0;
    always begin #(WPER / 2) wclk = 1'b1; #(WPER - WPER / 2) wclk = 1'b0; end
    always begin #(RPER / 3) rclk = 1'b1; #(RPER / 2) rclk = 1'b0; #(RPER - RPER / 3 - RPER / 2); end

    function automatic [W-1:0] word_of(input integer s);
        reg [31:0] h;
        begin
            h = s * 32'h9E3779B1 + SEED;
            h = h ^ (h >> 15); h = h * 32'h85EBCA6B; h = h ^ (h >> 13);
            word_of = {s[31:0], h};
        end
    endfunction

    // ---- integrity FIFO ----------------------------------------------------------------------------
    reg          a_in_v;  wire a_in_rdy; reg a_out_rdy; wire a_out_v; wire [W-1:0] a_out_d; wire a_ovf;
    integer      a_wseq, a_rseq, a_wpct, a_rpct, a_wcyc, a_rcyc;
    ot_gpu_cdc_fifo #(.ENABLE(1), .W(W), .AW(AW), .SYNC(2)) u_int (
        .wclk(wclk), .wrst_n(wrst_n), .in_v(a_in_v), .in_rdy(a_in_rdy), .in_d(word_of(a_wseq)),
        .rclk(rclk), .rrst_n(rrst_n), .out_v(a_out_v), .out_rdy(a_out_rdy), .out_d(a_out_d), .ovf_fault(a_ovf));

    function automatic integer pick_pct(input integer unsigned r);
        case (r % 5) 0: pick_pct = 5; 1: pick_pct = 25; 2: pick_pct = 50; 3: pick_pct = 90; default: pick_pct = 100;
        endcase
    endfunction

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            a_in_v <= 1'b0; a_wseq <= 0; a_wpct <= 50; a_wcyc <= 0;
        end else begin
            a_wcyc <= a_wcyc + 1;
            if ((a_wcyc & 255) == 255) a_wpct <= pick_pct($urandom);
            if (a_in_v && a_in_rdy) a_wseq <= a_wseq + 1;
            if (a_in_v && !a_in_rdy) a_in_v <= 1'b1;                       // hold while not accepted
            else a_in_v <= ((a_wseq + ((a_in_v && a_in_rdy) ? 1 : 0)) < NENT) && (($urandom % 100) < a_wpct);
        end
    end
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            a_out_rdy <= 1'b0; a_rseq <= 0; a_rpct <= 50; a_rcyc <= 0; int_done <= 1'b0; int_err <= 1'b0;
        end else begin
            a_rcyc <= a_rcyc + 1;
            if ((a_rcyc & 255) == 127) a_rpct <= pick_pct($urandom);
            a_out_rdy <= ($urandom % 100) < a_rpct;
            if (a_out_v && a_out_rdy) begin
                if (a_out_d !== word_of(a_rseq) || a_rseq >= NENT) begin
                    if (!int_err)
                        $display("  ERROR %0d/%0d AW=%0d entry %0d: got %h want %h", WPER, RPER, AW, a_rseq,
                                 a_out_d, word_of(a_rseq));
                    int_err <= 1'b1;
                end
                a_rseq <= a_rseq + 1;
                if (a_rseq + 1 == NENT) int_done <= 1'b1;
            end
        end
    end

    // ---- throughput FIFO ---------------------------------------------------------------------------
    wire b_in_rdy, b_out_v, b_ovf; wire [W-1:0] b_out_d;
    reg  b_in_v, b_out_rdy;
    integer b_wseq, b_rseq, b_pops;
    reg  b_err;
    ot_gpu_cdc_fifo #(.ENABLE(1), .W(W), .AW(AW), .SYNC(2)) u_thr (
        .wclk(wclk), .wrst_n(wrst_n), .in_v(b_in_v), .in_rdy(b_in_rdy), .in_d(word_of(b_wseq)),
        .rclk(rclk), .rrst_n(rrst_n), .out_v(b_out_v), .out_rdy(b_out_rdy), .out_d(b_out_d), .ovf_fault(b_ovf));
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin b_in_v <= 1'b0; b_wseq <= 0; end
        else begin b_in_v <= 1'b1; if (b_in_v && b_in_rdy) b_wseq <= b_wseq + 1; end
    end
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin b_out_rdy <= 1'b0; b_rseq <= 0; b_err <= 1'b0; end
        else begin
            b_out_rdy <= 1'b1;
            if (b_out_v && b_out_rdy) begin
                if (b_out_d !== word_of(b_rseq)) b_err <= 1'b1;
                b_rseq <= b_rseq + 1;
            end
        end
    end
    // measurement window: after 200 slower cycles of traffic, NWIN slower cycles
    real t0;
    integer p0;
    initial begin
        thr_done = 1'b0; thr_ppm = 0;
        wait (wrst_n && rrst_n);
        #(200 * TSLOW);
        @(posedge rclk); t0 = $realtime; p0 = b_rseq;
        #(NWIN * TSLOW);
        @(posedge rclk);
        thr_ppm = $rtoi(1.0e6 * (b_rseq - p0) * TSLOW / ($realtime - t0));
        if (b_err) thr_ppm = 0;                                            // integrity failure poisons rate
        thr_done = 1'b1;
    end

    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin ovf_seen <= 1'b0; full_cycles <= 0; end
        else begin
            if (a_ovf || b_ovf) ovf_seen <= 1'b1;
            if (a_in_v && !a_in_rdy) full_cycles <= full_cycles + 1;
        end
endmodule

module tb_gpu_cdc_fifo;
    parameter integer NENT = 20000;
    parameter integer NWIN = 20000;
    // Predicted AW per pair from tools/gpu_sys/cdc_sizing.py (run_cdc_fifo.py passes them with -G).
    parameter integer PRED_AW_0 = 3;   // 833 / 1000
    parameter integer PRED_AW_1 = 3;   // 1000 / 833
    parameter integer PRED_AW_2 = 3;   // 833 / 900
    parameter integer PRED_AW_3 = 2;   // 4000 / 833
    parameter integer PRED_AW_4 = 2;   // 833 / 4000
    localparam integer NP = 5, NA = 3; // AW 2..4

    function automatic integer wper_of(input integer p);
        case (p) 0: wper_of = 833; 1: wper_of = 1000; 2: wper_of = 833; 3: wper_of = 4000; default: wper_of = 833;
        endcase
    endfunction
    function automatic integer rper_of(input integer p);
        case (p) 0: rper_of = 1000; 1: rper_of = 833; 2: rper_of = 900; 3: rper_of = 833; default: rper_of = 4000;
        endcase
    endfunction
    function automatic integer pred_of(input integer p);
        case (p) 0: pred_of = PRED_AW_0; 1: pred_of = PRED_AW_1; 2: pred_of = PRED_AW_2; 3: pred_of = PRED_AW_3;
                 default: pred_of = PRED_AW_4; endcase
    endfunction

    reg wrst_n = 1'b0, rrst_n = 1'b0;
    wire [NP*NA-1:0] int_done, int_err, thr_done, ovf_seen;
    wire [31:0] ppm [0:NP*NA-1];
    integer     fullc [0:NP*NA-1];

    genvar gp, ga;
    generate for (gp = 0; gp < NP; gp = gp + 1) begin : g_pair
        for (ga = 0; ga < NA; ga = ga + 1) begin : g_aw
            tb_gpu_cdc_fifo_unit #(.WPER(wper_of(gp)), .RPER(rper_of(gp)), .AW(ga + 2), .NENT(NENT), .NWIN(NWIN),
                                   .SEED(gp * 16 + ga + 1)) u (
                .wrst_n(wrst_n), .rrst_n(rrst_n), .int_done(int_done[gp*NA+ga]), .int_err(int_err[gp*NA+ga]),
                .thr_done(thr_done[gp*NA+ga]), .thr_ppm(ppm[gp*NA+ga]), .ovf_seen(ovf_seen[gp*NA+ga]),
                .full_cycles(fullc[gp*NA+ga]));
        end
    end endgenerate

    // ---- (d) ENABLE=0 instance ---------------------------------------------------------------------------
    reg dclk = 1'b0;
    always #417 dclk = ~dclk;
    reg  d_in_v, d_out_rdy; reg [127:0] d_in_d;
    wire d_in_rdy, d_out_v, d_ovf; wire [127:0] d_out_d;
    reg  d_err = 1'b0;
    ot_gpu_cdc_fifo #(.ENABLE(0), .W(128), .AW(3), .SYNC(2)) u_off (
        .wclk(dclk), .wrst_n(wrst_n), .in_v(d_in_v), .in_rdy(d_in_rdy), .in_d(d_in_d),
        .rclk(dclk), .rrst_n(rrst_n), .out_v(d_out_v), .out_rdy(d_out_rdy), .out_d(d_out_d), .ovf_fault(d_ovf));
    always @(posedge dclk) begin
        d_in_v <= $urandom; d_out_rdy <= $urandom; d_in_d <= {$urandom, $urandom, $urandom, $urandom};
        if (d_in_rdy !== 1'b0 || d_out_v !== 1'b0 || d_ovf !== 1'b0 || d_out_d !== 128'b0) d_err <= 1'b1;
    end

    integer p, a, k, fails, smallest;
    reg ok;
    initial begin
        fails = 0;
        #3000 wrst_n = 1'b1;                       // per-domain release
        #1700 rrst_n = 1'b1;
        wait (&int_done && &thr_done);
        #10000;
        for (p = 0; p < NP; p = p + 1) begin
            for (a = 0; a < NA; a = a + 1) begin
                k = p * NA + a;
                ok = int_done[k] && !int_err[k] && (fullc[k] > 0);
                $display("%s integrity pair=%0d/%0d depth=%0d entries=%0d full_stall_cycles=%0d",
                         ok ? "PASS" : "FAIL", wper_of(p), rper_of(p), 1 << (a + 2), NENT, fullc[k]);
                if (!ok) fails = fails + 1;
            end
            smallest = 0;
            for (a = NA - 1; a >= 0; a = a - 1) if (ppm[p*NA+a] >= 990000) smallest = a + 2;
            for (a = 0; a < NA; a = a + 1)
                $display("RATE pair=%0d/%0d depth=%0d rate=%0.6f", wper_of(p), rper_of(p), 1 << (a + 2),
                         ppm[p*NA+a] / 1.0e6);
            ok = (pred_of(p) >= 2) && (pred_of(p) <= 4) && (ppm[p*NA+pred_of(p)-2] >= 990000);
            $display("%s throughput pair=%0d/%0d predicted_depth=%0d rate=%0.6f", ok ? "PASS" : "FAIL",
                     wper_of(p), rper_of(p), 1 << pred_of(p), ok ? ppm[p*NA+pred_of(p)-2] / 1.0e6 : 0.0);
            if (!ok) fails = fails + 1;
            ok = (smallest == pred_of(p));
            $display("%s model pair=%0d/%0d predicted_depth=%0d smallest_measured_depth=%0d", ok ? "PASS" : "FAIL",
                     wper_of(p), rper_of(p), 1 << pred_of(p), smallest == 0 ? 0 : 1 << smallest);
            if (!ok) fails = fails + 1;
        end
        ok = (ovf_seen == 0);
        $display("%s ovf_fault stays 0 (%0d instances)", ok ? "PASS" : "FAIL", 2 * NP * NA);
        if (!ok) fails = fails + 1;
        $display("%s enable0 outputs all zero", d_err ? "FAIL" : "PASS");
        if (d_err) fails = fails + 1;
        $display("TB_GPU_CDC_FIFO %s", fails == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
