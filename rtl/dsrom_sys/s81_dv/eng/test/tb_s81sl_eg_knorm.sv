`timescale 1ns/1ps
// RTLGAP-SUKV 10-21: eng.knorm (Engram key/h RMSNorm scalars, golden per copy j: rsqrt(csum(h_j^2)/5120 + eps),
// rsqrt(csum(k_j^2)/5120 + eps)) is computed on the die by ot_s81sl_eg's two ot_s81_engram_norm leaves (u_nh / u_nk:
// ot_dsrom_divc /5120, + eps, rsqrt), present in every slice (ot_s81sl_slice u_eg).  This bench drives the 4 copies'
// totals (xfin's finished hh / kk sums) back to back and checks the norm leaves' outputs bit-exact against the L14
// fixture op eng.knorm (8 words: rsqrt h_j, rsqrt k_j).  knorm.mem: 4 lines {dd, kk, hh} (96 b), exp_knorm.mem 8 words.
module tb_s81sl_eg_knorm;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    reg i_v = 0; reg [1:0] i_c = 0; reg [31:0] i_hh = 0, i_kk = 0, i_dd = 0;
    wire g_v; wire [1:0] g_c; wire [31:0] g; wire fault;
    reg [31:0] eps;
    ot_s81sl_eg dut (.clk(clk), .rst_n(rst_n), .eps(eps), .scale(32'h3f800000), .i_v(i_v), .i_c(i_c), .i_hh(i_hh),
        .i_kk(i_kk), .i_dd(i_dd), .g_v(g_v), .g_c(g_c), .g(g), .fault(fault));
    reg [95:0] cm [0:3]; reg [31:0] ex [0:7]; reg [31:0] ep [0:0];
    integer n = 0, bad = 0, cyc = 0, t0 = -1, lat = -1, ng = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (dut.nv[0]) begin
            if (lat < 0) lat = cyc - t0;
            if (dut.rs_h !== ex[2 * n] || dut.rs_k !== ex[2 * n + 1]) begin
                bad = bad + 1;
                $display("KNORM mismatch copy %0d rs_h %08h/%08h rs_k %08h/%08h", n, dut.rs_h, ex[2 * n], dut.rs_k, ex[2 * n + 1]);
            end
            n = n + 1;
        end
        if (g_v) ng = ng + 1;
    end
    integer i;
    initial begin
        $readmemh("knorm.mem", cm); $readmemh("exp_knorm.mem", ex); $readmemh("eps.mem", ep); eps = ep[0];
        repeat (8) @(negedge clk); rst_n = 1; repeat (16) @(negedge clk);
        for (i = 0; i < 4; i = i + 1) begin
            i_v = 1; i_c = i; {i_dd, i_kk, i_hh} = cm[i]; if (i == 0) t0 = cyc; @(negedge clk);
        end
        i_v = 0;
        repeat (400) @(negedge clk);
        $display("KNORM copies=%0d bad=%0d fault=%0d norm_latency=%0d gates=%0d", n, bad, fault, lat, ng);
        if (n != 4 || bad || fault || ng != 4) $fatal(1, "KNORM FAIL");
        $display("KNORM PASS eng.knorm = ot_s81sl_eg u_nh/u_nk bit-exact (L14 fixture)");
        $finish;
    end
endmodule
