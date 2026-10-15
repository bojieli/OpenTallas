`timescale 1ns/1ps
// el1011-q-kvd 2026-10-11: scoreboard bench of the hardened link-buffer tiles (ot_qkvd_sbuf / ot_qkvd_fbuf8) as the d2d
// parent drives them: occupancy counter (push - pop) caps pushes at D, pops only when the tile's head is valid, every
// popped word must be the model's next word, and the buffer must drain.  +define+FBUF8 selects the flop tile.
// Mutants: +define+KVD_FSBMUT (sbuf direct-path reorder) must FAIL.
module tb_qkvd_buf_tile;
    parameter integer D = 48, N = 200000, SEED = 1;
    localparam integer W = 528;
    reg clk = 0, rst_n = 0;
    reg push, pop; reg [W-1:0] din;
    wire [W-1:0] d1; wire e1;
    reg [6:0] cnt;
    reg [W-1:0] q [$]; reg [W-1:0] junk, hq;
`ifdef FBUF8
    ot_qkvd_fbuf8 u_dut (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop), .dout(d1), .empty(e1));
`else
    ot_qkvd_sbuf  u_dut (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop), .dout(d1), .empty(e1));
`endif
    always #1 clk = ~clk;
    always @(posedge clk or negedge rst_n) if (!rst_n) cnt <= 0; else cnt <= cnt + push - pop;
    integer cyc, bad, s, pp, qp, pops, k, gap;
    initial begin
        s = SEED; bad = 0; pops = 0; gap = 0; push = 0; pop = 0; din = 0;
        repeat (3) @(posedge clk); #0.1 rst_n = 1; repeat (6) @(posedge clk);
        for (cyc = 0; cyc < N + 600; cyc = cyc + 1) begin
            if (cyc % 2000 == 0) begin pp = $urandom(s) % 100; qp = $urandom(s) % 100; s = s + 7; end
            if (cyc >= N) begin pp = 0; qp = 100; end
            @(negedge clk);
            if (e1 && cnt != 0) gap = gap + 1;
            push = (cnt + 0 < D) && (($urandom % 100) < pp);
            pop  = !e1 && (($urandom % 100) < qp);
            if (pop) begin
                hq = q.size() ? q[0] : {W{1'bx}};
                if (q.size() == 0 || d1 !== hq) begin bad = bad + 1; if (bad <= 5) $display("MISMATCH cyc %0d popped %h expected %h", cyc, d1[31:0], hq[31:0]); end
                if (q.size()) junk = q.pop_front();
                pops = pops + 1;
            end
            for (k = 0; k < W; k = k + 32) din[k +: 32] = $urandom;
            if (push) q.push_back(din);
        end
        if (q.size() != 0 || cnt != 0 || !e1) begin bad = bad + 1; $display("MISMATCH no drain: model %0d count %0d empty %b", q.size(), cnt, e1); end
        if (bad == 0) $display("PASS buf_tile D=%0d cycles=%0d pops=%0d head_gap_cycles=%0d", D, N, pops, gap);
        else $display("FAIL buf_tile D=%0d mismatches=%0d", D, bad);
        $finish;
    end
endmodule
