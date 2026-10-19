`timescale 1ns/1ps
// RTL-BUILD-S81: bench of ot_s81sl_eg (Engram scalar finish) against tools/s81_dv/eg_golden.py (hdc_golden_v41
// engram_layer scalar chain, chunk8).  Cases stream in bursts of 4 copies back to back (one i_v a cycle, copy = case % 4),
// GAP idle cycles between bursts (GAP 0 = one continuous stream).  Every gate is checked bit-exact and in order, with its
// copy tag; the latency i_v -> g_v is measured and must be the same for every case (fixed latency).  MUT != 0 must
// produce mismatches (negative control).
module tb_s81sl_eg #(parameter integer MUT = 0, GAP = 3);
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    reg [31:0] eps, scale; reg i_v = 0; reg [1:0] i_c = 0; reg [31:0] i_hh, i_kk, i_dd;
    wire g_v; wire [1:0] g_c; wire [31:0] g; wire fault;
    ot_s81sl_eg #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .eps(eps), .scale(scale), .i_v(i_v), .i_c(i_c), .i_hh(i_hh),
        .i_kk(i_kk), .i_dd(i_dd), .g_v(g_v), .g_c(g_c), .g(g), .fault(fault));
    reg [127:0] cm [0:255]; reg [31:0] cfg [0:2]; string dir;
    integer n, i, nin = 0, nout = 0, bad = 0, cyc = 0, lat = -1, latbad = 0;
    integer tin [0:255];
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (fault && MUT == 0) $fatal(1, "fault at cycle %0d", cyc);
        if (g_v) begin
            if (nout >= n) $fatal(1, "extra gate");
            if (g !== cm[nout][31:0] || g_c !== nout[1:0]) begin
                bad = bad + 1;
                if (bad <= 6) $display("BAD case %0d copy %0d/%0d gate %08h/%08h", nout, g_c, nout % 4, g, cm[nout][31:0]);
            end
            if (lat < 0) lat = cyc - tin[nout]; else if (cyc - tin[nout] != lat) latbad = latbad + 1;
            nout = nout + 1;
        end
    end
    initial begin
        if (!$value$plusargs("dir=%s", dir)) dir = "fx";
        $readmemh({dir, "/cases.mem"}, cm); $readmemh({dir, "/cfg.mem"}, cfg);
        eps = cfg[0]; scale = cfg[1]; n = cfg[2];
        repeat (6) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
        for (i = 0; i < n; i = i + 1) begin
            i_v = 1; i_c = i[1:0]; i_hh = cm[i][127:96]; i_kk = cm[i][95:64]; i_dd = cm[i][63:32]; tin[i] = cyc;
            @(negedge clk);
            i_v = 0; i_hh = 32'hx; i_kk = 32'hx; i_dd = 32'hx;
            if (i % 4 == 3) repeat (GAP) @(negedge clk);
        end
        repeat (400) @(negedge clk);
        if (nout != n) $fatal(1, "TIMEOUT gates %0d of %0d", nout, n);
        if (MUT != 0) begin
            if (bad == 0) $fatal(1, "MUTANT %0d NOT DETECTED", MUT);
            $display("FAIL MUTANT %0d REJECTED mismatches=%0d of %0d", MUT, bad, n);
        end else begin
            if (bad != 0 || latbad != 0) $fatal(1, "FAIL mismatches=%0d latency_var=%0d", bad, latbad);
            $display("PASS ot_s81sl_eg %0d copies bit exact (GAP %0d), fixed latency i_v -> g_v %0d cycles", n, GAP, lat);
        end
        $finish;
    end
endmodule
