`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Latency-optimised combinational arithmetic for the hyper-connection
// Sinkhorn unit (ot_hdc_sinkhorn.sv).  Every module here is COMBINATIONAL and
// written structurally -- Kogge-Stone prefix carries, carry-save (3:2) trees,
// logarithmic shifters -- because the flow's generic `+` and `*` lower to
// ripple structures that dominate a chained datapath.  The integer
// specification of every operation is tools/gen_hdc_sinkhorn_recip_rom.py
// (add_pos, seed, xr_product, div), which that tool checks against IEEE
// binary32 and which the campaign checks this RTL against bit for bit.
//
//   ot_hdc_sk_cadd   compound adder: a+b and a+b+1 from one prefix tree
//   ot_hdc_sk_csa    carry-save reduction of N rows to two (row-level Wallace)
//   ot_hdc_sk_mul    unsigned multiplier: AND array (optionally truncated
//                    below a column) -> carry-save tree -> prefix adder
//   ot_hdc_sk_add    POSITIVE binary32 add, RNE, gradual underflow
//   ot_hdc_sk_seed   R ~ 1/T, one-sided (1/T - 2^-26 < R <= 1/T)
//   ot_hdc_sk_quot   correctly rounded X / T from the seed: candidate
//                    M' = floor(X' R) and two exact remainder signs
//   ot_hdc_sk_norm   normalise a (possibly subnormal) binary32 significand
// ---------------------------------------------------------------------------

// ---- compound Kogge-Stone adder ---------------------------------------------
module ot_hdc_sk_cadd #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W:0]   s0,     // a + b
    output wire [W:0]   s1      // a + b + 1
);
    localparam integer L = (W <= 1) ? 1 : $clog2(W);
    // level l holds generate/propagate of the span [i : i-2^l+1] (clipped at 0)
    genvar l, i;
    generate
        for (l = 0; l <= L; l = l + 1) begin : g_lv
            wire [W-1:0] g, p;
            if (l == 0) begin : g_init
                assign g = a & b;
                assign p = a ^ b;
            end else begin : g_step
                for (i = 0; i < W; i = i + 1) begin : g_bit
                    if (i >= (1 << (l - 1))) begin : g_op
                        assign g[i] = g_lv[l-1].g[i] | (g_lv[l-1].p[i] & g_lv[l-1].g[i-(1<<(l-1))]);
                        assign p[i] = g_lv[l-1].p[i] & g_lv[l-1].p[i-(1<<(l-1))];
                    end else begin : g_pass
                        assign g[i] = g_lv[l-1].g[i];
                        assign p[i] = g_lv[l-1].p[i];
                    end
                end
            end
        end
    endgenerate
    wire [W-1:0] gg = g_lv[L].g;       // generate of bits [i:0]
    wire [W-1:0] pp = g_lv[L].p;       // propagate of bits [i:0]
    wire [W-1:0] hp = a ^ b;
    wire [W-1:0] c0 = {gg[W-2:0], 1'b0};
    wire [W-1:0] c1 = {gg[W-2:0] | pp[W-2:0], 1'b1};
    assign s0 = {gg[W-1], hp ^ c0};
    assign s1 = {gg[W-1] | pp[W-1], hp ^ c1};
endmodule

// ---- carry-save reduction: N rows of W bits to two, s + c == sum (mod 2^W) ----
module ot_hdc_sk_csa #(
    parameter integer N = 3,
    parameter integer W = 8
) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s,
    output wire [W-1:0]   c
);
    function automatic integer nxt(input integer n);
        nxt = (n <= 2) ? n : 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer cnt(input integer l);
        integer k, n;
        begin
            n = N;
            for (k = 0; k < 64; k = k + 1) if (k < l) n = nxt(n);
            cnt = n;
        end
    endfunction
    function automatic integer levels(input integer dummy);
        integer k, n, lv;
        begin
            n = N; lv = 0;
            for (k = 0; k < 64; k = k + 1) if (n > 2) begin n = nxt(n); lv = lv + 1; end
            levels = lv;
        end
    endfunction
    localparam integer LV = levels(0);
    genvar l, t, r;
    generate
        for (l = 0; l <= LV; l = l + 1) begin : g_lv
            wire [N*W-1:0] v;          // level l: cnt(l) rows, the rest zero
            if (l == 0) begin : g_init
                assign v = rows;
            end else begin : g_step
                localparam integer NT = cnt(l - 1);
                localparam integer NG = NT / 3;
                for (t = 0; t < NG; t = t + 1) begin : g_fa
                    wire [W-1:0] x = g_lv[l-1].v[(3*t)*W +: W];
                    wire [W-1:0] y = g_lv[l-1].v[(3*t + 1)*W +: W];
                    wire [W-1:0] z = g_lv[l-1].v[(3*t + 2)*W +: W];
                    wire [W-1:0] maj = (x & y) | (x & z) | (y & z);
                    assign v[(2*t)*W +: W] = x ^ y ^ z;
                    assign v[(2*t + 1)*W +: W] = {maj[W-2:0], 1'b0};
                end
                for (r = 3 * NG; r < NT; r = r + 1) begin : g_pass
                    assign v[(2*NG + (r - 3*NG))*W +: W] = g_lv[l-1].v[r*W +: W];
                end
                if (N > cnt(l)) begin : g_fill
                    assign v[cnt(l)*W +: (N - cnt(l))*W] = {((N - cnt(l))*W){1'b0}};
                end
            end
        end
    endgenerate
    assign s = g_lv[LV].v[0 +: W];
    generate
        if (cnt(LV) >= 2) begin : g_two
            assign c = g_lv[LV].v[W +: W];
        end else begin : g_one
            assign c = {W{1'b0}};
        end
    endgenerate
endmodule

// ---- unsigned multiplier; partial-product bits in columns below DROP are not built ----
module ot_hdc_sk_mul #(
    parameter integer WA = 24,
    parameter integer WB = 24,
    parameter integer DROP = 0
) (
    input  wire [WA-1:0]    a,
    input  wire [WB-1:0]    b,
    output wire [WA+WB-1:0] p
);
    localparam integer W = WA + WB;
    wire [WB*W-1:0] rows;
    genvar j;
    generate
        for (j = 0; j < WB; j = j + 1) begin : g_pp
            wire [W-1:0] full = b[j] ? ({{WB{1'b0}}, a} << j) : {W{1'b0}};
            if (DROP > 0) begin : g_tr
                assign rows[j*W +: W] = {full[W-1:DROP], {DROP{1'b0}}};
            end else begin : g_full
                assign rows[j*W +: W] = full;
            end
        end
    endgenerate
    wire [W-1:0] s, c;
    wire [W:0]   s0, s1;
    ot_hdc_sk_csa #(.N(WB), .W(W)) u_tree (.rows(rows), .s(s), .c(c));
    ot_hdc_sk_cadd #(.W(W)) u_cpa (.a(s), .b(c), .s0(s0), .s1(s1));
    assign p = s0[W-1:0];
endmodule

// ---- POSITIVE binary32 addition, RNE, gradual underflow -------------------------
// Operands in the unit's unpacked form: an EFFECTIVE exponent (a zero field
// reads as 1) and the 24-bit significand with its hidden bit explicit (0 for a
// subnormal or zero).  Positive operands cannot cancel, so there is no
// leading-zero path: the exact sum S = big + small * 2^-d needs at most one
// right shift, and because the big significand has no fraction bits the
// fraction of S is exactly the shifted-out part of the small one:
//   no carry: result S (+1 if guard & (sticky | lsb));  guard = small bit d-1
//   carry:    result S >> 1 (+1 if S[0] & (any shifted-out | S[1]))
// S and S + 1 come from ONE compound prefix adder and the round only selects.
// `ovf`: the exponent reached 255 (the caller fails closed).
//
// CHAINING.  Operand a is the running sum of a chain; its exponent arrives as
// ea + ua, where ea is known early and the increment ua (the previous add's
// carry/round-up) is the LAST bit that previous add resolves.  Everything that
// depends only on exponents and on the early operand b -- both exponent
// differences, the order, b's alignment shift and its sticky bits -- is formed
// for BOTH values of ua and selected when ua arrives, so a chained add waits
// only for a's significand, not for an exponent subtraction.  The outputs are
// in the same form: eg + up (eg early, up late).  ua = 0 for a first add.
module ot_hdc_sk_add (
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
    wire [8:0] ea1 = {1'b0, ea} + 9'd1;
    wire [7:0] ea_c [0:1];
    assign ea_c[0] = ea;
    assign ea_c[1] = ea1[7:0];
    wire [1:0]  age_c;
    wire [7:0]  dba_c [0:1];
    wire [24:0] shb_c [0:1];
    wire [1:0]  bany_c, bst_c;
    genvar u, i;
    generate
        for (u = 0; u < 2; u = u + 1) begin : g_u
            wire [8:0] ab0, ab1, ba0, ba1;
            ot_hdc_sk_cadd #(.W(8)) u_dab (.a(ea_c[u]), .b(~eb), .s0(ab0), .s1(ab1));   // ea - eb
            ot_hdc_sk_cadd #(.W(8)) u_dba (.a(eb), .b(~ea_c[u]), .s0(ba0), .s1(ba1));   // eb - ea
            assign age_c[u] = ab1[8];
            assign dba_c[u] = ba1[7:0];                  // valid when b > a
            // b aligned under a, and its shifted-out bits (all early); dab valid when a >= b
            assign shb_c[u] = (ab1[7:0] >= 8'd25) ? 25'd0 : ({mb, 1'b0} >> ab1[4:0]);
            wire [23:0] mk_any, mk_st;
            for (i = 0; i < 24; i = i + 1) begin : g_mk
                assign mk_any[i] = (ab1[7:0] > i);
                assign mk_st[i]  = (ab1[7:0] > i + 1);
            end
            assign bany_c[u] = |(mb & mk_any);
            assign bst_c[u]  = |(mb & mk_st);
        end
    endgenerate
    wire        a_ge  = ua ? age_c[1] : age_c[0];
    wire        swap  = !a_ge;                   // b strictly larger exponent
    wire [7:0]  dba   = ua ? dba_c[1] : dba_c[0];
    wire [24:0] shb   = ua ? shb_c[1] : shb_c[0];
    wire        b_any = ua ? bany_c[1] : bany_c[0];
    wire        b_st  = ua ? bst_c[1] : bst_c[0];

    // a aligned under b (a is the late operand)
    wire [24:0] sha = (dba >= 8'd25) ? 25'd0 : ({ma, 1'b0} >> dba[4:0]);
    wire [23:0] mk_a_any, mk_a_st;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_mka
            assign mk_a_any[i] = (dba > i);
            assign mk_a_st[i]  = (dba > i + 1);
        end
    endgenerate
    wire a_any = |(ma & mk_a_any), a_st = |(ma & mk_a_st);

    wire [7:0]  eA   = ua ? ea1[7:0] : ea;
    assign eg        = swap ? eb : eA;
    wire [23:0] mg   = swap ? mb : ma;
    wire [23:0] ahi  = swap ? sha[24:1] : shb[24:1];
    wire        g    = swap ? sha[0] : shb[0];
    wire        any  = swap ? a_any : b_any;
    wire        st   = swap ? a_st : b_st;

    wire [24:0] s0, s1;
    ot_hdc_sk_cadd #(.W(24)) u_sum (.a(mg), .b(ahi), .s0(s0), .s1(s1));
    wire carry = s0[24];
    wire rnc = g & (st | s0[0]);
    wire rc  = s0[0] & (any | s0[1]);
    wire [23:0] mp = carry ? (rc ? s1[24:1] : s0[24:1]) : (rnc ? s1[23:0] : s0[23:0]);
    wire ovm = !carry & rnc & s1[24];          // S = 2^24 - 1 rounded up to 2^24
    wire [8:0] eg1 = {1'b0, eg} + 9'd1;
    assign up  = carry | ovm;
    assign e   = up ? eg1[7:0] : eg;
    assign m   = {mp[23] | ovm, mp[22:0]};
    assign ovf = up & (eg1[7:0] == 8'hFF);
endmodule

// ---- reciprocal seed: 1/T - 2^-26 < R <= 1/T, R in units of 2^-28 ---------------
// T = tm * 2^-23 in [1, 2).  One carry-save tree forms, exactly, at 2^-46:
//   S = c0 2^14 - c1 (h - 2^13) 2 + c2 sq(dm >> 4) - 2^18
// (h = tm[13:0], dm its one's-complement distance from the segment centre,
// sq the square of dm's 16-wide bucket centre / 2^12, from a ROM), and
// R = S[46:18].  The generator proves the bound for all 2^23 significands.
module ot_hdc_sk_seed (
    input  wire [23:0] tm,
    output wire [28:0] r
);
    wire [32:0] c0;
    wire [22:0] c1;
    wire [12:0] c2;
    ot_hdc_sk_recip_rom u_rom (.i(tm[22:14]), .c0(c0), .c1(c1), .c2(c2));
    wire [13:0] h  = tm[13:0];
    wire [12:0] dm = h[13] ? h[12:0] : ~h[12:0];
    // the C2 term's square is read, not computed: a 512-entry ROM on dm's top 9 bits,
    // looked up in parallel with the coefficients (bucket-centre square; proved in the bound)
    wire [13:0] sq;
    ot_hdc_sk_sq_rom u_sq (.dmh(dm[12:4]), .sq(sq));

    localparam integer W = 48;
    localparam integer NR = 2 + 14 + 14 + 1;
    wire [NR*W-1:0] rows;
    assign rows[0*W +: W] = {{(W-47){1'b0}}, c0, 14'd0};
    assign rows[1*W +: W] = {{(W-37){1'b0}}, c1, 14'd0};
    genvar j;
    generate
        for (j = 0; j < 14; j = j + 1) begin : g_c1
            // - c1 * h_j * 2^(j+1), negated as ~x (+1 folded into the constant row)
            wire [W-1:0] v = h[j] ? ({{(W-23){1'b0}}, c1} << (j + 1)) : {W{1'b0}};
            assign rows[(2 + j)*W +: W] = ~v;
        end
        for (j = 0; j < 14; j = j + 1) begin : g_c2
            assign rows[(16 + j)*W +: W] = sq[j] ? ({{(W-13){1'b0}}, c2} << j) : {W{1'b0}};
        end
    endgenerate
    // 14 negation carries minus the bias 2^18, modulo 2^48
    assign rows[30*W +: W] = 48'd14 - 48'd262144;
    wire [W-1:0] s, c;
    wire [W:0]   s0, s1;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(s), .c(c));
    ot_hdc_sk_cadd #(.W(W)) u_cpa (.a(s), .b(c), .s0(s0), .s1(s1));
    assign r = s0[46:18];
endmodule

// ---- correctly rounded quotient X / T from the seed ------------------------------
// xm, tm: normalised significands (bit 23 set); xe, te: unbiased exponents;
// xz: X is zero.  X' = X or 2X so that q' = X'/T is in [1, 2); E is q's
// unbiased exponent.  M' = floor(q'_approx 2^23) is M or M - 1 (M = floor of the
// exact q' 2^23), so with the two exact remainders
//   r1 = X' 2^24 - (2M'+1) T   (the sign of q' - (M' + 1/2) 2^-23)
//   r2 = r1 - 2T               (the sign of q' - (M' + 3/2) 2^-23)
// the correctly rounded significand is M' + [r1 > 0] + [r2 > 0] (a zero
// remainder is an exact tie: to even).  r1 lies in [-T, 3T), so the remainders
// are formed modulo 2^27 from the LOW columns of M' T only.
// SUBN = 1 adds gradual underflow: a result below 2^-126 is the same
// construction on the coarser grid 2^(-149): M'_s = M' >> s, X' 2^(24-s).
// SUBN = 0 is for operands whose quotient is known normal; an exponent outside
// [1, 254] raises `range` instead.
module ot_hdc_sk_quot #(
    parameter integer SUBN = 0
) (
    input  wire [23:0]       xm,
    input  wire signed [9:0] xe,
    input  wire              xz,
    input  wire [23:0]       tm,
    input  wire signed [9:0] te,
    input  wire [28:0]       r,
    output wire [30:0]       y,
    output wire              range
);
    // X < T (both normalised): the quotient's leading bit
    wire [24:0] cmp_s0, cmp_s1;
    ot_hdc_sk_cadd #(.W(24)) u_cmp (.a(xm), .b(~tm), .s0(cmp_s0), .s1(cmp_s1));
    wire lt = !cmp_s1[24];
    wire signed [10:0] e0 = $signed({xe[9], xe}) - $signed({te[9], te});
    wire signed [10:0] e1 = e0 - 11'sd1;
    wire signed [10:0] E  = lt ? e1 : e0;

    // M' = floor(X R 2^(lt-28) ... ) : the truncated product, taken one bit lower when X < T
    wire [52:0] pr;
    ot_hdc_sk_mul #(.WA(24), .WB(29), .DROP(20)) u_xr (.a(xm), .b(r), .p(pr));
    wire [23:0] mp = lt ? pr[50:27] : pr[51:28];
    wire [24:0] xp = lt ? {xm, 1'b0} : {1'b0, xm};

    // grid shift for a subnormal result
    wire [4:0]  s;
    wire        zero_s;
    generate
        if (SUBN != 0) begin : g_sub
            wire signed [10:0] sfull = -11'sd126 - E;
            assign zero_s = (sfull > 11'sd24);
            assign s = (sfull <= 11'sd0) ? 5'd0 : (zero_s ? 5'd0 : sfull[4:0]);
        end else begin : g_nosub
            assign zero_s = 1'b0;
            assign s = 5'd0;
        end
    endgenerate
    wire [23:0] ms = mp >> s;
    wire [26:0] xs = {2'b00, xp} << (5'd24 - s);          // X' 2^(24-s) mod 2^27

    // r1 = xs - T - sum_j T_j (ms << (j+1))  (mod 2^27), subtrahends negated as ~v (+1 each)
    localparam integer W = 27;
    localparam integer NR = 24 + 3;
    wire [NR*W-1:0] rows;
    genvar j;
    generate
        for (j = 0; j < 24; j = j + 1) begin : g_pp
            wire [W-1:0] v = tm[j] ? ({3'b000, ms} << (j + 1)) : {W{1'b0}};
            assign rows[j*W +: W] = ~v;
        end
    endgenerate
    assign rows[24*W +: W] = xs;
    assign rows[25*W +: W] = ~{3'b000, tm};
    assign rows[26*W +: W] = 27'd25;                         // 24 + 1 negation carries
    wire [W-1:0] ts, tc;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(ts), .c(tc));
    // r2 = r1 - 2T = ts + tc + ~(2T) + 1
    wire [W-1:0] t2 = ~{2'b00, tm, 1'b0};
    wire [W-1:0] u_s = ts ^ tc ^ t2;
    wire [W-1:0] u_maj = (ts & tc) | (ts & t2) | (tc & t2);
    wire [W-1:0] u_cs = {u_maj[W-2:0], 1'b0};
    wire [W:0] a1, a1p, a2, a2p;
    ot_hdc_sk_cadd #(.W(W)) u_r1 (.a(ts), .b(tc), .s0(a1), .s1(a1p));
    ot_hdc_sk_cadd #(.W(W)) u_r2 (.a(u_s), .b(u_cs), .s0(a2), .s1(a2p));
    wire neg1 = a1[W-1];
    wire neg2 = a2p[W-1];
    // zero tests without the carry chain: A + B + cin == 0 (mod 2^W) iff A ^ B == {(A | B) << 1, cin}
    wire z1 = ((ts ^ tc) == {(ts[W-2:0] | tc[W-2:0]), 1'b0});
    wire z2 = ((u_s ^ u_cs) == {(u_s[W-2:0] | u_cs[W-2:0]), 1'b1});
    wire inc1 = (!neg1 & !z1) | (z1 & ms[0]);
    wire inc2 = (!neg2 & !z2) | (z2 & !ms[0]);

    // M' + {0, 1, 2}
    wire [24:0] m1_s0, m1_s1;
    ot_hdc_sk_cadd #(.W(24)) u_inc (.a(ms), .b(24'd0), .s0(m1_s0), .s1(m1_s1));
    wire [23:0] m2_s0, m2_s1;
    ot_hdc_sk_cadd #(.W(23)) u_inc2 (.a(ms[23:1]), .b(23'd0), .s0(m2_s0), .s1(m2_s1));
    wire [24:0] mplus1 = m1_s1;
    wire [24:0] mplus2 = {m2_s1, ms[0]};
    wire [24:0] mf = inc2 ? mplus2 : (inc1 ? mplus1 : {1'b0, ms});

    wire ovm = mf[24];                                       // rounded up to 2^24
    wire signed [10:0] eb = E + 11'sd127;
    wire signed [10:0] eb1 = E + 11'sd128;
    wire sub = (SUBN != 0) && (s != 5'd0);
    wire [7:0] field = sub ? {7'd0, mf[23]} : (ovm ? eb1[7:0] : eb[7:0]);
    wire bad_hi = !sub && (ovm ? (eb1 > 11'sd254) : (eb > 11'sd254));
    wire bad_lo = (SUBN == 0) && (eb < 11'sd1);
    wire zero = xz | zero_s;
    assign y = zero ? 31'd0 : {field, ovm ? 23'd0 : mf[22:0]};
    assign range = !zero & (bad_hi | bad_lo);
endmodule

// ---- normalise a binary32 magnitude: significand to [2^23, 2^24), unbiased exponent ----
module ot_hdc_sk_norm (
    input  wire [30:0]       x,
    output reg  [23:0]       m,
    output reg signed [9:0]  e,
    output wire              z
);
    wire [7:0]  f  = x[30:23];
    wire [23:0] mm = {f != 8'd0, x[22:0]};
    assign z = (mm == 24'd0);
    integer k;
    reg [4:0] lz;
    always @* begin
        lz = 5'd0;
        for (k = 0; k < 24; k = k + 1) if (mm[k]) lz = 5'd23 - k[4:0];
        m = mm << lz;
        e = $signed({2'b00, (f == 8'd0) ? 8'd1 : f}) - 10'sd127 - $signed({5'd0, lz});
    end
endmodule
