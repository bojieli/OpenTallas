`timescale 1ns/1ps
// Exact lockstep bench: ot_gpu_router_topk (reference, as built) vs ot_gpu_router_topk_ps
// (PIPESEL = 1 pipelined selection, or 2 half-rate fallback) on one stream of NV router vectors:
// heavy ties, +-0, +-Inf, NaN payloads of both signs, denormals, all-equal vectors, back-to-back
// vectors and random bubbles (RATE = 2: a beat at most every other cycle, as PIPESEL = 2 needs).
// Every selection is compared in vector order; counts must match; the latency of both is printed.
// NEG != 0 plants a known error in the DUT; the bench must then FAIL (negative control).
module tb_router_topk_ps;
    parameter integer N = 384, P = 16, K = 6, NV = 400, SEED = 1, PIPESEL = 1, RATE = 1, NEG = 0;
    localparam integer IW = 9;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg in_valid = 0, in_last = 0;
    reg [P*32-1:0] in_vals = 0;
    wire ov0, ov1;
    wire [K*IW-1:0] id0, id1;
    ot_gpu_router_topk #(.N(N), .P(P), .K(K), .IW(IW)) d0 (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_vals(in_vals), .in_last(in_last), .out_valid(ov0), .out_ids(id0));
    ot_gpu_router_topk_ps #(.N(N), .P(P), .K(K), .IW(IW), .PIPESEL(PIPESEL), .NEG(NEG)) d1 (.clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_vals(in_vals), .in_last(in_last), .out_valid(ov1), .out_ids(id1));
    reg [K*IW-1:0] q0 [0:NV-1];
    reg [K*IW-1:0] q1 [0:NV-1];
    integer n0 = 0, n1 = 0, bad = 0, cyc = 0, lat0 = 0, lat1 = 0, lmin1 = 1 << 30, lmax1 = 0, tl [0:NV-1];
    integer seed, v, bt, j, mode, nb, gap, ties = 0;
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk) begin
        if (ov0 === 1'b1) begin q0[n0] = id0; lat0 = cyc - tl[n0]; n0 = n0 + 1; end
        if (ov1 === 1'b1) begin
            if (n1 < NV) q1[n1] = id1;
            lat1 = cyc - tl[n1]; if (lat1 < lmin1) lmin1 = lat1; if (lat1 > lmax1) lmax1 = lat1;
            n1 = n1 + 1;
        end
        if (ov1 !== 1'b0 && ov1 !== 1'b1 && rst_n) begin bad = bad + 1; $display("X on out_valid"); end
    end
    reg [31:0] spec [0:11];
    initial begin
        spec[0] = 32'h0000_0000; spec[1] = 32'h8000_0000; spec[2] = 32'h7f80_0000; spec[3] = 32'hff80_0000;
        spec[4] = 32'h7fc0_0000; spec[5] = 32'h7f80_0001; spec[6] = 32'hffc0_0000; spec[7] = 32'hff80_0001;
        spec[8] = 32'h3f80_0000; spec[9] = 32'hbf80_0000; spec[10] = 32'h0000_0001; spec[11] = 32'h8000_0001;
    end
    reg [31:0] fixed;
    function [31:0] rv(input integer md, input integer lane);
        reg [31:0] r;
        begin
            r = $random(seed);
            case (md)
                0: rv = r;                                                 // anything (NaN / Inf patterns)
                1: rv = {r[31], 8'd127 + r[2:0], r[22:21], 21'd0};         // few distinct values: many ties
                2: rv = (r[1:0] == 0) ? 32'h8000_0000 : (r[1:0] == 1) ? 32'h0 : {r[31], 8'd126, 23'd0};
                3: rv = spec[r[7:0] % 12];                                 // +-0, +-Inf, NaNs, +-1, denormals
                4: rv = fixed;                                             // all equal
                5: rv = {1'b0, 8'd120 + r[1:0], 23'd0};                    // positive, 4 values
                7: rv = (r[4:0] == 0) ? {r[5], 31'd0} : {1'b1, 8'd120 + r[4:0], r[22:0]};  // sparse +-0 above negatives
                6: rv = (r[4:0] == 0) ? spec[2 + r[6:5]] : {r[31], 8'd120 + r[4:0], r[22:0]};  // rare specials
                default: rv = {r[31], 8'd120 + r[4:0], r[22:0]};           // router-like magnitudes
            endcase
        end
    endfunction
    initial begin
        seed = SEED;
        repeat (5) @(posedge clk);
        #0.1 rst_n = 1;
        repeat (4) @(posedge clk);
        for (v = 0; v < NV; v = v + 1) begin
            mode = $random(seed); mode = (mode < 0 ? -mode : mode) % 9;
            fixed = spec[v % 12];
            nb = N / P;
            for (bt = 0; bt < nb; bt = bt + 1) begin
                gap = $random(seed);
                if (RATE == 1) begin
                    if ((gap & 15) == 0) begin @(negedge clk); in_valid = 0; in_last = 0; in_vals = {P{$random(seed)}}; end
                end else begin
                    @(negedge clk); in_valid = 0; in_last = 0; in_vals = {P{$random(seed)}};
                    if ((gap & 7) == 0) begin @(negedge clk); end
                end
                @(negedge clk);
                for (j = 0; j < P; j = j + 1) in_vals[32*j +: 32] = rv(mode, j);
                in_valid = 1; in_last = (bt == nb - 1);
                if (bt == nb - 1) tl[v] = cyc;
            end
        end
        @(negedge clk); in_valid = 0; in_last = 0;
        repeat (200) @(posedge clk);
        for (v = 0; v < NV; v = v + 1)
            if (q0[v] !== q1[v]) begin bad = bad + 1; if (bad < 10) $display("MISMATCH vec %0d ref %h dut %h", v, q0[v], q1[v]); end
        $display("ROUTER_PS PIPESEL=%0d RATE=%0d NEG=%0d SEED=%0d vectors ref=%0d dut=%0d bad=%0d latency ref=%0d dut=%0d..%0d",
                 PIPESEL, RATE, NEG, SEED, n0, n1, bad, lat0, lmin1, lmax1);
        if (bad != 0 || n0 != NV || n1 != NV) begin $display("ROUTER_PS FAIL"); $fatal(1, "ROUTER_PS FAIL"); end
        $display("ROUTER_PS PASS");
        $finish;
    end
endmodule
