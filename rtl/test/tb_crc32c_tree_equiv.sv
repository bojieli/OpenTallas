`timescale 1ns/1ps
// The XOR-mask CRC32C against the algorithm it is derived from.
//
// ot_crc_pkg::crc32c states the reflected Castagnoli CRC one bit at a time, which is
// the right way to state it and a 1,536-step chain to synthesise.  ot_crc32c_tree_pkg
// computes the same function as 32 balanced XOR reductions over generated masks.  The
// tables are verified against the reference at generation time; this is the standing
// gate, so a regenerated table that drifts fails here rather than in a route.
//
// Every width the synthesisable RTL calls crc32c at is driven: 64 (a link flit), 1024
// (a numeric descriptor and the wafer adapter's records), 1536 (a descriptor record)
// and 2048 (the adapter's topology record).  Each gets the edge cases a CRC gets
// wrong when a table is off by one -- all zeros, all ones, the lowest bit, the
// highest -- and random data.
module tb_crc32c_tree_equiv;
    integer errors = 0, checks = 0, t;
    reg [2047:0] d;
    reg [31:0] ref_v, tree_v;
    reg [31:0] seed = 32'h1234_5678;

    function [31:0] nxt; input [31:0] s; nxt = s*32'd1664525 + 32'd1013904223; endfunction

    task fill(input integer w);
        integer k;
        begin
            d = 2048'b0;
            for (k = 0; k < w; k = k + 32) begin
                seed = nxt(seed);
                d[k +: 32] = seed;
            end
        end
    endtask

    task check64;  begin
        ref_v  = ot_crc_pkg::crc32c(64,   {{(4096-64){1'b0}},   d[63:0]});
        tree_v = ot_crc32c_tree_pkg::crc32c_64(d[63:0]);
        checks = checks + 1;
        if (ref_v !== tree_v) begin errors = errors + 1;
            if (errors < 8) $display("FAIL w=64 data=%h ref %08x tree %08x", d[63:0], ref_v, tree_v); end
    end endtask
    task check1024; begin
        ref_v  = ot_crc_pkg::crc32c(1024, {{(4096-1024){1'b0}}, d[1023:0]});
        tree_v = ot_crc32c_tree_pkg::crc32c_1024(d[1023:0]);
        checks = checks + 1;
        if (ref_v !== tree_v) begin errors = errors + 1;
            if (errors < 8) $display("FAIL w=1024 ref %08x tree %08x", ref_v, tree_v); end
    end endtask
    task check1536; begin
        ref_v  = ot_crc_pkg::crc32c(1536, {{(4096-1536){1'b0}}, d[1535:0]});
        tree_v = ot_crc32c_tree_pkg::crc32c_1536(d[1535:0]);
        checks = checks + 1;
        if (ref_v !== tree_v) begin errors = errors + 1;
            if (errors < 8) $display("FAIL w=1536 ref %08x tree %08x", ref_v, tree_v); end
    end endtask
    task check2048; begin
        ref_v  = ot_crc_pkg::crc32c(2048, {{2048{1'b0}}, d[2047:0]});
        tree_v = ot_crc32c_tree_pkg::crc32c_2048(d[2047:0]);
        checks = checks + 1;
        if (ref_v !== tree_v) begin errors = errors + 1;
            if (errors < 8) $display("FAIL w=2048 ref %08x tree %08x", ref_v, tree_v); end
    end endtask

    task all_widths; begin check64; check1024; check1536; check2048; end endtask

    initial begin
        //: all zeros
        d = 2048'b0;                         all_widths;
        //: all ones
        d = {2048{1'b1}};                    all_widths;
        //: the lowest bit, which a table indexed from the wrong end drops
        d = 2048'b0; d[0] = 1'b1;            all_widths;
        //: the highest bit of each width, one at a time
        d = 2048'b0; d[63] = 1'b1;           check64;
        d = 2048'b0; d[1023] = 1'b1;         check1024;
        d = 2048'b0; d[1535] = 1'b1;         check1536;
        d = 2048'b0; d[2047] = 1'b1;         check2048;
        //: a walking one through the low 64, where a reflected CRC is most delicate
        for (t = 0; t < 64; t = t + 1) begin
            d = 2048'b0; d[t] = 1'b1;        all_widths;
        end
        //: and random data
        for (t = 0; t < 60; t = t + 1) begin
            fill(2048);                      all_widths;
        end

        if (errors == 0)
            $display("PASS crc32c_tree: %0d comparisons over four widths, the XOR-mask form equals ot_crc_pkg::crc32c on every one", checks);
        else
            $display("FAIL crc32c_tree: %0d of %0d comparisons differ", errors, checks);
        $finish;
    end
endmodule
