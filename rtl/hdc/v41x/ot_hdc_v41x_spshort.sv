`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SHORT sqrt(softplus) for the V4.1 stream unit's side pipe (serial-chain clock
// domain, 0.9 GHz): the same bits as ot_hdc_v41x_softplus (DEPTH 162) in fewer
// cycles.  Not one rounding of the golden (tools/hdc_golden_v41.softplus /
// log1p_unit / sqrt, tools/hdc_golden.exp) is removed, merged or reordered;
// what changes is how much work each rounding takes and where the registers
// sit.  The modules:
//
//   ot_hdc_hstep #(K, CUT) y = RN(RN(a*b) + K), the Horner step, two roundings,
//                          LATENCY 4 + CUT (a multiply 3 + an add 3 = 6 before)
//   ot_hdc_v41x_exp_s      exp(x), DEPTH 33 + 7 PCUT (ot_hdc_v41x_exp: 49), every input
//   ot_hdc_fp32_mul_x2     y = 2 * RN(a*b) (DOUBLE 1; the two roundings of
//                          mul(mul(u,p),2)) or RN(a*b) (DOUBLE 0), LATENCY 3 + CUT
//   ot_hdc_addpos2         RN(a + b) for operands of one sign, LATENCY 2
//   ot_hdc_fsqrt4          correctly rounded sqrt, radix 4, DEPTH 16 (31 before)
//   ot_hdc_v41x_spdiv      u = t / RN(t + 2) for t in [0, 1], DEPTH 19 from the
//                          exp's last Horner result (3 + 19 + the exp's
//                          exponent stage before)
//   ot_hdc_v41x_softplus_s softplus and sqrt(softplus), DEPTH 107 + 17 PCUT (162 before)
//
// CUT / PCUT = 1 puts a register between the product's carry-save tree and its
// 48-bit prefix add (ot_hdc_mul24_csa): the routed block at 1.111 ns SS was
// limited there (v1, PCUT 0 without keep-level adders: 685 MHz).  Every wide
// add is a keep-level prefix adder (rtl/hdc/ot_hdc_prefix.sv).
// WHY THE ROUNDINGS STAY THE SAME.  Each of these units returns the correctly
// rounded (RNE, canonical +0) value of the same exact quantity as the chain it
// replaces, and a correctly rounded value is unique, so the bits are the same.
// Where a unit relies on its operands' range (hstep: |RN(a*b)| <= K/2; spdiv:
// 0 <= t <= 1; exp_s: the Cody-Waite difference x - n*ln2_hi is exact) it CHECKS
// the range and raises `fault` outside it instead of returning a wrong value.
// tools/w11_softplus_short.py runs every 32-bit input through the old and the
// new softplus, exp and sqrt, and the Horner step on biased random operands
// against ot_hdc_qmul -> ot_hdc_qadd (results/rtl/w11_softplus_short.json).
// ---------------------------------------------------------------------------

// The last four carry-save levels of ot_hdc_mul24_sum (8 rows -> sum and carry), without its
// prefix add: a register may sit between them (the 1.111 ns SS cut).
module ot_hdc_mul24_csa (
    input  wire [48*8-1:0] rows,
    output wire [95:0]     cs      // {carry, sum}
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(rows[144*i +: 48], rows[144*i + 48 +: 48], rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign cs = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
endmodule

// ---------------------------------------------------------------------------
// Horner step y = RN(RN(a*b) + K), K a positive normal constant, LATENCY 4 + CUT.
//   F1  the multiplier's stage 1 (decode, normalise, partial products, three
//       carry-save levels) -- ot_hdc_fp32_mul_fast unchanged
//   F1b (CUT = 1) the tree's last four carry-save levels, registered
//   F2  the rest of the tree and the prefix final add; from the exponent sum
//       alone, for either leading-bit position: the product's distance d below
//       K's exponent, the alignment shift and its sticky mask
//   F3  the product rounded to 24 bits (the first rounding), then aligned to
//       K's frame (3 guard bits, the rest jammed into the lowest)
//   F4  K +- the aligned product, one-bit renormalise either way, the second
//       rounding, encode
// The range: |RN(a*b)| <= K/2 (the product's floor exponent at least 2 below
// K's), so the sum lies in [K/2, 3K/2]: its exponent is K's -1, 0 or +1, and a
// subtraction cancels at most one bit.  A product at least 30 binades below K
// (d >= 30; every subnormal product) is below K's quarter ulp and the result
// is K, as it is for a zero product.  Outside the range (d < 2), or with a
// nonfinite operand, the step FAILS CLOSED: fault, y = 0.  The softplus and
// exp Horner steps never leave it (their products are at most 0.12 K and
// 0.42 K).
// ---------------------------------------------------------------------------
module ot_hdc_hstep #(parameter [31:0] K = 32'h3F800000, parameter integer CUT = 1) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam [7:0]  KF = K[30:23];
    localparam [23:0] MK = {1'b1, K[22:0]};
    localparam signed [11:0] EK = $signed({4'd0, KF}) - 12'sd127;

    wire [4+CUT:0] vd;
    ot_hdc_vline #(.D(4 + CUT)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[4 + CUT];

    // -- F1: the multiplier's stage 1 -----------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32 u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32 u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    wire signed [11:0] a_power = (a_field == 8'd0) ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0) ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(a_power), .b(b_power), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows u_rows (.a(a_raw << a_lz[4:0]), .b(b_raw << b_lz[4:0]), .rows(rows));

    reg        s1_nf, s1_zero, s1_sign;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk) begin
        s1_nf <= nonfinite; s1_zero <= zero; s1_sign <= a[31] ^ b[31];
        s1_rows <= rows; s1_power <= power;
    end

    // -- F1b (CUT = 1): the tree's last four carry-save levels (8 rows -> 2), a register before the prefix add
    wire [95:0] cs;
    ot_hdc_mul24_csa u_cs (.rows(s1_rows), .cs(cs));
    wire        s1b_nf, s1b_zero, s1b_sign;
    wire [95:0] s1b_cs;
    wire [11:0] s1b_pw;
    wire signed [11:0] s1b_power = s1b_pw;
    ot_hdc_delay #(.W(111), .D(CUT)) d_cut (clk, rst_n, {s1_nf, s1_zero, s1_sign, cs, s1_power},
                                            {s1b_nf, s1b_zero, s1b_sign, s1b_cs, s1b_pw});

    // -- F2: product; distance below K for either leading bit ----------------
    wire [47:0] prod;
    wire prod_c;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(s1b_cs[47:0]), .b(s1b_cs[95:48]), .cin(1'b0), .s(prod), .cout(prod_c));
    //: The product's floor exponent is power + 47 (bit 47 set) or power + 46.
    //: d = EK - floor; the rounded product M' (25 bits) lands in K's frame
    //: (K = MK << 3) as 2 M' >> (d - 2).
    wire signed [11:0] d47 = EK - (s1b_power + 12'sd47);
    wire signed [11:0] d46 = EK - (s1b_power + 12'sd46);
    function automatic [4:0] shamt(input signed [11:0] d);
        shamt = (d > 12'sd29) ? 5'd27 : (d < 12'sd2) ? 5'd0 : d[4:0] - 5'd2;
    endfunction
    function automatic [25:0] lostmask(input [4:0] sh);
        integer k;
        for (k = 0; k < 26; k = k + 1) lostmask[k] = (k < sh);
    endfunction
    wire [4:0] sh47 = shamt(d47), sh46 = shamt(d46);

    reg        s2_nf, s2_zero, s2_sign, s2_tiny47, s2_tiny46, s2_oor47, s2_oor46;
    reg [47:0] s2_prod;
    reg [4:0]  s2_sh47, s2_sh46;
    reg [25:0] s2_m47, s2_m46;
    always @(posedge clk) begin
        s2_nf <= s1b_nf; s2_zero <= s1b_zero; s2_sign <= s1b_sign;
        s2_prod <= prod;
        s2_tiny47 <= d47 > 12'sd29; s2_tiny46 <= d46 > 12'sd29;
        s2_oor47 <= d47 < 12'sd2;   s2_oor46 <= d46 < 12'sd2;
        s2_sh47 <= sh47; s2_sh46 <= sh46;
        s2_m47 <= lostmask(sh47); s2_m46 <= lostmask(sh46);
    end

    // -- F3: first rounding (normal product), align to K's frame -------------
    wire top = s2_prod[47];
    wire [23:0] main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire rb = top ? s2_prod[23] : s2_prod[22];
    wire st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [23:0] mr;
    wire mr_c;
    ot_hdc_inc_k #(.W(24)) u_rp (.a(main), .inc(rb && (st || main[0])), .y(mr), .co(mr_c));
    wire [25:0] w2 = {mr_c, mr, 1'b0};                 // 2 M'
    wire [4:0]  sh = top ? s2_sh47 : s2_sh46;
    wire [25:0] msk = top ? s2_m47 : s2_m46;
    wire [25:0] al = w2 >> sh;
    wire        jam = |(w2 & msk);
    wire [27:0] pf = {2'b00, al[25:1], al[0] | jam};
    wire tiny = top ? s2_tiny47 : s2_tiny46;
    wire oor  = top ? s2_oor47 : s2_oor46;

    reg        s3_neg, s3_k, s3_f;
    reg [27:0] s3_pf;
    always @(posedge clk) begin
        s3_neg <= s2_sign;
        s3_pf  <= s2_sign ? ~pf : pf;                  // K - P = K + ~P + 1
        s3_k   <= s2_zero || tiny;
        s3_f   <= s2_nf || (!s2_zero && oor);
    end

    // -- F4: K +- P, renormalise, second rounding, encode --------------------
    wire [27:0] sum;
    wire sum_c;
    ot_hdc_ksadd_k #(.W(28)) u_add (.a({1'b0, MK, 3'b000}), .b(s3_pf), .cin(s3_neg), .s(sum), .cout(sum_c));
    //: val: [26:3] significand, [2] guard, [1:0] sticky.
    wire [26:0] val = sum[27] ? {sum[27:2], sum[1] | sum[0]} : sum[26] ? sum[26:0] : {sum[25:0], 1'b0};
    wire [7:0]  fld = sum[27] ? (KF + 8'd1) : sum[26] ? KF : (KF - 8'd1);
    wire inc = val[2] && ((|val[1:0]) || val[3]);
    wire [23:0] rs;
    wire rs_c;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(val[26:3]), .inc(inc), .y(rs), .co(rs_c));
    wire [31:0] code = {1'b0, fld + {7'd0, rs_c}, rs_c ? 23'd0 : rs[22:0]};
    always @(posedge clk) begin
        fault <= vd[3 + CUT] && s3_f;
        y <= s3_f ? 32'd0 : s3_k ? K : code;
    end
endmodule

// ---------------------------------------------------------------------------
// y = 2 * RN(a*b): ot_hdc_fp32_mul_fast with the doubling of mul(., 2.0) folded
// into its encode.  Doubling a binary32 value is exact unless it overflows: a
// normal result's field grows by one (field = floor + 128, overflow above floor
// 126), and a subnormal result's code, the integer rnd with value rnd*2^-149,
// becomes the code of 2 rnd, which is the 31-bit integer 2 rnd (rnd <= 2^23, so
// 2 rnd <= 2^24 is a subnormal or the code of 2^-125 or below).  Faults as
// ot_hdc_qmul (an overflow of the doubled value is the second multiply's).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_x2 #(parameter integer DOUBLE = 1, parameter integer CUT = 1) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    // -- stage 1 (ot_hdc_fp32_mul_fast) --
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32 u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32 u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    wire signed [11:0] a_power = (a_field == 8'd0) ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0) ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(a_power), .b(b_power), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows u_rows (.a(a_raw << a_lz[4:0]), .b(b_raw << b_lz[4:0]), .rows(rows));
    reg        s1_v, s1_byp, s1_nf, s1_sign;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) if (!rst_n) s1_v <= 1'b0; else s1_v <= v;
    always @(posedge clk) begin
        s1_byp <= nonfinite || zero; s1_nf <= nonfinite; s1_sign <= a[31] ^ b[31];
        s1_rows <= rows; s1_power <= power;
    end
    // -- stage 1b (CUT = 1): the tree's last four carry-save levels, a register before the prefix add --
    wire [95:0] cs;
    ot_hdc_mul24_csa u_cs (.rows(s1_rows), .cs(cs));
    wire        s1b_v, s1b_byp, s1b_nf, s1b_sign;
    wire [95:0] s1b_cs;
    wire [11:0] s1b_pw;
    wire signed [11:0] s1b_power = s1b_pw;
    ot_hdc_delay #(.W(111), .D(CUT)) d_cut (clk, rst_n, {s1_byp, s1_nf, s1_sign, cs, s1_power},
                                            {s1b_byp, s1b_nf, s1b_sign, s1b_cs, s1b_pw});
    ot_hdc_delay #(.W(1), .D(CUT), .RESET(1)) d_cutv (clk, rst_n, s1_v, s1b_v);
    // -- stage 2 (ot_hdc_fp32_mul_fast) --
    wire [47:0] prod;
    wire prod_c;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(s1b_cs[47:0]), .b(s1b_cs[95:48]), .cin(1'b0), .s(prod), .cout(prod_c));
    wire signed [11:0] fl47 = s1b_power + 12'sd47;
    wire signed [11:0] fl46 = s1b_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1b_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    reg        s2_v, s2_byp, s2_nf, s2_sign, s2_sub47, s2_sub46;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= s1b_v;
    always @(posedge clk) begin
        s2_byp <= s1b_byp; s2_nf <= s1b_nf; s2_sign <= s1b_sign;
        s2_prod <= prod;
        s2_sub47 <= fl47 < -12'sd126;
        s2_sub46 <= fl46 < -12'sd126;
        s2_fl47 <= fl47; s2_fl46 <= fl46;
        s2_sh <= shc; s2_mr <= m_round; s2_ms <= m_sticky;
    end
    // -- stage 3: as ot_hdc_fp32_mul_fast, encoding 2 * the rounded product --
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(main), .inc(rb && (st || main[0])), .y(rnd), .co(rnd_c));
    wire carry = !is_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = fl + {11'd0, carry};
    wire over = !is_sub && (floor_ > (DOUBLE ? 12'sd126 : 12'sd127));
    wire [7:0] field = floor_[7:0] + (DOUBLE ? 8'd128 : 8'd127);
    wire sub_carry = is_sub && rnd[23];
    wire [31:0] code = !is_sub ? {s2_sign, field, man[22:0]} :
                       DOUBLE ? {s2_sign, 6'd0, rnd, 1'b0} :
                       (sub_carry ? {s2_sign, 8'h01, 23'd0} : {s2_sign, 8'h00, rnd[22:0]});
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin
            if (s2_byp) begin y <= 32'd0; fault <= s2_v && s2_nf; end
            else if (over) begin y <= 32'd0; fault <= s2_v; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; fault <= 1'b0; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// RN(a + b) for two operands of the same sign (or a zero), LATENCY 2: the fast
// adder's stage 1 (ot_hdc_fp32_add_fast: bypass, one-compare swap, jam
// alignment), then the addition, its one-bit renormalise, the rounding and the
// encode in one stage -- an effective addition never cancels, so the
// leading-zero normalise of the fast adder's stage 2 is not needed.  Operands
// of opposite signs (both nonzero) FAIL CLOSED, as a nonfinite operand or an
// overflow does (y = 0).  Zero results are +0.
// ---------------------------------------------------------------------------
module ot_hdc_addpos2 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire mixed = (a[31] ^ b[31]) && !a_zero && !b_zero;
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire swap = !cmp_c;
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(a_man, dba);
    wire [27:0] small_b = jam28(b_man, dab);

    reg        s1_v, s1_byp, s1_bad, s1_sign;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) if (!rst_n) s1_v <= 1'b0; else s1_v <= v;
    always @(posedge clk) begin
        s1_byp <= bypass || mixed;
        s1_bad <= nonfinite || mixed;
        s1_code <= bypass_code;
        s1_sign <= swap ? b[31] : a[31];
        s1_exp <= swap ? b_exp : a_exp;
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? small_a : small_b;
    end

    wire [27:0] sum;
    wire sum_c;
    ot_hdc_ksadd_k #(.W(28)) u_sum (.a({1'b0, s1_big, 3'b000}), .b(s1_small), .cin(1'b0), .s(sum), .cout(sum_c));
    wire carry = sum[27];
    wire [26:0] val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire inc = val[2] && ((|val[1:0]) || val[3]);
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(val[26:3]), .inc(inc), .y(rnd), .co(rnd_c));
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, s1_exp} + {8'd0, carry} + {8'd0, rnd_c};
    //: A sum of two subnormals stays subnormal unless it reaches bit 23.
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {s1_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin
            if (s1_byp) begin y <= s1_bad ? 32'd0 : s1_code; fault <= s1_v && s1_bad; end
            else if (over) begin y <= 32'd0; fault <= s1_v; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; fault <= 1'b0; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// exp(x), DEPTH 33 + 7 PCUT, bit-identical to ot_hdc_v41x_exp (DEPTH 49) for every x.
// The same operations as tools/hdc_golden.exp:
//   xc = clamp(x, -87, 88); t = RN(xc*log2e); n = rint-to-even(t);
//   r = RN(RN(xc - n*LN2_HI) - RN(n*LN2_LO)); p = Horner (6 steps); y = p + n<<23.
// What is shorter:
//   * t is formed from x itself, beside the clamp: a clamped x has a fixed n
//     (+127 at 88, -126 at -87), and t only feeds n.  (A clamped x may be
//     nonfinite; its multiply's refusal is ignored because its t is.)
//   * r is ONE exact difference rounded once.  n*LN2_HI is exact and so is
//     xc - n*LN2_HI (Cody-Waite: |xc - n*LN2_HI| < 2^-1 and both terms are on
//     the 2^-25 grid when n != 0, so the difference has at most 24 bits), so
//     the golden's second add rounds the exact value xc - n*LN2_HI - RN(n*LN2_LO).
//     All three terms are on the 2^-43 grid and below 2^50 in magnitude, and xc,
//     n*LN2_HI and RN(n*LN2_LO) share n's sign, so |r| = | |xc| - T(|n|) | with
//     T(m) = m*LN2_HI + RN(m*LN2_LO) (a 128-entry table, exact integers of
//     2^-43): one subtraction, a normalise, a rounding.  n = 0 gives r = xc
//     (canonical +0), as the golden's adds of -0 do.
//   * the six Horner steps are ot_hdc_hstep (4 + PCUT cycles each, not 6).
// Stages (PCUT 0; PCUT 1 adds one to t and one to each Horner step): 1 clamp |
// 1-3 t = x*log2e | 2 |xc| on the 2^-43 grid | 4 n | 5 T(|n|) | 6 |xc| - T |
// 7 normalise | 8 round (r) | 9-32 Horner | 33 exponent.
// p_pre / n_pre are the last Horner result and n at depth T_P, for a consumer
// that folds the exponent step into its own first stage (ot_hdc_v41x_spdiv).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_exp_s #(parameter integer PCUT = 1) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire [31:0] p_pre,
    output wire [8:0]  n_pre,
    output wire        fault
);
    localparam integer LH = 4 + PCUT;           // Horner step latency
    localparam integer T_T = 3 + PCUT;          // t registered
    localparam integer T_R = T_T + 5;           // r registered (9)
    localparam integer T_P = T_R + 6 * LH;      // 39
    localparam integer DEPTH = T_P + 1;         // 40 (33 at PCUT = 0)
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction
    //: T(m) * 2^43 = m*LN2_HI*2^43 + RN(m*LN2_LO)*2^43, exact integers, from the
    //: golden's own binary32 products (the ot_hdc_v41x_exp table's entries).
    function automatic [49:0] ln2_fix(input [6:0] m);
        case (m)
            7'd0  : ln2_fix = 50'h0000000000000;   // n = +-0
            7'd1  : ln2_fix = 50'h0058B90BFBE8E;   // n = +-1
            7'd2  : ln2_fix = 50'h00B17217F7D1C;   // n = +-2
            7'd3  : ln2_fix = 50'h010A2B23F3BA8;   // n = +-3
            7'd4  : ln2_fix = 50'h0162E42FEFA38;   // n = +-4
            7'd5  : ln2_fix = 50'h01BB9D3BEB8C8;   // n = +-5
            7'd6  : ln2_fix = 50'h02145647E7750;   // n = +-6
            7'd7  : ln2_fix = 50'h026D0F53E35E0;   // n = +-7
            7'd8  : ln2_fix = 50'h02C5C85FDF470;   // n = +-8
            7'd9  : ln2_fix = 50'h031E816BDB300;   // n = +-9
            7'd10 : ln2_fix = 50'h03773A77D7190;   // n = +-10
            7'd11 : ln2_fix = 50'h03CFF383D3020;   // n = +-11
            7'd12 : ln2_fix = 50'h0428AC8FCEEA0;   // n = +-12
            7'd13 : ln2_fix = 50'h0481659BCAD30;   // n = +-13
            7'd14 : ln2_fix = 50'h04DA1EA7C6BC0;   // n = +-14
            7'd15 : ln2_fix = 50'h0532D7B3C2A50;   // n = +-15
            7'd16 : ln2_fix = 50'h058B90BFBE8E0;   // n = +-16
            7'd17 : ln2_fix = 50'h05E449CBBA770;   // n = +-17
            7'd18 : ln2_fix = 50'h063D02D7B6600;   // n = +-18
            7'd19 : ln2_fix = 50'h0695BBE3B2490;   // n = +-19
            7'd20 : ln2_fix = 50'h06EE74EFAE320;   // n = +-20
            7'd21 : ln2_fix = 50'h07472DFBAA1A0;   // n = +-21
            7'd22 : ln2_fix = 50'h079FE707A6040;   // n = +-22
            7'd23 : ln2_fix = 50'h07F8A013A1EC0;   // n = +-23
            7'd24 : ln2_fix = 50'h0851591F9DD40;   // n = +-24
            7'd25 : ln2_fix = 50'h08AA122B99BE0;   // n = +-25
            7'd26 : ln2_fix = 50'h0902CB3795A60;   // n = +-26
            7'd27 : ln2_fix = 50'h095B844391900;   // n = +-27
            7'd28 : ln2_fix = 50'h09B43D4F8D780;   // n = +-28
            7'd29 : ln2_fix = 50'h0A0CF65B89620;   // n = +-29
            7'd30 : ln2_fix = 50'h0A65AF67854A0;   // n = +-30
            7'd31 : ln2_fix = 50'h0ABE687381340;   // n = +-31
            7'd32 : ln2_fix = 50'h0B17217F7D1C0;   // n = +-32
            7'd33 : ln2_fix = 50'h0B6FDA8B79040;   // n = +-33
            7'd34 : ln2_fix = 50'h0BC8939774EE0;   // n = +-34
            7'd35 : ln2_fix = 50'h0C214CA370D60;   // n = +-35
            7'd36 : ln2_fix = 50'h0C7A05AF6CC00;   // n = +-36
            7'd37 : ln2_fix = 50'h0CD2BEBB68A80;   // n = +-37
            7'd38 : ln2_fix = 50'h0D2B77C764920;   // n = +-38
            7'd39 : ln2_fix = 50'h0D8430D3607A0;   // n = +-39
            7'd40 : ln2_fix = 50'h0DDCE9DF5C640;   // n = +-40
            7'd41 : ln2_fix = 50'h0E35A2EB584C0;   // n = +-41
            7'd42 : ln2_fix = 50'h0E8E5BF754340;   // n = +-42
            7'd43 : ln2_fix = 50'h0EE71503501C0;   // n = +-43
            7'd44 : ln2_fix = 50'h0F3FCE0F4C080;   // n = +-44
            7'd45 : ln2_fix = 50'h0F98871B47F00;   // n = +-45
            7'd46 : ln2_fix = 50'h0FF1402743D80;   // n = +-46
            7'd47 : ln2_fix = 50'h1049F9333FC00;   // n = +-47
            7'd48 : ln2_fix = 50'h10A2B23F3BA80;   // n = +-48
            7'd49 : ln2_fix = 50'h10FB6B4B37940;   // n = +-49
            7'd50 : ln2_fix = 50'h11542457337C0;   // n = +-50
            7'd51 : ln2_fix = 50'h11ACDD632F640;   // n = +-51
            7'd52 : ln2_fix = 50'h1205966F2B4C0;   // n = +-52
            7'd53 : ln2_fix = 50'h125E4F7B27380;   // n = +-53
            7'd54 : ln2_fix = 50'h12B7088723200;   // n = +-54
            7'd55 : ln2_fix = 50'h130FC1931F080;   // n = +-55
            7'd56 : ln2_fix = 50'h13687A9F1AF00;   // n = +-56
            7'd57 : ln2_fix = 50'h13C133AB16D80;   // n = +-57
            7'd58 : ln2_fix = 50'h1419ECB712C40;   // n = +-58
            7'd59 : ln2_fix = 50'h1472A5C30EAC0;   // n = +-59
            7'd60 : ln2_fix = 50'h14CB5ECF0A940;   // n = +-60
            7'd61 : ln2_fix = 50'h152417DB067C0;   // n = +-61
            7'd62 : ln2_fix = 50'h157CD0E702680;   // n = +-62
            7'd63 : ln2_fix = 50'h15D589F2FE500;   // n = +-63
            7'd64 : ln2_fix = 50'h162E42FEFA380;   // n = +-64
            7'd65 : ln2_fix = 50'h1686FC0AF6200;   // n = +-65
            7'd66 : ln2_fix = 50'h16DFB516F2080;   // n = +-66
            7'd67 : ln2_fix = 50'h17386E22EDF40;   // n = +-67
            7'd68 : ln2_fix = 50'h1791272EE9DC0;   // n = +-68
            7'd69 : ln2_fix = 50'h17E9E03AE5C40;   // n = +-69
            7'd70 : ln2_fix = 50'h18429946E1AC0;   // n = +-70
            7'd71 : ln2_fix = 50'h189B5252DD980;   // n = +-71
            7'd72 : ln2_fix = 50'h18F40B5ED9800;   // n = +-72
            7'd73 : ln2_fix = 50'h194CC46AD5680;   // n = +-73
            7'd74 : ln2_fix = 50'h19A57D76D1500;   // n = +-74
            7'd75 : ln2_fix = 50'h19FE3682CD380;   // n = +-75
            7'd76 : ln2_fix = 50'h1A56EF8EC9240;   // n = +-76
            7'd77 : ln2_fix = 50'h1AAFA89AC50C0;   // n = +-77
            7'd78 : ln2_fix = 50'h1B0861A6C0F40;   // n = +-78
            7'd79 : ln2_fix = 50'h1B611AB2BCDC0;   // n = +-79
            7'd80 : ln2_fix = 50'h1BB9D3BEB8C80;   // n = +-80
            7'd81 : ln2_fix = 50'h1C128CCAB4B00;   // n = +-81
            7'd82 : ln2_fix = 50'h1C6B45D6B0980;   // n = +-82
            7'd83 : ln2_fix = 50'h1CC3FEE2AC800;   // n = +-83
            7'd84 : ln2_fix = 50'h1D1CB7EEA8680;   // n = +-84
            7'd85 : ln2_fix = 50'h1D7570FAA4540;   // n = +-85
            7'd86 : ln2_fix = 50'h1DCE2A06A0380;   // n = +-86
            7'd87 : ln2_fix = 50'h1E26E3129C280;   // n = +-87
            7'd88 : ln2_fix = 50'h1E7F9C1E98100;   // n = +-88
            7'd89 : ln2_fix = 50'h1ED8552A93F80;   // n = +-89
            7'd90 : ln2_fix = 50'h1F310E368FE00;   // n = +-90
            7'd91 : ln2_fix = 50'h1F89C7428BC80;   // n = +-91
            7'd92 : ln2_fix = 50'h1FE2804E87B00;   // n = +-92
            7'd93 : ln2_fix = 50'h203B395A83980;   // n = +-93
            7'd94 : ln2_fix = 50'h2093F2667F800;   // n = +-94
            7'd95 : ln2_fix = 50'h20ECAB727B680;   // n = +-95
            7'd96 : ln2_fix = 50'h2145647E77500;   // n = +-96
            7'd97 : ln2_fix = 50'h219E1D8A73400;   // n = +-97
            7'd98 : ln2_fix = 50'h21F6D6966F280;   // n = +-98
            7'd99 : ln2_fix = 50'h224F8FA26B100;   // n = +-99
            7'd100: ln2_fix = 50'h22A848AE66F80;   // n = +-100
            7'd101: ln2_fix = 50'h230101BA62E00;   // n = +-101
            7'd102: ln2_fix = 50'h2359BAC65EC80;   // n = +-102
            7'd103: ln2_fix = 50'h23B273D25AB00;   // n = +-103
            7'd104: ln2_fix = 50'h240B2CDE56980;   // n = +-104
            7'd105: ln2_fix = 50'h2463E5EA52800;   // n = +-105
            7'd106: ln2_fix = 50'h24BC9EF64E700;   // n = +-106
            7'd107: ln2_fix = 50'h251558024A580;   // n = +-107
            7'd108: ln2_fix = 50'h256E110E46400;   // n = +-108
            7'd109: ln2_fix = 50'h25C6CA1A42280;   // n = +-109
            7'd110: ln2_fix = 50'h261F83263E100;   // n = +-110
            7'd111: ln2_fix = 50'h26783C3239F80;   // n = +-111
            7'd112: ln2_fix = 50'h26D0F53E35E00;   // n = +-112
            7'd113: ln2_fix = 50'h2729AE4A31C80;   // n = +-113
            7'd114: ln2_fix = 50'h278267562DB00;   // n = +-114
            7'd115: ln2_fix = 50'h27DB206229A00;   // n = +-115
            7'd116: ln2_fix = 50'h2833D96E25880;   // n = +-116
            7'd117: ln2_fix = 50'h288C927A21700;   // n = +-117
            7'd118: ln2_fix = 50'h28E54B861D580;   // n = +-118
            7'd119: ln2_fix = 50'h293E049219400;   // n = +-119
            7'd120: ln2_fix = 50'h2996BD9E15280;   // n = +-120
            7'd121: ln2_fix = 50'h29EF76AA11100;   // n = +-121
            7'd122: ln2_fix = 50'h2A482FB60CF80;   // n = +-122
            7'd123: ln2_fix = 50'h2AA0E8C208E00;   // n = +-123
            7'd124: ln2_fix = 50'h2AF9A1CE04D00;   // n = +-124
            7'd125: ln2_fix = 50'h2B525ADA00B80;   // n = +-125
            7'd126: ln2_fix = 50'h2BAB13E5FCA00;   // n = +-126
            7'd127: ln2_fix = 50'h2C03CCF1F8880;   // n = +-127
            default: ln2_fix = 50'd0;
        endcase
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp; t = x * log2e starts on x itself
    reg [31:0] xc;
    reg        c_hi, c_lo;
    always @(posedge clk) begin
        c_hi <= !x[31] && x[30:0] > K_MAX[30:0];
        c_lo <= x[31] && x[30:0] > K_MINM[30:0];
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end
    wire [31:0] t;
    wire        t_f;
    ot_hdc_fp32_mul_x2 #(.DOUBLE(0), .CUT(PCUT)) m_t (.clk(clk), .rst_n(rst_n), .v(v), .a(x), .b(K_LOG2E), .y(t), .fault(t_f));

    // depth 2: |xc| * 2^43 (valid when n != 0, which needs |xc| >= 2^-2)
    wire [7:0]  xe = xc[30:23];
    wire [7:0]  xsh = xe - 8'd107;
    reg  [49:0] afix;
    reg         x_small;
    always @(posedge clk) begin
        afix <= (xe < 8'd107) ? 50'd0 : ({26'd0, 1'b1, xc[22:0]} << xsh[4:0]);
        x_small <= xe < 8'd125;
    end
    wire [31:0] xc3;
    wire        chi3, clo3;
    ot_hdc_delay #(.W(32), .D(T_T - 1)) d_xc3 (clk, rst_n, xc, xc3);
    ot_hdc_delay #(.W(2), .D(T_T - 1)) d_c3 (clk, rst_n, {c_hi, c_lo}, {chi3, clo3});

    // depth 4: n = rint-to-even(t) (ot_hdc_v41x_exp's integer step), or the clamp's
    wire [23:0] tm = {1'b1, t[22:0]};
    wire [7:0]  te = t[30:23];
    wire [4:0]  tsh = 5'd23 - (te[4:0] - 5'd31);
    wire [23:0] tip = tm >> tsh;
    wire [4:0]  trb = tsh - 5'd1;
    wire        thalf = tm[trb];
    wire        tstk = |(tm & ~({24{1'b1}} << trb));
    wire [7:0]  tmag = (te < 8'd126) ? 8'd0 : (tip[7:0] + {7'd0, thalf && (tstk || tip[0])});
    reg  [8:0]  nint;
    reg  [6:0]  nmag;
    reg         nneg, nnz, f_t;
    always @(posedge clk) begin
        if (chi3)      begin nint <= 9'd127;  nmag <= 7'd127; nneg <= 1'b0; nnz <= 1'b1; end
        else if (clo3) begin nint <= -9'd126; nmag <= 7'd126; nneg <= 1'b1; nnz <= 1'b1; end
        else begin
            nint <= t[31] ? -{1'b0, tmag} : {1'b0, tmag};
            nmag <= tmag[6:0]; nneg <= t[31] && (tmag != 8'd0); nnz <= (tmag != 8'd0);
        end
        f_t <= vd[T_T] && !chi3 && !clo3 && (t_f || tmag[7]);
    end
    wire [31:0] xc4;
    wire [49:0] afix4;
    wire        xsm4;
    ot_hdc_delay #(.W(32), .D(1)) d_xc4 (clk, rst_n, xc3, xc4);
    ot_hdc_delay #(.W(51), .D(T_T - 1)) d_a4 (clk, rst_n, {x_small, afix}, {xsm4, afix4});

    // depth 5: T(|n|)
    reg [49:0] tfix, afix5;
    reg [31:0] xc5;
    reg        nnz5, xsm5;
    always @(posedge clk) begin
        tfix <= ln2_fix(nmag); afix5 <= afix4; xc5 <= xc4; nnz5 <= nnz; xsm5 <= xsm4;
    end

    // depth 6: | |xc| - T |, both orders at once
    wire [51-1:0] dab;
    wire dab_c;
    ot_hdc_ksadd_k #(.W(51)) u_dab (.a({1'b0, afix5}), .b(~({1'b0, tfix})), .cin(1'b1), .s(dab), .cout(dab_c));
    wire [51-1:0] dba;
    wire dba_c;
    ot_hdc_ksadd_k #(.W(51)) u_dba (.a({1'b0, tfix}), .b(~({1'b0, afix5})), .cin(1'b1), .s(dba), .cout(dba_c));
    reg  [49:0] dmag;
    reg         rsign, rzero, nnz6, f_rng;
    reg  [31:0] xc6;
    always @(posedge clk) begin
        dmag  <= dab[50] ? dba[49:0] : dab[49:0];
        rsign <= xc5[31] ^ dab[50];
        rzero <= (dab == 51'd0);
        nnz6  <= nnz5; xc6 <= xc5;
        f_rng <= vd[T_T + 2] && nnz5 && xsm5;       // n != 0 needs |xc| >= 2^-2: never fails
    end

    // depth 7: normalise (the leading one to bit 49); field = 133 - lz
    wire [5:0] lzh, lzl;
    ot_hdc_lzc32 u_lzh (.x(dmag[49:18]), .n(lzh));
    ot_hdc_lzc32 u_lzl (.x({dmag[17:0], 14'd0}), .n(lzl));
    wire [5:0] lz = lzh[5] ? (6'd32 + lzl) : lzh;
    reg  [49:0] nv;
    reg  [7:0]  nfield;
    reg         rsign7, rzero7, nnz7, f_rng7;
    reg  [31:0] xc7;
    always @(posedge clk) begin
        nv <= dmag << lz;
        nfield <= 8'd133 - {2'd0, lz};
        rsign7 <= rsign; rzero7 <= rzero; nnz7 <= nnz6; xc7 <= xc6; f_rng7 <= f_rng;
    end

    // depth 8: round to nearest even, encode r
    wire inc = nv[25] && ((|nv[24:0]) || nv[26]);
    wire [23:0] rs;
    wire rs_c;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(nv[49:26]), .inc(inc), .y(rs), .co(rs_c));
    reg [31:0] r;
    reg        f_rng8;
    always @(posedge clk) begin
        if (!nnz7) r <= (xc7[30:0] == 31'd0) ? 32'd0 : xc7;
        else if (rzero7) r <= 32'd0;
        else r <= {rsign7, nfield + {7'd0, rs_c}, rs_c ? 23'd0 : rs[22:0]};
        f_rng8 <= f_rng7;
    end

    // Horner: p = C0; six times p = RN(RN(p*r) + C[k]); r travels in 4-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pa [0:6];
    wire [6:1]  hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay #(.W(32), .D(LH)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_hstep #(.K(poly(k)), .CUT(PCUT)) u_h (.clk(clk), .rst_n(rst_n), .v(vd[T_R + LH*(k-1)]),
                                             .a(pa[k-1]), .b(rd[k-1]), .y(pa[k]), .vo(), .fault(hf[k]));
        end
    endgenerate

    wire [8:0] nint_d;
    ot_hdc_delay #(.W(9), .D(T_P - T_T - 1)) d_n (clk, rst_n, nint, nint_d);
    wire [8:0] y_hi;
    wire y_hi_c;
    ot_hdc_ksadd_k #(.W(9)) u_ye (.a(pa[6][31:23]), .b(nint_d), .cin(1'b0), .s(y_hi), .cout(y_hi_c));
    always @(posedge clk) y <= {y_hi, pa[6][22:0]};       // pa[6] + (n << 23)
    assign p_pre = pa[6];
    assign n_pre = nint_d;

    assign fault = f_t | f_rng8 | (|hf);
endmodule

// ---------------------------------------------------------------------------
// u = t / RN(t + 2), t = p + n<<23 the exp's result (tools/hdc_golden_v41.
// log1p_unit's first two roundings), DEPTH 19 from (p, n): ot_hdc_v41x_fdiv's
// digit recurrence and finish, behind a front that knows its operands:
//   D1  t's code (the exp's exponent step); RN(2 + t) for t in [0, 1] is
//       2 + RN_even(t * 2^22) * 2^-22 (its binade is [2, 4), and the "2" is an
//       even multiple of that ulp), so only t's significand shifted right by
//       128 - field and its round/sticky bits are formed
//   D2  the divisor significand (the rounding increment) and its triple, in
//       parallel (3 m + 3 inc)
// t outside [0, 1] (negative, subnormal, above 1, nonfinite) FAILS CLOSED; the
// exp of -|x| never is.  The recurrence and finish are ot_hdc_v41x_fdiv's.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_spdiv (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] p,
    input  wire [8:0]  n,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer QB = 27;
    localparam integer NS = (QB + 1) / 2;      // 14
    localparam integer DEPTH = 2 + NS + 3;     // 19

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- D1 ----
    wire [8:0]  t_hi;
    wire        t_hi_c;
    ot_hdc_ksadd_k #(.W(9)) u_te (.a(p[31:23]), .b(n), .cin(1'b0), .s(t_hi), .cout(t_hi_c));
    wire [31:0] t  = {t_hi, p[22:0]};                  // p + (n << 23)
    wire [7:0]  et = t[30:23];
    wire [23:0] mt = {1'b1, t[22:0]};
    wire [7:0]  s8 = 8'd128 - et;                      // >= 1 for t <= 1
    wire [4:0]  s  = (s8 > 8'd25) ? 5'd25 : s8[4:0];
    wire [23:0] fl = mt >> s;
    wire        g  = (s == 5'd25) ? 1'b0 : mt[s - 5'd1];
    wire        st = |(mt & ~({24{1'b1}} << (s - 5'd1)));
    wire        tz = (t[30:0] == 31'd0);
    reg        d_zero, d_bad, d_inc;
    reg [22:0] d_f;
    reg [23:0] d_ma;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_zero <= tz;
        d_bad  <= t[31] || (t[30:0] > 31'h3F800000) || (et == 8'd0 && !tz);
        d_f    <= fl[22:0];
        d_inc  <= g && (st || fl[0]);
        d_ma   <= tz ? 24'd0 : mt;
        d_e    <= $signed({3'd0, et}) - 11'sd128;
    end

    // ---- D2: divisor significand and its triple ----
    wire [23:0] mbf = {1'b1, d_f};
    wire [23:0] mb_i;
    wire        mb_c;
    ot_hdc_inc_k #(.W(24)) u_mb (.a(mbf), .inc(d_inc), .y(mb_i), .co(mb_c));
    //: 3 mbf + 3 inc: one carry-save level, then the prefix add
    wire [25:0] m3a = {2'b0, mbf}, m3b = {1'b0, mbf, 1'b0}, m3c = d_inc ? 26'd3 : 26'd0;
    wire [25:0] m3s = m3a ^ m3b ^ m3c;
    wire [25:0] m3k = {(m3a[24:0] & m3b[24:0]) | (m3a[24:0] & m3c[24:0]) | (m3b[24:0] & m3c[24:0]), 1'b0};
    wire [25:0] mb3_i;
    wire        mb3_c;
    ot_hdc_ksadd_k #(.W(26)) u_mb3 (.a(m3s), .b(m3k), .cin(1'b0), .s(mb3_i), .cout(mb3_c));
    reg        e_sign, e_zero, e_bad;
    reg [23:0] e_ma, e_mb;
    reg [25:0] e_mb3;
    reg signed [10:0] e_e;
    always @(posedge clk) begin
        e_sign <= 1'b0; e_zero <= d_zero; e_bad <= d_bad; e_e <= d_e; e_ma <= d_ma;
        e_mb  <= mb_i;
        e_mb3 <= mb3_i;
    end

    // ---- recurrence (ot_hdc_v41x_fdiv) ----
    reg [24:0]        r_rem  [0:NS-1];
    reg [QB-1:0]      r_q    [0:NS-1];
    reg [23:0]        r_mb   [0:NS-1];
    reg [25:0]        r_mb3  [0:NS-1];
    reg               r_sign [0:NS-1];
    reg               r_zero [0:NS-1];
    reg               r_bad  [0:NS-1];
    reg signed [10:0] r_e    [0:NS-1];
    genvar j;
    generate
        for (j = 0; j < NS; j = j + 1) begin : g_rec
            localparam integer TWO = (2 * j + 1 < QB);
            wire [23:0]   mb  = (j == 0) ? e_mb : r_mb[j-1];
            wire [25:0]   mb3 = (j == 0) ? e_mb3 : r_mb3[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [26:0]   x   = (j == 0) ? {2'b0, e_ma, 1'b0} :
                                TWO ? {r_rem[j-1][24:0], 2'b0} : {1'b0, r_rem[j-1][24:0], 1'b0};
            wire [28-1:0] d1;
            wire d1_c;
            ot_hdc_ksadd_k #(.W(28)) u_d1 (.a({1'b0, x}), .b(~({4'b0, mb})), .cin(1'b1), .s(d1), .cout(d1_c));
            wire [28-1:0] d2;
            wire d2_c;
            ot_hdc_ksadd_k #(.W(28)) u_d2 (.a({1'b0, x}), .b(~({3'b0, mb, 1'b0})), .cin(1'b1), .s(d2), .cout(d2_c));
            wire [28-1:0] d3;
            wire d3_c;
            ot_hdc_ksadd_k #(.W(28)) u_d3 (.a({1'b0, x}), .b(~({2'b0, mb3})), .cin(1'b1), .s(d3), .cout(d3_c));
            wire [1:0]    q  = !d3[27] ? 2'd3 : !d2[27] ? 2'd2 : !d1[27] ? 2'd1 : 2'd0;
            wire [26:0]   r  = !d3[27] ? d3[26:0] : !d2[27] ? d2[26:0] : !d1[27] ? d1[26:0] : x;
            always @(posedge clk) begin
                r_rem[j]  <= r[24:0];
                r_q[j]    <= TWO ? {qin[QB-3:0], q} : {qin[QB-2:0], q[0]};
                r_mb[j]   <= mb;
                r_mb3[j]  <= mb3;
                r_sign[j] <= (j == 0) ? e_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? e_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? e_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish (ot_hdc_v41x_fdiv) ----
    wire [QB-1:0] q = r_q[NS-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[NS-1];
        f1_zero <= r_zero[NS-1];
        f1_bad  <= r_bad[NS-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd126;
        end
    end
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = (25'd1 << sh) - 25'd1;
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    wire [30:0] code;
    wire        code_c;
    ot_hdc_inc_k #(.W(31)) u_code (.a({f2_field, f2_sig[22:0]}), .inc(rup), .y(code), .co(code_c));
    wire        ovf = f2_ovf || (code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f2_bad || (ovf && !f2_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f2_zero || code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f2_sign, code}; fault <= 1'b0; end
    end
endmodule

// ---------------------------------------------------------------------------
// Correctly rounded binary32 square root, RADIX 4: two root bits a stage, DEPTH
// 16 (ot_hdc_fsqrt: one bit a stage, DEPTH 31).  Same function and port
// convention as ot_hdc_fsqrt (sqrt(+-0) = +0, subnormals normalised, a negative
// or nonfinite argument fails closed with y = +0), and a correctly rounded root
// is unique, so the codes are the same.
//   * FRAC_SHIFT 13, not 15: the root then has 26 bits with its top at bit 25 or
//     24 -- the 24-bit significand, the guard bit, and (top at 25) one more --
//     and the remainder gives the sticky bit.
//   * Digit q in {0..3}: with root Q and remainder R, X = 16 R + the next four
//     radicand bits is compared with (4Q + q)^2 - 16 Q^2 = 8Qq + q^2 for q = 1,
//     2, 3 in parallel -- 8Q+1 and 16Q+4 are concatenations, 24Q+9 is
//     8(3Q+1)+1, so 3Q+1 is carried as a register and updated per digit
//     (4(3Q+1) + 3q - 3: q = 1, 2 concatenations, q = 0, 3 its decrement and
//     increment, formed beside the compares).
// Stages: 1 decode, 13 digits, 2 finish.
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt4 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT = 13;
    localparam integer ND    = 13;                 // radix-4 digits
    localparam integer RAD_W = 4 * ND;             // 52 >= 25 + 2*13
    localparam integer Q_W   = 2 * ND;             // 26
    localparam integer RW    = Q_W + 6;            // remainder / trial width
    localparam integer EXP_W = 12;
    localparam integer DEPTH = ND + 3;             // 16
    localparam integer TOP   = FRAC_SHIFT + 12;    // 25

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, even exponent (ot_hdc_fsqrt) ----
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - 25 - 2 * FRAC_SHIFT){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- digit stages ----
    reg [RAD_W-1:0]        rad_st  [1:ND];
    reg [RW-1:0]           rem_st  [1:ND];
    reg [Q_W-1:0]          q_st    [1:ND];
    reg [Q_W+1:0]          q3_st   [1:ND];     // 3Q + 1
    reg signed [EXP_W-1:0] half_st [1:ND];
    reg                    zero_st [1:ND];
    reg                    err_st  [1:ND];
    genvar gi;
    generate
        for (gi = 1; gi <= ND; gi = gi + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad = (gi == 1) ? s0_radicand : rad_st[gi-1];
            wire [RW-1:0]    src_rem = (gi == 1) ? {RW{1'b0}} : rem_st[gi-1];
            wire [Q_W-1:0]   src_q   = (gi == 1) ? {Q_W{1'b0}} : q_st[gi-1];
            wire [Q_W+1:0]   src_q3  = (gi == 1) ? {{(Q_W+1){1'b0}}, 1'b1} : q3_st[gi-1];
            wire [RW-1:0] xx = {src_rem[RW-5:0], src_rad[RAD_W-1 -: 4]};
            wire [RW-1:0] t1 = {{(RW-Q_W-3){1'b0}}, src_q, 3'b001};
            wire [RW-1:0] t2 = {{(RW-Q_W-4){1'b0}}, src_q, 4'b0100};
            wire [RW-1:0] t3 = {{(RW-Q_W-5){1'b0}}, src_q3, 3'b001};
            wire [RW:0] d1;
            wire d1_c;
            ot_hdc_ksadd_k #(.W(RW+1)) u_d1 (.a({1'b0, xx}), .b(~({1'b0, t1})), .cin(1'b1), .s(d1), .cout(d1_c));
            wire [RW:0] d2;
            wire d2_c;
            ot_hdc_ksadd_k #(.W(RW+1)) u_d2 (.a({1'b0, xx}), .b(~({1'b0, t2})), .cin(1'b1), .s(d2), .cout(d2_c));
            wire [RW:0] d3;
            wire d3_c;
            ot_hdc_ksadd_k #(.W(RW+1)) u_d3 (.a({1'b0, xx}), .b(~({1'b0, t3})), .cin(1'b1), .s(d3), .cout(d3_c));
            wire [1:0] q = !d3[RW] ? 2'd3 : !d2[RW] ? 2'd2 : !d1[RW] ? 2'd1 : 2'd0;
            wire [RW-1:0] r = !d3[RW] ? d3[RW-1:0] : !d2[RW] ? d2[RW-1:0] : !d1[RW] ? d1[RW-1:0] : xx;
            wire [Q_W+1:0] q3m, q3p;
            wire q3m_c, q3p_c;
            ot_hdc_ksadd_k #(.W(Q_W+2)) u_q3m (.a(src_q3), .b({(Q_W+2){1'b1}}), .cin(1'b0), .s(q3m), .cout(q3m_c));
            ot_hdc_inc_k #(.W(Q_W+2)) u_q3p (.a(src_q3), .inc(1'b1), .y(q3p), .co(q3p_c));
            wire [Q_W+1:0] q3n = (q == 2'd0) ? {q3m[Q_W-1:0], 2'b01} :
                                 (q == 2'd1) ? {src_q3[Q_W-1:0], 2'b00} :
                                 (q == 2'd2) ? {src_q3[Q_W-1:0], 2'b11} : {q3p[Q_W-1:0], 2'b10};
            always @(posedge clk) begin
                rem_st[gi]  <= r;
                q_st[gi]    <= {src_q[Q_W-3:0], q};
                q3_st[gi]   <= q3n;
                rad_st[gi]  <= {src_rad[RAD_W-5:0], 4'b0000};
                half_st[gi] <= (gi == 1) ? s0_half : half_st[gi-1];
                zero_st[gi] <= (gi == 1) ? s0_zero : zero_st[gi-1];
                err_st[gi]  <= (gi == 1) ? s0_err  : err_st[gi-1];
            end
        end
    endgenerate

    // ---- finish 1 / 2 (ot_hdc_fsqrt) ----
    wire [Q_W-1:0] root = q_st[ND];
    wire [RW-1:0]  rem  = rem_st[ND];
    wire hi = root[TOP];
    reg [23:0] f_trunc;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg signed [EXP_W-1:0] f_unb;
    always @(posedge clk) begin
        f_zero <= zero_st[ND];
        f_err  <= err_st[ND];
        if (hi) begin
            f_trunc  <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= root[0] || (|rem);
            f_unb    <= $signed(TOP) + half_st[ND] - $signed(FRAC_SHIFT);
        end else begin
            f_trunc  <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|rem);
            f_unb    <= $signed(TOP - 1) + half_st[ND] - $signed(FRAC_SHIFT);
        end
    end
    wire        round_up = f_guard && (f_sticky || f_trunc[0]);
    wire [23:0] rnd24;
    wire        rnd24_c;
    ot_hdc_inc_k #(.W(24)) u_rq (.a(f_trunc), .inc(round_up), .y(rnd24), .co(rnd24_c));
    wire [24:0] rounded  = {rnd24_c, rnd24};
    wire        carried  = rounded[24];
    wire [23:0] sig_out  = carried ? rounded[24:1] : rounded[23:0];
    wire signed [EXP_W-1:0] biased = f_unb + (carried ? 12'sd1 : 12'sd0) + 12'sd127;
    wire out_of_range = (biased < 12'sd1) || (biased > 12'sd254);
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased[7:0], sig_out[22:0]}; fault <= 1'b0; end
    end
endmodule

// ---------------------------------------------------------------------------
// softplus(x) and sqrt(softplus(x)): II 1, DEPTH 107 (PCUT 0) or 124 (PCUT 1),
// the ports, results and fault of ot_hdc_v41x_softplus (DEPTH 162).  The same
// roundings (depths at PCUT 0 / 1):
//     t = exp(-|x|)                      ot_hdc_v41x_exp_s, (p, n) at 32 / 39
//     u = t / RN(t + 2)                  ot_hdc_v41x_spdiv          -> 51 / 58
//     u2 = RN(u * u)                     ot_hdc_fp32_mul_x2 DOUBLE 0 -> 54 / 62
//     p = 1/17; p = RN(RN(p*u2) + 1/(2i+1)), i = 7 .. 0  8 x ot_hdc_hstep -> 86 / 102
//     l = 2 * RN(u * p)                  ot_hdc_fp32_mul_x2         -> 89 / 106
//     sp = RN(max(x, 0) + l)             ot_hdc_addpos2             -> 91 / 108
//     r = sqrt(sp)                       ot_hdc_fsqrt4              -> 107 / 124
// ---------------------------------------------------------------------------
module ot_hdc_v41x_softplus_s #(parameter integer PCUT = 1) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] sp,
    output wire [31:0] r,
    output wire        vo,
    output wire        fault
);
    localparam integer LH     = 4 + PCUT;        // Horner step latency
    localparam integer LM     = 3 + PCUT;        // multiply latency
    localparam integer T_PN   = 8 + PCUT + 6 * LH;   // 39: the exp's last Horner result
    localparam integer T_U    = T_PN + 19;       // 58
    localparam integer T_U2   = T_U + LM;        // 62
    localparam integer T_P    = T_U2 + 8 * LH;   // 102
    localparam integer T_L    = T_P + LM;        // 106
    localparam integer T_SP   = T_L + 2;         // 108
    localparam integer DEPTH  = T_SP + 16;       // 124 (107 at PCUT = 0)
    localparam [32*9-1:0] C = {32'h3D70F0F1, 32'h3D888889, 32'h3D9D89D9, 32'h3DBA2E8C, 32'h3DE38E39,
                               32'h3E124925, 32'h3E4CCCCD, 32'h3EAAAAAB, 32'h3F800000};  // 1/17 .. 1/1
    function automatic [31:0] coef(input integer i);
        coef = C[32*(8-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    wire [31:0] p_pre, u, u2, l, spv;
    wire [8:0]  n_pre;
    wire f_exp, f_div, f_u2, f_l, f_sp, f_sq;
    ot_hdc_v41x_exp_s #(.PCUT(PCUT)) u_exp (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b1, x[30:0]}), .y(), .vo(),
                             .p_pre(p_pre), .n_pre(n_pre), .fault(f_exp));
    ot_hdc_v41x_spdiv u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_PN]), .p(p_pre), .n(n_pre),
                             .y(u), .vo(), .fault(f_div));
    ot_hdc_fp32_mul_x2 #(.DOUBLE(0), .CUT(PCUT)) m_u2 (.clk(clk), .rst_n(rst_n), .v(vd[T_U]), .a(u), .b(u), .y(u2), .fault(f_u2));

    wire [31:0] u2d [0:7];
    wire [31:0] pa  [0:8];
    wire [8:1]  hf;
    assign u2d[0] = u2;
    assign pa[0] = coef(0);
    genvar k;
    generate
        for (k = 1; k <= 8; k = k + 1) begin : g_h
            if (k < 8) begin : g_d
                ot_hdc_delay #(.W(32), .D(LH)) d_u2 (clk, rst_n, u2d[k-1], u2d[k]);
            end
            ot_hdc_hstep #(.K(coef(k)), .CUT(PCUT)) u_h (.clk(clk), .rst_n(rst_n), .v(vd[T_U2 + LH*(k-1)]),
                                            .a(pa[k-1]), .b(u2d[k-1]), .y(pa[k]), .vo(), .fault(hf[k]));
        end
    endgenerate

    wire [31:0] u_d;
    ot_hdc_delay #(.W(32), .D(T_P - T_U)) d_u (clk, rst_n, u, u_d);
    ot_hdc_fp32_mul_x2 #(.CUT(PCUT)) m_l (.clk(clk), .rst_n(rst_n), .v(vd[T_P]), .a(u_d), .b(pa[8]), .y(l), .fault(f_l));

    reg  [31:0] mx;
    wire [31:0] mx_d;
    wire x_nan = (x[30:23] == 8'hFF) && (x[22:0] != 23'd0);
    always @(posedge clk) mx <= (x[31] && !x_nan) ? 32'd0 : x;
    ot_hdc_delay #(.W(32), .D(T_L - 1)) d_mx (clk, rst_n, mx, mx_d);
    ot_hdc_addpos2 a_sp (.clk(clk), .rst_n(rst_n), .v(vd[T_L]), .a(mx_d), .b(l), .y(spv), .fault(f_sp));

    ot_hdc_fsqrt4 u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP]), .a(spv), .y(r), .vo(), .fault(f_sq));
    ot_hdc_delay #(.W(32), .D(DEPTH - T_SP)) d_sp (clk, rst_n, spv, sp);

    wire f_sp_d;
    ot_hdc_delay #(.W(1), .D(DEPTH - T_SP), .RESET(1)) d_fsp (clk, rst_n, f_sp, f_sp_d);
    assign fault = f_sp_d | f_sq | f_exp | f_div | f_u2 | (|hf) | f_l;
endmodule
