`timescale 1ns/1ps
// S81-RF1 (DIE-S81-51/RF-B 11-03): lockstep bench ot_s81sl_cap_rt RF1=0 (pre-RF1 logic) vs RF1=1 (group-local key
// compare + 3 clock entry pins tied to one clock).  Same random stimulus on both; every output compared every edge,
// plus the registered lookups fa_kh / fb_kh (sampled in the low phase, after the RF1 out-face latch opens).  Stimulus tags come from a small domain so slots and keys collide.
// Run with -DOT_S81_CAP_RT_RF1 -DOT_S81_CAP_RT_FACE_REGS.  PASS = 0 mismatches and nonzero key-hit coverage.
// S81-RF2 (DIE-S81-51/RF-D 11-03): -GRA / -GRB pick the two RF1 forms (default 0 / 1; RF2 record 1 / 2); the registered
// lookups fa_ev / fb_ev / fa_es / fb_es are compared too.  Mutants OT_RFD_MUT_CAP2 / OT_RFD_MUT_CAP2B must FAIL.
module tb_ot_s81sl_cap_rt_rf1;
    parameter integer RA = 0, RB = 1;
    parameter integer N = 200000;
    parameter integer SEED = 1;
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg w_v, w_e, w_f, e_v, e_e, e_f, cfg_v;
    reg [31:0] w_t, w_d, e_t, e_d;
    reg [159:0] cfg_d;
    wire [5:0] s_v0, s_v1; wire [71:0] s_a0, s_a1; wire [191:0] s_d0, s_d1;
    wire [3:0] n_v0, n_v1; wire [47:0] n_a0, n_a1; wire [127:0] n_d0, n_d1; wire f0, f1;
    ot_s81sl_cap_rt #(.RF1(RA)) u0 (.clk(clk), .clk_g0(clk), .clk_g1(clk), .rst_n(rst_n),
        .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f), .e_v(e_v), .e_t(e_t), .e_d(e_d), .e_e(e_e), .e_f(e_f),
        .cfg_v(cfg_v), .cfg_d(cfg_d), .cw_s_v(s_v0), .cw_s_a(s_a0), .cw_s_d(s_d0), .cw_n_v(n_v0), .cw_n_a(n_a0),
        .cw_n_d(n_d0), .fault(f0));
    ot_s81sl_cap_rt #(.RF1(RB)) u1 (.clk(clk), .clk_g0(clk), .clk_g1(clk), .rst_n(rst_n),
        .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f), .e_v(e_v), .e_t(e_t), .e_d(e_d), .e_e(e_e), .e_f(e_f),
        .cfg_v(cfg_v), .cfg_d(cfg_d), .cw_s_v(s_v1), .cw_s_a(s_a1), .cw_s_d(s_d1), .cw_n_v(n_v1), .cw_n_a(n_a1),
        .cw_n_d(n_d1), .fault(f1));
    integer seed, cyc, mism, kh_hits, ins, mrg, outs, phase;
    function [31:0] tag(input integer r);
        reg [2:0] pos; reg [15:0] row; reg [4:0] lo, n; reg [2:0] k;
        begin
            pos = r[1:0]; row = {14'd0, r[3:2]}; k = r[6:4] % 5; n = 5'd1 + r[11:7] % 31;
            lo = r[16:12] & ~((5'd1 << k) - 5'd1);
            tag = {pos, row, lo, k, n};
        end
    endfunction
    task drive; integer r;
        begin
            r = $random(seed);
            w_v = r[0] & r[1]; e_v = r[2] & r[3];
            w_t = tag($random(seed)); e_t = tag($random(seed));
            w_d = $random(seed); e_d = $random(seed);
            w_e = (r[15:8] == 0); e_e = (r[23:16] == 0); w_f = 0; e_f = 0;
            cfg_v = (cyc % 4096) == 37;
            cfg_d = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            cfg_d[28:27] = 2'd1; cfg_d[26:24] = 3'd3; cfg_d[44:29] = 16'd0; cfg_d[55:45] = 11'd4;
        end
    endtask
    initial begin
        seed = SEED; mism = 0; kh_hits = 0; ins = 0; mrg = 0; outs = 0;
        w_v = 0; e_v = 0; w_t = 0; e_t = 0; w_d = 0; e_d = 0; w_e = 0; e_e = 0; w_f = 0; e_f = 0; cfg_v = 0; cfg_d = 0;
        cyc = 0;
        repeat (8) @(negedge clk);
        rst_n = 1;
        for (cyc = 0; cyc < N; cyc = cyc + 1) begin
            @(negedge clk); #0.1;   // compare in the low phase: the RF1 out-face latch is transparent then
            // periodic re-reset so the sticky fault does not freeze the comparison at a constant
            if ((cyc % 20000) == 19990) rst_n = 0; else if ((cyc % 20000) == 19999) rst_n = 1;
            drive;
            if ({s_v0, s_a0, s_d0, n_v0, n_a0, n_d0, f0} !== {s_v1, s_a1, s_d1, n_v1, n_a1, n_d1, f1}
                || u0.fa_kh !== u1.fa_kh || u0.fb_kh !== u1.fb_kh
                || {u0.fa_ev, u0.fb_ev, u0.fa_es, u0.fb_es, u0.fa_cn, u0.fb_cn} !== {u1.fa_ev, u1.fb_ev, u1.fa_es, u1.fb_es, u1.fa_cn, u1.fb_cn}) begin
                mism = mism + 1;
                if (mism < 6) $display("MISMATCH cyc %0d fa_kh %b/%b fb_kh %b/%b fault %b/%b", cyc, u0.fa_kh, u1.fa_kh,
                                       u0.fb_kh, u1.fb_kh, f0, f1);
            end
            if (u0.fa_kh || u0.fb_kh) kh_hits = kh_hits + 1;
            if (u0.do_ins) ins = ins + 1;
            if (u0.do_mrg) mrg = mrg + 1;
            if (|s_v0 || |n_v0) outs = outs + 1;
        end
        $display("RF1_LOCKSTEP cycles %0d mismatches %0d key_hits %0d inserts %0d merges %0d out_words %0d", N, mism,
                 kh_hits, ins, mrg, outs);
        if (mism == 0 && kh_hits > 0 && mrg > 0) $display("RF1_LOCKSTEP PASS"); else $display("RF1_LOCKSTEP FAIL");
        $finish;
    end
endmodule
