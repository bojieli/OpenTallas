`timescale 1ns/1ps
// S81-VPW-SLR lock-step bench: ot_s81sl_vpw XR 1 with SLR 0 (reference, the source form) against SLR 1, identical random
// inputs every cycle (legal and colliding writers alike, reset pulses included).  Contract: every output, same cycle.
// -DCTL_XR0: the second instance is XR 0 instead (one edge earlier), which this bench must report as FAIL.
module tb;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg sw_v, x_wv, hs_v; reg [1:0] cw_v; reg [9:0] sw_a, x_wa, hs_a; reg [7:0] sw_m, x_wm; reg [23:0] cw_a; reg [63:0] cw_d;
    reg [255:0] sw_d, xwd, hs_d;
    wire [1:0] wv_a, wv_b; wire [8:0] wa0_a, wa0_b, wa1_a, wa1_b; wire [127:0] wd0_a, wd0_b, wd1_a, wd1_b, wm0_a, wm0_b, wm1_a, wm1_b;
    wire wcol_a, wcol_b;
`define C(s) .clk(clk), .rst_n(rst_n), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), \
    .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .xwd(xwd), .hs_v(hs_v), .hs_a(hs_a), .hs_d(hs_d), .wv(wv``s), .wa0(wa0``s), .wa1(wa1``s), \
    .wd0(wd0``s), .wd1(wd1``s), .wm0(wm0``s), .wm1(wm1``s), .wcol(wcol``s)
    ot_s81sl_vpw #(.XR(1), .SLR(0)) u_a (`C(_a));
`ifdef CTL_XR0
    ot_s81sl_vpw #(.XR(0)) u_b (`C(_b));
`else
    ot_s81sl_vpw #(.XR(1), .SLR(1)) u_b (`C(_b));
`endif
    wire [2+18+512+1-1:0] oa = {wv_a, wa0_a, wa1_a, wd0_a, wd1_a, wm0_a, wm1_a, wcol_a}, ob = {wv_b, wa0_b, wa1_b, wd0_b, wd1_b, wm0_b, wm1_b, wcol_b};
    integer cyc = 0, errs = 0, checks = 0, nw = 0, ncol = 0, nd = 0, mode;
    function automatic [255:0] r256(input integer dummy); r256 = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom}; endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        rst_n <= !(cyc < 6 || (cyc % 9973) < 3);
        mode = (cyc / 5000) % 3;                       // 0: sparse single writers, 1: mixed, 2: dense / colliding
        sw_v <= (mode == 2) ? $urandom : (($urandom % (mode ? 3 : 6)) == 0);
        x_wv <= (mode == 2) ? $urandom : (($urandom % (mode ? 4 : 9)) == 0);
        hs_v <= (mode == 2) ? (($urandom % 4) == 0) : (($urandom % (mode ? 7 : 13)) == 0);
        cw_v <= (mode == 0) ? ((($urandom % 5) == 0) ? (2'b01 << ($urandom % 2)) : 2'b00) : $urandom;
        sw_a <= $urandom; x_wa <= $urandom; hs_a <= $urandom; sw_m <= (($urandom % 8) == 0) ? 8'h00 : $urandom; x_wm <= $urandom;
        cw_a <= $urandom; cw_d <= {$urandom, $urandom}; sw_d <= r256(0); xwd <= r256(0); hs_d <= r256(0);
        if (cyc > 8) begin
            checks <= checks + 1;
            if (ob !== oa) begin errs <= errs + 1; if (errs < 6) $display("MISMATCH cyc %0d diff bits %0d (wv %b/%b wcol %b/%b)", cyc, $countones(ob ^ oa), wv_b, wv_a, wcol_b, wcol_a); end
            if (|wv_a) nw <= nw + 1; if (wcol_a) ncol <= ncol + 1; if (|wd0_a || |wd1_a) nd <= nd + 1;
        end
        if (cyc == `NCYC) begin
            $display("VPW_SLR_RESULT %s checks %0d errors %0d | write cycles %0d, with data %0d, collisions %0d", (errs == 0) ? "PASS" : "FAIL", checks, errs, nw, nd, ncol);
            $finish;
        end
    end
endmodule
