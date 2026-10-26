// GENERATED (S81-VE4 2026-10-20) -- the r3 ve RTL at 6ad9506a1 (rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv + ot_s81sl_ve_fp.sv),
// every ot_s81sl_ve* module renamed r3ref_ot_s81sl_ve*; the reference side of tb_s81sl_ve_miter.sv (bench only).
// Regenerate: git show 6ad9506a1:<file> | sed -E "s/\bot_s81sl_ve/r3ref_ot_s81sl_ve/g"
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-VE r3 (2026-10-19): ve-local copies of the 1.2 GHz binary32 add / multiply of rtl/hdc/ot_hdc_fp32_f12.sv
// (ot_hdc_fp32_add_f12 -> r3ref_ot_s81sl_ve_fadd, ot_hdc_fp32_mul_f12 -> r3ref_ot_s81sl_ve_fmul; the shared file is unchanged
// because closed views bind it).  The ONLY change: valid-only reset -- the output word y and its error code err lose
// their asynchronous reset (y / err are observed only with valid_out, which keeps its reset; the cut bundles of
// ot_hdc_f12_cut already reset only their valid bit).  Bit for bit and cycle for cycle the shared units otherwise
// (the bodies below are extracted verbatim by script; diff them against the shared file).  Reset loads per unit:
// adder LAT 4 = 3 cut valids + valid_out = 4; multiplier LAT 5 = 4 cut valids + valid_out = 5 (r2: 38 / 39).
// Wrappers r3ref_ot_s81sl_ve_qadd (LAT 4, CUTS 6'b101010 = ot_hdc_fp32_add_f12_l4) / r3ref_ot_s81sl_ve_qmul (LAT 5, CUTS
// 8'b01101010 = ot_hdc_fp32_mul_f12_l5) also EXPORT the unit's valid_out (vo), so the ve leaves chain each unit's
// valid from the unit before it instead of a separate reset valid delay line.
// Needs rtl/hdc/ot_hdc_fp32_f12.sv (ot_hdc_f12_cut), rtl/hdc/ot_hdc_fastfp.sv, rtl/hdc/ot_hdc_prefix.sv.
// ---------------------------------------------------------------------------------------------------------------------
module r3ref_ot_s81sl_ve_fadd #(
    parameter integer CUTS = 6'b101010
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    localparam integer K0 = CUTS % 2, K1 = (CUTS / 2) % 2, K2 = (CUTS / 4) % 2, K3 = (CUTS / 8) % 2,
                       K4 = (CUTS / 16) % 2, K5 = (CUTS / 32) % 2, K6 = (CUTS / 64) % 2;

    // ---- decode, exponent differences (bit 6: cut here, the magnitude compare after it); magnitude compare ----------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    wire [5:0] g6, g0;                         // {valid, f_eq, f_lt, -, dab >= 28, dba >= 28}
    ot_hdc_f12_cut #(.W(6), .CUT(K6)) u_g6 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a_field == b_field, a_field < b_field, 1'b0, dab >= 8'd28, dba >= 8'd28}), .q(g6));
    localparam integer WA6 = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8 + 31 + 31;
    wire [WA6-1:0] q6;
    ot_hdc_f12_cut #(.W(WA6), .CUT(K6)) u_k6 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
            a_exp, b_exp, a_man, b_man, dab, dba, a[30:0], b[30:0]}), .q(q6));
    wire [30:0] c_a = q6[61:31], c_b = q6[30:0];
    // the magnitude order of the encodings (swap = |b| > |a|) split at the exponent field: the field order is decided
    // beside the exponent differences (f_lt, f_eq, carried in g6 / g0), the fraction order after the cut; the same
    // predicate as the 31-bit compare of add_lat (the lane's compare + swap stage was 2-13 ps over 0.833 ns)
    wire frac_c;
    wire [22:0] frac_s;
    ot_hdc_ksadd_k #(.W(23)) u_cmp (.a(c_a[22:0]), .b(~c_b[22:0]), .cin(1'b1), .s(frac_s), .cout(frac_c));
    wire cmp_c = g6[4] ? frac_c : !g6[3];          // a >= b
    localparam integer WA = 1 + 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] qa;
    ot_hdc_f12_cut #(.W(WA), .CUT(K0)) u_k0 (.clk(clk), .rst_n(rst_n),
        .d({q6[WA6-1], !cmp_c, q6[WA6-2:62]}), .q(qa));
    wire        x_v, x_swap, x_byp, x_sub, x_as, x_bs;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_v, x_swap, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = qa;
    // ---- both alignments, the swap pick -------------------------------------------------------------
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
    // the shifted-out-entirely flags (d >= 28), decided beside the exponent differences and carried through the cuts
    // (the stage after cut 6 was 4 ps over 0.833 ns in the lane with the compares in it)

    function automatic [27:0] jam28f;
        input [23:0] man;
        input [4:0]  d;
        input        far;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (far) jam28f = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d);
                jam28f = (val >> d) | {27'd0, |lost};
            end
        end
    endfunction
    ot_hdc_f12_cut #(.W(6), .CUT(K0)) u_g0 (.clk(clk), .rst_n(rst_n), .d(g6), .q(g0));
    wire [27:0] small_a = jam28f(x_aman, x_dba[4:0], g0[0]);
    wire [27:0] small_b = jam28f(x_bman, x_dab[4:0], g0[1]);
    localparam integer W1 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 28;
    wire [W1-1:0] q1;
    ot_hdc_f12_cut #(.W(W1), .CUT(K1)) u_k1 (.clk(clk), .rst_n(rst_n),
        .d({x_v, x_byp, x_sub, x_swap ? x_bs : x_as, x_err, x_code, x_swap ? x_bexp : x_aexp,
            x_swap ? x_bman : x_aman, x_swap ? small_a : small_b}), .q(q1));
    wire        s1_v, s1_byp, s1_sub, s1_sign;
    wire [1:0]  s1_err;
    wire [31:0] s1_code;
    wire [7:0]  s1_exp;
    wire [23:0] s1_big;
    wire [27:0] s1_small;
    assign {s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, s1_big, s1_small} = q1;
    // ---- the sum and the difference ------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer W2 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [W2-1:0] q2;
    ot_hdc_f12_cut #(.W(W2), .CUT(K2)) u_k2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(q2));
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = q2;
    // ---- the add's renormalise; the sentinel leading-zero count ------------------------------------------
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32 u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    localparam integer W3 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [W3-1:0] q3;
    ot_hdc_f12_cut #(.W(W3), .CUT(K3)) u_k3 (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(q3));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = q3;
    // ---- the cancellation shift, the exponent adjust ------------------------------------------------------
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_inc_k #(.W(8)) u_eadd (.a(w_exp), .inc(w_carry), .y(exp_add), .co(exp_add_c));
    localparam integer W4 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27;
    wire [W4-1:0] q4;
    ot_hdc_f12_cut #(.W(W4), .CUT(K4)) u_k4 (.clk(clk), .rst_n(rst_n),
        .d({w_v, w_byp, w_sign, w_sub && (w_dif == 28'd0), w_err, w_code, w_sub ? exp_sub : exp_add,
            w_sub ? sub_val : w_add}), .q(q4));
    wire        s2_v, s2_byp, s2_sign, s2_zero;
    wire [1:0]  s2_err;
    wire [31:0] s2_code;
    wire [7:0]  s2_exp;
    wire [26:0] s2_val;
    assign {s2_v, s2_byp, s2_sign, s2_zero, s2_err, s2_code, s2_exp, s2_val} = q4;
    // ---- round increment ----------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(s2_val[26:3]), .inc(inc), .y(rnd_w), .co(rnd_cw));
    localparam integer W5 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [W5-1:0] q5;
    ot_hdc_f12_cut #(.W(W5), .CUT(K5)) u_k5 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(q5));
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = q5;
    // ---- encode, subnormal, overflow, canonical zero -------------------------------------------------------
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    // S81-VE r3: valid-only reset (the result word and its error code carry no reset: never observed without valid_out)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) valid_out <= 1'b0;
        else valid_out <= u_v;
    always @(posedge clk) begin
        if (u_byp) begin y <= u_code; err <= u_err; end
        else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
        else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
        else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
    end
