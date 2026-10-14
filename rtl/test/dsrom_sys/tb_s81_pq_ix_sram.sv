`timescale 1ns/1ps
module tb_s81_pq_ix_sram;
    parameter integer PAR = 0;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg [1023:0] xw = 0;
    reg ba_v = 0;
    reg [7:0] ba_blk = 0;
    reg [35:0] h_hi = 0;
    reg [6:0] hw7 = 0;
    wire [255:0] actual, reference;
    wire fault;
    ot_s81_pq_ix_sram dut (.clk(clk), .rst_n(rst_n), .par(1'(PAR)), .xw(xw), .ba_v(ba_v),
        .ba_blk(ba_blk), .h_hi(h_hi), .hw7(hw7), .bt_d(actual), .fault(fault));
    ot_v41_pqc_ix #(.KMAX(6144), .VRD(64)) ref_ix (.clk(clk), .rst_n(rst_n), .par(1'(PAR)), .xw(xw), .ba_v(ba_v),
        .ba_blk(ba_blk), .h_hi(h_hi), .hw7(hw7), .bt_d(reference));
    integer checks = 0, rows = 0, cycle = 0;
    reg compare = 0;
    always @(negedge clk) begin
        cycle = cycle + 1;
        if (compare) begin
            if (actual !== reference) begin
                $display("PQ_IX_SRAM FAIL par=%0d cycle=%0d actual=%h reference=%h", PAR, cycle, actual, reference);
                $fatal(1, "bit-exact mismatch");
            end
            if (fault) $fatal(1, "unexpected parity fault");
            checks = checks + 16;
        end
    end
    integer b, k, hi, sub, group;
    initial begin
        repeat (8) @(negedge clk);
        rst_n = 1;
        repeat (8) @(negedge clk);
        // Full production storage, both buffer parities. Pipeline data is
        // deliberately changed every edge: the original tile fixes alignment.
        for (b = 0; b < 192; b = b + 1) begin
            xw = '0;
            for (k = 0; k < 32; k = k + 1)
                xw[32*k +: 32] = 32'h3e800000 ^ (32'(b) << 15) ^ (32'(k) << 7) ^ 32'h42;
            ba_blk = 8'(b); ba_v = 1;
            @(negedge clk);
        end
        ba_v = 0;
        repeat (8) @(negedge clk);
        compare = 1;
        // Every row, every byte selector, and independent rows for all four
        // concurrent read groups. Group enables include partial lane activity.
        for (hi = 0; hi < 96; hi = hi + 1)
            for (sub = 0; sub < 8; sub = sub + 1) begin
                for (group = 0; group < 4; group = group + 1)
                    h_hi[9*group +: 9] = 9'((hi + 17*group) % 96);
                hw7 = {4'b1111, 3'(sub)};
                @(negedge clk);
                rows = rows + 4;
            end
        for (k = 0; k < 256; k = k + 1) begin
            for (group = 0; group < 4; group = group + 1)
                h_hi[9*group +: 9] = 9'((13*k + 29*group) % 96);
            hw7 = {4'(k), 3'(k)};
            @(negedge clk);
        end
        hw7 = 0;
        repeat (6) @(negedge clk);
        compare = 0;
        if (checks < 16000) $fatal(1, "insufficient production coverage");
        // A physical SRAM-bit corruption must reach the sticky fault output;
        // the memory response is consumed through the actual macro model.
        dut.g_read_group[0].g_bank[0].u_mem.arr[0][0] = ~dut.g_read_group[0].g_bank[0].u_mem.arr[0][0];
        h_hi = 0; hw7 = 7'b0001000;
        repeat (8) @(negedge clk);
        if (!fault) $fatal(1, "physical SRAM corruption was not caught");
        hw7 = 0;
        repeat (5) @(negedge clk);
        if (!fault) $fatal(1, "parity fault was not sticky");
        $display("PQ_IX_SRAM PASS par=%0d checks=%0d independent_reads=%0d rows=96 replicas=4 macros=8 parity_fault=1", PAR, checks, rows);
        $finish;
    end
endmodule
