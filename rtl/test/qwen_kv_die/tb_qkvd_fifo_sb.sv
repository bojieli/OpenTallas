`timescale 1ns/1ps
// el1011-q-kvd 2026-10-11: scoreboard bench of ot_qkvd_fifo_sb (SRAM body) against an ideal FIFO model and, in lockstep,
// ot_qkvd_fifo RH=1 for count / full: random bursty push (when !full) / pop (when the DUT's head is valid); every popped
// word must be the model's next word, count / full must equal RH=1's every cycle, and the FIFO must drain to empty.
// Reports head-empty-while-count>0 cycles (the SRAM-path latency).  Build with +define+KVD_FSBMUT: must FAIL.
module tb_qkvd_fifo_sb;
    parameter integer D = 48, P = 8, N = 200000, SEED = 1;
    localparam integer W = 528;
    reg clk = 0, rst_n = 0;
    reg push, pop; reg [W-1:0] din;
    wire [W-1:0] d1; wire e1, f0, f1; wire [$clog2(D+1)-1:0] c0, c1;
    reg  [W-1:0] q [$]; reg [W-1:0] junk, hq;
    ot_qkvd_fifo_sb #(.W(W), .D(D), .P(P)) u_dut (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop),
        .dout(d1), .empty(e1), .full(f1), .count(c1));
    // RH=1 reference for occupancy only (its pop follows the DUT's, so counts must agree)
    wire [W-1:0] d0; wire e0;
    ot_qkvd_fifo #(.RH(1), .W(W), .D(D)) u_ref (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop),
        .dout(d0), .empty(e0), .full(f0), .count(c0));
    always #1 clk = ~clk;
    integer cyc, bad, s, pp, qp, pops, k, gap;
    initial begin
        s = SEED; bad = 0; pops = 0; gap = 0; push = 0; pop = 0; din = 0;
        repeat (3) @(posedge clk); #0.1 rst_n = 1;
        for (cyc = 0; cyc < N + 400; cyc = cyc + 1) begin
            if (cyc % 2000 == 0) begin pp = $urandom(s) % 100; qp = $urandom(s) % 100; s = s + 7; end
            if (cyc >= N) begin pp = 0; qp = 100; end
            @(negedge clk);
            if (f0 !== f1 || c0 !== c1) begin bad = bad + 1; if (bad <= 5) $display("MISMATCH cyc %0d count %0d/%0d full %b/%b", cyc, c0, c1, f0, f1); end
            if (e1 && c1 != 0) gap = gap + 1;
            push = !f1 && (($urandom % 100) < pp);
            pop  = !e1 && (($urandom % 100) < qp);
            if (pop) begin
                hq = q.size() ? q[0] : {W{1'bx}}; if (q.size() == 0 || d1 !== hq) begin bad = bad + 1; if (bad <= 5) $display("MISMATCH cyc %0d popped %h expected %h", cyc, d1[31:0], hq[31:0]); end
                if (q.size()) junk = q.pop_front();
                pops = pops + 1;
            end
            for (k = 0; k < W; k = k + 32) din[k +: 32] = $urandom;
            if (push) q.push_back(din);
        end
        if (q.size() != 0 || c1 != 0 || !e1) begin bad = bad + 1; $display("MISMATCH no drain: model %0d count %0d empty %b", q.size(), c1, e1); end
        if (bad == 0) $display("PASS fifo_sb D=%0d P=%0d cycles=%0d pops=%0d head_gap_cycles=%0d", D, P, N, pops, gap);
        else $display("FAIL fifo_sb D=%0d P=%0d mismatches=%0d", D, P, bad);
        $finish;
    end
endmodule
