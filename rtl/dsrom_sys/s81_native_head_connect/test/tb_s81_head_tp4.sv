`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// tb_s81_head_tp4 (s81-functional-token r3, 2026-10-14): the S81 head stage of the 1M token on the native head
// terminal of ALL FOUR ranks, ot_s81_native_head_tp4 (OPT_NATIVE_HEAD 1): every rank streams its 32,320 lm_head rows'
// golden roots {root4096, root1024} (tools/s81_ftok/head_stage.py golden: asserted merge == golden logit for every
// row) in row order at up to one row a cycle (random gaps), the rank's join + carried argmax runs, the ranks chain
// 0 -> 1 -> 2 -> 3, the final record is the token.
// CHECKS: every logit the terminal emits (row, bits) = the golden logit of that row, in row order, none poisoned; the
// final result = the golden argmax (id 21946, its bits); no rank fault.
// MUT 1 (negative control): rank 0's join loses phase B (its padded root1024 forced to +0) -> logits and token wrong.
// Plusargs: +DIR=<work dir with roots_r<r>.mem, logits_r<r>.mem, expect.mem>.
// ---------------------------------------------------------------------------------------------------------------------
module tb_s81_head_tp4;
    parameter integer MUT = 0, ROWS = 32320;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    reg [3:0] start = 0;
    wire [3:0] ready, in_ready, logit_valid, logit_poison, rank_fault;
    reg  [3:0] in_valid = 0;
    reg  [4*17-1:0] in_row = 0;
    reg  [4*32-1:0] r4096 = 0, r1024 = 0;
    wire [4*17-1:0] logit_row; wire [4*32-1:0] logit_bits; wire [4*47-1:0] logit_owner;
    wire result_valid, fault; wire [31:0] rid, rbits; wire [46:0] rown; wire [63:0] rseq;
    localparam [46:0] OWN = 47'h0123456789ab;
    localparam [63:0] SEQ = 64'd1048575;
    ot_s81_native_head_tp4 #(.OPT_NATIVE_HEAD(1), .ROWS(ROWS)) u (
        .clk(clk), .rst_n(rst_n), .start(start), .cancel(4'd0), .start_owner({4{OWN}}), .start_sequence({4{SEQ}}),
        .ready(ready), .in_valid(in_valid), .in_ready(in_ready), .in_owner({4{OWN}}), .in_sequence({4{SEQ}}),
        .in_row(in_row), .root4096(r4096), .root1024(r1024),
        .logit_valid(logit_valid), .logit_ready(4'hF), .logit_owner(logit_owner), .logit_row(logit_row),
        .logit_bits(logit_bits), .logit_poison(logit_poison),
        .result_valid(result_valid), .result_ready(1'b1), .result_global_id(rid), .result_bits(rbits),
        .result_owner(rown), .result_sequence(rseq), .rank_fault(rank_fault), .fault(fault));
    generate if (MUT == 1) begin : g_mut
        initial force u.g_rank[0].u_head.y2 = 32'd0;
    end endgenerate
    reg [63:0] roots [0:3][0:ROWS-1];
    reg [31:0] gl [0:3][0:ROWS-1];
    reg [63:0] tr [0:ROWS-1];
    reg [31:0] tl [0:ROWS-1];
    reg [31:0] ex [0:1];
    integer sent [0:3], got [0:3], bad = 0, pois = 0, order_bad = 0, cyc = 0, done_cyc = -1;
    reg [31:0] res_id = 32'hFFFFFFFF, res_bits = 0;
    reg [63:0] rs = 64'h9E3779B97F4A7C15;
    always @(posedge clk) cyc <= cyc + 1;
    string dir;
    integer r, k;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        for (r = 0; r < 4; r = r + 1) begin
            $readmemh($sformatf("%s/roots_r%0d.mem", dir, r), tr);
            $readmemh($sformatf("%s/logits_r%0d.mem", dir, r), tl);
            for (k = 0; k < ROWS; k = k + 1) begin roots[r][k] = tr[k]; gl[r][k] = tl[k]; end
            sent[r] = 0; got[r] = 0;
        end
        $readmemh({dir, "/expect.mem"}, ex);
    end
    // row feeders: one row a cycle per rank while in_ready, random idle cycles
    always @(posedge clk) if (rst_n) begin
        for (k = 0; k < 4; k = k + 1) begin
            if (in_valid[k] && in_ready[k]) sent[k] = sent[k] + 1;
            rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17);
            if (sent[k] < ROWS && rs[2:0] != 0) begin
                in_valid[k] <= 1'b1;
                in_row[17 * k +: 17] <= 17'(k * ROWS + sent[k]);
                r4096[32 * k +: 32] <= roots[k][sent[k]][63:32];
                r1024[32 * k +: 32] <= roots[k][sent[k]][31:0];
            end else in_valid[k] <= 1'b0;
        end
    end
    // logits out of every rank: row order, golden bits
    always @(posedge clk) if (rst_n) for (k = 0; k < 4; k = k + 1) if (logit_valid[k]) begin
        if (logit_row[17 * k +: 17] !== 17'(k * ROWS + got[k])) begin order_bad = order_bad + 1; if (order_bad < 5) $display("ERR rank %0d logit row %0d expected %0d", k, logit_row[17 * k +: 17], k * ROWS + got[k]); end
        else if (logit_bits[32 * k +: 32] !== gl[k][got[k]]) begin bad = bad + 1; if (bad < 5) $display("ERR rank %0d row %0d logit %h golden %h", k, got[k], logit_bits[32 * k +: 32], gl[k][got[k]]); end
        if (logit_poison[k]) pois = pois + 1;
        got[k] = got[k] + 1;
    end
    always @(posedge clk) if (result_valid && done_cyc < 0) begin res_id <= rid; res_bits <= rbits; done_cyc <= cyc; end
    initial begin
        repeat (5) @(negedge clk); rst_n = 1;
        repeat (3) @(negedge clk);
        while (ready != 4'hF) @(negedge clk);
        start = 4'hF; @(negedge clk); start = 0;
        while (done_cyc < 0 && cyc < 200000 && !fault) @(negedge clk);
        repeat (20) @(negedge clk);
        $display("S81_HEAD rows_sent=%0d/%0d/%0d/%0d logits=%0d/%0d/%0d/%0d logit_bad=%0d order_bad=%0d poisoned=%0d rank_fault=%b fault=%b token=%0d bits=%h expect=%0d/%h cycles=%0d MUT=%0d",
                 sent[0], sent[1], sent[2], sent[3], got[0], got[1], got[2], got[3], bad, order_bad, pois, rank_fault, fault,
                 res_id, res_bits, ex[0], ex[1], done_cyc, MUT);
        if (done_cyc >= 0 && res_id == ex[0] && res_bits == ex[1] && bad == 0 && order_bad == 0 && pois == 0 && !fault &&
            got[0] == ROWS && got[1] == ROWS && got[2] == ROWS && got[3] == ROWS)
            $display("S81_HEAD PASS token=%0d", res_id);
        else $display("S81_HEAD FAIL token=%0d", res_id);
        $finish;
    end
endmodule
