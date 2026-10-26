`timescale 1ns/1ps
// el1011-q-kvd 2026-10-12: ot_qkvd_d2d link-pair stress bench.  A = the KV end's d2d (ot_qkvd_kv_end parameters; HT=1
// -> hardened buffers + IRL / ORL relays + PQ registered pops), B = a matched far end (flop FIFOs).  Random die-face
// traffic both ways under random die credit return and random tx_up drops; every word must arrive once, in order, per
// class, with no fault.  Prints "PAIR PASS words <n> cycles <c>" or "PAIR FAIL ...".  Build (iverilog):
//   iverilog -g2012 -DHTV=1 -o tb rtl/test/qwen_kv_die/tb_qkvd_d2d_pair.sv <d2d, fifo, fifo_sb, buf_tiles, fifo_sl,
//            ot_rst_relay, ot_sram_1r1w_64x512_m1_r2c2 model>
module tb_qkvd_d2d_pair;
`ifndef HTV
`define HTV 1
`endif
    localparam integer W = 528, FW = 548, HT = `HTV, NCYC = 40000;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    // A: KV end (3 TX classes 4..6, 4 RX classes 0..3); B: far end (4 TX classes 0..3, 3 RX classes 4..6)
    reg  [2:0] a_tv; reg [3*W-1:0] a_td; wire [2:0] a_tcr; wire [3:0] a_rv; wire [4*W-1:0] a_rd; reg [3:0] a_rcr;
    reg  [3:0] b_tv; reg [4*W-1:0] b_td; wire [3:0] b_tcr; wire [2:0] b_rv; wire [3*W-1:0] b_rd; reg [2:0] b_rcr;
    reg a_up, b_up; wire a_txv, b_txv; wire [FW-1:0] a_txf, b_txf; wire a_f, b_f; wire [4:0] a_fc, b_fc;
    ot_qkvd_d2d #(.NT(3), .NR(4), .TXB(4), .RXB(0), .W(W), .IBD({8'd8, 8'd4, 8'd48, 8'd48}),
        .FCR({8'd0, 8'd4, 8'd32, 8'd32}), .RBD({8'd32, 8'd8, 8'd32, 8'd4}), .OCR({8'd32, 8'd8, 8'd48, 8'd4}),
        .HT(HT), .ORL(HT), .IRL(HT), .PQ(`ifdef PQV `PQV `else HT `endif)) u_a (.clk(clk), .rst_n(rst_n), .t_v(a_tv), .t_d(a_td), .t_cr(a_tcr),
        .r_v(a_rv), .r_d(a_rd), .r_cr(a_rcr), .tx_up(a_up), .tx_v(a_txv), .tx_flit(a_txf), .rx_v(b_txv), .rx_flit(b_txf),
        .fault(a_f), .fault_cause(a_fc));
    ot_qkvd_d2d #(.NT(4), .NR(3), .TXB(0), .RXB(4), .W(W), .IBD({8'd8, 8'd8, 8'd8, 8'd8}),
        .FCR({8'd32, 8'd8, 8'd32, 8'd4}), .RBD({8'd8, 8'd4, 8'd32, 8'd32}), .OCR({8'd8, 8'd8, 8'd8, 8'd8})) u_b (
        .clk(clk), .rst_n(rst_n), .t_v(b_tv), .t_d(b_td), .t_cr(b_tcr), .r_v(b_rv), .r_d(b_rd), .r_cr(b_rcr),
        .tx_up(b_up), .tx_v(b_txv), .tx_flit(b_txf), .rx_v(a_txv), .rx_flit(a_txf), .fault(b_f), .fault_cause(b_fc));
    // die-face credits held by the tb senders, pending die credits owed back by the tb receivers
    integer a_cr [0:2], b_cr [0:3], a_ow [0:3], b_ow [0:2];
    integer a_sent [0:2], b_sent [0:3], a_got [0:3], b_got [0:2];
    integer k, cyc, errs, total;
    integer seed = 12345;
    function [W-1:0] word(input integer cls, input integer n);
        word = {16'(cls * 4096 + n), {16{32'(n * 2654435761 + cls)}}};
    endfunction
    initial begin
        errs = 0; total = 0;
        for (k = 0; k < 3; k = k + 1) begin a_cr[k] = (k == 2) ? 4 : 48; a_sent[k] = 0; b_got[k] = 0; b_ow[k] = 0; end
        for (k = 0; k < 4; k = k + 1) begin b_cr[k] = 8; b_sent[k] = 0; a_got[k] = 0; a_ow[k] = 0; end
        a_tv = 0; b_tv = 0; a_td = 0; b_td = 0; a_rcr = 0; b_rcr = 0; a_up = 0; b_up = 0;
        repeat (5) @(posedge clk);
        rst_n = 1;
        repeat (10) @(posedge clk);
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            // phase-varying load: bursts, idle stretches, and link drops
            a_up = ($urandom(seed) % 16) != 0 || cyc < 100; b_up = ($urandom % 16) != 0;
`ifdef SAT
            // SAT=<c>: throughput probe -- only A TX class c, offered every cycle, link always up, credits returned at once
            a_up = 1; b_up = 1;
