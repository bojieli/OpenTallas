`timescale 1ns/1ps
// ELEM-XFV/XFIN 10-21 (opt-in, OT_S81DV_XFIN_SRAM only): NATIVE32 successor of ot_hdc_fp32_add_f12 #(CUTS) as used
// by ot_dsrom_fp32_add_f12_l6 (CUTS 7'b1101011).  Bit for bit and cycle for cycle the original: the cut bundles
// are unchanged; the widely fanned cut fields (k0 swap / shift amounts / far flags, k3 cancellation shift amount and
// sub select, k5 bypass / zero / rounding carry) get extra KEPT same-edge copies and each consumer group reads its
// own copy (the shifters and the encode are built twice and sliced).  Census r1: k0 135, k3 60, k5 53 loads.
// Shared arithmetic files are unchanged.
module ot_s81dv_kcut #(parameter integer W = 2, parameter integer CUT = 1) (input wire clk, input wire [W-1:0] d,
                                                                        output wire [W-1:0] q);
    generate if (CUT) begin : g_r
        (* keep *) reg [W-1:0] r;
        always @(posedge clk) r <= d;
        assign q = r;
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

module ot_s81dv_fp32_add_f12_n32 #(
    parameter integer CUTS = 7'b1101011
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
    // N32: KEPT same-edge copies of the k0 fan-out fields (swap 4, shift amounts 2+2, far flags 2+2); each consumer
    // group reads its own copy, the alignment shifters are built twice and sliced (low / high half)
    wire [3:0] swc;
    wire [4:0] dba_c0, dba_c1, dab_c0, dab_c1; wire fa_c0, fa_c1, fb_c0, fb_c1;
    ot_s81dv_kcut #(.W(4 + 20 + 4), .CUT(K0)) u_k0c (.clk(clk),
        .d({{4{!cmp_c}}, q6[66:62], q6[66:62], q6[74:70], q6[74:70], g6[0], g6[0], g6[1], g6[1]}),   // q6 dba[4:0] / dab[4:0]
        .q({swc, dba_c0, dba_c1, dab_c0, dab_c1, fa_c0, fa_c1, fb_c0, fb_c1}));
    wire [27:0] sa0 = jam28f(x_aman, dba_c0, fa_c0), sa1 = jam28f(x_aman, dba_c1, fa_c1);
    wire [27:0] sb0 = jam28f(x_bman, dab_c0, fb_c0), sb1 = jam28f(x_bman, dab_c1, fb_c1);
    wire [27:0] small_a = {sa1[27:14], sa0[13:0]};
    wire [27:0] small_b = {sb1[27:14], sb0[13:0]};
    localparam integer W1 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 28;
    wire [W1-1:0] q1;
    ot_hdc_f12_cut #(.W(W1), .CUT(K1)) u_k1 (.clk(clk), .rst_n(rst_n),
        .d({x_v, x_byp, x_sub, swc[0] ? x_bs : x_as, x_err, x_code, swc[0] ? x_bexp : x_aexp,
            swc[1] ? x_bman : x_aman, swc[3] ? small_a[27:14] : small_b[27:14], swc[2] ? small_a[13:0] : small_b[13:0]}),
        .q(q1));
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
    // N32: kept copies of the shift amount (2) and of the sub select (2); the shifter is built twice and sliced
    wire [4:0] lzc0, lzc1; wire sbc0, sbc1;
    ot_s81dv_kcut #(.W(12), .CUT(K3)) u_k3c (.clk(clk), .d({lz_w[4:0], lz_w[4:0], t_sub, t_sub}), .q({lzc0, lzc1, sbc0, sbc1}));
    wire [26:0] sv0 = w_dif[26:0] << lzc0, sv1 = w_dif[26:0] << lzc1;
    wire [26:0] sub_val = {sv1[26:13], sv0[12:0]};
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_inc_k #(.W(8)) u_eadd (.a(w_exp), .inc(w_carry), .y(exp_add), .co(exp_add_c));
    localparam integer W4 = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27;
    wire [W4-1:0] q4;
    ot_hdc_f12_cut #(.W(W4), .CUT(K4)) u_k4 (.clk(clk), .rst_n(rst_n),
        .d({w_v, w_byp, w_sign, w_sub && (w_dif == 28'd0), w_err, w_code, sbc0 ? exp_sub : exp_add,
            sbc1 ? sub_val[26:13] : w_add[26:13], sbc0 ? sub_val[12:0] : w_add[12:0]}), .q(q4));
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
    // N32: the encode is built twice from KEPT copies of {byp, zero, rnd_c} (y[15:0] / y[31:16] + err)
    wire [1:0] bypc, zc, rcc;
    ot_s81dv_kcut #(.W(6), .CUT(K5)) u_k5c (.clk(clk), .d({s2_byp, s2_byp, s2_zero, s2_zero, rnd_cw, rnd_cw}),
        .q({bypc, zc, rcc}));
    reg [31:0] yh [0:1]; reg [1:0] eh [0:1];
    genvar h;
    for (h = 0; h < 2; h = h + 1) begin : g_enc
        wire [23:0] man = rcc[h] ? {1'b1, rnd[23:1]} : rnd;
        wire [8:0]  e = {1'b0, u_exp} + {8'd0, rcc[h]};
        wire subnormal = (e == 9'd1) && !man[23];
        wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
        wire over = (u_exp == 8'hff) || (e >= 9'd255);
        always @(*) begin
            if (bypc[h]) begin yh[h] = u_code; eh[h] = u_err; end
            else if (zc[h]) begin yh[h] = 32'd0; eh[h] = E_NONE; end
            else if (over) begin yh[h] = 32'd0; eh[h] = E_OVERFLOW; end
            else begin yh[h] = (code[30:0] == 31'd0) ? 32'd0 : code; eh[h] = E_NONE; end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= u_v;
            y <= {yh[1][31:16], yh[0][15:0]}; err <= eh[1];
        end
    end
endmodule

module ot_s81dv_qadd_n32 #(parameter integer LAT = 6) (
    input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b, output wire [31:0] y,
    output wire fault
);
    generate if (LAT == 6) begin : g6
        wire [1:0] err; wire vo;
        ot_s81dv_fp32_add_f12_n32 #(.CUTS(7'b1101011)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y),
            .err(err), .valid_out(vo));
        assign fault = vo && (err != 2'd0);
    end else begin : g_bad
        ot_s81dv_qadd_n32_requires_LAT6 u_bad();
    end endgenerate
endmodule

// ot_dsrom_rsqrt verbatim (same Newton steps, constants, depth) with its three adds on ot_s81dv_qadd_n32.
module ot_s81dv_rsqrt_n32 #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer IT = 3 * LM + LA;
    localparam integer DEPTH = 1 + 3 * IT;      // 37 (LM 3), 46 (LM 4)
    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    wire [31:0] y0_n;
    wire        unused_cy;
    ot_hdc_kadd #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_y0 (.a(32'h5F3759DF), .b(~{1'b0, x[31:1]}), .cin(1'b1), .s(y0_n),
                                                      .cout(unused_cy));
    always @(posedge clk) y0 <= y0_n;
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_s81dv_qmul_n32 #(LM) m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // LM
    ot_hdc_delay #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 1 + LM
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay #(.W(32), .D(IT)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_s81dv_qmul_n32 #(LM) m_yy (clk, rst_n, vd[1 + IT*k],             yi[k], yi[k], yy[k], f[4*k]);
            ot_s81dv_qmul_n32 #(LM) m_hm (clk, rst_n, vd[1 + IT*k + LM],        hd[k], yy[k], hm[k], f[4*k+1]);
            ot_s81dv_qadd_n32 #(.LAT(LA)) a_s  (clk, rst_n, vd[1 + IT*k + 2*LM],      32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay #(.W(32), .D(2*LM + LA)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_s81dv_qmul_n32 #(LM) m_y  (clk, rst_n, vd[1 + IT*k + 2*LM + LA], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// ELEM-XFV/XFIN 10-21: NATIVE32 successor of ot_hdc_fp32_mul_f12 #(8'b01101010) (ot_hdc_qmul_lat LAT 5), bit and cycle
// equal; kept copies at k1 (significands, split AND rows), k3 (power, 4 mask quarters), k5 (top, shift), k7 (encode x2).
module ot_s81dv_fp32_mul_f12_n32 #(
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
    function automatic [5:0] shq;               // the subnormal shift amount (shc) of a power
        input signed [11:0] pwr;
        reg signed [11:0] sh;
        begin
            sh = -(pwr + 12'sd149);
            shq = (sh > 12'sd63) ? 6'd63 : sh[5:0];
        end
    endfunction
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
    // N32: two KEPT copies each of the normalised significands; partial product (row i, bit k) reads a copy
    // [i >= 12][k] and b copy [k >= 12][i], so no significand bit drives more than 12 AND rows
    wire [23:0] pa0, pa1, pb0, pb1;
    ot_s81dv_kcut #(.W(96), .CUT(K1)) u_k1c (.clk(clk), .d({a_n, a_n, b_n, b_n}), .q({pa0, pa1, pb0, pb1}));
    ot_s81dv_mul24_rows_n32 u_rows (.a0(pa0), .a1(pa1), .b0(pb0), .b1(pb1), .rows(rows));
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
    // N32: the 96 mask compares read four KEPT copies of the power (one per 24 compares)
    wire [11:0] pw [0:3];
    ot_s81dv_kcut #(.W(48), .CUT(K3)) u_k3c (.clk(clk), .d({4{s1_power}}), .q({pw[3], pw[2], pw[1], pw[0]}));
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shq(pw[k / 24])} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shq(pw[2 + k / 24])} - 12'd1);
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
    // N32: KEPT copies of the product's top bit (3 select groups) and of the subnormal shift (2, sliced shifter)
    wire [2:0] tpc; wire [5:0] shk0, shk1;
    ot_s81dv_kcut #(.W(15), .CUT(K5)) u_k5c (.clk(clk), .d({{3{prod[47]}}, q_sh, q_sh}), .q({tpc, shk0, shk1}));
    wire top = tpc[0];
    wire is_sub = tpc[0] ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = tpc[0] ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = {tpc[1] ? s2_prod[47:36] : s2_prod[46:35], tpc[2] ? s2_prod[35:24] : s2_prod[34:23]};
    wire n_rb = tpc[0] ? s2_prod[23] : s2_prod[22];
    wire n_st = tpc[0] ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] ssh0 = s2_prod >> shk0, ssh1 = s2_prod >> shk1;
    wire [23:0] s_main = {ssh1[23:12], ssh0[11:0]};
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
    wire [7:0]  fa = tpc[1] ? fa47 : fa46, fb = tpc[2] ? fb47 : fb46;
    wire        oa = tpc[1] ? oa47 : oa46, ob = tpc[2] ? ob47 : ob46;
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
    // N32: built twice (y[15:0] / y[31:16] + err) from KEPT k6 copies of {byp, sub, main, inc}; each half has its
    // own rounding increment (K7 = 0: the encode follows the round in the same stage)
    wire [1:0] obc, osc, inc6;
    wire [23:0] mn6 [0:1];
    ot_s81dv_kcut #(.W(54), .CUT(K6)) u_k6c (.clk(clk),
        .d({s2_byp, s2_byp, is_sub, is_sub, rb && (st || main[0]), rb && (st || main[0]), main, main}),
        .q({obc, osc, inc6, mn6[1], mn6[0]}));
    reg [31:0] yh [0:1]; reg [1:0] eh [0:1];
    genvar h;
    for (h = 0; h < 2; h = h + 1) begin : g_enc
        wire [23:0] rnd_h; wire rc_h;
        ot_hdc_inc_k #(.W(24)) u_rnd_h (.a(mn6[h]), .inc(inc6[h]), .y(rnd_h), .co(rc_h));
        wire [23:0] rnd = rnd_h;
        wire carry = !osc[h] && rc_h;
        wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
        wire over = !osc[h] && (carry ? o_ob : o_oa);
        wire [7:0] field = carry ? o_fb : o_fa;
        wire sub_carry = osc[h] && rnd[23];
        wire [31:0] code = osc[h] ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                                  : {o_sign, field, man[22:0]};
        always @(*) begin
            if (obc[h]) begin yh[h] = 32'd0; eh[h] = o_err; end
            else if (over) begin yh[h] = 32'd0; eh[h] = E_OVERFLOW; end
            else begin yh[h] = (code[30:0] == 31'd0) ? 32'd0 : code; eh[h] = E_NONE; end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= o_v;
            y <= {yh[1][31:16], yh[0][15:0]}; err <= eh[1];
        end
    end
endmodule

// ot_hdc_mul24_rows with split operand copies: partial product (row i, bit k) = a[i >= 12 ? 1 : 0][k] & b[k >= 12][i]
module ot_s81dv_mul24_rows_n32 (
    input  wire [23:0] a0, a1, b0, b1,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i, k;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            wire [23:0] pp;
            for (k = 0; k < 24; k = k + 1) begin : g_b
                assign pp[k] = (i >= 12 ? a1[k] : a0[k]) & (k >= 12 ? b1[i] : b0[i]);
            end
            assign l0[48*i +: 48] = {24'd0, pp} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule
module ot_s81dv_qmul_n32 #(parameter integer LAT = 5) (
    input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b, output wire [31:0] y,
    output wire fault
);
    generate if (LAT == 5) begin : g_l5
        wire [1:0] err; wire vo;
        ot_s81dv_fp32_mul_f12_n32 #(.CUTS(8'b01101010)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y),
            .err(err), .valid_out(vo));
        assign fault = vo && (err != 2'd0);
    end else begin : g_bad
        ot_s81dv_qmul_n32_requires_LAT5 u_bad();
    end endgenerate
endmodule

// ELEM-XFV/XFIN 10-21: NATIVE32 copy of ot_dsrom_divc (same stages, values, latency 9): kept copies of the normalise
// shift, the guard/sticky shift and mask, and the encode selects; shifters / masks / encode built twice and sliced.
module ot_s81dv_divc_n32 #(
    parameter integer F = 5,
    parameter integer K = 10
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer LATENCY = 9;
    initial if (F != 1 && F != 5) $error("ot_s81dv_divc_n32: F must be 1 or 5");
    wire [LATENCY:0] vl;
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    assign vo = vl[LATENCY];

    // -- S1: decode, leading-zero count of the significand ---------------------------------
    reg        s1_s, s1_z, s1_nf, s1_sub;
    reg [23:0] s1_m;
    reg [7:0]  s1_e;
    reg [4:0]  s1_lz;
    (* keep *) reg [4:0] lzc0, lzc1;          // N32: kept copies of the normalise shift (sliced shifter)
    reg [4:0]  lz;
    wire [23:0] m0 = {(x[30:23] != 8'd0), x[22:0]};
    integer i;
    always @(*) begin
        lz = 5'd0;
        for (i = 0; i < 24; i = i + 1) if (m0[i]) lz = 5'd23 - i[4:0];
    end
    always @(posedge clk) begin
        s1_s <= x[31];
        s1_z <= (x[30:0] == 31'd0);
        s1_nf <= (x[30:23] == 8'hFF);
        s1_sub <= (x[30:23] == 8'd0);
        s1_m <= m0;
        s1_e <= x[30:23];
        s1_lz <= lz;
        lzc0 <= lz; lzc1 <= lz;
    end
    // -- S2: normalise ------------------------------------------------------------------------
    wire [23:0] sl0 = s1_m << lzc0, sl1 = s1_m << lzc1;
    reg               s2_s, s2_z, s2_nf;
    reg [23:0]        s2_m;
    reg signed [10:0] s2_eu;                 // unbiased exponent of the normalised significand
    always @(posedge clk) begin
        s2_s <= s1_s; s2_z <= s1_z; s2_nf <= s1_nf;
        s2_m <= {sl1[23:12], sl0[11:0]};
        s2_eu <= (s1_sub ? -11'sd126 : ($signed({3'b000, s1_e}) - 11'sd127)) - $signed({6'd0, s1_lz});
    end
    // -- S3, S4: floor(m / 5), m mod 5: radix-16 digits, three a stage --------------------------
    function automatic [6:0] dstep(input [2:0] r, input [3:0] d);   // {q digit[3:0], remainder[2:0]}
        reg [6:0] t, q, m;
        begin
            t = {r, d};                       // r * 16 + d, <= 79
            q = t / 7'd5;
            m = t % 7'd5;
            dstep = {q[3:0], m[2:0]};
        end
    endfunction
    // three stages of two digits: S3 digits 0-1, S3b digits 2-3, S4 digits 4-5
    reg               s3_s, s3_z, s3_nf, s3b_s, s3b_z, s3b_nf;
    reg [23:0]        s3_m, s3b_m;
    reg [7:0]         s3_qh;
    reg [15:0]        s3b_qh;
    reg [2:0]         s3_r, s3b_r;
    reg signed [10:0] s3_eu, s3b_eu;
    reg [6:0] d0, d1, d2, d3, d4, d5;
    always @(*) begin
        d0 = dstep(3'd0, s2_m[23:20]);
        d1 = dstep(d0[2:0], s2_m[19:16]);
        d2 = dstep(s3_r, s3_m[15:12]);
        d3 = dstep(d2[2:0], s3_m[11:8]);
        d4 = dstep(s3b_r, s3b_m[7:4]);
        d5 = dstep(d4[2:0], s3b_m[3:0]);
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf; s3_m <= s2_m; s3_eu <= s2_eu;
        s3_qh <= {d0[6:3], d1[6:3]};
        s3_r <= d1[2:0];
        s3b_s <= s3_s; s3b_z <= s3_z; s3b_nf <= s3_nf; s3b_m <= s3_m; s3b_eu <= s3_eu;
        s3b_qh <= {s3_qh, d2[6:3], d3[6:3]};
        s3b_r <= d3[2:0];
    end
    reg               s4_s, s4_z, s4_nf;
    reg [23:0]        s4_qm;
    reg [2:0]         s4_r0;
    reg signed [10:0] s4_eu;
    always @(posedge clk) begin
        s4_s <= s3b_s; s4_z <= s3b_z; s4_nf <= s3b_nf; s4_eu <= s3b_eu;
        s4_qm <= (F == 5) ? {s3b_qh, d4[6:3], d5[6:3]} : s3b_m;
        s4_r0 <= (F == 5) ? d5[2:0] : 3'd0;
    end
    // -- S5: the exact truncated quotient Q (50 bits), its exponent and the shift --------------------
    function automatic [25:0] tail(input [2:0] r);                    // floor(r * 2^26 / 5)
        case (r)
            3'd1: tail = 26'd13421772;
            3'd2: tail = 26'd26843545;
            3'd3: tail = 26'd40265318;
            3'd4: tail = 26'd53687091;
            default: tail = 26'd0;
        endcase
    endfunction
    reg               s5_s, s5_z, s5_nf, s5_st0, s5_sub;
    reg [49:0]        s5_q;
    reg [5:0]         s5_sh;
    (* keep *) reg [5:0] shc0, shc1, shc2, shc3;   // N32: kept copies (guard/sticky shifter halves, mask halves)
    reg signed [10:0] s5_er;
    reg [5:0]         lead;
    reg signed [10:0] er;
    reg signed [11:0] sh;
    always @(*) begin
        lead = (F == 5) ? (s4_qm[21] ? 6'd47 : 6'd46) : 6'd49;
        er = s4_eu - 11'sd49 - K + $signed({5'd0, lead});
        sh = $signed({6'd0, lead}) - 12'sd23 + ((er < -11'sd126) ? (-12'sd126 - er) : 12'sd0);
    end
    always @(posedge clk) begin
        s5_s <= s4_s; s5_z <= s4_z; s5_nf <= s4_nf;
        s5_q <= {s4_qm, tail(s4_r0)};
        s5_st0 <= (s4_r0 != 3'd0);
        s5_er <= er;
        s5_sub <= (er < -11'sd126);
        s5_sh <= (sh > 12'sd51) ? 6'd51 : sh[5:0];         // 51: every bit of Q below the guard (sticky only)
        shc0 <= (sh > 12'sd51) ? 6'd51 : sh[5:0]; shc1 <= (sh > 12'sd51) ? 6'd51 : sh[5:0];
        shc2 <= (sh > 12'sd51) ? 6'd51 : sh[5:0]; shc3 <= (sh > 12'sd51) ? 6'd51 : sh[5:0];
    end
    // -- S6: shift, guard, sticky ---------------------------------------------------------------------
    reg               s6_s, s6_z, s6_nf, s6_g, s6_st, s6_sub;
    reg [24:0]        s6_m;
    reg signed [10:0] s6_er;
    reg [50:0]        w;
    wire [50:0] w0 = {s5_q, 1'b0} >> shc0, w1 = {s5_q, 1'b0} >> shc1;
    always @(*) w = {w1[50:13], w0[12:0]};    // w[0]: guard; the bits shifted out below it: sticky
    reg [49:0] lowmask, lm0, lm1;
    always @(posedge clk) begin
        s6_s <= s5_s; s6_z <= s5_z; s6_nf <= s5_nf; s6_er <= s5_er; s6_sub <= s5_sub;
        s6_m <= w[25:1];
        s6_g <= w[0];
        lm0 = (shc2 == 6'd0) ? 50'd0 : ((50'd1 << (shc2 - 6'd1)) - 50'd1);
        lm1 = (shc3 == 6'd0) ? 50'd0 : ((50'd1 << (shc3 - 6'd1)) - 50'd1);
        lowmask = {lm1[49:25], lm0[24:0]};
        s6_st <= s5_st0 | ((s5_q & lowmask) != 50'd0);
    end
    // -- S7: round ------------------------------------------------------------------------------------
    reg               s7_s, s7_z, s7_nf, s7_sub;
    reg [24:0]        s7_m;
    reg signed [10:0] s7_er;
    wire [24:0] s6_mi;
    ot_hdc_kinc #(.W(25), .K(1)) u_inc (.a(s6_m), .inc(s6_g & (s6_st | s6_m[0])), .y(s6_mi));   // keep-prefix
    (* keep *) reg [1:0] s7_zc, s7_nfc, s7_subc;   // N32: encode built twice from kept select copies
    always @(posedge clk) begin
        s7_s <= s6_s; s7_z <= s6_z; s7_nf <= s6_nf; s7_er <= s6_er; s7_sub <= s6_sub;
        s7_m <= s6_mi;
        s7_zc <= {2{s6_z}}; s7_nfc <= {2{s6_nf}}; s7_subc <= {2{s6_sub}};
    end
    reg [31:0] yh [0:1];
    integer h;
    always @(*)
        for (h = 0; h < 2; h = h + 1)
            if (s7_nfc[h] || s7_zc[h] || s7_m == 25'd0) yh[h] = 32'd0;
            else if (s7_subc[h]) yh[h] = {s7_s, (s7_m[23] ? 8'd1 : 8'd0), s7_m[22:0]};
            else if (s7_m[24]) yh[h] = {s7_s, s7_er[7:0] + 8'd128, 23'd0};
            else yh[h] = {s7_s, s7_er[7:0] + 8'd127, s7_m[22:0]};
    // -- S8: encode ---------------------------------------------------------------------------------------
    always @(posedge clk) begin
        fault <= vl[8] && s7_nf;
        y <= {yh[1][31:16], yh[0][15:0]};
    end
endmodule
