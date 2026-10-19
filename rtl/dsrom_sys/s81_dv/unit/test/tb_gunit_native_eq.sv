`timescale 1ns/1ps
// S81-NATIVE3 (10-17): dsdv_gunit_l2 / dsdv_gunit_l3 pin fixes (reset relay; L2 hct/rct pin flops ORed after capture,
// vstop JREG 0) vs the CLOSED views' RTL (L2 99ffdc846, L3 7205fead6; renamed *_ref by run_gunit_native_eq.sh).
// Every input is random on every edge (valids 1 in 4, so beats, injections, collisions, faults and su_rw jobs all
// occur; hct/rct mostly exclusive so each fault onset is compared); inputs are idle until 6 edges after each reset
// release (the relay releases 3 edges later), then every output of both leaves must be identical on every edge.  A reset
// pulse every 400 edges re-arms the sticky faults and checks the async assert.
module tb_gunit_native_eq;
    parameter integer NCYC = 20000;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg go = 0;
    // ---------------- L2 stimulus
    reg [275:0] rn_i, hct_b, rs_i, rct_b; reg hct_v, hf, rct_v, rf, cw_v; reg [3:0] sid; reg [9:0] cw_a; reg [255:0] cw_d;
    // ---------------- L3 stimulus
    reg [275:0] l3_rn_i, l3_vi_s; reg rw_st, rw_v, rw_l; reg [511:0] rw_x; reg [31:0] rw_scale; reg [9:0] rw_row;
    reg [4:0] rw_lm; reg [15:0] rw_sm; reg [3:0] sid_i;
`define L2_OUTS(p) wire [275:0] p``rn_o, p``hp_a, p``hp_b, p``rs_o, p``dl_a, p``dl_b; wire p``hp_av, p``hp_bv, p``cwn_v, p``dl_av, p``dl_bv, p``cws_v, p``fault; \
    wire [9:0] p``cwn_a, p``cws_a; wire [255:0] p``cwn_d, p``cws_d; wire [3:0] p``sidn, p``sids;
    `L2_OUTS(r_) `L2_OUTS(n_)
`define L2_CONN(p) (.clk(clk), .rst_n(rst_n), .rn_i(rn_i), .rn_o(p``rn_o), .hp_av(p``hp_av), .hp_a(p``hp_a), .hp_bv(p``hp_bv), .hp_b(p``hp_b), \
    .cwn_v(p``cwn_v), .cwn_a(p``cwn_a), .cwn_d(p``cwn_d), .sidn(p``sidn), .hct_v(hct_v), .hct_b(hct_b), .hf(hf), \
    .rs_i(rs_i), .rs_o(p``rs_o), .dl_av(p``dl_av), .dl_a(p``dl_a), .dl_bv(p``dl_bv), .dl_b(p``dl_b), \
    .cws_v(p``cws_v), .cws_a(p``cws_a), .cws_d(p``cws_d), .sids(p``sids), .rct_v(rct_v), .rct_b(rct_b), .rf(rf), \
    .sid(sid), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .fault(p``fault))
    dsdv_gunit_l2_ref r_l2 `L2_CONN(r_);
`ifdef MUT
    dsdv_gunit_l2 #(.MUT(`MUT)) n_l2 `L2_CONN(n_);
`else
    dsdv_gunit_l2 n_l2 `L2_CONN(n_);
`endif
    wire [2003:0] r2 = {r_rn_o, r_hp_a, r_hp_b, r_rs_o, r_dl_a, r_dl_b, r_hp_av, r_hp_bv, r_cwn_v, r_dl_av, r_dl_bv, r_cws_v, r_fault, r_cwn_a, r_cws_a, r_cwn_d, r_cws_d, r_sidn, r_sids};
    wire [2003:0] n2 = {n_rn_o, n_hp_a, n_hp_b, n_rs_o, n_dl_a, n_dl_b, n_hp_av, n_hp_bv, n_cwn_v, n_dl_av, n_dl_bv, n_cws_v, n_fault, n_cwn_a, n_cws_a, n_cwn_d, n_cws_d, n_sidn, n_sids};
`define L3_OUTS(p) wire [275:0] p``l3_rn_o, p``w_b, p``vo_s; wire p``w_v, p``l3_fault;
    `L3_OUTS(r_) `L3_OUTS(n_)
`define L3_CONN(p) (.clk(clk), .rst_n(rst_n), .rn_i(l3_rn_i), .rn_o(p``l3_rn_o), .rw_st(rw_st), .rw_v(rw_v), .rw_l(rw_l), .rw_x(rw_x), \
    .rw_scale(rw_scale), .rw_row(rw_row), .rw_lm(rw_lm), .rw_sm(rw_sm), .sid_i(sid_i), .w_v(p``w_v), .w_b(p``w_b), .fault(p``l3_fault), \
    .vo_s(p``vo_s), .vi_s(l3_vi_s))
    dsdv_gunit_l3_ref r_l3 `L3_CONN(r_);
`ifdef MUT3
    dsdv_gunit_l3 #(.MUT(4)) n_l3 `L3_CONN(n_);      // negative control: route_scale skipped
