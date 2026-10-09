`timescale 1ns/1ps
// tb_sc_pfifo: ot_sc_pfifo against a reference queue under random valid / ready stalls (stream struct-close).
// Every pushed beat must come out once, in order, unmodified; never more than S beats held; in_ready must be high
// whenever fewer than S beats are held at the start of a cycle (no throughput loss vs a S-entry skid).
module tb_sc_pfifo;
    parameter integer W = 70, S = 2, G = 16, MUT = 0, SEED = 1, N = 20000;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0, iv = 0, ordy = 0; reg [W-1:0] id = 0;
    wire ir, ov; wire [W-1:0] od;
    ot_sc_pfifo #(.W(W), .S(S), .G(G), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(ir),
        .in_data(id), .out_valid(ov), .out_ready(ordy), .out_data(od));
    reg [W-1:0] q [0:65535]; integer qw = 0, qr = 0, cyc = 0, sent = 0, rs, k;
    function [W-1:0] rnd_w(input integer s); integer j; begin for (j = 0; j < W; j = j + 32) rnd_w[j +: 32] = $random(s); end endfunction
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if (ov && ordy) begin
            if (qr >= qw || od !== q[qr]) begin $display("SC_PFIFO FAIL: beat %0d mismatch", qr); $finish; end
            qr = qr + 1;
        end
        if (iv && ir) begin q[qw] = id; qw = qw + 1; end
        if (qw - qr > S) begin $display("SC_PFIFO FAIL: holds %0d > %0d", qw - qr, S); $finish; end
        if ((qw - qr) < S && !ir && !(iv && ir)) ; // in_ready is registered: checked below at the next edge
        // next stimulus (random, with garbage data while not valid)
        iv <= ($random(rs) % 4 != 0) && sent < N; id <= rnd_w(rs);
        ordy <= ($random(rs) % 3 != 0);
        if (iv && ir) sent = sent + 1;
    end
    // throughput: when the queue holds < S beats after an edge, in_ready must be 1 after that edge
    always @(negedge clk) if (rst_n && cyc > 2) if ((qw - qr) < S && !ir) begin
        $display("SC_PFIFO FAIL: in_ready low with %0d < %0d held", qw - qr, S); $finish; end
    initial begin
        rs = SEED;
        repeat (4) @(posedge clk); rst_n = 1;
        while (qr < N && cyc < 20 * N) @(posedge clk);
        if (qr < N) begin $display("SC_PFIFO FAIL: timeout %0d / %0d", qr, N); $finish; end
        $display("SC_PFIFO PASS W=%0d S=%0d G=%0d beats=%0d cycles=%0d", W, S, G, qr, cyc); $finish;
    end
endmodule
