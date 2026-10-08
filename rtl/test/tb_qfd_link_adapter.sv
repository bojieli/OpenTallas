`timescale 1ns/1ps
// qwen-missing 2026-10-07: two ot_qfd_link_adapter instances back to back through a PHY model (fixed LAT-cycle FDI
// pipe each way, the link up after UP cycles), random die-bus traffic both ways with the die-bus credit protocol and
// random receiver back-pressure.  PASS: both streams arrive complete, in order, bit-exact, with no fault.  MUT = 1
// (one extra link credit on side A) with long receiver stalls must FAIL (receive-buffer overrun detected or a word lost).
// gaps-design 2026-10-08: RATE = 1 is the line-rate sweep point: both senders offer a word every cycle they hold a
// credit and both receivers return every credit at once; the bench prints the sustained B-side receive rate (words a
// cycle between the 1st and the last word) and FAILs below MINRATE (per mille).  SRAM = 1 builds the receive buffer
// from the ot_sram_1r1w_512x128_m4_r2c2 behavioural model (compile it and rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv).
module tb_qfd_link_adapter;
    parameter integer W = 1024, RXD = 32, LAT = 4, UP = 20, N = 3000, MUT = 0, SEED = 11, STALL = 0, SRAM = 0, RATE = 0, MINRATE = 0, SW = 200;
    localparam integer CRW = $clog2(RXD + 1), FW = W + CRW + 9;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg a_cv, b_cv; reg [W-1:0] a_cd, b_cd; wire a_ccr, b_ccr;
    wire a_rv, b_rv; wire [W-1:0] a_rd, b_rd; reg a_rcr, b_rcr;
    wire a_tv, b_tv; wire [FW-1:0] a_tf, b_tf; wire a_f, b_f;
    reg [LAT*(FW+1)-1:0] ab, ba;     // PHY pipes
    always @(posedge clk) if (!rst_n) begin ab <= 0; ba <= 0; end else begin ab <= {ab, a_tv, a_tf}; ba <= {ba, b_tv, b_tf}; end
    wire ab_v = ab[LAT*(FW+1)-1]; wire [FW-1:0] ab_f = ab[(LAT-1)*(FW+1) +: FW];
    wire ba_v = ba[LAT*(FW+1)-1]; wire [FW-1:0] ba_f = ba[(LAT-1)*(FW+1) +: FW];
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    wire up = cyc > UP;
    ot_qfd_link_adapter #(.W(W), .RXD(RXD), .SRAM(SRAM), .MUT(MUT)) A (.clk(clk), .rst_n(rst_n), .c_v(a_cv), .c_d(a_cd), .c_cr(a_ccr),
        .r_v(a_rv), .r_d(a_rd), .r_cr(a_rcr), .tx_up(up), .tx_v(a_tv), .tx_flit(a_tf), .rx_v(ba_v), .rx_flit(ba_f), .fault(a_f));
    ot_qfd_link_adapter #(.W(W), .RXD(RXD), .SRAM(SRAM)) B (.clk(clk), .rst_n(rst_n), .c_v(b_cv), .c_d(b_cd), .c_cr(b_ccr),
        .r_v(b_rv), .r_d(b_rd), .r_cr(b_rcr), .tx_up(up), .tx_v(b_tv), .tx_flit(b_tf), .rx_v(ab_v), .rx_flit(ab_f), .fault(b_f));
    // senders (IBUF = 4 credits each) and receivers (credit back a word some cycles after it arrives)
    integer t_first, t_last, rate_pm;
    integer seed, a_sent, b_sent, a_got, b_got, a_cr, b_cr, bad, i, a_pend, b_pend;
    function [W-1:0] word(input integer side, input integer k);
        integer j; reg [W-1:0] x;
        begin for (j = 0; j < W / 32; j = j + 1) x[j*32 +: 32] = (side * 32'h9E3779B9) ^ (k * 32'h85EBCA6B) ^ (j * 32'hC2B2AE35); word = x; end
    endfunction
    initial begin
        seed = SEED; t_first = -1; t_last = 0; a_sent = 0; b_sent = 0; a_got = 0; b_got = 0; a_cr = 4; b_cr = 4; bad = 0; a_pend = 0; b_pend = 0;
        a_cv = 0; b_cv = 0; a_rcr = 0; b_rcr = 0; ab = 0; ba = 0;
        repeat (3) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);   // no die-bus traffic within the reset-copy window
        while ((a_got < N || b_got < N) && cyc < 40 * N) begin
            @(negedge clk);
            if (a_ccr) a_cr = a_cr + 1;
            if (b_ccr) b_cr = b_cr + 1;
            // receive and check
            if (b_rv) begin if (b_rd !== word(0, b_got)) begin if (bad < 3) $display("B mismatch got=%0d at cyc %0d data=%h", b_got, cyc, b_rd[31:0]); bad = bad + 1; end if (t_first < 0) t_first = cyc; t_last = cyc; b_got = b_got + 1; b_pend = b_pend + 1; end
            if (a_rv) begin if (a_rd !== word(1, a_got)) bad = bad + 1; a_got = a_got + 1; a_pend = a_pend + 1; end
            // receivers return credits (stalls: none for STALL = 0, long windows otherwise)
            b_rcr = 0; a_rcr = 0;
            if (b_pend > 0 && ((RATE != 0) ? 1 : (STALL == 0 ? (($random(seed) & 3) != 0) : ((cyc / SW) % 3 == 2)))) begin b_rcr = 1; b_pend = b_pend - 1; end
            if (a_pend > 0 && (RATE != 0 || ($random(seed) & 3) != 0)) begin a_rcr = 1; a_pend = a_pend - 1; end
            // senders
            a_cv = 0; b_cv = 0;
            if (a_sent < N && a_cr > 0 && (RATE != 0 || ($random(seed) & 1))) begin a_cv = 1; a_cd = word(0, a_sent); a_sent = a_sent + 1; a_cr = a_cr - 1; end
            if (b_sent < N && b_cr > 0 && (RATE != 0 || ($random(seed) & 1))) begin b_cv = 1; b_cd = word(1, b_sent); b_sent = b_sent + 1; b_cr = b_cr - 1; end
            if (a_f || b_f) bad = bad + 1;
        end
        rate_pm = (t_last > t_first) ? ((N - 1) * 1000) / (t_last - t_first) : 0;
        $display("RATE qfd_link_adapter RXD=%0d LAT=%0d SRAM=%0d rate=%0d/1000 words-per-cycle (min %0d)", RXD, LAT, SRAM, rate_pm, MINRATE);
        if (bad == 0 && a_got == N && b_got == N && !a_f && !b_f && rate_pm >= MINRATE)
            $display("PASS qfd_link_adapter W=%0d RXD=%0d LAT=%0d words=%0d each way cycles=%0d", W, RXD, LAT, N, cyc);
        else
            $display("FAIL qfd_link_adapter bad=%0d a_got=%0d b_got=%0d fault=%0d/%0d cycles=%0d", bad, a_got, b_got, a_f, b_f, cyc);
        $finish;
    end
endmodule
