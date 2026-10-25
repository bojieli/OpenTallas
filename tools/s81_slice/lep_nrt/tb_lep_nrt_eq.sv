`timescale 1ns/1ps
// S81/PORTFIX-DEAD D-MURT: ot_s81sl_lep_mu_a_nrt (no MU tag return, RT_EN 0) vs ot_s81sl_lep_mu_a at the TP-end leps' parameters
// (CRED 12, DR 12, RX_SRAM 1, IN_PIPE 1, NATIVE32 1).  Same random stimulus; every output except mu_rt compared every edge.
// +seed=N +n=EDGES +pv=valid-percent
module tb_lep_nrt_eq;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg [1103:0] ro; reg lo0_r, lo1_r, li0_v, li1_v; reg [552:0] li0_d, li1_d; reg [33:0] mu_c; reg ml_rv; reg [1103:0] ml_rd;
    wire [1103:0] ri_a, ri_b, wd_a, wd_b; wire [552:0] lo0d_a, lo0d_b, lo1d_a, lo1d_b; wire [1:0] rxv_a, rxv_b;
    wire lo0v_a, lo0v_b, lo1v_a, lo1v_b, li0r_a, li0r_b, li1r_a, li1r_b, wv_a, wv_b, f_a, f_b; wire [31:0] mu_rt;
    ot_s81sl_lep_mu_a #(.CRED(12), .DR(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_a (.clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri_a),
        .lo0_v(lo0v_a), .lo0_r(lo0_r), .lo0_d(lo0d_a), .lo1_v(lo1v_a), .lo1_r(lo1_r), .lo1_d(lo1d_a),
        .li0_v(li0_v), .li0_r(li0r_a), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1r_a), .li1_d(li1_d), .rxv(rxv_a),
        .sl_f(1'b0), .l0_f(3'd0), .l1_f(3'd0), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(wv_a), .ml_wd(wd_a), .ml_rv(ml_rv), .ml_rd(ml_rd),
        .ml_f(1'b0), .fault(f_a));
    ot_s81sl_lep_mu_a_nrt #(.CRED(12), .DR(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_b (.clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri_b),
        .lo0_v(lo0v_b), .lo0_r(lo0_r), .lo0_d(lo0d_b), .lo1_v(lo1v_b), .lo1_r(lo1_r), .lo1_d(lo1d_b),
        .li0_v(li0_v), .li0_r(li0r_b), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1r_b), .li1_d(li1_d), .rxv(rxv_b),
        .sl_f(1'b0), .l0_f(3'd0), .l1_f(3'd0), .mu_c(mu_c), .ml_wv(wv_b), .ml_wd(wd_b), .ml_rv(ml_rv), .ml_rd(ml_rd),
        .ml_f(1'b0), .fault(f_b));
    integer seed, n, pv, e, k, mism = 0, act = 0, rtn = 0;
    function automatic [1103:0] rnd1104(); integer q; begin for (q = 0; q < 1104; q = q + 32) rnd1104[q +: 32] = $urandom; end endfunction
    function automatic [552:0] rnd553(); integer q; begin for (q = 0; q < 553; q = q + 32) rnd553[q +: 32] = $urandom; end endfunction
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("n=%d", n)) n = 20000;
        if (!$value$plusargs("pv=%d", pv)) pv = 30;
        void'($urandom(seed));
        ro = 0; lo0_r = 1; lo1_r = 1; li0_v = 0; li1_v = 0; li0_d = 0; li1_d = 0; mu_c = 0; ml_rv = 0; ml_rd = 0;
        repeat (8) @(posedge clk); #0.3 rst_n = 1;
        for (e = 0; e < n; e = e + 1) begin
            @(negedge clk);
            ro = ($urandom % 100 < pv) ? rnd1104() : 1104'd0;
            li0_v = $urandom % 100 < pv; li0_d = rnd553(); li1_v = $urandom % 100 < pv; li1_d = rnd553();
            lo0_r = $urandom % 100 < 80; lo1_r = $urandom % 100 < 80;
            mu_c = ($urandom % 100 < 5) ? {$urandom, 2'b11} : 34'd0;
            ml_rv = $urandom % 100 < pv; ml_rd = rnd1104();
            @(posedge clk); #0.1;
            if (lo0v_a || lo1v_a || wv_a || |ri_a) act = act + 1;
            if (mu_rt[31]) rtn = rtn + 1;
            if (ri_a !== ri_b || lo0v_a !== lo0v_b || lo1v_a !== lo1v_b || (lo0v_a && lo0d_a !== lo0d_b) || (lo1v_a && lo1d_a !== lo1d_b)
                || li0r_a !== li0r_b || li1r_a !== li1r_b || rxv_a !== rxv_b || wv_a !== wv_b || (wv_a && wd_a !== wd_b) || f_a !== f_b) begin
                mism = mism + 1;
                if (mism < 8) $display("MISMATCH edge %0d ri %0d lo %b%b/%b%b wv %b/%b f %b/%b", e, ri_a !== ri_b, lo0v_a, lo1v_a, lo0v_b, lo1v_b, wv_a, wv_b, f_a, f_b);
            end
        end
        $display("LEP_NRT_EQ %s seed %0d edges %0d active_edges %0d mu_rt_words(ref) %0d fault %b/%b mismatches %0d",
                 (mism == 0 && act > 0) ? "PASS" : "FAIL", seed, n, act, rtn, f_a, f_b, mism);
        $finish;
    end
endmodule
