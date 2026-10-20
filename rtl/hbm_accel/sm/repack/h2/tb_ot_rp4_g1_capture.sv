`timescale 1ns/1ps
module tb_ot_rp4_g1_capture;
    parameter integer MUT = 0;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, bov = 0, fov = 0, bfault = 0, ffault = 0;
    reg [31:0] by = 0, fy = 0;
    reg [15:0] btag = 0, ftag = 0;
    wire gv, gf;
    wire [31:0] gy;
    wire [15:0] gt;
    ot_rp4_g1_capture #(.MUT(MUT)) dut (.*);
    reg ref_v = 0, ref_f = 0, prev_v = 0, prev_f = 0;
    reg [47:0] ref_data = 0, prev_data = 0;
    integer cycle, errors = 0, checked = 0, collisions = 0, resets = 0;
    initial begin
        for (cycle = 0; cycle < 4096; cycle = cycle + 1) begin
            @(negedge clk);
            // Includes reset reassertion, both producers, faults without valid,
            // and independent junk payload on invalid cycles.
            rst_n = cycle > 2 && (cycle % 257 != 0) && (cycle % 257 != 1);
            bov = $urandom_range(0, 1); fov = $urandom_range(0, 1);
            bfault = $urandom_range(0, 15) == 0;
            ffault = $urandom_range(0, 15) == 0;
            by = $urandom; fy = $urandom; btag = $urandom; ftag = $urandom;
            prev_v = ref_v; prev_f = ref_f; prev_data = ref_data;
            // Legacy G1 register is the reference, followed by one age edge.
            ref_v = rst_n && (bov | fov);
            ref_f = rst_n && (bfault | ffault | (bov & fov));
            ref_data = bov ? {by,btag} : {fy,ftag};
            @(posedge clk); #1;
            if (cycle > 1) begin
                checked = checked + 1;
                if (gv !== (rst_n && prev_v) || gf !== (rst_n && prev_f)
                    || {gy,gt} !== prev_data) begin
                    if (errors < 8) $display("G1_CAPTURE_MISMATCH cycle=%0d gv=%b gf=%b", cycle, gv, gf);
                    errors = errors + 1;
                end
            end
            if (bov && fov && rst_n) collisions = collisions + 1;
            if (!rst_n) resets = resets + 1;
        end
        if (errors) $fatal(1, "G1_CAPTURE FAIL errors=%0d checked=%0d", errors, checked);
        $display("G1_CAPTURE PASS checked=%0d collisions=%0d resets=%0d", checked, collisions, resets);
        $finish;
    end
endmodule
