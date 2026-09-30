`timescale 1ns/1ps
// Equivalence bench: ot_fp32_add_rne_deep (every SPLIT) against the qualified ot_fp32_add_rne_pipe, on random
// operands biased to every class (zeros, subnormals, near-equal magnitudes, cancellation, overflow, nonfinite)
// with random valid gaps.  Compares y, err and valid after aligning the deep pipe's extra latency.
module tb_fp32_add_deep_equiv;
    parameter integer SPLIT = 7, N = 400000;
    localparam integer EXTRA = (SPLIT & 1) + ((SPLIT >> 1) & 1) + ((SPLIT >> 2) & 1);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg v; reg [31:0] a, b; reg [3:0] r4;
    wire [31:0] y0, y1; wire [1:0] e0, e1; wire v0, v1;
    ot_fp32_add_rne_pipe ref_u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y0), .err(e0), .valid_out(v0));
    ot_fp32_add_rne_deep #(.SPLIT(SPLIT)) dut (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y1), .err(e1), .valid_out(v1));
    reg [34:0] hist [0:15];
    integer i, bad = 0, checked = 0, seed = 1;
    function [31:0] rnd(input integer s);
        reg [31:0] r; integer c;
        begin
            r = $urandom(seed); c = $urandom(seed) % 10;
            case (c)
                0: r[30:0] = 31'd0;
                1: r[30:23] = 8'd0;
                2: r[30:23] = 8'hff;
                3: r[30:23] = 8'hfe;
                4: r[30:23] = 8'd1;
                default: ;
            endcase
            rnd = r;
        end
    endfunction
    always @(posedge clk) begin
        // keep the reference's outputs EXTRA cycles to align with the deep pipe
        for (i = 15; i > 0; i = i - 1) hist[i] <= hist[i-1];
        hist[0] <= {v0, e0, y0};
        if (rst_n && $time > 30 && checked < N) begin
            if (v1 !== (EXTRA == 0 ? v0 : hist[EXTRA-1][34])) begin bad = bad + 1; $display("VALID mismatch t=%0t v1=%b", $time, v1); end
            else if (v1) begin
                checked = checked + 1;
                if ({e1, y1} !== (EXTRA == 0 ? {e0, y0} : hist[EXTRA-1][33:0])) begin
                    bad = bad + 1;
                    if (bad < 5) $display("MISMATCH y=%h e=%d ref=%h", y1, e1, hist[EXTRA-1][31:0]);
                end
            end
        end
    end
    initial begin
        v = 0; a = 0; b = 0;
        for (i = 0; i < 16; i = i + 1) hist[i] = 0;
        repeat (3) @(posedge clk);
        rst_n = 1;
        while (checked < N) begin
            @(negedge clk);
            v = ($urandom(seed) % 8) != 0;
            a = rnd(0);
            r4 = $urandom(seed);
            b = ($urandom(seed) % 3 == 0) ? {~a[31], a[30:4], r4} : rnd(0);
        end
        $display("EQUIV split=%0d extra=%0d checked=%0d bad=%0d", SPLIT, EXTRA, checked, bad);
        $finish;
    end
endmodule
