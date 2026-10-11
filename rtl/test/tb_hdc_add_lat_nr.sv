`timescale 1ns/1ps
// tb_hdc_add_lat_nr (hardcore-1010 D, 2026-10-10): ot_hdc_fp32_add_lat_nr #(LAT) against ot_hdc_fp32_add_lat #(LAT)
// (the qualified adder) at transaction level: the same random operand stream (normals, subnormals, zeros of both
// signs, inf / NaN, near-cancellation pairs) with random valid gaps; every valid result (y, err) and the valid
// sequence must match.  Reset is applied mid-run too (in-flight operations are dropped by both).  HMUT = 1 must FAIL.
module tb_hdc_add_lat_nr;
    parameter integer LAT = 7, HMUT = 0, N = 200000, SEED = 1;
    reg clk = 0, rst_n = 0, v = 0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] y0, y1; wire [1:0] e0, e1; wire v0, v1;
    ot_hdc_fp32_add_lat    #(.LAT(LAT))              u_ref (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y0), .err(e0), .valid_out(v0));
    ot_hdc_fp32_add_lat_nr #(.LAT(LAT), .HMUT(HMUT)) u_dut (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y1), .err(e1), .valid_out(v1));
    always #0.5 clk = ~clk;
    integer i, bad = 0, nv = 0, seed = SEED;
    initial begin seed = SEED; $display("SEED=%0d", seed); end  // runtime seed: Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
    function [31:0] rnd_fp(input integer k);
        reg [31:0] r;
        begin
            r = $random(seed);
            case (k % 8)
                0: rnd_fp = {r[31], 8'd0, r[22:0]};                       // subnormal
                1: rnd_fp = {r[31], 31'd0};                                // +-0
                2: rnd_fp = {r[31], 8'hff, (r[3] ? r[22:0] : 23'd0)};      // inf / NaN
                default: rnd_fp = {r[31], 8'd100 + r[30:26], r[22:0]};    // normals, close exponents
            endcase
        end
    endfunction
    initial begin
        repeat (4) @(posedge clk);
        rst_n <= 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            if (i == N / 2) rst_n = 0; else rst_n = 1;
            v = ($random(seed) & 3) != 0;
            a = rnd_fp($random(seed) & 255);
            if (($random(seed) & 3) == 0) b = {~a[31], a[30:0]} ^ ($random(seed) & 32'h7);   // near cancellation
            else b = rnd_fp($random(seed) & 255);
        end
        v = 0; repeat (LAT + 4) @(posedge clk);
        if (bad == 0 && nv > N / 2) $display("PASS add_lat_nr LAT=%0d results=%0d", LAT, nv);
        else $display("FAIL add_lat_nr LAT=%0d mismatches=%0d results=%0d", LAT, bad, nv);
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        if (v0 !== v1 || (v0 && (y0 !== y1 || e0 !== e1))) begin
            bad = bad + 1;
            if (bad <= 5) $display("MISMATCH t=%0t v %b/%b y %h/%h err %0d/%0d", $time, v0, v1, y0, y1, e0, e1);
        end
        if (v0) nv = nv + 1;
    end
endmodule
