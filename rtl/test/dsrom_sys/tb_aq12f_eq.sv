`timescale 1ns/1ps
// lockstep equivalence: ot_dsrom_aq12f (v10) vs ot_dsrom_aq12 (v9, the exact-proven quantiser), every output every cycle
module tb_aq12f_eq;
    reg clk = 0, rst_n = 0, v = 0;
    reg [1023:0] x;
    wire vo0, vo1, f0, f1; wire [255:0] q0, q1; wire signed [9:0] e0, e1; wire [511:0] y0, y1;
    ot_dsrom_aq12  u_ref (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo0), .q(q0), .e(e0), .y(y0), .fault(f0));
    ot_dsrom_aq12f u_dut (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo1), .q(q1), .e(e1), .y(y1), .fault(f1));
    integer cyc = 0, mism = 0, nvo = 0, nfault = 0, k, N;
    reg [31:0] r; reg [7:0] base;
    function [31:0] lane(input [7:0] bexp, input integer mode);
        reg [31:0] t; begin
            t = $urandom;
            case (mode)
                0: t[30:23] = bexp + ($urandom % 24) - 12;      // clustered exponents (max tree ties near)
                1: t[30:23] = $urandom % 255;                     // anything finite
                2: t[30:0] = 31'd0;                                // zero
                3: t[30:23] = 8'd0;                                // subnormal
                default: t[30:23] = bexp;                          // same exponent
            endcase
            lane = t;
        end
    endfunction
    always #1 clk = ~clk;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 200000;
        x = 0; repeat (4) @(posedge clk); rst_n = 1;
        while (cyc < N) begin
            @(negedge clk);
            v = ($urandom % 4) != 0;
            base = 8'd40 + ($urandom % 180);
            for (k = 0; k < 32; k = k + 1) x[32*k +: 32] = lane(base, ($urandom % 16 < 9) ? 0 : ($urandom % 4) + 1);
            if ($urandom % 50 == 0) x[32*($urandom % 32) + 23 +: 8] = 8'hFF;   // nonfinite in a random lane
            if ($urandom % 20 == 0) x[32*($urandom % 32) +: 32] = x[32*($urandom % 32) +: 32];  // exact tie
            cyc = cyc + 1;
        end
        repeat (30) @(posedge clk);
        $display("AQ12F_EQ cycles=%0d vo=%0d faults=%0d mismatches=%0d %s", cyc, nvo, nfault, mism, mism == 0 ? "PASS" : "FAIL");
        if (mism != 0 || nvo < N / 2) $fatal(1, "AQ12F_EQ FAIL");
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        if (vo0) nvo = nvo + 1;
        if (vo0 && f0) nfault = nfault + 1;
        if (vo0 !== vo1 || f0 !== f1 || (vo0 && (q0 !== q1 || e0 !== e1 || y0 !== y1))) begin
            mism = mism + 1;
            if (mism < 4) $display("MISMATCH t=%0t vo %b/%b f %b/%b e %0d/%0d", $time, vo0, vo1, f0, f1, e0, e1);
        end
    end
endmodule