`endif
            a_tv = 0; b_tv = 0; a_rcr = 0; b_rcr = 0;
            for (k = 0; k < 3; k = k + 1) if (a_cr[k] > 0 && cyc < NCYC - 2000 &&
`ifdef SAT
                k == `SAT
`else
                ($urandom % 100) < ((cyc / 3000) % 2 ? 95 : 40)
`endif
                ) begin
                a_tv[k] = 1; a_td[W*k +: W] = word(4 + k, a_sent[k]); a_sent[k] = a_sent[k] + 1; a_cr[k] = a_cr[k] - 1; end
            for (k = 0; k < 4; k = k + 1) if (b_cr[k] > 0 && cyc < NCYC - 2000 && ($urandom % 100) < (`ifdef SAT 0 `else 60 `endif)) begin
                b_tv[k] = 1; b_td[W*k +: W] = word(k, b_sent[k]); b_sent[k] = b_sent[k] + 1; b_cr[k] = b_cr[k] - 1; end
            for (k = 0; k < 4; k = k + 1) if (a_ow[k] > 0 && ($urandom % 100) < ((cyc / 5000) % 2 ? 90 : 30)) begin a_rcr[k] = 1; a_ow[k] = a_ow[k] - 1; end
            for (k = 0; k < 3; k = k + 1) if (b_ow[k] > 0 && ($urandom % 100) < (`ifdef SAT 100 `else 70 `endif)) begin b_rcr[k] = 1; b_ow[k] = b_ow[k] - 1; end
            @(posedge clk); #0.1;
            for (k = 0; k < 3; k = k + 1) if (a_tcr[k]) a_cr[k] = a_cr[k] + 1;
            for (k = 0; k < 4; k = k + 1) if (b_tcr[k]) b_cr[k] = b_cr[k] + 1;
            for (k = 0; k < 4; k = k + 1) if (a_rv[k]) begin
                if (a_rd[W*k +: W] !== word(k, a_got[k])) begin errs = errs + 1; if (errs < 5) $display("A rx class %0d word %0d mismatch", k, a_got[k]); end
                a_got[k] = a_got[k] + 1; a_ow[k] = a_ow[k] + 1; total = total + 1; end
            for (k = 0; k < 3; k = k + 1) if (b_rv[k]) begin
                if (b_rd[W*k +: W] !== word(4 + k, b_got[k])) begin errs = errs + 1; if (errs < 5) $display("B rx class %0d word %0d mismatch", 4 + k, b_got[k]); end
                b_got[k] = b_got[k] + 1; b_ow[k] = b_ow[k] + 1; total = total + 1; end
            if (a_f || b_f) begin $display("PAIR FAIL fault a %b (%b) b %b (%b) at cycle %0d", a_f, a_fc, b_f, b_fc, cyc); $finish; end
        end
        for (k = 0; k < 3; k = k + 1) if (b_got[k] != a_sent[k]) begin errs = errs + 1; $display("class %0d: sent %0d got %0d", 4 + k, a_sent[k], b_got[k]); end
        for (k = 0; k < 4; k = k + 1) if (a_got[k] != b_sent[k]) begin errs = errs + 1; $display("class %0d: sent %0d got %0d", k, b_sent[k], a_got[k]); end
        if (errs == 0) $display("PAIR PASS words %0d cycles %0d HT %0d (A->B %0d %0d %0d)", total, NCYC, HT, b_got[0], b_got[1], b_got[2]);
        else $display("PAIR FAIL errors %0d", errs);
        $finish;
    end
endmodule
