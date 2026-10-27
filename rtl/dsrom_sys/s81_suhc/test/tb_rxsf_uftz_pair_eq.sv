`timescale 1ns/1ps
// S81-CORES-R1 (2026-10-27): lockstep bench of the rxsf -> rxsb PAIR (the two hard cores dsfd_su_t_rxsf, now m_u2 UFTZ 1,
// and dsfd_su_t_rxsb, wired as in the parent: [30:0] u / u2, mx, f) against the shipped units ot_s81_su_rxsf
// #(.TFTZ(1), .UFTZ(0)) -> ot_s81_su_rxsb.  Every edge: o_v, o_f identical; o_r identical whenever o_v.  Stimulus: random
// valid gaps; x weighted on |x| in [32, 64) (u^2 subnormal band |x| ~ 43.7 .. 52), all binades, +-0, inf, NaN.
// Negative control +define+OT_RXSF_MUT_FTZ (every FTZ instance flushes |y| < 1: in the DUT also u^2) must FAIL.
module tb_rxsf_uftz_pair_eq;
    parameter integer NX = 400000;
    reg clk = 0, rst = 0; always #1 clk = ~clk;
    reg i_v = 0; reg [31:0] i_x = 0;
    wire rv, rf, sv, sf, bv, bf, nv, nf, mv, mf;
    wire [31:0] ru, ru2, rmx, rr, nmx; wire [30:0] nu, nu2, nr;
    ot_s81_su_rxsf #(.PCUT(1), .TFTZ(1), .UFTZ(0)) u_rf (.clk(clk), .rst_in(rst), .i_v(i_v), .i_x(i_x), .o_v(rv), .o_u(ru),
        .o_u2(ru2), .o_mx(rmx), .o_f(rf));
    ot_s81_su_rxsb #(.PCUT(1)) u_rb (.clk(clk), .rst_in(rst), .i_v(rv), .i_u({1'b0, ru[30:0]}), .i_u2({1'b0, ru2[30:0]}),
        .i_mx(rmx), .i_f(rf), .o_v(bv), .o_r(rr), .o_f(bf));
    dsfd_su_t_rxsf u_nf (.ck(clk), .rst(rst), .i_v(i_v), .i_x(i_x), .o_v(nv), .o_u(nu), .o_u2(nu2), .o_mx(nmx), .o_f(nf));
    dsfd_su_t_rxsb u_nb (.ck(clk), .rst(rst), .i_v(nv), .i_u(nu), .i_u2(nu2), .i_mx(nmx), .i_f(nf), .o_v(mv), .o_r(nr), .o_f(mf));
    integer cyc = 0, mism = 0, outs = 0, band = 0, u2diff = 0, n;
    always @(posedge clk) if (rst) begin
        cyc <= cyc + 1;
        if (rv && nv && ru2[30:0] !== nu2) u2diff = u2diff + 1;
        if (bv !== mv || bf !== mf || (bv && rr[30:0] !== nr)) begin
            mism = mism + 1; if (mism <= 8) $display("MISMATCH cyc=%0d ref v%b f%b r%h new v%b f%b r%h", cyc, bv, bf, rr, mv, mf, nr);
        end
        if (bv) outs = outs + 1;
    end
    function [31:0] rx; input integer d; reg [31:0] r; integer c; begin
        r = $urandom; c = $urandom % 16;
        case (c)
            0, 1, 2, 3, 4, 5, 6, 7: r[30:23] = 132;          // |x| in [32, 64): the u^2 subnormal band
            8:          r[30:0]  = ($urandom % 2) ? 31'd0 : {8'hFF, 23'd0};
            9:          r[30:23] = 8'hFF;
            10, 11:     r[30:23] = 125 + ($urandom % 10);
            default:    ;
        endcase
        rx = r; end endfunction
    initial begin
        repeat (4) @(negedge clk); rst = 1; repeat (4) @(negedge clk);
        for (n = 0; n < NX; n = n + 1) begin
            @(negedge clk); i_v = ($urandom % 8) != 0; i_x = rx(0);
            if (i_v && i_x[30:23] == 132 && i_x[22:0] >= 23'h2E0000 && i_x[22:0] < 23'h500000) band = band + 1;
        end
        @(negedge clk); i_v = 0; repeat (400) @(negedge clk);
        $display("RXSFPAIR inputs=%0d band=%0d outputs=%0d u2diff=%0d mismatches=%0d", NX, band, outs, u2diff, mism);
        if (mism != 0 || outs == 0 || band == 0 || u2diff == 0) $display("FAIL rxsf UFTZ pair lockstep");
        else $display("PASS rxsf UFTZ pair lockstep (o_v/o_f every edge, o_r on every valid output identical; u2 differs %0d)", u2diff);
        $finish;
    end
endmodule
