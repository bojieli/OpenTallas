`timescale 1ns/1ps
// tb_hgi_coll_crl (HBM P2P step 1, 2026-10-14): ot_hgi_coll_crl_tx -> RLY relays each way -> ot_hgi_coll_crl_rx, the TOPK
// line-write link of the SW engine (W 568).  A producer offers N random words with random valid gaps (valid/ready, holds
// until taken), the consumer pulls with random ready.  Checks: the consumer sees exactly the produced sequence (order,
// exactly once), idle is low from the edge after any accepted word until the consumer took it, high at the end, no fault.
// Mutant MUT 1 (rx returns a credit at the push too) must FAIL.  Prints CRL PASS / CRL FAIL.
module tb_hgi_coll_crl;
    parameter integer RLY = 8, CRD = 8, MUT = 0, N = 3000, W = 568;
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg in_v = 0; reg [W-1:0] in_d = 0; wire in_rdy, idle, t_v, f_cr, out_v, txf, rxf; wire [W-1:0] t_d, out_d; reg out_rdy = 0;
    reg [W:0] fw [0:RLY-1]; reg bw [0:RLY-1];
    always @(posedge clk) begin fw[0] <= {t_v, t_d}; bw[0] <= f_cr; for (integer i = 1; i < RLY; i = i + 1) begin fw[i] <= fw[i-1]; bw[i] <= bw[i-1]; end end
    ot_hgi_coll_crl_tx #(.W(W), .CRD(CRD)) u_t (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_d(in_d), .in_rdy(in_rdy), .idle(idle),
        .t_v(t_v), .t_d(t_d), .f_cr(bw[RLY-1]), .fault(txf));
    ot_hgi_coll_crl_rx #(.W(W), .CRD(CRD), .MUT(MUT)) u_r (.clk(clk), .rst_n(rst_n), .t_v(fw[RLY-1][W]), .t_d(fw[RLY-1][W-1:0]),
        .f_cr(f_cr), .out_v(out_v), .out_d(out_d), .out_rdy(out_rdy), .fault(rxf));
    function automatic [W-1:0] word(input integer k); word = {18{32'(k * 2654435761 + 7)}}; endfunction
    integer sent = 0, got = 0, errs = 0, inflight = 0;
    always @(posedge clk) if (rst_n) begin
        if (in_v && in_rdy) begin sent = sent + 1; inflight = inflight + 1; end
        if (out_v && out_rdy) begin
            if (out_d !== word(got)) begin errs = errs + 1; if (errs < 5) $display("CRL_MISMATCH k=%0d", got); end
            got = got + 1; inflight = inflight - 1;
        end
    end
    // idle must be low while anything accepted is not yet taken by the consumer (checked a cycle late: registered)
    reg [1:0] busy_h = 0; always @(posedge clk) busy_h <= {busy_h[0], inflight != 0};
    always @(negedge clk) if (rst_n && busy_h[1] && inflight != 0 && idle) begin errs = errs + 1; if (errs < 5) $display("CRL_IDLE_EARLY cyc=%0d", cyc); end
    always @(negedge clk) if (rst_n) begin
        if (!in_v || in_rdy) begin in_v = (sent + (in_v && in_rdy ? 1 : 0) < N) && ($urandom % 4 != 0); end
        out_rdy = ($urandom % 3) != 0;
    end
    always @* in_d = word(sent);                                       // the next word after each transfer edge
    initial begin
        repeat (4) @(negedge clk); rst_n = 1;
        while ((got < N || !idle) && cyc < 200000) @(negedge clk);
        repeat (50) @(negedge clk);
        if (got != N || sent != N) begin errs = errs + 1; $display("CRL_COUNT sent=%0d got=%0d", sent, got); end
        if (!idle || txf || rxf) begin errs = errs + 1; $display("CRL_END idle=%0d txfault=%0d rxfault=%0d", idle, txf, rxf); end
        if (errs == 0) $display("CRL PASS words=%0d cycles=%0d RLY=%0d CRD=%0d", got, cyc, RLY, CRD); else $display("CRL FAIL errors=%0d", errs);
        $finish;
    end
endmodule
