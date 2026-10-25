`timescale 1ns/1ps
// S81-CORES2/SW 10-25 lockstep bench: ot_s81sl_vsw LR = 1 (lane-input register stage) against LR = 0 (the previous
// design).  Same random stimulus (groups at random spacing 1..9 edges incl. overruns, random FP32 data / weight / limit,
// one mid-run reset); PASS = every output of LR = 1 at edge t equals LR = 0 at edge t - 1 (o_v, o_d, o_f, X-exact), and the
// negative control (no shift) must mismatch.
module tb_s81sl_vsw_lr_eq;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg i_v = 0; reg [255:0] i_d = 0; reg [31:0] i_w = 0, i_lim = 0;
    wire o_v0, o_f0, o_v1, o_f1; wire [63:0] o_d0, o_d1;
    ot_s81sl_vsw #(.LR(0)) u_ref (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_w(i_w), .i_lim(i_lim), .o_v(o_v0), .o_d(o_d0), .o_f(o_f0));
    ot_s81sl_vsw #(.LR(1)) u_new (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_w(i_w), .i_lim(i_lim), .o_v(o_v1), .o_d(o_d1), .o_f(o_f1));
    reg o_v0d, o_f0d; reg [63:0] o_d0d;
    integer cyc = 0, mis = 0, mis0 = 0, nov = 0, nf = 0, gap = 0, k;
    integer seed = 12345;
    function [31:0] rfp(input integer dummy);
        reg [31:0] r; begin r = $random(seed); r[30:23] = 8'd112 + ($random(seed) & 8'd31); rfp = r; end
    endfunction
    always @(posedge clk) begin
        o_v0d <= o_v0; o_f0d <= o_f0; o_d0d <= o_d0;
        cyc <= cyc + 1;
        if (cyc > 3) begin
            if ({o_v1, o_f1, o_d1} !== {o_v0d, o_f0d, o_d0d}) begin
                mis = mis + 1;
                if (mis < 6) $display("MISMATCH cyc %0d new v%b f%b d%h ref(t-1) v%b f%b d%h", cyc, o_v1, o_f1, o_d1, o_v0d, o_f0d, o_d0d);
            end
            if ({o_v1, o_f1, o_d1} !== {o_v0, o_f0, o_d0}) mis0 = mis0 + 1;
            if (o_v0) nov = nov + 1;
            if (o_f0) nf = nf + 1;
        end
    end
    initial begin
        if ($value$plusargs("seed=%d", seed)) ;
        repeat (6) @(negedge clk); rst_n = 1;
        for (k = 0; k < 40000; k = k + 1) begin
            @(negedge clk);
            if (k == 20000) begin rst_n = 0; repeat (5) @(negedge clk); rst_n = 1; end
            if (gap == 0) begin
                i_v = 1; i_d = {rfp(0), rfp(0), rfp(0), rfp(0), rfp(0), rfp(0), rfp(0), rfp(0)}; i_w = rfp(0); i_lim = rfp(0);
                gap = (($random(seed) & 15) == 0) ? 1 + ($random(seed) & 1) : 4 + ($random(seed) & 3);
            end else begin
                i_v = 0; i_d = {8{$random(seed)}}; i_w = $random(seed); i_lim = $random(seed);
            end
            gap = gap - 1;
        end
        repeat (300) @(negedge clk);
        $display("VSW_LR_EQ cycles %0d o_v(ref) %0d o_f(ref) cycles %0d mismatches(shift 1) %0d negative-control mismatches(shift 0) %0d", cyc, nov, nf, mis, mis0);
        if (mis == 0 && mis0 > 0 && nov > 1000 && nf > 0) $display("VSW_LR_EQ PASS"); else $display("VSW_LR_EQ FAIL");
        $finish;
    end
endmodule
