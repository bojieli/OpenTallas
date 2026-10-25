`timescale 1ns/1ps
// HBM-HC 2026-10-24: DEFAULT (W 64) BIT-EXACTNESS of the W-parameterised HC hub / bank masters against the unchanged
// originals (claude/hbm-bind-1024r@fc76a2c42; run_hc_w_default_eq.sh renames them *_orig; the terminal bank reference is
// the die's scoped copy rtl/hbm_accel/die_glue/scoped_d4g/hcbt.sv of 4418ce6ff).  LOCKSTEP: every DUT / REF pair gets
// the SAME random input on every edge (all inputs, incl. rst_n pulses, x-wave beats, ingest events, descriptors, sums,
// chain inputs), and every output bit must be equal on every edge (both sides start from the same initial state).
//   pairs: qcen (DRLY 2, CHX 11), qhub (DRLY 2, CHX 11), bankq (CPI 1, CPO 1), bankq_ft, bankq0 (DRLY 2, CPO 1),
//          bankq_term (CPI 1, CPO 1) vs scoped term, qeng (ring composition, CPR 1, DRLY 2).
// MUTB (bench mutant, must FAIL): 1 = DUT qcen MUT 4 (tree pairs), 2 = DUT term MUT 3 (f_out), 3 = DUT bankq MUT 1.
module tb_hbm_hc_w_default_eq;
    parameter integer MUTB = 0;
    parameter integer NCYC = 20000;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0, errs = 0, seed = 1;
    // ---------------------------------------------------------------- random inputs
    reg d_v, d_ss, i_v, i_kind, x_v, f_in, wv, xv, j;
    reg [6:0] d_nv; reg [9:0] d_wa, d_xa, i_word, x_word, wa; reg [1:0] i_slot, x_beat; reg [4:0] i_lo, i_w;
    reg [11:0] i_cnt; reg [2048:0] s_i; reg [7:0] wfault_i; reg [2047:0] sum_in; reg [255:0] xb_d, fa_d, fb_d;
    reg [2047:0] xw2048; reg [7:0] tgt; reg cfg_v, desc_v, launch_v; reg [7:0] cfg_target; reg [11:0] cfg_addr, desc_base;
    reg [255:0] cfg_data; reg [12:0] desc_limit; reg [15:0] desc_loops; reg [2055:0] lg_rr; reg [7:0] lg_w_done;
    reg result_v; reg [2:0] result_position; reg [767:0] result; reg fa_v, fb_v, fa_wv, fa_xv, fa_j, fb_wv, fb_xv, fb_j;
    reg [1:0] fa_b, fb_b; reg [9:0] fa_wa, fb_wa; reg fa_rst, fb_rst, fa_wf, fb_wf;
    reg [8191:0] xw8192;
    function automatic [31:0] rfp(input integer dummy);   // mostly finite binary32 (exp 100..150), some zeros / specials
        reg [31:0] r; r = $urandom;
        if (r[3:0] == 0) rfp = 32'd0; else if (r[7:0] == 8'hff) rfp = 32'h7f800000;
        else rfp = {r[31], 8'(100 + ($urandom % 51)), r[22:0]};
    endfunction
    task automatic rnd;
        d_v = ($urandom % 3) != 0; d_ss = ($urandom % 5) == 0; d_nv = 7'($urandom % 70); d_wa = $urandom; d_xa = $urandom;
        i_v = ($urandom % 40) == 0; i_kind = $urandom; i_slot = $urandom; i_lo = $urandom % 26; i_w = $urandom % 24;
        i_cnt = $urandom % 64; i_word = $urandom;
        x_v = ($urandom % 4) != 0; x_beat = $urandom; x_word = $urandom;
        for (integer k = 0; k < 64; k = k + 1) s_i[k*32 +: 32] = rfp(0);
        s_i[2048] = ($urandom % 50) == 0;
        for (integer k = 0; k < 64; k = k + 1) sum_in[k*32 +: 32] = rfp(0);
        wfault_i = (($urandom % 30) == 0) ? 8'($urandom) : 8'd0; f_in = ($urandom % 50) == 0;
        for (integer k = 0; k < 8; k = k + 1) begin xb_d[k*32 +: 32] = rfp(0); fa_d[k*32 +: 32] = rfp(0); fb_d[k*32 +: 32] = rfp(0); end
        if (($urandom % 3) != 0) for (integer k = 0; k < 8; k = k + 1) begin xb_d[k*32 +: 16] = 0; fa_d[k*32 +: 16] = 0; fb_d[k*32 +: 16] = 0; end
        wv = ($urandom % 3) == 0; xv = ($urandom % 3) == 0; j = $urandom; wa = $urandom;
        fa_v = $urandom; fb_v = $urandom; fa_b = $urandom; fb_b = $urandom; fa_wv = $urandom; fa_xv = $urandom; fa_j = $urandom;
        fb_wv = $urandom; fb_xv = $urandom; fb_j = $urandom; fa_wa = $urandom; fb_wa = $urandom;
        fa_rst = ($urandom % 200) != 0; fb_rst = ($urandom % 200) != 0; fa_wf = ($urandom % 40) == 0; fb_wf = ($urandom % 40) == 0;
        for (integer k = 0; k < 64; k = k + 1) xw2048[k*32 +: 32] = rfp(0);
        for (integer k = 0; k < 256; k = k + 1) xw8192[k*32 +: 32] = rfp(0);
        tgt = 8'd110; cfg_v = ($urandom % 50) == 0; cfg_target = ($urandom % 2) ? 8'd110 : 8'($urandom); cfg_addr = $urandom;
        for (integer k = 0; k < 8; k = k + 1) cfg_data[k*32 +: 32] = $urandom;
        desc_v = ($urandom % 100) == 0; desc_base = $urandom % 16; desc_limit = $urandom % 64; desc_loops = $urandom % 4;
        launch_v = ($urandom % 100) == 0;
        for (integer k = 0; k < 65; k = k + 1) lg_rr[k*32 +: 32] = $urandom;
        lg_w_done = $urandom; result_v = ($urandom % 20) == 0; result_position = $urandom;
        for (integer k = 0; k < 24; k = k + 1) result[k*32 +: 32] = rfp(0);
    endtask
    // ---------------------------------------------------------------- compare helper
    `define EQ(name, a, b) if ((a) !== (b)) begin errs = errs + 1; if (errs < 12) $display("MISMATCH cyc=%0d %s", cyc, name); end
    // ---------------------------------------------------------------- 1 qcen
    wire [7:0] c_rb0, c_rb1; wire c_bdv0, c_bdss0, c_bdv1, c_bdss1; wire [6:0] c_bdnv0, c_bdnv1; wire [9:0] c_bdwa0, c_bdxa0, c_bdwa1, c_bdxa1;
    wire [12:0] c_wc0 [0:3], c_wc1 [0:3]; wire c_psv0, c_psf0, c_flt0, c_psv1, c_psf1, c_flt1; wire [31:0] c_ps0, c_ps1;
    ot_hbm_hc_qcen_static_orig #(.DRLY(2), .CHX(11)) r_cen (.clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv),
        .d_wa(d_wa), .d_xa(d_xa), .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt),
        .i_word(i_word), .x_v(x_v), .x_beat(x_beat), .x_word(x_word), .s_i(s_i), .wfault_i(wfault_i), .rst_b(c_rb0),
        .bd_v(c_bdv0), .bd_ss(c_bdss0), .bd_nv(c_bdnv0), .bd_wa(c_bdwa0), .bd_xa(c_bdxa0), .wc_w(c_wc0[0]), .wc_n(c_wc0[1]),
        .wc_e(c_wc0[2]), .wc_s(c_wc0[3]), .ps_v(c_psv0), .ps(c_ps0), .ps_f(c_psf0), .fault(c_flt0));
    ot_hbm_hc_qcen_static #(.DRLY(2), .CHX(11), .MUT(MUTB == 1 ? 4 : 0)) d_cen (.clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv),
        .d_wa(d_wa), .d_xa(d_xa), .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt),
        .i_word(i_word), .x_v(x_v), .x_beat(x_beat), .x_word(x_word), .s_i(s_i), .wfault_i(wfault_i), .rst_b(c_rb1),
        .bd_v(c_bdv1), .bd_ss(c_bdss1), .bd_nv(c_bdnv1), .bd_wa(c_bdwa1), .bd_xa(c_bdxa1), .wc_w(c_wc1[0]), .wc_n(c_wc1[1]),
        .wc_e(c_wc1[2]), .wc_s(c_wc1[3]), .ps_v(c_psv1), .ps(c_ps1), .ps_f(c_psf1), .fault(c_flt1));
    wire [127:0] cen_o0 = {c_rb0, c_bdv0, c_bdss0, c_bdnv0, c_bdwa0, c_bdxa0, c_wc0[0], c_wc0[1], c_wc0[2], c_wc0[3], c_psv0, c_ps0, c_psf0, c_flt0};
    wire [127:0] cen_o1 = {c_rb1, c_bdv1, c_bdss1, c_bdnv1, c_bdwa1, c_bdxa1, c_wc1[0], c_wc1[1], c_wc1[2], c_wc1[3], c_psv1, c_ps1, c_psf1, c_flt1};
    // ---------------------------------------------------------------- 2 qhub (die params)
    `define QHUB_PORTS(P) .clk(clk), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), \
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), \
        .launch_v(launch_v), .configured(P``_conf), .lg_rq(P``_lgrq), .lg_wq(P``_lgwq), .lg_rr(lg_rr), .lg_w_done(lg_w_done), \
        .residual_done(P``_rd), .gathered_mix_v(P``_gmv), .gathered_mix_row(P``_gmr), .gathered_mix_pos(P``_gmp), \
        .gathered_mix_data(P``_gmd), .gather_done(P``_gd), .result_v(result_v), .result_position(result_position), \
        .result(result), .program_active(P``_pa), .program_done(P``_pd), .hcq_fault(P``_hf), \
        .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), \
        .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt), .i_word(i_word), .ps_v(P``_psv), .ps(P``_ps), .ps_f(P``_psf), \
        .eng_fault(P``_ef), .rstb_w(P``_rw), .rstb_e(P``_re), .rstb_n(P``_rn), .rstb_s(P``_rs), .bd_v(P``_bdv), \
        .bd_ss(P``_bdss), .bd_nv(P``_bdnv), .bd_wa(P``_bdwa), .bd_xa(P``_bdxa), .s_i(s_i), .wf_w(wfault_i[0]), \
        .wf_e(wfault_i[4]), .wf_n(wfault_i[3:1]), .wf_s(wfault_i[7:5]), .wc_w(P``_wcw), .wc_n(P``_wcn), .wc_e(P``_wce), \
        .wc_s(P``_wcs), .xb_v(P``_xv), .xb_beat(P``_xb), .xb_v_n(P``_xvn), .xb_v_e(P``_xve), .xb_v_s(P``_xvs), \
        .xb_beat_n(P``_xbn), .xb_beat_e(P``_xbe), .xb_beat_s(P``_xbs), .xb_d0(P``_d0), .xb_d1(P``_d1), .xb_d2(P``_d2), \
        .xb_d3(P``_d3), .xb_d4(P``_d4), .xb_d5(P``_d5), .xb_d6(P``_d6), .xb_d7(P``_d7)
    `define QHUB_WIRES(P) wire P``_conf, P``_rd, P``_gmv, P``_gd, P``_pa, P``_pd, P``_hf, P``_psv, P``_psf, P``_ef, P``_rw, P``_re; \
        wire [135:0] P``_lgrq; wire [2247:0] P``_lgwq; wire [4:0] P``_gmr; wire [2:0] P``_gmp, P``_rn, P``_rs; wire [31:0] P``_gmd, P``_ps; \
        wire P``_bdv, P``_bdss; wire [6:0] P``_bdnv; wire [9:0] P``_bdwa, P``_bdxa; wire [12:0] P``_wcw, P``_wcn, P``_wce, P``_wcs; \
        wire P``_xv, P``_xvn, P``_xve, P``_xvs; wire [1:0] P``_xb, P``_xbn, P``_xbe, P``_xbs; \
        wire [255:0] P``_d0, P``_d1, P``_d2, P``_d3, P``_d4, P``_d5, P``_d6, P``_d7; \
        wire [4799:0] P``_all = {P``_conf, P``_rd, P``_gmv, P``_gd, P``_pa, P``_pd, P``_hf, P``_psv, P``_psf, P``_ef, P``_rw, P``_re, \
            P``_lgrq, P``_gmr, P``_gmp, P``_rn, P``_rs, P``_gmd, P``_ps, P``_bdv, P``_bdss, P``_bdnv, P``_bdwa, P``_bdxa, \
            P``_wcw, P``_wcn, P``_wce, P``_wcs, P``_xv, P``_xvn, P``_xve, P``_xvs, P``_xb, P``_xbn, P``_xbe, P``_xbs}; \
        wire [2048+2247:0] P``_dat = {P``_lgwq, P``_d0, P``_d1, P``_d2, P``_d3, P``_d4, P``_d5, P``_d6, P``_d7};
    `QHUB_WIRES(hr)
    `QHUB_WIRES(hd)
    // (hub client timing at the canonical defaults: the die's RD_CAPTURE / GATHER_PHASE 51 belong to the die's scoped
    // hc_<q> copy; the centre params are the die's)
    ot_hbm_hc_qhub_static_orig #(.DRLY(2), .CHX(11)) r_hub (`QHUB_PORTS(hr));
    ot_hbm_hc_qhub_static #(.DRLY(2), .CHX(11)) d_hub (`QHUB_PORTS(hd));
    // ---------------------------------------------------------------- 3..6 bank tiles
    `define BANK_COMMON .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), \
        .xb_v(x_v), .xb_beat(x_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa)
    `define BANK_FWD(P) .o_v(P``_ov), .o_ss(P``_oss), .o_nv(P``_onv), .o_wa(P``_owa), .o_xa(P``_oxa), .sum_out(P``_so), .f_out(P``_fo), .wfault(P``_wf)
    `define BANK_WIRES(P) wire P``_ov, P``_oss, P``_fo, P``_wf; wire [6:0] P``_onv; wire [9:0] P``_owa, P``_oxa; wire [2047:0] P``_so; \
        wire [2077:0] P``_all = {P``_ov, P``_oss, P``_fo, P``_wf, P``_onv, P``_owa, P``_oxa, P``_so};
    `BANK_WIRES(br) `BANK_WIRES(bd) `BANK_WIRES(fr) `BANK_WIRES(fd) `BANK_WIRES(zr) `BANK_WIRES(zd)
    ot_hbm_hc_bankq_static_orig #(.CPI(1), .CPO(1)) r_bq (`BANK_COMMON, `BANK_FWD(br), .sum_in(sum_in), .f_in(f_in));
    ot_hbm_hc_bankq_static #(.CPI(1), .CPO(1), .MUT(MUTB == 3 ? 1 : 0)) d_bq (`BANK_COMMON, `BANK_FWD(bd), .sum_in(sum_in), .f_in(f_in));
    `define FT_WIRES(P) wire P``_av, P``_awv, P``_axv, P``_aj, P``_bv, P``_bwv, P``_bxv, P``_bj, P``_ar, P``_brs, P``_awf, P``_bwf; \
        wire [1:0] P``_ab, P``_bb; wire [255:0] P``_ad, P``_bd; wire [9:0] P``_awa, P``_bwa; \
        wire [559:0] P``_fall = {P``_av, P``_awv, P``_axv, P``_aj, P``_bv, P``_bwv, P``_bxv, P``_bj, P``_ar, P``_brs, P``_awf, P``_bwf, \
            P``_ab, P``_bb, P``_ad, P``_bd, P``_awa, P``_bwa};
    `define FT_PORTS(P) .fa_xb_v(fa_v), .fa_xb_beat(fa_b), .fa_xb_d(fa_d), .fa_wv(fa_wv), .fa_xv(fa_xv), .fa_j(fa_j), .fa_wa(fa_wa), \
        .fa_xb_v_o(P``_av), .fa_xb_beat_o(P``_ab), .fa_xb_d_o(P``_ad), .fa_wv_o(P``_awv), .fa_xv_o(P``_axv), .fa_j_o(P``_aj), .fa_wa_o(P``_awa), \
        .fb_xb_v(fb_v), .fb_xb_beat(fb_b), .fb_xb_d(fb_d), .fb_wv(fb_wv), .fb_xv(fb_xv), .fb_j(fb_j), .fb_wa(fb_wa), \
        .fb_xb_v_o(P``_bv), .fb_xb_beat_o(P``_bb), .fb_xb_d_o(P``_bd), .fb_wv_o(P``_bwv), .fb_xv_o(P``_bxv), .fb_j_o(P``_bj), .fb_wa_o(P``_bwa), \
        .fa_rst_n(fa_rst), .fb_rst_n(fb_rst), .fa_rst_n_o(P``_ar), .fb_rst_n_o(P``_brs), .fa_wfault(fa_wf), .fb_wfault(fb_wf), \
        .fa_wfault_o(P``_awf), .fb_wfault_o(P``_bwf)
    `FT_WIRES(fr) `FT_WIRES(fd)
    ot_hbm_hc_bankq_ft_static_orig r_ft (`BANK_COMMON, `BANK_FWD(fr), .sum_in(sum_in), .f_in(f_in), `FT_PORTS(fr));
    ot_hbm_hc_bankq_ft_static d_ft (`BANK_COMMON, `BANK_FWD(fd), .sum_in(sum_in), .f_in(f_in), `FT_PORTS(fd));
    wire [2048:0] zr_so0, zd_so0;
    ot_hbm_hc_bankq0_static_orig #(.DRLY(2), .CPO(1)) r_b0 (`BANK_COMMON, `BANK_FWD(zr), .s_i(s_i), .s_o(zr_so0));
    ot_hbm_hc_bankq0_static #(.DRLY(2), .CPO(1)) d_b0 (`BANK_COMMON, `BANK_FWD(zd), .s_i(s_i), .s_o(zd_so0));
    wire tr_fo, tr_wf, td_fo, td_wf; wire [2047:0] tr_so, td_so;
    ot_hbm_hc_bankq_term_static_orig #(.CPI(1), .CPO(1)) r_t (`BANK_COMMON, .sum_in(sum_in), .f_in(f_in), .sum_out(tr_so),
        .f_out(tr_fo), .wfault(tr_wf));
    ot_hbm_hc_bankq_term_static #(.CPI(1), .CPO(1), .MUT(MUTB == 2 ? 3 : 0)) d_t (`BANK_COMMON, .sum_in(sum_in), .f_in(f_in),
        .sum_out(td_so), .f_out(td_fo), .wfault(td_wf));
    // ---------------------------------------------------------------- 7 qeng ring composition
    wire qr_psv, qr_psf, qr_f, qd_psv, qd_psf, qd_f; wire [31:0] qr_ps, qd_ps;
    ot_hbm_hc_qeng_static_orig #(.DRLY(2), .CPR(1)) r_qe (.clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv),
        .d_wa(d_wa), .d_xa(d_xa), .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt),
        .i_word(i_word), .x_wave_v(x_v), .x_wave_beat(x_beat), .x_wave_word(x_word), .x_wave(xw2048), .ps_v(qr_psv),
        .ps(qr_ps), .ps_f(qr_psf), .fault(qr_f));
    ot_hbm_hc_qeng_static #(.DRLY(2), .CPR(1)) d_qe (.clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv),
        .d_wa(d_wa), .d_xa(d_xa), .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt),
        .i_word(i_word), .x_wave_v(x_v), .x_wave_beat(x_beat), .x_wave_word(x_word), .x_wave(xw2048), .ps_v(qd_psv),
        .ps(qd_ps), .ps_f(qd_psf), .fault(qd_f));
    // ---------------------------------------------------------------- drive + check
    integer nact_ps = 0, nact_tree = 0;
    always @(negedge clk) begin
        rnd;
        if (cyc > 30 && ($urandom % 3000) == 0) rst_n = 1'b0; else if (cyc > 8) rst_n = 1'b1;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc > 2) begin
            `EQ("qcen", cen_o0, cen_o1)
            `EQ("qhub ctl", hr_all, hd_all)
            `EQ("qhub data", hr_dat, hd_dat)
            `EQ("bankq", br_all, bd_all)
            `EQ("bankq_ft", {fr_all, fr_fall}, {fd_all, fd_fall})
            `EQ("bankq0", {zr_all, zr_so0}, {zd_all, zd_so0})
            `EQ("bankq_term", {tr_so, tr_fo, tr_wf}, {td_so, td_fo, td_wf})
            `EQ("qeng", {qr_psv, qr_ps, qr_psf, qr_f}, {qd_psv, qd_ps, qd_psf, qd_f})
            if (c_psv0) nact_tree = nact_tree + 1;
            if (qr_psv) nact_ps = nact_ps + 1;
        end
        if (cyc == NCYC) begin
            $display("HC_W_DEFAULT_EQ MUTB=%0d cycles=%0d mismatches=%0d (qcen tree outputs %0d, qeng ring outputs %0d) %s",
                MUTB, cyc, errs, nact_tree, nact_ps, errs == 0 ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
