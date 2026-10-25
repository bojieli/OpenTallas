`timescale 1ns/1ps
// S81-CORES2/RV (2026-10-25): lockstep bench of the dsfd_su_t_rxsf hard core (u_exp TFTZ 1: m_t flushes t's subnormal
// results to +0) against ot_s81_su_rxsf #(.TFTZ(0)) (the unchanged unit).  Every edge: o_v, o_f identical; o_u, o_u2,
// o_mx identical whenever o_v.  Stimulus: random valid gaps, x drawn from all binades with heavy weight on the tiny
// ones (|x| < 2^-120: t = x log2e subnormal or rounding to 2^-126), the |t| ~ 0.5 .. 1 rint edge, +-0, the clamps,
// infinities and NaNs.  Negative control +define+OT_RXSF_MUT_FTZ (flush every |t| < 1: n = rint(t) changes) must FAIL.
module tb_rxsf_ftz_eq;
    parameter integer NX = 200000;
    reg clk = 0, rst = 0; always #1 clk = ~clk;
    reg i_v = 0; reg [31:0] i_x = 0;
    wire rv, rf, nv, nf; wire [31:0] ru, ru2, rmx; wire [30:0] nu, nu2; wire [31:0] nmx;
    ot_s81_su_rxsf #(.PCUT(1), .TFTZ(0)) u_ref (.clk(clk), .rst_in(rst), .i_v(i_v), .i_x(i_x), .o_v(rv), .o_u(ru), .o_u2(ru2),
        .o_mx(rmx), .o_f(rf));
    dsfd_su_t_rxsf u_new (.ck(clk), .rst(rst), .i_v(i_v), .i_x(i_x), .o_v(nv), .o_u(nu), .o_u2(nu2), .o_mx(nmx), .o_f(nf));
    integer cyc = 0, mism = 0, outs = 0, tiny = 0, faults = 0, n;
    always @(posedge clk) if (rst) begin
        cyc <= cyc + 1;
        if (rv !== nv || rf !== nf || (rv && (ru[30:0] !== nu || ru2[30:0] !== nu2 || rmx !== nmx || ru[31] !== 1'b0 || ru2[31] !== 1'b0))) begin
            mism = mism + 1; if (mism <= 8) $display("MISMATCH cyc=%0d ref v%b f%b u%h u2%h mx%h new v%b f%b u%h u2%h mx%h", cyc, rv, rf, ru, ru2, rmx, nv, nf, nu, nu2, nmx);
        end
        if (rv) outs = outs + 1; if (rf) faults = faults + 1;
    end
    function [31:0] rx; input integer d; reg [31:0] r; integer c; begin
        r = $urandom; c = $urandom % 16;
        case (c)
            0, 1, 2, 3: r[30:23] = $urandom % 3;            // subnormal / min-normal x: t subnormal or 2^-126
            4, 5:       r[30:23] = 3 + ($urandom % 30);     // tiny normal x
            6, 7:       r[30:23] = 125 + ($urandom % 3);    // |t| ~ 0.36 .. 2.9: the rint(t) 0/1 edge
            8:          r[30:0]  = ($urandom % 2) ? 31'd0 : {8'hFF, 23'd0};   // +-0, +-inf
            9:          r[30:23] = 8'hFF;                   // NaN / inf
            10:         r[30:23] = 130 + ($urandom % 6);    // near the clamps
            default:    ;                                   // any binade
        endcase
        rx = r; end endfunction
    initial begin
        repeat (4) @(negedge clk); rst = 1; repeat (4) @(negedge clk);
        for (n = 0; n < NX; n = n + 1) begin
            @(negedge clk); i_v = ($urandom % 8) != 0; i_x = rx(0);
            if (i_v && i_x[30:23] < 3) tiny = tiny + 1;
        end
        @(negedge clk); i_v = 0; repeat (200) @(negedge clk);
        $display("RXSFEQ inputs=%0d tiny=%0d outputs=%0d faults=%0d mismatches=%0d", NX, tiny, outs, faults, mism);
        if (mism != 0 || outs == 0 || tiny == 0) $display("FAIL rxsf TFTZ lockstep");
        else $display("PASS rxsf TFTZ lockstep (o_v/o_f every edge, o_u/o_u2/o_mx on every valid output identical)");
        $finish;
    end
endmodule
