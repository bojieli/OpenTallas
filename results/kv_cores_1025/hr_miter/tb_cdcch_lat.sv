`timescale 1ns/1ps
// KV-CORE-RTL/HR 2026-10-25: cycle accounting of the whole ot_qwen_die_cdc_ch at the qkd_hr_cdc_ch shape (W546 IBUF4
// OCRED4 AD8 PIPE2) on ONE clock: SAMECLK=0 (shipped async path, both clocks tied) vs SAMECLK=1 (register stage).
// Same word stream into both, each with its own credit loop; reports i_v -> o_v latency of an isolated word, the
// i_v -> i_cr credit return, and checks the two output streams are identical (values, order) over N words.
module tb_cdcch_lat;
    parameter integer W = 546, N = 20000;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [1:0] iv = 0; reg [W-1:0] id [0:1]; reg [1:0] ocr = 0;
    wire [1:0] icr, ov, wf, rf; wire [W-1:0] od [0:1];
    ot_qwen_die_cdc_ch #(.W(W), .IBUF(4), .OCRED(4), .AD(8), .PIPE(2), .SAMECLK(0)) u_old (.wclk(clk), .wrst_n(rst_n),
        .i_v(iv[0]), .i_d(id[0]), .i_cr(icr[0]), .w_fault(wf[0]), .rclk(clk), .rrst_n(rst_n), .o_v(ov[0]), .o_d(od[0]),
        .o_cr(ocr[0]), .r_fault(rf[0]));
    ot_qwen_die_cdc_ch #(.W(W), .IBUF(4), .OCRED(4), .AD(8), .PIPE(2), .SAMECLK(1)) u_new (.wclk(clk), .wrst_n(rst_n),
        .i_v(iv[1]), .i_d(id[1]), .i_cr(icr[1]), .w_fault(wf[1]), .rclk(clk), .rrst_n(rst_n), .o_v(ov[1]), .o_d(od[1]),
        .o_cr(ocr[1]), .r_fault(rf[1]));
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [W-1:0] src [0:N-1]; reg [W-1:0] got [0:1][0:N-1];
    integer sent [0:1], recv [0:1], cr [0:1], lat_o [0:1], lat_c [0:1], t0, k, bad = 0, flt = 0;
    integer rq [0:1][$];
    genvar g;
    for (g = 0; g < 2; g++) begin : g_d
        always @(negedge clk) if (rst_n) begin
            if (ov[g]) begin got[g][recv[g]] = od[g]; recv[g] = recv[g] + 1; rq[g].push_back(cyc + (src[recv[g] % N][3:0] % 5)); end
            if (icr[g]) cr[g] = cr[g] + 1;
            if (wf[g] || rf[g]) flt = flt + 1;
        end
    end
    initial begin
        for (k = 0; k < N; k++) src[k] = {W/32+1{$urandom}};
        for (k = 0; k < 2; k++) begin sent[k] = 0; recv[k] = 0; cr[k] = 4; lat_o[k] = -1; lat_c[k] = -1; end
        id[0] = 0; id[1] = 0;
        repeat (4) @(negedge clk); rst_n = 1; repeat (20) @(negedge clk);
        // isolated word: latency
        iv = 2'b11; id[0] = src[0]; id[1] = src[0]; t0 = cyc; cr[0] = cr[0] - 1; cr[1] = cr[1] - 1; sent[0] = 1; sent[1] = 1;
        @(negedge clk); iv = 0;
        repeat (40) begin
            for (k = 0; k < 2; k++) begin
                if (lat_o[k] < 0 && recv[k] > 0) lat_o[k] = cyc - t0 - 1;
                if (lat_c[k] < 0 && cr[k] == 4) lat_c[k] = cyc - t0 - 1;
            end
            @(negedge clk);
        end
        // stream: each side its own credit loop, same words, same downstream return pattern
        while ((sent[0] < N || sent[1] < N || recv[0] < N || recv[1] < N) && cyc < 40 * N) begin
            for (k = 0; k < 2; k++) begin
                iv[k] = 0; ocr[k] = 0;
                if (sent[k] < N && cr[k] > 0 && ($urandom % 3) != 0) begin iv[k] = 1; id[k] = src[sent[k]]; sent[k] = sent[k] + 1; cr[k] = cr[k] - 1; end
                if (rq[k].size() > 0 && rq[k][0] <= cyc) begin ocr[k] = 1; void'(rq[k].pop_front()); end
            end
            @(negedge clk);
        end
        iv = 0; ocr = 0;
        for (k = 0; k < N; k++) if (got[0][k] !== src[k] || got[1][k] !== src[k]) bad = bad + 1;
        $display("CDC_CH LATENCY i_v->o_v edges: SAMECLK0(old,tied clocks)=%0d SAMECLK1(new)=%0d ; i_v->i_cr: old=%0d new=%0d",
            lat_o[0], lat_o[1], lat_c[0], lat_c[1]);
        $display("%s stream words=%0d recv old=%0d new=%0d order/value mismatches=%0d faults=%0d end_cycle=%0d",
            (bad == 0 && flt == 0 && recv[0] == N && recv[1] == N) ? "STREAM PASS" : "STREAM FAIL", N, recv[0], recv[1], bad, flt, cyc);
        $finish;
    end
endmodule
