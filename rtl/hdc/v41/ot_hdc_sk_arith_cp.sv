`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// FAM-HBM-B/HCTAIL 10-21 (RELEASE_TREE H.STA.BLK.1): CUT (registered-stage) forms of the Sinkhorn step arithmetic of
// rtl/hdc/v41/ot_hdc_sk_arith.sv, for ot_hdc_sinkhorn_cp.  Same function bit for bit: every module below is the
// ot_hdc_sk_* module of the same suffix with free-running pipeline registers ("cuts") inserted at fixed points of its
// combinational cone; CUT = 0 removes every cut (the original combinational module).
//
// HELD-INPUT PIPELINE.  The Sinkhorn is a dependent recurrence (step k+1 reads all of step k), so the step datapath is
// never overlapped: its state registers change on one enable edge and are HELD for STEP_CYC core edges.  A cut on any
// net of a cone whose inputs are held settles one edge after its own inputs settle, so a cone with at most D cuts on
// any input->output path delivers its exact combinational value D edges after its inputs change.  The caller captures
// the result only on its next enable edge (STEP_CYC >= D + 1), and every path between cuts is an ordinary
// single-period core-clock path: no multicycle constraint, no added control, no side-signal delay lines (a value that
// skips a cut is simply held).  Cuts carry no reset and no enable.
// Cut points (estimated ASAP7 logic levels per segment <= ~16, i.e. <= ~600 ps at TT):
//   ot_hdc_skc_add   P after the exponent precompute (both ua candidates: differences, b shift, sticky masks),
//                    M after the swap / a-shift (before the 24-bit sum), X on the outputs (e, m, up, ovf); the
//                    early exponent eg leaves after M, so the next add's precompute overlaps this add's sum segment.
//   ot_hdc_skc_seed  S1 after the two ROMs, S2 after the 31-row carry-save tree, S3 on r.
//   ot_hdc_skc_quot  Q1 after the 29-row carry-save tree of X'R, Q2 after the product select / subnormal shift
//                    (ms, xs), Q3 after the 27-row remainder tree; QO (optional) on the outputs y / range.
// ---------------------------------------------------------------------------
module ot_hdc_skc_cut #(
    parameter integer W  = 1,
    parameter integer EN = 1
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (EN != 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk) r <= d;
        assign q = r;
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

module ot_hdc_skc_add #(
    parameter integer CUT = 1
) (
    input  wire        clk,
    input  wire [7:0]  ea,
    input  wire        ua,
    input  wire [23:0] ma,
    input  wire [7:0]  eb,
    input  wire [23:0] mb,
    output wire [7:0]  eg,
    output wire        up,
    output wire [7:0]  e,
    output wire [23:0] m,
    output wire        ovf
);
    // ---- precompute (both ua candidates) --------------------------------------------- cut P
    wire [8:0] ea1 = {1'b0, ea} + 9'd1;
    wire [7:0] ea_c [0:1];
    assign ea_c[0] = ea;
    assign ea_c[1] = ea1[7:0];
    wire [1:0]  age_n;
    wire [7:0]  dba_n [0:1];
    wire [24:0] shb_n [0:1];
    wire [1:0]  bany_n, bst_n;
    genvar u, i;
    generate
        for (u = 0; u < 2; u = u + 1) begin : g_u
            wire [8:0] ab0, ab1, ba0, ba1;
            ot_hdc_sk_cadd #(.W(8)) u_dab (.a(ea_c[u]), .b(~eb), .s0(ab0), .s1(ab1));   // ea - eb
            ot_hdc_sk_cadd #(.W(8)) u_dba (.a(eb), .b(~ea_c[u]), .s0(ba0), .s1(ba1));   // eb - ea
            assign age_n[u] = ab1[8];
            assign dba_n[u] = ba1[7:0];
            assign shb_n[u] = (ab1[7:0] >= 8'd25) ? 25'd0 : ({mb, 1'b0} >> ab1[4:0]);
            wire [23:0] mk_any, mk_st;
            for (i = 0; i < 24; i = i + 1) begin : g_mk
                assign mk_any[i] = (ab1[7:0] > i);
                assign mk_st[i]  = (ab1[7:0] > i + 1);
            end
            assign bany_n[u] = |(mb & mk_any);
            assign bst_n[u]  = |(mb & mk_st);
        end
    endgenerate
    wire [1:0]  age_c;
    wire [7:0]  dba_c0, dba_c1, ea_p, ea1_p;
    wire [24:0] shb_c0, shb_c1;
    wire [1:0]  bany_c, bst_c;
    ot_hdc_skc_cut #(.W(2 + 16 + 50 + 4 + 16), .EN(CUT)) u_cp (.clk(clk),
        .d({age_n, dba_n[0], dba_n[1], shb_n[0], shb_n[1], bany_n, bst_n, ea, ea1[7:0]}),
        .q({age_c, dba_c0, dba_c1, shb_c0, shb_c1, bany_c, bst_c, ea_p, ea1_p}));
    // ---- swap, a shift ----------------------------------------------------------------- cut M
    wire        a_ge  = ua ? age_c[1] : age_c[0];
    wire        swap  = !a_ge;
    wire [7:0]  dba   = ua ? dba_c1 : dba_c0;
    wire [24:0] shb   = ua ? shb_c1 : shb_c0;
    wire        b_any = ua ? bany_c[1] : bany_c[0];
    wire        b_st  = ua ? bst_c[1] : bst_c[0];
    wire [24:0] sha = (dba >= 8'd25) ? 25'd0 : ({ma, 1'b0} >> dba[4:0]);
    wire [23:0] mk_a_any, mk_a_st;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_mka
            assign mk_a_any[i] = (dba > i);
            assign mk_a_st[i]  = (dba > i + 1);
        end
    endgenerate
    wire a_any = |(ma & mk_a_any), a_st = |(ma & mk_a_st);
    wire [7:0]  eA    = ua ? ea1_p : ea_p;
    wire [7:0]  eg_n  = swap ? eb : eA;
    wire [23:0] mg_n  = swap ? mb : ma;
    wire [23:0] ahi_n = swap ? sha[24:1] : shb[24:1];
    wire        g_n   = swap ? sha[0] : shb[0];
    wire        any_n = swap ? a_any : b_any;
    wire        st_n  = swap ? a_st : b_st;
    wire [7:0]  egm;
    wire [23:0] mg, ahi;
    wire        g, any, st;
    ot_hdc_skc_cut #(.W(8 + 24 + 24 + 3), .EN(CUT)) u_cm (.clk(clk), .d({eg_n, mg_n, ahi_n, g_n, any_n, st_n}),
        .q({egm, mg, ahi, g, any, st}));
    assign eg = egm;
    // ---- 24-bit sum, round, exponent ----------------------------------------------------- cut X
    wire [24:0] s0, s1;
    ot_hdc_sk_cadd #(.W(24)) u_sum (.a(mg), .b(ahi), .s0(s0), .s1(s1));
    wire carry = s0[24];
    wire rnc = g & (st | s0[0]);
    wire rc  = s0[0] & (any | s0[1]);
    wire [23:0] mp = carry ? (rc ? s1[24:1] : s0[24:1]) : (rnc ? s1[23:0] : s0[23:0]);
    wire ovm = !carry & rnc & s1[24];
    wire [8:0] eg1 = {1'b0, egm} + 9'd1;
    wire up_n = carry | ovm;
    wire [7:0]  e_n = up_n ? eg1[7:0] : egm;
    wire [23:0] m_n = {mp[23] | ovm, mp[22:0]};
    wire ovf_n = up_n & (eg1[7:0] == 8'hFF);
    ot_hdc_skc_cut #(.W(1 + 8 + 24 + 1), .EN(CUT)) u_cx (.clk(clk), .d({up_n, e_n, m_n, ovf_n}), .q({up, e, m, ovf}));
endmodule

module ot_hdc_skc_seed #(
    parameter integer CUT = 1
) (
    input  wire        clk,
    input  wire [23:0] tm,
    output wire [28:0] r
);
    wire [32:0] c0_n;
    wire [22:0] c1_n;
    wire [12:0] c2_n;
    ot_hdc_sk_recip_rom u_rom (.i(tm[22:14]), .c0(c0_n), .c1(c1_n), .c2(c2_n));
    wire [12:0] dm = tm[13] ? tm[12:0] : ~tm[12:0];
    wire [13:0] sq_n;
    ot_hdc_sk_sq_rom u_sq (.dmh(dm[12:4]), .sq(sq_n));
    wire [32:0] c0; wire [22:0] c1; wire [12:0] c2; wire [13:0] sq, h;
    ot_hdc_skc_cut #(.W(33 + 23 + 13 + 14 + 14), .EN(CUT)) u_s1 (.clk(clk), .d({c0_n, c1_n, c2_n, sq_n, tm[13:0]}),
        .q({c0, c1, c2, sq, h}));
    localparam integer W = 48;
    localparam integer NR = 2 + 14 + 14 + 1;
    wire [NR*W-1:0] rows;
    assign rows[0*W +: W] = {{(W-47){1'b0}}, c0, 14'd0};
    assign rows[1*W +: W] = {{(W-37){1'b0}}, c1, 14'd0};
    genvar j;
    generate
        for (j = 0; j < 14; j = j + 1) begin : g_c1
            wire [W-1:0] v = h[j] ? ({{(W-23){1'b0}}, c1} << (j + 1)) : {W{1'b0}};
            assign rows[(2 + j)*W +: W] = ~v;
        end
        for (j = 0; j < 14; j = j + 1) begin : g_c2
            assign rows[(16 + j)*W +: W] = sq[j] ? ({{(W-13){1'b0}}, c2} << j) : {W{1'b0}};
        end
    endgenerate
    assign rows[30*W +: W] = 48'd14 - 48'd262144;
    wire [W-1:0] s_n, c_n, s, c;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(s_n), .c(c_n));
    ot_hdc_skc_cut #(.W(2 * W), .EN(CUT)) u_s2 (.clk(clk), .d({s_n, c_n}), .q({s, c}));
    wire [W:0] s0, s1;
    ot_hdc_sk_cadd #(.W(W)) u_cpa (.a(s), .b(c), .s0(s0), .s1(s1));
    ot_hdc_skc_cut #(.W(29), .EN(CUT)) u_s3 (.clk(clk), .d(s0[46:18]), .q(r));
endmodule

module ot_hdc_skc_quot #(
    parameter integer SUBN = 0,
    parameter integer CUT  = 1,
    parameter integer CUTO = 0                               // QO: register y / range as well
) (
    input  wire              clk,
    input  wire [23:0]       xm,
    input  wire signed [9:0] xe,
    input  wire              xz,
    input  wire [23:0]       tm,
    input  wire signed [9:0] te,
    input  wire [28:0]       r,
    output wire [30:0]       y,
    output wire              range
);
    wire [24:0] cmp_s0, cmp_s1;
    ot_hdc_sk_cadd #(.W(24)) u_cmp (.a(xm), .b(~tm), .s0(cmp_s0), .s1(cmp_s1));
    wire lt = !cmp_s1[24];
    wire signed [10:0] e0 = $signed({xe[9], xe}) - $signed({te[9], te});
    wire signed [10:0] e1 = e0 - 11'sd1;
    wire signed [10:0] E_n = lt ? e1 : e0;
    // X' R: 29-row carry-save tree (DROP 20, as ot_hdc_sk_mul) -> Q1 -> carry-propagate add
    localparam integer MW = 24 + 29;
    wire [29*MW-1:0] prow;
    genvar j;
    generate
        for (j = 0; j < 29; j = j + 1) begin : g_pp
            wire [MW-1:0] full = r[j] ? ({{29{1'b0}}, xm} << j) : {MW{1'b0}};
            assign prow[j*MW +: MW] = {full[MW-1:20], 20'd0};
        end
    endgenerate
    wire [MW-1:0] ps_n, pc_n, ps, pc;
    ot_hdc_sk_csa #(.N(29), .W(MW)) u_ptree (.rows(prow), .s(ps_n), .c(pc_n));
    ot_hdc_skc_cut #(.W(2 * MW), .EN(CUT)) u_q1 (.clk(clk), .d({ps_n, pc_n}), .q({ps, pc}));
    wire [MW:0] pr0, pr1;
    ot_hdc_sk_cadd #(.W(MW)) u_pcpa (.a(ps), .b(pc), .s0(pr0), .s1(pr1));
    wire [52:0] pr = pr0[MW-1:0];
    wire [23:0] mp = lt ? pr[50:27] : pr[51:28];
    wire [24:0] xp = lt ? {xm, 1'b0} : {1'b0, xm};
    wire [4:0]  s_n;
    wire        zero_s_n;
    generate
        if (SUBN != 0) begin : g_sub
            wire signed [10:0] sfull = -11'sd126 - E_n;
            assign zero_s_n = (sfull > 11'sd24);
            assign s_n = (sfull <= 11'sd0) ? 5'd0 : (zero_s_n ? 5'd0 : sfull[4:0]);
        end else begin : g_nosub
            assign zero_s_n = 1'b0;
            assign s_n = 5'd0;
        end
    endgenerate
    wire [23:0] ms_n = mp >> s_n;
    wire [26:0] xs_n = {2'b00, xp} << (5'd24 - s_n);
    wire [23:0] ms; wire [26:0] xs; wire signed [10:0] E; wire [4:0] s; wire zero_s;
    ot_hdc_skc_cut #(.W(24 + 27 + 11 + 5 + 1), .EN(CUT)) u_q2 (.clk(clk), .d({ms_n, xs_n, E_n, s_n, zero_s_n}),
        .q({ms, xs, E, s, zero_s}));
    // remainder signs: 27-row tree -> Q3
    localparam integer W = 27;
    localparam integer NR = 24 + 3;
    wire [NR*W-1:0] rows;
    generate
        for (j = 0; j < 24; j = j + 1) begin : g_rr
            wire [W-1:0] v = tm[j] ? ({3'b000, ms} << (j + 1)) : {W{1'b0}};
            assign rows[j*W +: W] = ~v;
        end
    endgenerate
    assign rows[24*W +: W] = xs;
    assign rows[25*W +: W] = ~{3'b000, tm};
    assign rows[26*W +: W] = 27'd25;
    wire [W-1:0] ts_n, tc_n, ts, tc;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(ts_n), .c(tc_n));
    ot_hdc_skc_cut #(.W(2 * W), .EN(CUT)) u_q3 (.clk(clk), .d({ts_n, tc_n}), .q({ts, tc}));
    wire [W-1:0] t2 = ~{2'b00, tm, 1'b0};
    wire [W-1:0] u_s = ts ^ tc ^ t2;
    wire [W-1:0] u_maj = (ts & tc) | (ts & t2) | (tc & t2);
    wire [W-1:0] u_cs = {u_maj[W-2:0], 1'b0};
    wire [W:0] a1, a1p, a2, a2p;
    ot_hdc_sk_cadd #(.W(W)) u_r1 (.a(ts), .b(tc), .s0(a1), .s1(a1p));
    ot_hdc_sk_cadd #(.W(W)) u_r2 (.a(u_s), .b(u_cs), .s0(a2), .s1(a2p));
    wire neg1 = a1[W-1];
    wire neg2 = a2p[W-1];
    wire z1 = ((ts ^ tc) == {(ts[W-2:0] | tc[W-2:0]), 1'b0});
    wire z2 = ((u_s ^ u_cs) == {(u_s[W-2:0] | u_cs[W-2:0]), 1'b1});
    wire inc1 = (!neg1 & !z1) | (z1 & ms[0]);
    wire inc2 = (!neg2 & !z2) | (z2 & !ms[0]);
    wire [24:0] m1_s0, m1_s1;
    ot_hdc_sk_cadd #(.W(24)) u_inc (.a(ms), .b(24'd0), .s0(m1_s0), .s1(m1_s1));
    wire [23:0] m2_s0, m2_s1;
    ot_hdc_sk_cadd #(.W(23)) u_inc2 (.a(ms[23:1]), .b(23'd0), .s0(m2_s0), .s1(m2_s1));
    wire [24:0] mplus1 = m1_s1;
    wire [24:0] mplus2 = {m2_s1, ms[0]};
    wire [24:0] mf = inc2 ? mplus2 : (inc1 ? mplus1 : {1'b0, ms});
    wire ovm = mf[24];
    wire signed [10:0] eb = E + 11'sd127;
    wire signed [10:0] eb1 = E + 11'sd128;
    wire sub = (SUBN != 0) && (s != 5'd0);
    wire [7:0] field = sub ? {7'd0, mf[23]} : (ovm ? eb1[7:0] : eb[7:0]);
    wire bad_hi = !sub && (ovm ? (eb1 > 11'sd254) : (eb > 11'sd254));
    wire bad_lo = (SUBN == 0) && (eb < 11'sd1);
    wire zero = xz | zero_s;
    wire [30:0] y_n = zero ? 31'd0 : {field, ovm ? 23'd0 : mf[22:0]};
    wire range_n = !zero & (bad_hi | bad_lo);
    ot_hdc_skc_cut #(.W(32), .EN(CUT != 0 && CUTO != 0)) u_qo (.clk(clk), .d({y_n, range_n}), .q({y, range}));
endmodule
