`timescale 1ns/1ps
// S81U-2 (2026-10-17): exact bench of the per-slice SM share ot_s81_su_sms (smq tap + smh head subtree) against the
// slab's SM stop: ot_s81_su_smt + two ot_s81_su_smh at the spine's DOP = SRL + 2, i.e. dsfd_sp_su_h g_sm (-DSU_SMU,
// leaf for leaf and station for station the default g_h body whose su_gate run is bit-exact to the golden).
// Production parameters (SM_H 16, SM_LPH 16, S_RD 16, WS 2, NVMAX 40, LM 5, LA 4, SRL 2).  Two DUT shares (heads
// g = 2 TI, 2 TI + 1) get the same jobs as the stop over their serial row ports; the REAL lane / sum / root / divide
// arithmetic runs on both sides (no bench-made e / o events).  Jobs: SE (2 parameter rows, nv = 1..40 score vectors
// with random gaps and -Inf inactive lanes), each followed by an SO (5 parameter rows, 32-pair cos / sin stream,
// 32 P.V vectors) that divides by that SE's den.  Compared, in order, per head: every write row (address, mask, data:
// SE e rows; SO o rows = the stop's full row's masked half) and the final status.  Measured and checked CONSTANT
// (the static schedule): SE first e row after the last score row, SE e rows back to back, SO o row k after P.V row k,
// den after the job's LAST e row, per tree depth lt = clog2(nv) (the row sum's time levels).  Prints "SMS PASS ..." / "SMS FAIL ..." as its LAST line.
module tb_s81_su_sms;
    parameter integer MUT = 0, TI = 5, NJOB = 12, SEED = 1017;
    localparam integer SRL = 2;
    reg clk = 0, rst = 0;
    always #1 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ------------------------------------------------------------------ reference: the slab's SM stop
    reg dn_st = 0; reg [3:0] dn_kind = 0; reg [7:0] dn_jid = 0; reg [15:0] dn_v = 0; reg [2559:0] dn_p = 0;
    reg [1023:0] dn_d = 0;                                        // spine slots 2 TI, 2 TI + 1 (the stop's operand rows)
    wire s_v, p_v, c_v, cs_v; wire [6:0] c_nv; wire [2:0] c_lt; wire [31:0] c_scale; wire [63:0] c_sink; wire [4:0] cs_i;
    wire [63:0] cs_d; wire [1:0] w_v; wire [27:0] w_a; wire [31:0] w_m; wire [1023:0] w_d;
    wire t_fu, t_fo, t_al, t_den, t_rdy; wire [7:0] t_rj;
    wire [1:0] he_v, ho_v, hdn; wire [1023:0] he_d; wire [511:0] ho_d; wire [15:0] hf;
    ot_s81_su_smt #(.SM_H(16), .SM_LPH(16), .S_RD(16), .WS(2)) u_t (
        .clk(clk), .rst_in(rst), .cfg_ti(TI[3:0]), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid), .dn_v_i(dn_v),
        .dn_p_i(dn_p), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale), .c_sink(c_sink),
        .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .e_v_i(he_v[0]), .e_d_i(he_d), .o_v_i(ho_v[0]), .o_d_i(ho_d),
        .den_v_i(hdn[0]), .f_i(|hf),
        .o_v(w_v), .o_a(w_a), .o_m(w_m), .o_d(w_d), .o_fu(t_fu), .o_fo(t_fo), .o_alive(t_al), .o_den(t_den),
        .o_rdy(t_rdy), .o_rjid(t_rj));
    genvar h;
    generate for (h = 0; h < 2; h = h + 1) begin : g_r
        ot_s81_su_smh #(.SM_NVMAX(40), .LM(5), .LA(4), .SRL(SRL)) u_smh (
            .clk(clk), .rst_in(rst), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale),
            .c_sink(c_sink[32 * h +: 32]), .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .d(dn_d[512 * h +: 512]),
            .e_v(he_v[h]), .e_d(he_d[512 * h +: 512]), .o_v(ho_v[h]), .o_d(ho_d[256 * h +: 256]), .den_v(hdn[h]),
            .f(hf[8 * h +: 8]));
    end endgenerate

    // ------------------------------------------------------------------ DUT: two per-slice SM shares
    reg q_st = 0; reg [3:0] q_kind = 0; reg [7:0] q_jid = 0; reg r_v = 0, r_p = 0; reg [2:0] r_j = 0;
    reg [511:0] r_d0 = 0, r_d1 = 0;
    wire [1:0] qw_v, q_fu, q_fo, q_al, q_den; wire [27:0] qw_a; wire [31:0] qw_m; wire [1023:0] qw_d; wire [15:0] q_rj;
    generate for (h = 0; h < 2; h = h + 1) begin : g_q
        ot_s81_su_sms #(.MUT(MUT)) u_sms (
            .clk(clk), .rst_in(rst), .cfg_g(4'(2 * TI + h)), .j_st(q_st), .j_kind(q_kind), .j_jid(q_jid),
            .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(h ? r_d1 : r_d0),
            .w_v(qw_v[h]), .w_a(qw_a[14 * h +: 14]), .w_m(qw_m[16 * h +: 16]), .w_d(qw_d[512 * h +: 512]),
            .o_fu(q_fu[h]), .o_fo(q_fo[h]), .o_alive(q_al[h]), .o_den(q_den[h]), .o_rjid(q_rj[8 * h +: 8]));
    end endgenerate

    // ------------------------------------------------------------------ logs
    integer err = 0, nchk = 0;
    reg [1023:0] tq_w [$]; reg [1023:0] hq_w0 [$], hq_w1 [$];
    integer wc0 [$];                                              // DUT head-0 write cycles
    integer den_cyc [$];                                          // DUT head-0 o_den rising cycles
    reg pden = 0;
    integer k;
    always @(posedge clk) if (rst) begin
        for (k = 0; k < 2; k = k + 1) if (w_v[k]) tq_w.push_back({w_a[14 * k +: 14], w_m[16 * k +: 16], w_d[512 * k +: 512]});
        if (qw_v[0]) begin hq_w0.push_back({qw_a[13:0], qw_m[15:0], qw_d[511:0]}); wc0.push_back(cyc); end
        if (qw_v[1]) hq_w1.push_back({qw_a[27:14], qw_m[31:16], qw_d[1023:512]});
        if (q_den[0] && !pden) den_cyc.push_back(cyc);
        pden <= q_den[0];
    end

    // ------------------------------------------------------------------ stimulus
    function [31:0] rscore(input integer dummy);       // moderate fp32, both signs; ~1/16 the -Inf inactive sentinel
        begin
            if ($urandom % 16 == 0) rscore = 32'hff800000;
            else rscore = {1'($urandom), 8'(124 + $urandom % 8), 23'($urandom)};
        end
    endfunction
    function [31:0] rval(input integer dummy);
        rval = {1'($urandom), 8'(118 + $urandom % 14), 23'($urandom)};
    endfunction
    function [511:0] rrow(input integer sc);
        integer i; begin for (i = 0; i < 16; i = i + 1) rrow[32 * i +: 32] = sc ? rscore(0) : rval(0); end
    endfunction
    function [2:0] clog2(input integer n);
        integer v; begin clog2 = 0; v = 1; while (v < n) begin v = v * 2; clog2 = clog2 + 1; end end
    endfunction
    reg [511:0] prm [0:4];
    integer j, b, nv, np, kind, seed, jj;
    integer se_last [$];                                          // per SE: cycle the last score row is at the DUT pins
    integer se_nv [$];
    integer pv_cyc [$];                                           // per SO P.V row: cycle at the DUT pins
    integer kinds [$];
    reg [511:0] x0, x1;
    task tick; begin @(posedge clk); #0.1; end endtask
    task job(input integer kd, input integer nvv);
        begin
            np = (kd == 5) ? 5 : 2;
            for (b = 0; b < 5; b = b + 1) prm[b] = rrow(0);
            prm[0][13:0] = $urandom; prm[0][64 +: 7] = nvv; prm[0][128 +: 3] = clog2(nvv);
            prm[0][96 +: 32] = {1'b0, 8'(121 + $urandom % 4), 23'($urandom)};       // scale
            kinds.push_back(kd);
            dn_st = 1; dn_kind = kd; dn_jid = jj; q_st = 1; q_kind = kd; q_jid = jj; tick; jj = jj + 1;
            dn_st = 0; q_st = 0;
            dn_v = (16'd1 << np) - 16'd1;
            for (b = 0; b < 5; b = b + 1) dn_p[512 * b +: 512] = prm[b];
            r_v = 1; r_p = 1; r_j = 0; r_d0 = prm[0]; r_d1 = prm[0]; tick;
            dn_v = 0;
            for (b = 1; b < np; b = b + 1) begin r_j = b; r_d0 = prm[b]; r_d1 = prm[b]; tick; end
            r_v = 0; r_p = 0;
            if (kd == 5) repeat (40) tick;                         // the cos / sin stream (32 pairs) reaches the engines
            else repeat (2 + $urandom % 3) tick;
            for (b = 0; b < ((kd == 5) ? 32 : nvv); b = b + 1) begin
                x0 = rrow(kd == 4); x1 = rrow(kd == 4);
                dn_v = 16'hFFFF; dn_d = {x1, x0}; r_v = 1; r_p = 0; r_d0 = x0; r_d1 = x1;
                if (kd == 5) pv_cyc.push_back(cyc); else if (b == nvv - 1) begin se_last.push_back(cyc); se_nv.push_back(nvv); end
                tick;
                dn_v = 0; r_v = 0;
                if (kd == 4 && $urandom % 3 == 0) repeat (1 + $urandom % 2) tick;
            end
            repeat (400) tick;                                     // results drain before the next job
        end
    endtask
    initial begin
        seed = SEED; seed = $urandom(seed); jj = 0;
        repeat (4) tick;
        rst = 1;
        repeat (6) tick;
        for (j = 0; j < NJOB; j = j + 1) begin
            nv = (j == 0) ? 40 : (j == 1) ? 1 : 1 + $urandom % 40;
            job(4, nv);
            job(5, 0);
        end
        repeat (12) tick;
        check;
    end

    task fail(input [8*48-1:0] what, input integer i);
        begin if (err < 12) $display("SMS MISMATCH %0s at %0d", what, i); err = err + 1; end
    endtask
    integer l_se, l_so, nse, nso;
    integer l_dn [0:7];
    task check;
        integer i, q, w, jx, x, lt; reg [1023:0] t; reg [541:0] r0, r1;
        begin
            if (hq_w0.size() != hq_w1.size()) fail("head row counts", 0);
            nse = 0; nso = 0;
            for (i = 0; i < hq_w0.size() && i < hq_w1.size(); i = i + 1) begin
                t = hq_w0[i]; r0 = t[541:0]; t = hq_w1[i]; r1 = t[541:0];
                nchk = nchk + 1;
                if (r0[527:512] == 16'hFFFF) begin                 // SE: the stop writes head 0 then head 1 (slots 0, 1)
                    nse = nse + 1;
                    if (tq_w.size() < 2) fail("stop SE rows short", i);
                    else begin
                        t = tq_w.pop_front(); if (t[541:0] != r0) fail("SE row head 0", i);
                        t = tq_w.pop_front(); if (t[541:0] != r1) fail("SE row head 1", i);
                    end
                end else begin                                     // SO: one stop row = the two masked halves
                    nso = nso + 1;
                    if (tq_w.size() < 1) fail("stop SO rows short", i);
                    else begin
                        t = tq_w.pop_front();
                        if (r0[541:528] != t[541:528] || r1[541:528] != t[541:528]) fail("SO row addr", i);
                        if (r0[527:512] != 16'h00FF || r1[527:512] != 16'hFF00) fail("SO row mask", i);
                        if ({r1[511:256], r0[255:0]} != t[511:0]) fail("SO row data", i);
                    end
                end
            end
            if (tq_w.size() != 0) fail("stop rows left", tq_w.size());
            if (q_fu != {t_fu, t_fu} || q_fo != {t_fo, t_fo} || q_den != {t_den, t_den} || t_fo || t_fu)
                begin fail("status", 0); $display("status stop fu%b fo%b den%b share fu%b fo%b den%b", t_fu, t_fo, t_den, q_fu, q_fo, q_den); end
            // fixed latencies (DUT head 0): walk the jobs in order over the write cycles
            w = 0; l_se = -1; l_so = -1; for (i = 0; i < 8; i = i + 1) l_dn[i] = -1;
            for (jx = 0; jx < kinds.size(); jx = jx + 1) begin
                if (kinds[jx] == 4) begin
                    x = se_last.pop_front(); q = se_nv.pop_front();
                    if (w >= wc0.size()) fail("SE rows missing", jx);
                    else begin
                        if (l_se < 0) l_se = wc0[w] - x; else if (wc0[w] - x != l_se) fail("SE latency varies", jx);
                        for (i = 1; i < q; i = i + 1) if (wc0[w + i] != wc0[w] + i) fail("SE rows not back to back", jx);
                        x = wc0[w + q - 1];                           // the job's last e row
                        w = w + q;
                    end
                    if (den_cyc.size() == 0) fail("den missing", jx);
                    else begin
                        i = den_cyc.pop_front(); lt = clog2(q);
                        if (l_dn[lt] < 0) l_dn[lt] = i - x; else if (i - x != l_dn[lt]) fail("den latency varies", jx);
                    end
                end else begin
                    for (i = 0; i < 32; i = i + 1) begin
                        x = pv_cyc.pop_front();
                        if (w >= wc0.size()) begin fail("SO rows missing", jx); i = 32; end
                        else begin
                            if (l_so < 0) l_so = wc0[w] - x; else if (wc0[w] - x != l_so) fail("SO latency varies", jx);
                            w = w + 1;
                        end
                    end
                end
            end
            if (w != wc0.size()) fail("extra rows", wc0.size() - w);
            if (nchk < 400) fail("too few checks", nchk);
            $display("SMS stats MUT=%0d jobs=%0d se_rows=%0d so_rows=%0d checks=%0d", MUT, kinds.size(), nse, nso, nchk);
            $display("SMS latency (cycles at the share's pins): SE first e row = last score row + %0d, e rows back to back; SO o row k = P.V row k + %0d",
                     l_se, l_so);
            for (i = 0; i < 8; i = i + 1) if (l_dn[i] >= 0) $display("SMS latency: o_den = last e row + %0d at lt = clog2(nv) = %0d", l_dn[i], i);
            // the static schedule's published constants (lanes/S81U-2.md; the svc slice schedules its write window from them)
            if (l_se != 106) fail("SE latency != 106", l_se);
            if (l_so != 54) fail("SO latency != 54", l_so);
            for (i = 0; i < 8; i = i + 1) if (l_dn[i] >= 0 && l_dn[i] != 46 + 5 * i) fail("den latency != 46 + 5 lt", i);
            if (err == 0) $display("SMS PASS MUT=%0d checks=%0d", MUT, nchk);
            else $display("SMS FAIL MUT=%0d errors=%0d checks=%0d", MUT, err, nchk);
            $finish;
        end
    endtask
endmodule
