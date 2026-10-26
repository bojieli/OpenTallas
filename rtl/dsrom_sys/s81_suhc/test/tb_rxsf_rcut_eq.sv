`timescale 1ns/1ps
// CORES-KITS/S81-RXSF (2026-10-26): lockstep bench of the dsfd_su_t_rxsf hard core with U2RC 1 (m_u2 last stage split,
// o_u2 face register retimed onto the round / pack logic, 0 cycles) against the UNMODIFIED core of the reference
// revision (dsfd_su_t_rxsf__ref: the ref revision's ot_s81_su_rxh.sv / ot_hdc_v41x_spshort.sv with every module renamed
// *__ref by tools/s81_slice/rxsf_rcut_eq.sh).  The full RA lane is checked too: new rxsf -> new rxsb (m_l = mul_x2 RCUT 0,
// the refactored default path) against ref rxsf -> ref rxsb.  Every edge: o_v, o_f of both leaves identical; every data
// output of rxsf (o_u, o_u2, o_mx) identical on every edge outside the reset window (rst low and the 4 edges after it:
// the old o_u2 <= y delay register showed the reset y = 0, the new o_u2 the stage-3 data; o_v = 0 there); rxsb o_r on
// every valid edge and on every edge once its pipeline has flushed the reset-window data (256 edges after reset).  Stimulus: random valid gaps
// and back-to-back runs, x from all binades with weight on the large |x| (u = t / (t + 2) tiny -> u^2 subnormal / zero),
// the tiny ones, the rint edge, +-0, clamps, inf / NaN; 3 mid-run resets.  Negative control +define+OT_RXSF_MUT_RCUT
// (candidate only: the round bit bypasses the new stage register) must FAIL.
module tb_rxsf_rcut_eq;
    parameter integer NX = 300000;
    reg clk = 0, rst = 0; always #1 clk = ~clk;
    reg i_v = 0; reg [31:0] i_x = 0;
    wire rv, rf, nv, nf; wire [30:0] ru, ru2, nu, nu2; wire [31:0] rmx, nmx;
    wire bv, bf, cv, cf; wire [30:0] br, cr;
    dsfd_su_t_rxsf__ref u_ref (.ck(clk), .rst(rst), .i_v(i_v), .i_x(i_x), .o_v(rv), .o_u(ru), .o_u2(ru2), .o_mx(rmx), .o_f(rf));
    dsfd_su_t_rxsf      u_new (.ck(clk), .rst(rst), .i_v(i_v), .i_x(i_x), .o_v(nv), .o_u(nu), .o_u2(nu2), .o_mx(nmx), .o_f(nf));
    dsfd_su_t_rxsb__ref b_ref (.ck(clk), .rst(rst), .i_v(rv), .i_u(ru), .i_u2(ru2), .i_mx(rmx), .i_f(rf), .o_v(bv), .o_r(br), .o_f(bf));
    dsfd_su_t_rxsb      b_new (.ck(clk), .rst(rst), .i_v(nv), .i_u(nu), .i_u2(nu2), .i_mx(nmx), .i_f(nf), .o_v(cv), .o_r(cr), .o_f(cf));
    integer cyc = 0, mism = 0, outs = 0, bouts = 0, sub2 = 0, zero2 = 0, faults = 0, armed = 0, n, resets = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        armed = rst ? armed + 1 : 0;
        if (rv !== nv || rf !== nf || bv !== cv || bf !== cf ||
            (armed > 4 && (ru !== nu || ru2 !== nu2 || rmx !== nmx)) || ((bv || armed > 256) && br !== cr)) begin
            mism = mism + 1;
            if (mism <= 8) $display("MISMATCH cyc=%0d armed=%0d ref v%b f%b u%h u2%h mx%h r%h bv%b bf%b | new v%b f%b u%h u2%h mx%h r%h bv%b bf%b",
                cyc, armed, rv, rf, ru, ru2, rmx, br, bv, bf, nv, nf, nu, nu2, nmx, cr, cv, cf);
        end
        if (rv) begin outs = outs + 1; if (ru2[30:23] == 8'd0 && ru2[22:0] != 0) sub2 = sub2 + 1; if (ru2 == 0) zero2 = zero2 + 1; end
        if (bv) bouts = bouts + 1;
        if (rf || bf) faults = faults + 1;
    end
    function [31:0] rx; input integer d; reg [31:0] r; integer c; begin
        r = $urandom; c = $urandom % 16;
        case (c)
            0, 1:       r[30:23] = $urandom % 3;            // subnormal / min-normal x
            2:          r[30:23] = 3 + ($urandom % 30);     // tiny normal x
            3, 4:       r[30:23] = 125 + ($urandom % 3);    // |t| ~ 0.36 .. 2.9
            5, 6, 7:    r[30:23] = 131 + ($urandom % 3);    // |x| 16 .. 128: t down to 2^-180, u^2 subnormal / zero
            8:          r[30:0]  = ($urandom % 2) ? 31'd0 : {8'hFF, 23'd0};   // +-0, +-inf
            9:          r[30:23] = 8'hFF;                   // NaN / inf
            10:         r[30:23] = 130 + ($urandom % 6);    // near the clamps
            11:         r[30:23] = 128 + ($urandom % 4);    // |x| 2 .. 32
            default:    ;                                   // any binade
        endcase
        rx = r; end endfunction
    initial begin
        repeat (4) @(negedge clk); rst = 1; repeat (4) @(negedge clk);
        for (n = 0; n < NX; n = n + 1) begin
            @(negedge clk);
            if (n % 100000 == 77777) begin rst = 0; resets = resets + 1; end else rst = 1;
            i_v = (n % 4096 < 512) ? 1'b1 : (($urandom % 8) != 0); i_x = rx(0);
        end
        @(negedge clk); i_v = 0; repeat (400) @(negedge clk);
        $display("RXSFRCUT inputs=%0d rxsf_outputs=%0d rxsb_outputs=%0d u2_subnormal=%0d u2_zero=%0d faults=%0d resets=%0d mismatches=%0d",
                 NX, outs, bouts, sub2, zero2, faults, resets, mism);
        if (mism != 0 || outs == 0 || bouts == 0 || sub2 == 0) $display("FAIL rxsf U2RC lockstep");
        else $display("PASS rxsf U2RC lockstep (o_v/o_f every edge, all data outputs every edge outside reset, rxsf + rxsb lane)");
        $finish;
    end
endmodule
