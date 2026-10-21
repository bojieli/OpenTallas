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
    ot_hdc_qmul_lat #(LM) m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // LM
    ot_hdc_delay #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 1 + LM
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay #(.W(32), .D(IT)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_qmul_lat #(LM) m_yy (clk, rst_n, vd[1 + IT*k],             yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_qmul_lat #(LM) m_hm (clk, rst_n, vd[1 + IT*k + LM],        hd[k], yy[k], hm[k], f[4*k+1]);
            ot_s81dv_qadd_n32 #(.LAT(LA)) a_s  (clk, rst_n, vd[1 + IT*k + 2*LM],      32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay #(.W(32), .D(2*LM + LA)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_qmul_lat #(LM) m_y  (clk, rst_n, vd[1 + IT*k + 2*LM + LA], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule
