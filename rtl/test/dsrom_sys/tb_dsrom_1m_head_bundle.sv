`timescale 1ns/1ps
// DS-ROM 1M head, recovery lever "head": one ot_dsrom_head_bundle (5 logical macros, 10 ROM4096, 128 rows) on the
// golden final-norm x.  tools/dsrom_1m_head.py (lmhead --sched bundle) writes into +DIR=<dir>:
//   xa.hex  256 lines: x slice m of K 0..4095 (16 BF16, lane l at [16l +: 16]);  xb.hex  64 lines: K 4096..5119
//   <inst>_{0,1}.viamap.hex  the skewed ROM images (loaded by the behavioural macros through +OT_ROM_DIR)
// +ROW0=<first row>.  Prints "B <n> <bits> <cyc>" (padded root1024, B row order), "A <q> <bits> <cyc>" (root4096),
// "L <q> <bits> <cyc>" (logit), then "RES <row> <bits> <fault> <cyc>" with cyc counted from the go cycle.
module tb_dsrom_1m_head_bundle #(parameter integer IOREG = 0, parameter integer SAFE = 0, parameter [8:0] CUT = 9'b1_0111_1011, parameter integer SPLIT9 = 0);
    reg clk = 1'b0, rst_n = 1'b0, go = 1'b0;
    always #0.5 clk = ~clk;
    reg [255:0] xa = '0, xb = '0;
    reg [16:0] row0;
    wire res_v, fault;
    wire [16:0] res_row;
    wire [31:0] res_bits;
    ot_dsrom_head_bundle #(.INSTANCE("h"), .IOREG(IOREG), .SAFE(SAFE), .CUT(CUT), .SPLIT9(SPLIT9)) dut (.clk(clk), .rst_n(rst_n), .go(go), .row0(row0), .xa(xa), .xb(xb),
        .res_v(res_v), .res_row(res_row), .res_bits(res_bits), .fault(fault));
    reg [255:0] ma [0:255];
    reg [255:0] mb [0:63];
    reg [8*1024-1:0] dir;
    integer cyc = 0, g0 = 0, m, r0, nb = 0;
    integer na [0:3];
    initial begin na[0] = 0; na[1] = 0; na[2] = 0; na[3] = 0; end
    always @(posedge clk) cyc <= cyc + 1;
    always @(negedge clk) begin
        if (dut.bo_v) begin $display("B %0d %08h %0d", nb, dut.bo_d, cyc - g0); nb = nb + 1; end
        if (dut.g_a[0].ov) $display("A 0 %08h %0d", dut.g_a[0].od, cyc - g0);
        if (dut.g_a[1].ov) $display("A 1 %08h %0d", dut.g_a[1].od, cyc - g0);
        if (dut.g_a[2].ov) $display("A 2 %08h %0d", dut.g_a[2].od, cyc - g0);
        if (dut.g_a[3].ov) $display("A 3 %08h %0d", dut.g_a[3].od, cyc - g0);
        if (dut.g_a[0].lv) $display("L 0 %08h %0d", dut.g_a[0].ld, cyc - g0);
        if (dut.g_a[1].lv) $display("L 1 %08h %0d", dut.g_a[1].ld, cyc - g0);
        if (dut.g_a[2].lv) $display("L 2 %08h %0d", dut.g_a[2].ld, cyc - g0);
        if (dut.g_a[3].lv) $display("L 3 %08h %0d", dut.g_a[3].ld, cyc - g0);
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("ROW0=%d", r0)) $fatal(1, "+ROW0");
        row0 = r0[16:0];
        $readmemh({dir, "/xa.hex"}, ma);
        $readmemh({dir, "/xb.hex"}, mb);
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);
        go = 1'b1; g0 = cyc;            // go is sampled at the end of cycle 0 (cycles printed relative to it)
        @(negedge clk); go = 1'b0;
        // slice m in cycle 5 + m
        fork
            begin
                for (m = 0; m < 8192 + 7 * 8 + 8; m = m + 1) begin
                    while (cyc - g0 != 5 + m) @(negedge clk);
                    xa = ma[m % 256]; xb = mb[m % 64];
                end
            end
            begin
                while (!res_v) @(negedge clk);
                $display("RES %0d %08h %0d %0d", res_row, res_bits, fault, cyc - g0);
                $finish;
            end
        join
    end
    initial begin #2000000; $display("TIMEOUT"); $finish; end
endmodule