`else
    dsdv_gunit_l3 n_l3 `L3_CONN(n_);
`endif
    wire [829:0] r3 = {r_l3_rn_o, r_w_b, r_vo_s, r_w_v, r_l3_fault}, n3 = {n_l3_rn_o, n_w_b, n_vo_s, n_w_v, n_l3_fault};
    integer fon = 0, cyc = 0, m2 = 0, m3 = 0, i, inj = 0, wv = 0, f2 = 0, jobs = 0; reg chk = 0;
    task rnd(output [511:0] x); begin for (i = 0; i < 16; i = i + 1) x[32 * i +: 32] = $urandom; end endtask
    reg [511:0] t;
    task stim; begin
        if (!go) begin
            rn_i = 0; hct_b = 0; rs_i = 0; rct_b = 0; hct_v = 0; hf = 0; rct_v = 0; rf = 0; cw_v = 0; sid = 0; cw_a = 0; cw_d = 0;
            l3_rn_i = 0; l3_vi_s = 0; rw_st = 0; rw_v = 0; rw_l = 0; rw_x = 0; rw_scale = 0; rw_row = 0; rw_lm = 0; rw_sm = 0; sid_i = 0;
        end else begin
            rnd(t); rn_i = t[275:0]; rn_i[0] = ($urandom % 4) == 0; rnd(t); rs_i = t[275:0]; rs_i[0] = ($urandom % 4) == 0;
            rnd(t); hct_b = ($urandom % 8) == 0 ? t[275:0] : 0; rnd(t); rct_b = ($urandom % 8) == 0 && (hct_b == 0 || ($urandom % 16) == 0) ? t[275:0] : 0;
            hct_v = |hct_b; rct_v = |rct_b; hf = ($urandom % 512) == 0; rf = ($urandom % 512) == 0;
            sid = $urandom; cw_v = ($urandom % 4) == 0; cw_a = $urandom; rnd(t); cw_d = t[255:0];
            rnd(t); l3_rn_i = t[275:0]; rnd(t); l3_vi_s = t[275:0];
            rw_st = ($urandom % 64) == 0; rw_v = ($urandom % 3) == 0; rw_l = ($urandom % 6) == 0;
            for (i = 0; i < 16; i = i + 1) rw_x[32 * i +: 32] = {1'b0, 8'd110 + 8'($urandom % 30), 23'($urandom)};
            rw_scale = {1'b0, 8'd127, 23'($urandom)}; rw_row = $urandom; rw_lm = $urandom; rw_sm = $urandom; sid_i = $urandom;
        end
    end endtask
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (chk) begin
            if (r2 !== n2) begin m2 = m2 + 1; if (m2 <= 6) $display("MISMATCH L2 cyc=%0d fault r%b n%b cws_eq=%b rs_o_eq=%b rn_o_eq=%b", cyc, r_fault, n_fault, r_cws_d === n_cws_d, r_rs_o === n_rs_o, r_rn_o === n_rn_o); end
            if (r3 !== n3) begin m3 = m3 + 1; if (m3 <= 6) $display("MISMATCH L3 cyc=%0d w_v r%b n%b fault r%b n%b", cyc, r_w_v, n_w_v, r_l3_fault, n_l3_fault); end
            if (r_rs_o[0] || r_rn_o[0]) inj = inj + 1; if (r_w_v) wv = wv + 1; if (r_fault) f2 = f2 + 1; if (r_fault && !$past(r_fault)) fon = fon + 1; if (rw_st) jobs = jobs + 1;
        end
    end
    initial begin
        stim; repeat (4) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk); go = 1; chk = 1;
        for (i = 0; i < NCYC; i = i + 0) begin stim; @(negedge clk);
            if (cyc % 400 == 0) begin rst_n = 0; go = 0; chk = 0; stim; repeat (3) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk); go = 1; chk = 1; end
            if (cyc > NCYC) i = NCYC; end
        $display("GUNITEQ cycles=%0d L2 mismatches=%0d (rung beats out %0d, fault edges %0d, onsets %0d) L3 mismatches=%0d (w_v %0d, starts %0d)", NCYC, m2, inj, f2, fon, m3, wv, jobs);
        if (m2 == 0 && m3 == 0 && inj > 0 && wv > 0) $display("PASS gunit native equivalence (L2 + L3 identical every edge)");
        else $display("FAIL gunit native equivalence");
        $finish;
    end
endmodule
