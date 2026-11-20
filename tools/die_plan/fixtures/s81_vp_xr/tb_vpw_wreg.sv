`timescale 1ns/1ps
// S81-VPW-WREG lock-step bench: ot_s81sl_vpw XR 1 WREG 0 (reference, explicit) against XR 1 with WREG left at its default,
// which the bare-name define OT_S81SL_VP_WREG sets.  Identical random inputs every cycle (legal and colliding writers alike,
// reset pulses included).  Contract: b(t) == a(t - SHIFT) on every output, SHIFT = 1 with the define, 0 without it.
// The first 3 cycles after any reset cycle are not compared (the reference's last pre-reset output vs the reset stage).
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
    ot_s81sl_vpw #(.XR(1), .WREG(0)) u_a (`C(_a));
    ot_s81sl_vpw #(.XR(1)) u_b (`C(_b));
    localparam integer OW = 2 + 18 + 512 + 1;
    wire [OW-1:0] oa = {wv_a, wa0_a, wa1_a, wd0_a, wd1_a, wm0_a, wm1_a, wcol_a}, ob = {wv_b, wa0_b, wa1_b, wd0_b, wd1_b, wm0_b, wm1_b, wcol_b};
    reg [OW-1:0] oa_q;
    wire [OW-1:0] oref = (`SHIFT == 0) ? oa : oa_q;
    integer cyc = 0, errs = 0, checks = 0, nw = 0, ncol = 0, nd = 0, nx = 0, last_rst = 0, mode;
    function automatic [255:0] r256(input integer dummy); r256 = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom}; endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        oa_q <= oa;
        rst_n <= !(cyc < 6 || (cyc % 9973) < 3);
        if (!rst_n) last_rst <= cyc;
        mode = (cyc / 5000) % 3;                       // 0: sparse single writers, 1: mixed, 2: dense / colliding
        sw_v <= (mode == 2) ? $urandom : (($urandom % (mode ? 3 : 6)) == 0);
        x_wv <= (mode == 2) ? $urandom : (($urandom % (mode ? 4 : 9)) == 0);
        hs_v <= (mode == 2) ? (($urandom % 4) == 0) : (($urandom % (mode ? 7 : 13)) == 0);
        cw_v <= (mode == 0) ? ((($urandom % 5) == 0) ? (2'b01 << ($urandom % 2)) : 2'b00) : $urandom;
        sw_a <= $urandom; x_wa <= $urandom; hs_a <= $urandom; sw_m <= (($urandom % 8) == 0) ? 8'h00 : $urandom; x_wm <= $urandom;
        cw_a <= $urandom; cw_d <= {$urandom, $urandom}; sw_d <= r256(0); xwd <= r256(0); hs_d <= r256(0);
        if (cyc > 8 && rst_n && cyc - last_rst > 3) begin
            checks <= checks + 1;
            if (ob !== oref) begin errs <= errs + 1; if (errs < 6) $display("MISMATCH cyc %0d diff bits %0d (wv %b/%b wcol %b/%b)", cyc, $countones(ob ^ oref), wv_b, oref[OW-1 -: 2], wcol_b, oref[0]); end
            if (|wv_b) nw <= nw + 1; if (wcol_b) ncol <= ncol + 1; if (|wd0_b || |wd1_b) nd <= nd + 1;
            if (|u_b.xl_q[0] || |u_b.xh_q[0] || |u_b.xl_q[1] || |u_b.xh_q[1]) nx <= nx + 1;
        end
        if (cyc == `NCYC) begin
            $display("VPW_WREG_RESULT %s shift %0d wreg %0d checks %0d errors %0d | write cycles %0d, with data %0d, x-data %0d, collisions %0d",
                     (errs == 0) ? "PASS" : "FAIL", `SHIFT, u_b.WREG, checks, errs, nw, nd, nx, ncol);
            $finish;
        end
    end
endmodule
