`timescale 1ns/1ps
// lockstep equivalence: ot_dsrom_aq12m (v13 margin restaging, LATENCY 29) vs ot_dsrom_aq12f (v10/v11, LATENCY 18): every
// output of aq12m at cycle t + 11 against aq12f at cycle t, every cycle (outputs and vo / fault, valid or not)
module tb_aq12m_eq;
    localparam integer DL = 29 - 18;
    reg clk = 0, rst_n = 0, v = 0;
    reg [1023:0] x;
    wire vo0, vo1, f0, f1; wire [255:0] q0, q1; wire signed [9:0] e0, e1; wire [511:0] y0, y1;
    ot_dsrom_aq12f u_ref (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo0), .q(q0), .e(e0), .y(y0), .fault(f0));
    ot_dsrom_aq12m u_dut (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo1), .q(q1), .e(e1), .y(y1), .fault(f1));
    integer cyc = 0, mism = 0, nvo = 0, nfault = 0, k, N, sd;
    reg [31:0] r; reg [7:0] base;
    function [31:0] lane(input [7:0] bexp, input integer mode);
        reg [31:0] t; begin
            t = $urandom;
            case (mode)
                0: t[30:23] = bexp + ($urandom % 24) - 12;      // clustered exponents (max tree ties near)
                1: t[30:23] = $urandom % 255;                     // anything finite
                2: t[30:0] = 31'd0;                                // zero
                3: t[30:23] = 8'd0;                                // subnormal
                4: t[30:23] = $urandom % 110;                     // tiny (amax at / below the 1e-4 floor)
                default: t[30:23] = bexp;                          // same exponent
            endcase
            lane = t;
        end
    endfunction
    always #1 clk = ~clk;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 200000;
        if ($value$plusargs("SEED=%d", sd)) k = $urandom(sd);           // shard seed (one stream per run)
        x = 0; repeat (4) @(posedge clk); rst_n = 1;
        while (cyc < N) begin
            @(negedge clk);
            v = (cyc % 4096 < 1024) ? 1'b1 : (($urandom % 4) != 0);         // back-to-back bursts
            if (cyc % 7919 < 64) base = 8'd1 + ($urandom % 30);              // tiny-only bursts below
            if (!(cyc % 7919 < 64)) base = 8'd40 + ($urandom % 180);
            for (k = 0; k < 32; k = k + 1) x[32*k +: 32] = lane(base, ($urandom % 16 < 9) ? 0 : ($urandom % 5) + 1);
            if ($urandom % 50 == 0) x[32*($urandom % 32) + 23 +: 8] = 8'hFF;   // nonfinite in a random lane
            if ($urandom % 20 == 0) x[32*($urandom % 32) +: 32] = x[32*($urandom % 32) +: 32];  // exact tie
            cyc = cyc + 1;
        end
        repeat (50) @(posedge clk);
        $display("AQ12M_EQ cycles=%0d compared=%0d vo=%0d faults=%0d mismatches=%0d %s", cyc, cmpn, nvo, nfault, mism, mism == 0 ? "PASS" : "FAIL");
        if (mism != 0 || nvo < N / 2) $fatal(1, "AQ12M_EQ FAIL");
        $finish;
    end
    // reference history: aq12f outputs of the last DL cycles (h[0] = previous cycle's sample... h[DL-1] = DL cycles ago)
    reg hvo [0:DL-1]; reg hf [0:DL-1]; reg [255:0] hq [0:DL-1]; reg signed [9:0] he [0:DL-1]; reg [511:0] hy [0:DL-1];
    integer j, cmpn = 0;
    always @(posedge clk) if (rst_n) begin
        if (vo0) nvo = nvo + 1;
        if (vo0 && f0) nfault = nfault + 1;
        if (cyc > DL + 4) begin
            cmpn = cmpn + 1;
            if (hvo[DL-1] !== vo1 || hf[DL-1] !== f1 || (vo1 && (hq[DL-1] !== q1 || he[DL-1] !== e1 || hy[DL-1] !== y1))) begin
                mism = mism + 1;
                if (mism < 4) $display("MISMATCH t=%0t vo %b/%b f %b/%b e %0d/%0d", $time, hvo[DL-1], vo1, hf[DL-1], f1, he[DL-1], e1);
            end
        end
        for (j = DL - 1; j > 0; j = j - 1) begin hvo[j] = hvo[j-1]; hf[j] = hf[j-1]; hq[j] = hq[j-1]; he[j] = he[j-1]; hy[j] = hy[j-1]; end
        hvo[0] = vo0; hf[0] = f0; hq[0] = q0; he[0] = e0; hy[0] = y0;
    end
endmodule