endmodule

module r3ref_ot_s81sl_ve_fmul #(
    parameter integer CUTS = 8'b01101010
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    localparam integer K0 = CUTS % 2, K1 = (CUTS / 2) % 2, K2 = (CUTS / 4) % 2, K3 = (CUTS / 8) % 2,
                       K4 = (CUTS / 16) % 2, K5 = (CUTS / 32) % 2, K6 = (CUTS / 64) % 2, K7 = (CUTS / 128) % 2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- decode; the fractions' leading zeros ---------------------------------------------------------
    wire [7:0] a_field = a[30:23];
    wire [7:0] b_field = b[30:23];
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_cz, b_cz;                      // clz23 of the fraction (23 for a zero fraction)
    ot_hdc_lzc32 u_la (.x({a[22:0], 9'h1ff}), .n(a_cz));
    ot_hdc_lzc32 u_lb (.x({b[22:0], 9'h1ff}), .n(b_cz));
    localparam integer W0 = 1 + 1 + 2 + 1 + 23 + 23 + 8 + 8 + 5 + 5;
    wire [W0-1:0] q0;
    ot_hdc_f12_cut #(.W(W0), .CUT(K0)) u_k0 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), a[31] ^ b[31], a[22:0], b[22:0],
            a_field, b_field, a_cz[4:0], b_cz[4:0]}), .q(q0));
    wire        o0_v, o0_byp, o0_sign;
    wire [1:0]  o0_err;
    wire [22:0] o0_af, o0_bf;
    wire [7:0]  o0_ae, o0_be;
    wire [4:0]  o0_acz, o0_bcz;
    assign {o0_v, o0_byp, o0_err, o0_sign, o0_af, o0_bf, o0_ae, o0_be, o0_acz, o0_bcz} = q0;
    // ---- normalise (a subnormal's significand {frac, 0} << clz23; mul_lat's a_raw << (1 + clz23)), powers ---
    wire a_s = (o0_ae == 8'd0), b_s = (o0_be == 8'd0);
    wire [23:0] a_n = a_s ? ({o0_af, 1'b0} << o0_acz) : {1'b1, o0_af};
    wire [23:0] b_n = b_s ? ({o0_bf, 1'b0} << o0_bcz) : {1'b1, o0_bf};
    wire signed [11:0] a_power = a_s ? (-12'sd150 - {7'd0, o0_acz}) : ($signed({4'd0, o0_ae}) - 12'sd150);
    wire signed [11:0] b_power = b_s ? (-12'sd150 - {7'd0, o0_bcz}) : ($signed({4'd0, o0_be}) - 12'sd150);
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] q1;
    ot_hdc_f12_cut #(.W(W1), .CUT(K1)) u_k1 (.clk(clk), .rst_n(rst_n),
        .d({o0_v, o0_byp, o0_err, o0_sign, a_n, b_n, a_power, b_power}), .q(q1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = q1;
    // ---- rows (24 AND rows, three carry-save levels), the exponent sum -----------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows u_rows (.a(p_a), .b(p_b), .rows(rows));
    localparam integer W2 = 1 + 1 + 2 + 1 + 48 * 8 + 12;
    wire [W2-1:0] q2;
    ot_hdc_f12_cut #(.W(W2), .CUT(K2)) u_k2 (.clk(clk), .rst_n(rst_n),
        .d({p_v, p_byp, p_err, p_sign, rows, power}), .q(q2));
    wire        s1_v, s1_byp, s1_sign;
    wire [1:0]  s1_err;
    wire [48*8-1:0] s1_rows;
    wire signed [11:0] s1_power;
    assign {s1_v, s1_byp, s1_err, s1_sign, s1_rows, s1_power} = q2;
    // ---- two carry-save levels (8 -> 6 -> 4) ---------------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    localparam integer W3 = 1 + 1 + 2 + 1 + 48 * 4 + 12;
    wire [W3-1:0] q3;
    ot_hdc_f12_cut #(.W(W3), .CUT(K3)) u_k3 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l5, s1_power}), .q(q3));
    wire        r3_v, r3_byp, r3_sign;
    wire [1:0]  r3_err;
    wire [48*4-1:0] r3_l5;
    wire signed [11:0] r3_power;
    assign {r3_v, r3_byp, r3_err, r3_sign, r3_l5, r3_power} = q3;
    // ---- two more carry-save levels (4 -> 3 -> 2); the floors and the subnormal masks -------------------
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    assign l6[0 +: 96] = csa(r3_l5[0 +: 48], r3_l5[48 +: 48], r3_l5[96 +: 48]);
    assign l6[96 +: 48] = r3_l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = r3_power + 12'sd47;
    wire signed [11:0] fl46 = r3_power + 12'sd46;
    wire signed [11:0] sh_sub = -(r3_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W4 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W4-1:0] q4;
    ot_hdc_f12_cut #(.W(W4), .CUT(K4)) u_k4 (.clk(clk), .rst_n(rst_n),
        .d({r3_v, r3_byp, r3_err, r3_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(q4));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = q4;
    // ---- the 48-bit prefix add ---------------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));
    localparam integer W5 = 1 + 1 + 2 + 1 + 48 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W5-1:0] q5;
    ot_hdc_f12_cut #(.W(W5), .CUT(K5)) u_k5 (.clk(clk), .rst_n(rst_n),
        .d({q_v, q_byp, q_err, q_sign, prod, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms}), .q(q5));
    wire        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    wire [1:0]  s2_err;
    wire [47:0] s2_prod, s2_mr, s2_ms;
    wire [5:0]  s2_sh;
    wire signed [11:0] s2_fl47, s2_fl46;
    assign {s2_v, s2_byp, s2_err, s2_sign, s2_prod, s2_sub47, s2_sub46, s2_fl47, s2_fl46, s2_sh, s2_mr, s2_ms} = q5;
    // ---- select, subnormal shift, round / sticky bits; both encode exponents ------------------------------
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
    // mul_lat's encode: floor_ = fl + carry; over = !sub && floor_ > 127; field = floor_[7:0] + 127.  Both
    // carries here (from the select's fl, both top choices side by side), picked by the carry after the round
    wire signed [11:0] f47p1 = s2_fl47 + 12'sd1, f46p1 = s2_fl46 + 12'sd1;
    wire [7:0]  fa47 = s2_fl47[7:0] + 8'd127, fb47 = f47p1[7:0] + 8'd127;
    wire [7:0]  fa46 = s2_fl46[7:0] + 8'd127, fb46 = f46p1[7:0] + 8'd127;
    wire        oa47 = s2_fl47 > 12'sd127, ob47 = f47p1 > 12'sd127;
    wire        oa46 = s2_fl46 > 12'sd127, ob46 = f46p1 > 12'sd127;
    wire [7:0]  fa = top ? fa47 : fa46, fb = top ? fb47 : fb46;
    wire        oa = top ? oa47 : oa46, ob = top ? ob47 : ob46;
    localparam integer W6 = 1 + 1 + 2 + 1 + 1 + 24 + 1 + 8 + 8 + 1 + 1;
    wire [W6-1:0] q6;
    ot_hdc_f12_cut #(.W(W6), .CUT(K6)) u_k6 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, main, rb && (st || main[0]), fa, fb, oa, ob}), .q(q6));
    wire        r_v, r_byp, r_sign, r_sub, r_inc, r_oa, r_ob;
    wire [1:0]  r_err;
    wire [23:0] r_main;
    wire [7:0]  r_fa, r_fb;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_main, r_inc, r_fa, r_fb, r_oa, r_ob} = q6;
    // ---- round ----------------------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_inc_k #(.W(24)) u_rnd (.a(r_main), .inc(r_inc), .y(rnd_w), .co(rnd_cw));
    localparam integer W7 = 1 + 1 + 2 + 1 + 1 + 24 + 1 + 8 + 8 + 1 + 1;
    wire [W7-1:0] q7;
    ot_hdc_f12_cut #(.W(W7), .CUT(K7)) u_k7 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, rnd_w, rnd_cw, r_fa, r_fb, r_oa, r_ob}), .q(q7));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c, o_oa, o_ob;
    wire [1:0]  o_err;
    wire [23:0] rnd;
    wire [7:0]  o_fa, o_fb;
    assign {o_v, o_byp, o_err, o_sign, o_sub, rnd, rnd_c, o_fa, o_fb, o_oa, o_ob} = q7;
    // ---- encode ---------------------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire over = !o_sub && (carry ? o_ob : o_oa);
    wire [7:0] field = carry ? o_fb : o_fa;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    // S81-VE r3: valid-only reset (the result word and its error code carry no reset: never observed without valid_out)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) valid_out <= 1'b0;
        else valid_out <= o_v;
    always @(posedge clk) begin
        if (o_byp) begin y <= 32'd0; err <= o_err; end
        else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
        else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
    end
endmodule

module r3ref_ot_s81sl_ve_qadd #(parameter integer LAT = 4) (
    input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
    output wire [31:0] y, output wire vo, output wire fault);
    wire [1:0] err;
    r3ref_ot_s81sl_ve_fadd #(.CUTS(6'b101010)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    assign fault = vo && (err != 2'd0);
`ifndef SYNTHESIS
    initial if (LAT != 4) $error("r3ref_ot_s81sl_ve_qadd: only LAT 4 (the ve calendar's adder)");
`endif
endmodule

module r3ref_ot_s81sl_ve_qmul #(parameter integer LAT = 5) (
    input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
    output wire [31:0] y, output wire vo, output wire fault);
    wire [1:0] err;
    r3ref_ot_s81sl_ve_fmul #(.CUTS(8'b01101010)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                              .valid_out(vo));
    assign fault = vo && (err != 2'd0);
`ifndef SYNTHESIS
    initial if (LAT != 5) $error("r3ref_ot_s81sl_ve_qmul: only LAT 5 (the ve calendar's multiplier)");
`endif
endmodule
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-MIX (2026-10-17): ve = the Engram-mix sub-leaf of one BEAT of a DV vector slice (planned x5 per slice, own clock
// root).  It replaces the hub-era dsfd_engram_mix4_c / the p4j void units mix4_w / mix4_e (dsfd_engram_mix4_half, never
// built): every Engram operand is beat-resident in DV (h in vn's h store; K = 4 x 5120 and V = 5120 FP32 = the
// engram.wkv field rows, captured into vp's leaf store; W = q_weight * k_weight, a per-element FP32 constant row in the
// leaf store), so the mix runs where the data is, and only 12 scalars per beat (3 sums x 4 copies) leave the leaf.
//
// Golden (tools/hdc_golden_v41.py engram_layer, chunk8 su class), copy j, D = 5120:
//   hh = csum(h*h), kk = csum(k*k), dd = csum((h*w)*k)       -> this leaf: the beat's aligned 64-element subtree sums
//   rstd = rsqrt(hh/D + eps) * rsqrt(kk/D + eps); dot = (dd*rstd)*scale; gate = sigmoid(signed sqrt(max(|dot|,1e-6)))
//                                                             -> slice finish (xfin exchange + ot_s81_engram_norm/_gate)
//   out = bf16(h + gate*v)                                    -> this leaf (add phase), written back into vn's h store
// A beat (64 elements) is 8 golden chunks = an aligned subtree of the padded pairwise tree, so the beat partial here is
// bit-identical to the flat engine's node, exactly as vn's norm beat partial.
//
// Arithmetic leaves are the gated hub-era Engram leaves, UNCHANGED (rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv):
//   ot_s81_engram_mul4   (4 lanes: h*h, k*k, h*w, (h*w)*k)      x1
//   ot_s81_engram_chunk8 (golden chunk of 8, sequential from +0) x3 (hh, kk, dd)
//   ot_s81_engram_add8   (8 lanes: bf16(h + gate*v))             x1
// plus the beat tree here (3 golden pairwise levels over the 8 chunk sums, one ot_dsrom_qadd per sum, dataflow issue
// with fixed operands per node: exact by construction, as vn's beat tree).
//
// Streams (static schedule, no ready / credit; the feeder -- the beat's vs over vp's extension port -- issues on the
// compiler's fixed timeline):
//   reduce  r_v: 4 elements a cycle {h (BF16 in an FP32 word), k, w}, copy-major, element order (16 cycles a copy,
//           64 a beat); r_c = the copy (checked against the leaf's own count: out of order = sticky fault).
//           -> p_v / p_c / p_hh / p_kk / p_dd: one beat partial triple per copy.
//   add     a_v: 8 elements a cycle {h, v} + the copy's gate; -> o_v / o_c / o_y (BF16 in the upper half of each word).
// S81-VE r2 (10-19, route b571a8c2c NEEDS_RTL TT -338 / FF -25): static streaming pairwise beat tree (one adder per golden
// level, same association and issue cycle, 129 cyc GAP 0) and D>=3 delay lines as rings instead of shift registers.
// S81-VE r3 (10-19, SAFE-DESIGN checklist after the failed route; r2 gate: ONE merged reset sync drove 2,320 flops,
// 1,230 non-clock roots > 32 loads, ring write pointers 760-870 loads, pack enables 379, operand decodes merged across
// lanes 264):
//   reset   one ot_rst_relay (2 sync + 1 kept relay stage, 18 region copies) behind the kit's 2-stage reset landing;
//           every region copy resets <= 32 flops and ONLY valid / control state: the per-leaf ot_s81_engram_reset
//           syncs are gone (identical, so synthesis merged them into one 2,320-load flop), the FP units are the ve-local
//           valid-only-reset copies (r3ref_ot_s81sl_ve_fp.sv: 4 / 5 reset flops a unit, r2 38 / 39), and the separate reset
//           valid delay lines are gone (each unit's valid is the previous unit's exported valid_out: same cycle).
//   copies  reset-free KEPT copies: ring row selects are one-hot registers replicated per 8-bit slice (each bit: 8
//           write enables + 8 read gates), the pack's low-quad hold enable is 24 kept copies (16 bits each), every
//           multiplier operand that fed two decodes has its own kept operand register (mh a / b, mk a / b, mw a, key
//           line), the add phase's gate word is one kept copy per lane (r2: one decode for 8 lanes, 264 loads).
//   tree    level operands: the held even operand feeds the adder directly, the odd one through one free register;
//           data registers carry no enable (consumers are valid-qualified), so no wide enable net remains.
// Calendars unchanged (reduce first-in -> last partial 129 cyc at GAP 0, add 44 cyc); reset release +1 edge (relay
// stage), a one-time cost after reset, nothing on the token path.  MUT (bench only): 1 key -> 1.0 inside mul4; 2 beat
// tree level-1 pairs (s0 + s2), (s1 + s3); 3 the chunk operand rings' slice-1 READ select one row late.
// ---------------------------------------------------------------------------------------------------------------------
module r3ref_ot_s81sl_ve #(parameter integer LM = 5, LA = 4, MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    // reduce stream
    input  wire         r_v,
    input  wire [1:0]   r_c,
    input  wire [127:0] r_h, r_k, r_w,
    // beat partials
    output reg          p_v,
    output reg  [1:0]   p_c,
    output reg  [31:0]  p_hh, p_kk, p_dd,
    // add stream
    input  wire         a_v,
    input  wire [1:0]   a_c,
    input  wire [255:0] a_h, a_val,
    input  wire [31:0]  a_g,
    output reg          o_v,
    output reg  [1:0]   o_c,
    output reg  [255:0] o_y,
    output reg          fault
);
    // ---------------------------------------------------------------- reset regions (<= 32 reset loads each)
    //  0 top control | 1..4 mul4 lanes | 5,6 chunk_hh | 7,8 chunk_kk | 9,10 chunk_dd | 11..13 trees | 14..17 add8 lane pairs
    localparam integer NR = 18;
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    wire rn = rq[0];

    // ---------------------------------------------------------------- input pin flops
    reg         rv_q, av_q;
    reg [1:0]   rc_q, ac_q;
    reg [127:0] rh_q, rk_q, rw_q;
    reg [255:0] ah_q, aval_q;
    reg [31:0]  ag_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin rv_q <= 1'b0; av_q <= 1'b0; end
        else begin rv_q <= r_v; av_q <= a_v; end
    always @(posedge clk) begin
        rc_q <= r_c; rh_q <= r_h; rk_q <= r_k; rw_q <= r_w;
        ac_q <= a_c; ah_q <= a_h; aval_q <= a_val; ag_q <= a_g;
    end

    // input order check: element quad counter (16 a copy), copy must match
    reg [5:0] icnt;
    reg       f_order;
    always @(posedge clk or negedge rn)
        if (!rn) begin icnt <= 6'd0; f_order <= 1'b0; end
        else if (rv_q) begin
            icnt <= icnt + 6'd1;
            if (rc_q != icnt[5:4]) f_order <= 1'b1;
        end

    // ---------------------------------------------------------------- products (h*h, k*k, (h*w)*k), 4 lanes
    wire         mv, mvpre;
    wire [127:0] mhh, mkk, mdd;
    wire         mf;
    r3ref_ot_s81sl_ve_mul4 #(.LM(LM), .MUT(MUT == 1 ? 1 : 0)) mul (clk, rq[4:1], rv_q, 1'b0, rh_q, rk_q, rw_q,
                                                              mv, mvpre, mhh, mkk, mdd, mf);

    // ---------------------------------------------------------------- pack two quads into one golden chunk of 8
    // half / cv: control (reset).  The low quad is held by 24 kept enable copies (16 bits each): e_lo(t) = mv(t) &&
    // !half(t), registered one edge early from mul4's pre-pin valid (mv(t) = mvpre(t-1), half(t) = half ^ mv).  The
    // chunk word register carries no enable (chunk8 qualifies it with cv).
    reg         half;
    reg         cv;
    always @(posedge clk or negedge rn)
        if (!rn) begin half <= 1'b0; cv <= 1'b0; end
        else begin
            cv <= mv && half;
            if (mv) half <= ~half;
        end
    wire e_lo_d = mvpre && !(half ^ mv);
    (* keep = "true" *) reg [23:0] e_lo;
    always @(posedge clk) e_lo <= {24{e_lo_d}};
    reg  [383:0] sbus;                                   // {sdd, skk, shh}
    wire [383:0] mbus = {mdd, mkk, mhh};
    genvar g;
    generate for (g = 0; g < 24; g = g + 1) begin : g_lo
        always @(posedge clk) if (e_lo[g]) sbus[16*g +: 16] <= mbus[16*g +: 16];
    end endgenerate
    reg [255:0] chh, ckk, cdd;
    always @(posedge clk) begin
        chh <= {mhh, sbus[127:0]}; ckk <= {mkk, sbus[255:128]}; cdd <= {mdd, sbus[383:256]};
    end

    wire [2:0]  sv, sf;
    wire [31:0] shh_s, skk_s, sdd_s;
    r3ref_ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_hh (clk, rq[6:5],  cv, chh, sv[0], shh_s, sf[0]);
    r3ref_ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_kk (clk, rq[8:7],  cv, ckk, sv[1], skk_s, sf[1]);
    r3ref_ot_s81sl_ve_chunk8 #(.LA(LA), .MUT(MUT)) chunk_dd (clk, rq[10:9], cv, cdd, sv[2], sdd_s, sf[2]);

    // ---------------------------------------------------------------- beat trees (lockstep)
    wire [2:0]  tv, tf;
    wire [1:0]  tc0, tc1, tc2;
    wire [31:0] thh, tkk, tdd;
    r3ref_ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_hh (clk, rq[11], sv[0], shh_s, tv[0], tc0, thh, tf[0]);
    r3ref_ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_kk (clk, rq[12], sv[1], skk_s, tv[1], tc1, tkk, tf[1]);
    r3ref_ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_dd (clk, rq[13], sv[2], sdd_s, tv[2], tc2, tdd, tf[2]);

    always @(posedge clk or negedge rn)
        if (!rn) p_v <= 1'b0;
        else p_v <= tv[0];
    always @(posedge clk) begin p_c <= tc0; p_hh <= thh; p_kk <= tkk; p_dd <= tdd; end
    wire f_lock = (tv[0] != tv[1]) || (tv[0] != tv[2]) || (sv[0] != sv[1]) || (sv[0] != sv[2]) ||
                  (tv[0] && ((tc0 != tc1) || (tc0 != tc2)));

    // ---------------------------------------------------------------- add phase: bf16(h + gate*v), 8 lanes
    wire         yv;
    wire [255:0] yd;
    wire         yf;
    wire [1:0]   yc;
    r3ref_ot_s81sl_ve_add8 #(.LM(LM), .LA(LA)) add (clk, rq[17:14], av_q, 1'b1, ah_q, aval_q, ag_q, ac_q, yv, yd, yf, yc);
    always @(posedge clk or negedge rn)
        if (!rn) o_v <= 1'b0;
        else o_v <= yv;
    always @(posedge clk) begin o_c <= yc; o_y <= yd; end

    always @(posedge clk or negedge rn)
        if (!rn) fault <= 1'b0;
        else if (f_order || mf || (|sf) || (|tf) || f_lock || yf) fault <= 1'b1;
endmodule

// Beat tree: 8 chunk sums of one copy arrive in order (at most one a cycle) -> the golden pairwise node
// ((s0+s1)+(s2+s3))+((s4+s5)+(s6+s7)).  Static streaming form: three pipelined adders, one per level.  Each level sees
// its operands in order, holds the even one (enabled 32-bit register) and issues the pair the cycle after the odd one
// lands: the odd operand goes through one free-running register, the held even operand feeds the adder directly (it is
// rewritten at the earliest on the edge the adder captures it).  Level valids are the adders' own valid_out.
// MUT 2 (bench only): level-1 pairs (s0 + s2), (s1 + s3).
module r3ref_ot_s81sl_ve_tree #(parameter integer LA = 4, MUT = 0) (
    input  wire        clk, rn, v,
    input  wire [31:0] s,
    output reg         vo,
    output reg  [1:0]  co,
    output reg  [31:0] y,
    output reg         fault
);
    // ---- level 1: leaf pairs
    reg  [2:0]  li;                        // leaf index within the copy
    reg  [31:0] h1, m1, a1, b1;
    reg         i1;
    wire hold1  = (MUT == 2) ? (li == 3'd0 || li == 3'd4 || li == 3'd6) : !li[0];
    wire stash1 = (MUT == 2) && (li == 3'd1);
    wire [31:0] pa1 = (MUT == 2 && li == 3'd3) ? m1 : h1;
    always @(posedge clk or negedge rn)
        if (!rn) begin li <= 3'd0; i1 <= 1'b0; end
        else begin
            i1 <= v && !hold1 && !stash1;
            if (v) li <= li + 3'd1;
        end
    always @(posedge clk) begin
        if (v && hold1) h1 <= s;
        if (v && stash1) m1 <= s;
        a1 <= pa1;                         // MUT 2 only (the MUT 0 build drops it)
        b1 <= s;
    end
    wire [31:0] s1;
    wire        f1, r1;
    r3ref_ot_s81sl_ve_qadd #(.LAT(LA)) add1 (clk, rn, i1, (MUT == 2) ? a1 : h1, b1, s1, r1, f1);
    // ---- level 2: pairs of level-1 sums (n0,n1) -> n4, (n2,n3) -> n5
    reg         p2, i2;
    reg  [31:0] h2, b2;
    always @(posedge clk or negedge rn)
        if (!rn) begin p2 <= 1'b0; i2 <= 1'b0; end
        else begin
            i2 <= r1 && p2;
            if (r1) p2 <= ~p2;
        end
    always @(posedge clk) begin
        if (r1 && !p2) h2 <= s1;
        b2 <= s1;
    end
    wire [31:0] s2;
    wire        f2, r2;
    r3ref_ot_s81sl_ve_qadd #(.LAT(LA)) add2 (clk, rn, i2, h2, b2, s2, r2, f2);
    // ---- level 3: (n4, n5) -> n6 = the beat partial
    reg         p3, i3;
    reg  [31:0] h3, b3;
    always @(posedge clk or negedge rn)
        if (!rn) begin p3 <= 1'b0; i3 <= 1'b0; end
        else begin
            i3 <= r2 && p3;
            if (r2) p3 <= ~p3;
        end
    always @(posedge clk) begin
        if (r2 && !p3) h3 <= s2;
        b3 <= s2;
    end
    wire [31:0] s3;
    wire        f3, r3;
    r3ref_ot_s81sl_ve_qadd #(.LAT(LA)) add3 (clk, rn, i3, h3, b3, s3, r3, f3);
    // ---- output: copy = arrival order
    reg [1:0] oc;
    always @(posedge clk or negedge rn)
        if (!rn) begin vo <= 1'b0; oc <= 2'd0; fault <= 1'b0; end
        else begin
            vo <= r3;
            if (r3) oc <= oc + 2'd1;
            if (f1 || f2 || f3) fault <= 1'b1;
        end
    always @(posedge clk) begin y <= s3; co <= oc; end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Ring delay line (r3): q is d delayed by exactly D edges, cycle-exact as ot_hdc_delay / ot_hdc_delay_rf for D >= 3:
// input register -> N = D - 2 rows (one row written per edge) -> output register.  The row select is a ONE-HOT
// register replicated per 8-bit slice (* keep *), each bit driving 8 write enables + 8 read AND gates; all copies are
// registered from one decode of the next write pointer (self-correcting: wptr leaves any out-of-range power-up value on
// its first edge, the one-hot copies follow one edge later -- before the line has filled, as the rf form).  No reset
// (data and pointer), no runtime-indexed array (rows are plain registers, the read is an AND-OR of the selected row).
// D < 3: ot_hdc_delay (wire / one or two registers).  MUT 3 (bench only): slice 1's read select one row late.
// ---------------------------------------------------------------------------------------------------------------------
module r3ref_ot_s81sl_ve_dly #(parameter integer W = 32, D = 1, MUT = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (D >= 3) begin : g_ring
        r3ref_ot_s81sl_ve_ring #(.W(W), .D(D), .MUT(MUT)) u (clk, d, q);
    end else begin : g_sh
        ot_hdc_delay #(.W(W), .D(D)) u (clk, 1'b1, d, q);
    end endgenerate
endmodule

module r3ref_ot_s81sl_ve_ring #(parameter integer W = 32, D = 3, MUT = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    localparam integer N = D - 2;
    localparam integer K = (N <= 2) ? 1 : $clog2(N);
    localparam [K-1:0] LAST = N - 1;
    localparam integer S = (W + 7) / 8;
    reg [W-1:0] din, dout;
    reg [K-1:0] wptr;
    wire [K-1:0] wnext = (wptr >= LAST) ? {K{1'b0}} : wptr + 1'b1;
    reg  [N-1:0] oh_d, oh_late;
    integer r;
    always @* for (r = 0; r < N; r = r + 1) begin
        oh_d[r] = (wnext == r[K-1:0]);
        oh_late[r] = (wptr == r[K-1:0]);
    end
    always @(posedge clk) begin din <= d; wptr <= wnext; end
    genvar sl, i;
    generate for (sl = 0; sl < S; sl = sl + 1) begin : g_s
        localparam integer LO = 8 * sl;
        localparam integer SW = (W - LO) < 8 ? (W - LO) : 8;
        (* keep = "true" *) reg [N-1:0] oh;          // this slice's row select copy
        always @(posedge clk) oh <= oh_d;
        // MUT 3 (bench only): slice 1 READS one row late (a uniformly rotated select would still be exact)
        reg [N-1:0] ohr;
        always @(posedge clk) ohr <= (MUT == 3 && sl == 1) ? oh_late : oh_d;
        wire [N-1:0] rsel = (MUT == 3) ? ohr : oh;
        wire [SW*N-1:0] sel;
        for (i = 0; i < N; i = i + 1) begin : g_r
            reg [SW-1:0] row;
            always @(posedge clk) if (oh[i]) row <= din[LO +: SW];
            assign sel[SW*i +: SW] = row & {SW{rsel[i]}};
        end
        reg [SW-1:0] rd;
        integer j;
        always @* begin rd = {SW{1'b0}}; for (j = 0; j < N; j = j + 1) rd = rd | sel[SW*j +: SW]; end
        always @(posedge clk) dout[LO +: SW] <= rd;
    end endgenerate
    assign q = dout;
`ifndef SYNTHESIS
    initial wptr = {K{1'b0}};
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ve-local arithmetic leaves: the gated hub Engram leaves of rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv (mul4,
// chunk8, add8), identical arithmetic and latency; r3: regional resets from the top relay (rq), valid-only-reset FP
// units (r3ref_ot_s81sl_ve_qmul / _qadd), unit valids chained from the unit before, kept operand copies, ring delay lines.
// ---------------------------------------------------------------------------------------------------------------------
module r3ref_ot_s81sl_ve_mul4 #(parameter integer LM=5,MUT=0)(
 input wire clk,input wire [3:0] rq,input wire v,phase,input wire [127:0] h,k,w,
 output wire vo,output wire vpre,output wire [127:0] hh,kk,dot,output reg fault);
 wire rn=rq[0];
 reg [127:0] hp,kp,wp;reg vp_in,phase_in;
 always @(posedge clk or negedge rn)if(!rn)begin vp_in<=0;phase_in<=0;end else begin vp_in<=v;phase_in<=phase;end
 always @(posedge clk)begin hp<=h;kp<=k;wp<=w;end
 reg vr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=vp_in&&!phase_in;
 wire [127:0] hs,ks,hw,dot_mid;wire [15:0] f;wire [3:0] dv;
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  // one kept operand register per decode (r2: hr fed mh a, mh b and mw a; kr fed mk a, mk b and the key line)
  (* keep = "true" *) reg [31:0] ha,hb,hwa,ka,kb,kl;
  reg [31:0] wl;
  always @(posedge clk)begin ha<=hp[32*l+:32];hb<=hp[32*l+:32];hwa<=hp[32*l+:32];
   ka<=kp[32*l+:32];kb<=kp[32*l+:32];kl<=kp[32*l+:32];wl<=wp[32*l+:32];end
  wire [31:0] kd,dr;wire vh,vk,vw;
  r3ref_ot_s81sl_ve_qmul #(LM) mh(clk,rq[l],vr,ha,hb,hs[32*l+:32],vh,f[4*l]);
  r3ref_ot_s81sl_ve_qmul #(LM) mk(clk,rq[l],vr,ka,kb,ks[32*l+:32],vk,f[4*l+1]);
  r3ref_ot_s81sl_ve_qmul #(LM) mw(clk,rq[l],vr,hwa,wl,hw[32*l+:32],vw,f[4*l+2]);
  r3ref_ot_s81sl_ve_dly #(.W(32),.D(LM)) key_line(clk,kl,kd);
  r3ref_ot_s81sl_ve_qmul #(LM) md(clk,rq[l],vw,hw[32*l+:32],(MUT==1)?32'h3f800000:kd,dr,dv[l],f[4*l+3]);
  reg [31:0] dout;always @(posedge clk)dout<=dr;assign dot_mid[32*l+:32]=dout;
 end endgenerate
 wire [127:0] hmid,kmid;
 r3ref_ot_s81sl_ve_dly #(.W(128),.D(LM+1)) hline(clk,hs,hmid);
 r3ref_ot_s81sl_ve_dly #(.W(128),.D(LM+1)) kline(clk,ks,kmid);
 reg [127:0] hh_pin,kk_pin,dot_pin;
 always @(posedge clk)begin hh_pin<=hmid;kk_pin<=kmid;dot_pin<=dot_mid;end
 assign hh=hh_pin;assign kk=kk_pin;assign dot=dot_pin;
 reg valid;always @(posedge clk or negedge rn)if(!rn)valid<=0;else valid<=dv[0];
 reg valid_pin;always @(posedge clk or negedge rn)if(!rn)valid_pin<=0;else valid_pin<=valid;
 assign vo=valid_pin;assign vpre=valid;wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module r3ref_ot_s81sl_ve_chunk8 #(parameter integer LA=4,MUT=0)(
 input wire clk,input wire [1:0] rq,input wire v,input wire [255:0] x,
 output wire vo,output wire [31:0] sum,output reg fault);
 wire rn=rq[0];
 reg [255:0] xr;reg vr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v;
 always @(posedge clk)xr<=x;
 wire [31:0] acc[0:8];wire [7:0] f;wire [8:0] tv;assign acc[0]=0;assign tv[0]=vr;
 genvar t;
 generate for(t=0;t<8;t=t+1)begin:term
  wire [31:0] xd;
  r3ref_ot_s81sl_ve_dly #(.W(32),.D(LA*t),.MUT(MUT)) operand_line(clk,xr[32*t+:32],xd);
  r3ref_ot_s81sl_ve_qadd #(.LAT(LA)) add(clk,rq[t/4],tv[t],acc[t],xd,acc[t+1],tv[t+1],f[t]);
 end endgenerate
 assign vo=tv[8];assign sum=acc[8];wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module r3ref_ot_s81sl_ve_add8 #(parameter integer LM=5,LA=4)(
 input wire clk,input wire [3:0] rq,input wire v,phase,input wire [255:0] h,value,input wire [31:0] gate,input wire [1:0] copy,
 output reg vo,output reg [255:0] y,output reg fault,output wire [1:0] copy_out);
 wire rn=rq[0];
 reg vr;reg [255:0] hr,valr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v&&phase;
 always @(posedge clk)begin hr<=h;valr<=value;end
 wire [15:0] f;wire [7:0] av;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:lane
  // one kept gate copy per lane (r2: one gr register -> 8 lane multipliers -> their b decodes merged, 264 loads)
  (* keep = "true" *) reg [31:0] gl;
  always @(posedge clk)gl<=gate;
  wire [31:0] prod,hd,ys;wire mvo;
  r3ref_ot_s81sl_ve_qmul #(LM) mul(clk,rq[l/2],vr,valr[32*l+:32],gl,prod,mvo,f[2*l]);
  r3ref_ot_s81sl_ve_dly #(.W(32),.D(LM)) hline(clk,hr[32*l+:32],hd);
  r3ref_ot_s81sl_ve_qadd #(.LAT(LA)) add(clk,rq[l/2],mvo,hd,prod,ys,av[l],f[2*l+1]);
  wire [31:0] rounded=ys+32'h7fff+ys[16];
  always @(posedge clk)y[32*l+:32]<={rounded[31:16],16'd0};
 end endgenerate
 always @(posedge clk or negedge rn)if(!rn)vo<=0;else vo<=av[0];
 wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
 r3ref_ot_s81sl_ve_dly #(.W(2),.D(LM+LA+2)) copy_line(clk,copy,copy_out);
endmodule
