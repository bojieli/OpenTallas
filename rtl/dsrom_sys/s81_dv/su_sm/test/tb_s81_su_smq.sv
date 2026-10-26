`timescale 1ns/1ps
// S81U-2 (2026-10-17): differential bench of the per-head tap ot_s81_su_smq against the 2-head stop tap ot_s81_su_smt
// (production parameters SM_H 16, SM_LPH 16, S_RD 16, WS 2).  The same random SE / SO jobs (parameter rows, operand
// beats, e / o result events, den, divide faults) drive smt over its spine tap (all parameter rows in one beat, 16-slot
// operand beats) and two smq (heads g = 2 TI, 2 TI + 1) over their serial row ports.  Compared, in order, per job:
//   SE configuration (nv, lt, scale, the head's sink); the 32-pair cos / sin stream (index, data); operand beats
//   (smq forwards the head's row); write rows (SE: smt slot q = head q's row; SO: smt's full row = the two heads'
//   masked halves at the same address); final status (fault / overflow / den).
// Prints "SMQ PASS ..." or "SMQ FAIL ..." as its LAST line.
module tb_s81_su_smq;
    parameter integer MUT = 0, TI = 5, NJOB = 40, SEED = 1017;
    reg clk = 0, rst = 0;
    always #1 clk = ~clk;
    // smt drive
    reg dn_st = 0; reg [3:0] dn_kind = 0; reg [7:0] dn_jid = 0; reg [15:0] dn_v = 0; reg [2559:0] dn_p = 0;
    reg e_v = 0; reg [1023:0] e_d = 0; reg o_v = 0; reg [511:0] o_d = 0; reg den_v = 0; reg [15:0] f16 = 0;
    // smq drive (both heads share job / row valid; rows differ)
    reg q_st = 0; reg [3:0] q_kind = 0; reg [7:0] q_jid = 0; reg r_v = 0, r_p = 0; reg [2:0] r_j = 0;
    reg [511:0] r_d0 = 0, r_d1 = 0;
    wire s_v, p_v, c_v, cs_v; wire [6:0] c_nv; wire [2:0] c_lt; wire [31:0] c_scale; wire [63:0] c_sink; wire [4:0] cs_i;
    wire [63:0] cs_d; wire [1:0] w_v; wire [27:0] w_a; wire [31:0] w_m; wire [1023:0] w_d;
    wire t_fu, t_fo, t_al, t_den, t_rdy; wire [7:0] t_rj;
    ot_s81_su_smt #(.SM_H(16), .SM_LPH(16), .S_RD(16), .WS(2)) u_t (
        .clk(clk), .rst_in(rst), .cfg_ti(TI[3:0]), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid), .dn_v_i(dn_v),
        .dn_p_i(dn_p), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale), .c_sink(c_sink),
        .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .e_v_i(e_v), .e_d_i(e_d), .o_v_i(o_v), .o_d_i(o_d), .den_v_i(den_v),
        .f_i(|f16), .o_v(w_v), .o_a(w_a), .o_m(w_m), .o_d(w_d), .o_fu(t_fu), .o_fo(t_fo), .o_alive(t_al), .o_den(t_den),
        .o_rdy(t_rdy), .o_rjid(t_rj));
    wire [1:0] qs_v, qp_v, qc_v, qcs_v, qw_v, q_fu, q_fo, q_al, q_den;
    wire [13:0] qc_nv; wire [5:0] qc_lt; wire [63:0] qc_scale, qc_sink; wire [9:0] qcs_i; wire [127:0] qcs_d;
    wire [1023:0] qd_o, qw_d; wire [27:0] qw_a; wire [31:0] qw_m; wire [15:0] q_rj;
    genvar h;
    generate for (h = 0; h < 2; h = h + 1) begin : g_q
        ot_s81_su_smq #(.MUT(MUT)) u_q (
            .clk(clk), .rst_in(rst), .cfg_g(4'(2 * TI + h)), .j_st(q_st), .j_kind(q_kind), .j_jid(q_jid),
            .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(h ? r_d1 : r_d0),
            .s_v(qs_v[h]), .p_v(qp_v[h]), .c_v(qc_v[h]), .c_nv(qc_nv[7 * h +: 7]), .c_lt(qc_lt[3 * h +: 3]),
            .c_scale(qc_scale[32 * h +: 32]), .c_sink(qc_sink[32 * h +: 32]), .cs_v(qcs_v[h]), .cs_i(qcs_i[5 * h +: 5]),
            .cs_d(qcs_d[64 * h +: 64]), .d_o(qd_o[512 * h +: 512]),
            .e_v(e_v), .e_d(e_d[512 * h +: 512]), .o_vi(o_v), .o_di(o_d[256 * h +: 256]), .den_v(den_v), .f_i(f16[8 * h +: 8]),
            .w_v(qw_v[h]), .w_a(qw_a[14 * h +: 14]), .w_m(qw_m[16 * h +: 16]), .w_d(qw_d[512 * h +: 512]),
            .o_fu(q_fu[h]), .o_fo(q_fo[h]), .o_alive(q_al[h]), .o_den(q_den[h]), .o_rjid(q_rj[8 * h +: 8]));
    end endgenerate

    // ------------------------------------------------------------------ event logs (pushed by monitors)
    integer err = 0, nchk = 0;
    reg [1023:0] tq_c [$]; reg [1023:0] hq_c0 [$], hq_c1 [$];      // configuration
    reg [1023:0] tq_s [$]; reg [1023:0] hq_s0 [$], hq_s1 [$];      // cos / sin stream
    reg [1023:0] tq_w [$]; reg [1023:0] hq_w0 [$], hq_w1 [$];      // write rows {kind marker, addr, mask, data}
    reg [1023:0] hq_o0 [$], hq_o1 [$];                              // forwarded operand rows
    reg [1023:0] exp_o0 [$], exp_o1 [$];
    integer nsv = 0, npv = 0, nqs [0:1], nqp [0:1];
    initial begin nqs[0] = 0; nqs[1] = 0; nqp[0] = 0; nqp[1] = 0; end
    integer k;
    always @(posedge clk) if (rst) begin
        if (c_v) tq_c.push_back({c_nv, c_lt, c_scale, c_sink});
        if (cs_v) tq_s.push_back({cs_i, cs_d});
        if (s_v) nsv = nsv + 1;
        if (p_v) npv = npv + 1;
        for (k = 0; k < 2; k = k + 1) if (w_v[k]) tq_w.push_back({w_a[14 * k +: 14], w_m[16 * k +: 16], w_d[512 * k +: 512]});
        if (qc_v[0]) hq_c0.push_back({qc_nv[6:0], qc_lt[2:0], qc_scale[31:0], qc_sink[31:0]});
        if (qc_v[1]) hq_c1.push_back({qc_nv[13:7], qc_lt[5:3], qc_scale[63:32], qc_sink[63:32]});
        if (qcs_v[0]) hq_s0.push_back({qcs_i[4:0], qcs_d[63:0]});
        if (qcs_v[1]) hq_s1.push_back({qcs_i[9:5], qcs_d[127:64]});
        if (qs_v[0]) nqs[0] = nqs[0] + 1; if (qs_v[1]) nqs[1] = nqs[1] + 1;
        if (qp_v[0]) nqp[0] = nqp[0] + 1; if (qp_v[1]) nqp[1] = nqp[1] + 1;
        if (qs_v[0] || qp_v[0]) hq_o0.push_back(qd_o[511:0]);
        if (qs_v[1] || qp_v[1]) hq_o1.push_back(qd_o[1023:512]);
        if (qw_v[0]) hq_w0.push_back({qw_a[13:0], qw_m[15:0], qw_d[511:0]});
        if (qw_v[1]) hq_w1.push_back({qw_a[27:14], qw_m[31:16], qw_d[1023:512]});
    end

    // ------------------------------------------------------------------ stimulus
    function [511:0] rnd512(input integer dummy);
        integer i; begin for (i = 0; i < 16; i = i + 1) rnd512[32 * i +: 32] = $urandom; end
    endfunction
    reg [511:0] prm [0:4];
    integer j, b, nb, np, kind, gap, ne, seed;
    reg [511:0] x0, x1;
    task tick; begin @(posedge clk); #0.1; end endtask
    initial begin
        seed = SEED; seed = $urandom(seed);
        repeat (4) tick;
        rst = 1;
        repeat (6) tick;
        for (j = 0; j < NJOB; j = j + 1) begin
            kind = ($urandom % 2) ? 5 : 4; np = (kind == 5) ? 5 : 2;
            for (b = 0; b < 5; b = b + 1) prm[b] = rnd512(0);
            prm[0][13:0] = $urandom; prm[0][64 +: 7] = $urandom % 41; prm[0][128 +: 3] = $urandom;
            // job announce (both)
            dn_st = 1; dn_kind = kind; dn_jid = j; q_st = 1; q_kind = kind; q_jid = j; tick;
            dn_st = 0; q_st = 0;
            // smt: every parameter row in one beat; smq: one row a cycle
            dn_v = (16'd1 << np) - 16'd1;
            for (b = 0; b < 5; b = b + 1) dn_p[512 * b +: 512] = prm[b];
            r_v = 1; r_p = 1; r_j = 0; r_d0 = prm[0]; r_d1 = prm[0]; tick;
            dn_v = 0;
            for (b = 1; b < np; b = b + 1) begin r_j = b; r_d0 = prm[b]; r_d1 = prm[b]; tick; end
            r_v = 0; r_p = 0;
            repeat (3 + $urandom % 3) tick;
            // operand beats (smt: all 16 slots valid; smq: the head's row)
            nb = 1 + $urandom % 4;
            for (b = 0; b < nb; b = b + 1) begin
                x0 = rnd512(0); x1 = rnd512(0);
                exp_o0.push_back(x0); exp_o1.push_back(x1);
                dn_v = 16'hFFFF; r_v = 1; r_p = 0; r_d0 = x0; r_d1 = x1; tick;
                dn_v = 0; r_v = 0;
                if ($urandom % 2) tick;
            end
            repeat (40) tick;                                 // the cos / sin stream (32 pairs) drains
            // result events (same cycles for both), with gaps; occasionally back-to-back
            ne = 1 + $urandom % 4;
            for (b = 0; b < ne; b = b + 1) begin
                if (kind == 4) begin e_v = 1; e_d = {rnd512(0), rnd512(0)}; end
                else begin o_v = 1; o_d = rnd512(0); end
                tick; e_v = 0; o_v = 0;
                gap = $urandom % 3; repeat (gap) tick;
            end
            den_v = 1; tick; den_v = 0;
            repeat (8) tick;
        end
        // a divide fault at the end: both report o_fu
        f16 = 16'h0100; tick; f16 = 0;
        repeat (12) tick;
        check;
    end

    task fail(input [8*48-1:0] what, input integer i);
        begin if (err < 12) $display("SMQ MISMATCH %0s at %0d", what, i); err = err + 1; end
    endtask
    task check;
        integer i, hh; reg [1023:0] t, a;
        begin
            for (hh = 0; hh < 2; hh = hh + 1) begin
                if ((hh ? hq_c1.size() : hq_c0.size()) != tq_c.size()) fail("config count", hh);
                for (i = 0; i < tq_c.size() && i < (hh ? hq_c1.size() : hq_c0.size()); i = i + 1) begin
                    t = tq_c[i]; a = hh ? hq_c1[i] : hq_c0[i]; nchk = nchk + 1;
                    if (a[73:32] != t[105:64] || a[31:0] != (hh ? t[63:32] : t[31:0])) fail("config", i);
                end
                if ((hh ? hq_s1.size() : hq_s0.size()) != tq_s.size()) fail("cos/sin count", hh);
                for (i = 0; i < tq_s.size() && i < (hh ? hq_s1.size() : hq_s0.size()); i = i + 1) begin
                    a = hh ? hq_s1[i] : hq_s0[i]; t = tq_s[i]; nchk = nchk + 1; if (a[68:0] != t[68:0]) fail("cos/sin", i);
                end
                if (nqs[hh] + nqp[hh] != nsv + npv || nqs[hh] != nsv) fail("operand beats", hh);
                if ((hh ? hq_o1.size() : hq_o0.size()) != (hh ? exp_o1.size() : exp_o0.size())) fail("operand rows", hh);
                for (i = 0; i < (hh ? exp_o1.size() : exp_o0.size()) && i < (hh ? hq_o1.size() : hq_o0.size()); i = i + 1) begin
                    a = hh ? hq_o1[i] : hq_o0[i]; t = hh ? exp_o1[i] : exp_o0[i];
                    nchk = nchk + 1; if (a[511:0] != t[511:0]) fail("operand row", i);
                end
            end
            // write rows: smt rows in order; SE slots (2 a cycle) = heads 0/1 rows, SO row = both masked halves
            if (hq_w0.size() != hq_w1.size()) fail("head row counts", 0);
            for (i = 0; i < hq_w0.size() && i < hq_w1.size(); i = i + 1) begin
                reg [541:0] r0, r1; t = hq_w0[i]; r0 = t[541:0]; t = hq_w1[i]; r1 = t[541:0];
                nchk = nchk + 1;
                if (r0[527:512] == 16'hFFFF) begin                 // SE: smt pushes head 0 then head 1 (slots 0, 1)
                    if (tq_w.size() < 2) begin fail("smt SE rows short", i); end
                    else begin
                        t = tq_w.pop_front(); if (t[541:0] != r0) fail("SE row head 0", i);
                        t = tq_w.pop_front(); if (t[541:0] != r1) fail("SE row head 1", i);
                    end
                end else begin                                     // SO: one smt row
                    if (tq_w.size() < 1) fail("smt SO rows short", i);
                    else begin
                        t = tq_w.pop_front();
                        if (r0[541:528] != t[541:528] || r1[541:528] != t[541:528]) fail("SO row addr", i);
                        if (r0[527:512] != 16'h00FF || r1[527:512] != 16'hFF00) fail("SO row mask", i);
                        if ({r1[511:256], r0[255:0]} != t[511:0]) fail("SO row data", i);
                    end
                end
            end
            if (tq_w.size() != 0) fail("smt rows left", tq_w.size());
            if (q_fu != 2'b10 || (|q_fu) != t_fu || q_fo != {t_fo, t_fo} || q_den != {t_den, t_den} || t_fu != 1'b1) begin fail("status", 0); $display("status t fu%b fo%b den%b q fu%b fo%b den%b", t_fu, t_fo, t_den, q_fu, q_fo, q_den); end
            if (nchk < 200) fail("too few checks", nchk);
            $display("SMQ stats MUT=%0d jobs=%0d config=%0d cs=%0d rows_smt_seen=%0d head_rows=%0d sv=%0d pv=%0d checks=%0d",
                     MUT, NJOB, tq_c.size(), tq_s.size(), hq_w0.size(), hq_w0.size() + hq_w1.size(), nsv, npv, nchk);
            if (err == 0) $display("SMQ PASS MUT=%0d checks=%0d", MUT, nchk);
            else $display("SMQ FAIL MUT=%0d errors=%0d checks=%0d", MUT, err, nchk);
            $finish;
        end
    endtask
endmodule
