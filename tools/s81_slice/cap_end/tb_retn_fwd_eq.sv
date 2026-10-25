`timescale 1ns/1ps
// S81/PORTFIX-DEAD D-CAPEND: ot_s81_retn_fwd (one-sided node) vs the full nodes with an idle b side, every edge.
//   r1: ot_s81_retn_static #(WIN 2, RST 1, DLR 1)   (cap_tr's na / nb / nc)     vs fwd #(2, 1)
//   r0: ot_s81sl_cap_rt_retn #(WIN 2, RST 0)        (cap_rt's n6)               vs fwd #(2, 0)
//   s1: ot_s81_retn_static #(WIN 2, RST 1)          (DLR 0, shift form)         vs fwd #(2, 1)
// o_v compared every edge; o_t / o_d / o_e when o_v; the full nodes' fault must stay 0.  +seed=N, +n=EDGES.
module tb_retn_fwd_eq;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg a_v; reg [31:0] a_t, a_d; reg a_e;
    wire fv1, fv0, fvs, gv1, gv0, gvs, fe1, fe0, fes, ge1, ge0, ges, f1, f0, fs;
    wire [31:0] ft1, ft0, fts, gt1, gt0, gts, fd1, fd0, fds, gd1, gd0, gds;
    ot_s81_retn_static #(.WIN(2), .RST(1), .DLR(1)) u_r1 (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e),
        .b_v(1'b0), .b_t(32'd0), .b_d(32'd0), .b_e(1'b0), .o_v(fv1), .o_t(ft1), .o_d(fd1), .o_e(fe1), .fault(f1));
    ot_s81sl_cap_rt_retn #(.WIN(2), .RST(0)) u_r0 (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e),
        .b_v(1'b0), .b_t(32'd0), .b_d(32'd0), .b_e(1'b0), .o_v(fv0), .o_t(ft0), .o_d(fd0), .o_e(fe0), .fault(f0));
    ot_s81_retn_static #(.WIN(2), .RST(1)) u_s1 (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e),
        .b_v(1'b0), .b_t(32'd0), .b_d(32'd0), .b_e(1'b0), .o_v(fvs), .o_t(fts), .o_d(fds), .o_e(fes), .fault(fs));
    ot_s81_retn_fwd #(.WIN(2), .RST(1)) u_g1 (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e),
        .o_v(gv1), .o_t(gt1), .o_d(gd1), .o_e(ge1));
    ot_s81_retn_fwd #(.WIN(2), .RST(0)) u_g0 (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e),
        .o_v(gv0), .o_t(gt0), .o_d(gd0), .o_e(ge0));
    integer seed, n, e, mism, words, outs, pv;
    task chk(input [8*3-1:0] nm, input fv, input gv, input [31:0] ft, gt, fd, gd, input fe, ge);
        begin
            if (fv !== gv || (fv && (ft !== gt || fd !== gd || fe !== ge))) begin
                mism = mism + 1;
                if (mism < 10) $display("MISMATCH %s edge %0d v %b/%b t %h/%h d %h/%h e %b/%b", nm, e, fv, gv, ft, gt, fd, gd, fe, ge);
            end
        end
    endtask
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("n=%d", n)) n = 200000;
        if (!$value$plusargs("pv=%d", pv)) pv = 40;
        mism = 0; words = 0; outs = 0;
        a_v = 0; a_t = 0; a_d = 0; a_e = 0;
        repeat (5) @(posedge clk);
        #0.5 rst_n = 1;
        for (e = 0; e < n; e = e + 1) begin
            @(negedge clk);
            a_v = ($urandom(seed) % 100) < pv; seed = seed + 1;
            a_t = $urandom; a_d = $urandom; a_e = ($urandom % 50) == 0;
            if (e % 50000 == 25000) begin rst_n = 0; #0.2 rst_n = 0; end   // mid-run reset pulses
            if (e % 50000 == 25003) rst_n = 1;
            if (a_v) words = words + 1;
            @(posedge clk); #0.1;
            chk("r1", fv1, gv1, ft1, gt1, fd1, gd1, fe1, ge1);
            chk("r0", fv0, gv0, ft0, gt0, fd0, gd0, fe0, ge0);
            chk("s1", fvs, gv1, fts, gt1, fds, gd1, fes, ge1);
            if (fv1) outs = outs + 1;
            if (f1 || f0 || fs) begin mism = mism + 1; if (mism < 10) $display("FULL NODE FAULT edge %0d", e); end
        end
        $display("RETN_FWD_EQ %s edges %0d a_words %0d out_words %0d mismatches %0d", mism == 0 && outs > 0 ? "PASS" : "FAIL", n, words, outs, mism);
        $finish;
    end
endmodule
