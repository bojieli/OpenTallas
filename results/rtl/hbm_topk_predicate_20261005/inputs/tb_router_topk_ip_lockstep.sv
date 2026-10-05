`timescale 1ns/1ps
// Lockstep bench: ot_gpu_router_topk (as built) vs ot_gpu_router_topk_f (1.2 GHz successor) on the same
// stream of NV random router vectors (heavy ties, +-0, extreme exponents, NaN bit patterns, random bubbles).
// Every selection of both is compared in order; the latency delta is printed.
module tb_router_topk_ip_lockstep;
    parameter integer N = 384, P = 16, K = 6, NV = 2000, SEED = 1;
    localparam integer IW = 9;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg in_valid = 0, in_last = 0;
    reg [P*32-1:0] in_vals;
    wire ov0, ov1;
    wire [K*IW-1:0] id0, id1;
    ot_gpu_router_topk #(.N(N), .P(P), .K(K), .IW(IW)) d0 (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_vals(in_vals), .in_last(in_last), .out_valid(ov0), .out_ids(id0));
    ot_gpu_router_topk_ip_f #(.N(N), .P(P), .K(K), .IW(IW)) d1 (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_vals(in_vals), .in_last(in_last), .out_valid(ov1), .out_ids(id1));
    reg [K*IW-1:0] q0 [0:NV-1];
    integer n0 = 0, n1 = 0, bad = 0, cyc = 0, c0 = 0, c1 = 0, lat0 = 0, lat1 = 0, tl [0:NV-1];
    integer seed, v, b, j, mode;
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk) begin
        if (ov0) begin q0[n0] = id0; lat0 = cyc - tl[n0]; n0 = n0 + 1; end
        if (ov1) begin
            if (n1 >= n0 && !ov0) begin bad = bad + 1; $display("ORDER %0d", n1); end
            else if (q0[n1] !== id1) begin bad = bad + 1; if (bad < 10) $display("MISMATCH %0d %h %h", n1, q0[n1], id1); end
            lat1 = cyc - tl[n1]; n1 = n1 + 1;
        end
    end
    function [31:0] rv(input integer m);
        reg [31:0] r;
        begin
            r = $random(seed);
            case (m)
                0: rv = r;                                         // anything (incl. NaN / Inf patterns)
                1: rv = {r[31], 8'd127 + r[2:0], r[22:20], 20'd0}; // few distinct values: many ties
                2: rv = (r[1:0] == 0) ? 32'h8000_0000 : (r[1:0] == 1) ? 32'h0 : {r[31], 8'd126, 23'd0};
                default: rv = {r[31], 8'd120 + r[4:0], r[22:0]};   // router-like magnitudes
            endcase
        end
    endfunction
    initial begin
        seed = SEED;
        repeat (3) @(posedge clk);
        rst_n = 1;
        for (v = 0; v < NV; v = v + 1) begin
            mode = v % 4;
            for (b = 0; b < N / P; b = b + 1) begin
                @(negedge clk);
                if (($random(seed) & 7) == 0) begin in_valid = 0; in_last = 0; @(negedge clk); end
                in_valid = 1; in_last = (b == N / P - 1);
                for (j = 0; j < P; j = j + 1) in_vals[32*j +: 32] = rv(mode);
                if (in_last) tl[v] = cyc + 1;
            end
            if (($random(seed) & 3) == 0) begin @(negedge clk); in_valid = 0; in_last = 0; repeat ($random(seed) & 15) @(negedge clk); end
        end
        @(negedge clk); in_valid = 0; in_last = 0;
        // Intrinsic finite pipeline drain, not a wall/CPU execution cap.
        repeat (4*$clog2(P)+16) @(posedge clk);
        if (n0 != NV || n1 != NV) bad = bad + 1;
        $display("LOCKSTEP N=%0d P=%0d K=%0d vectors=%0d sel0=%0d sel1=%0d mismatches=%0d lat0=%0d lat1=%0d", N, P, K, NV, n0, n1, bad, lat0, lat1);
        if (bad != 0) $fatal(1,"EXACTNESS_FAIL");
        $finish;
    end
endmodule
