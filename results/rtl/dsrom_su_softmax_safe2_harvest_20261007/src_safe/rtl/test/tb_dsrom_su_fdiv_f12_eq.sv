`timescale 1ns/1ps
// Equivalence of ot_dsrom_su_fdiv_f12 (DEPTH 32) with ot_hdc_v41x_fdiv (DEPTH 19): {y, fault} of every pair equal.
// +N=<pairs> +SEED=<seed>.  Operands: random bit patterns, subnormals, specials (0, inf, NaN), equal and adjacent
// significands, results near overflow / underflow.  Prints FDIVEQ n=<pairs> mismatches=<m>.
module tb_dsrom_su_fdiv_f12_eq;
    parameter integer NR = 0;                   // the unit under test's non-restoring build (DEPTH 34)
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    reg         v;
    reg  [31:0] a, b;
    wire [31:0] y0, y1;
    wire        f0, f1, vo0, vo1;
    ot_hdc_v41x_fdiv     u0 (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(y0), .vo(vo0), .fault(f0));
    ot_dsrom_su_fdiv_f12 #(.NR(NR)) u1 (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(y1), .vo(vo1), .fault(f1));
    reg [32:0] q0 [0:63];
    integer n, N, seed, mism, w0, r0, k;
    reg [31:0] ta;
    function automatic [31:0] pick(input integer s);
        reg [31:0] r;
        integer c;
        begin
            r = $urandom;
            c = $urandom % 10;
            case (c)
                0: pick = {r[31], 8'd0, r[22:0]};                       // subnormal
                1: pick = {r[31], 8'd0, 22'd0, r[0]};                   // tiny subnormal
                2: pick = {r[31], 8'hFF, (r[1] ? r[22:0] : 23'd0)};     // inf / NaN
                3: pick = {r[31], 31'd0};                               // zero
                4: pick = {r[31], 8'd254 - r[2:0], r[22:0]};            // huge
                5: pick = {r[31], 8'd1 + r[2:0], r[22:0]};              // near the subnormal edge
                default: pick = r;
            endcase
        end
    endfunction
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 1000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        void'($urandom(seed));
        v = 0; a = 0; b = 0; mism = 0; w0 = 0; r0 = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        for (n = 0; n < N + 40; n = n + 1) begin
            @(posedge clk);
            if (n < N) begin
                v <= 1'b1;
                k = $urandom % 5;
                if (k == 4) begin
                    // directed: a near the subnormal edge over a power of two, so the quotient denormalises and
                    // often lands exactly halfway (remainder zero, the round-to-even tie that reads the sticky)
                    ta = $urandom;
                    a <= {ta[31], 8'd1 + {4'd0, ta[26:23] & 4'd7}, ta[22:0]};
                    b <= {ta[30], 8'd128 + ($urandom % 26), 23'd0};
                end else begin
                    a <= pick(0);
                    if (k == 0) b <= {$urandom} ; else if (k == 1) b <= {a[31] ^ 1'b0, a[30:23] - 8'd1 + ($urandom % 3), a[22:0] ^ ($urandom % 4)};
                    else b <= pick(1);
                end
            end else v <= 1'b0;
        end
        $display("FDIVEQ n=%0d mismatches=%0d", N, mism);
        $finish;
    end
    // the 19-deep result waits in a FIFO for the 32-deep one
    always @(posedge clk) begin
        if (vo0) begin q0[w0 % 64] <= {f0, y0}; w0 <= w0 + 1; end
        if (vo1) begin
            if (q0[r0 % 64] !== {f1, y1}) begin
                if (mism < 10) $display("MISMATCH %h %h", q0[r0 % 64], {f1, y1});
                mism = mism + 1;
            end
            r0 <= r0 + 1;
        end
    end
endmodule
