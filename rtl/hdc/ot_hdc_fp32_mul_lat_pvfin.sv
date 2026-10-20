`timescale 1ns/1ps
// KV-PARAMS4 10-20: native-32 successor of ot_hdc_fp32_mul_lat #(.LAT(6)) (the K-tree scale multiply), bit for bit and
// cycle for cycle (every flop the LAT-6/DRST-1 original resets is reset here to the same value, on bounded leaves).
// Changes vs the original: (1) the reset of each fully-reset cut is spread over leaves of <= 28 flops (rst_v);
// (2) kept same-edge copies of the S3a selects (top = prod[47], sub47/46) and the subnormal shift amount captured one-hot
// (48 b, through c2), masks decoded from 6 kept s1_power copies, so no select drives more than ~32 loads.  0 added cycles.
// Uses ot_hdc_w11_cut (rtl/hdc/ot_hdc_fp32_add_lat.sv), ot_hdc_mul24_rows (rtl/hdc/ot_hdc_fastfp.sv), ot_hdc_ksadd_k, ot_hdc_lzc32.
module ot_hdc_fp32_mul_lat_pvfin #(
    parameter integer LAT = 6,
    parameter integer MUT = 0,
    // BCONST_EN = 1: operand b is the constant BCONST (the K-tree SCALE); the b port is ignored, so the b-side decode folds
    parameter integer BCONST_EN = 0,
    parameter [31:0]  BCONST = 32'd0
) (
    input  wire        clk,
    input  wire [25:0] rst_v,      // 21 bounded reset leaves (each <= 28 flops; native census <= 32)
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [63:0] a_nrm,     // 2 copies of a (same value, separate drivers) for the subnormal normalise; tie to {a, a}
    input wire [63:0] b_nrm,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    generate if (LAT != 6) begin : g_bad_lat
        ot_hdc_fp32_mul_lat_ncr_needs_LAT_6 u_trap ();
    end endgenerate
    localparam integer CUTS = -1, KCP = 1, DRST = 1;
    // leaf map: c1 -> rst_v[3:0], c2 -> rst_v[13:4], c3 -> rst_v[15:14], s1_v/s2_v/err/valid_out -> rst_v[16], y -> rst_v[18:17], c3 B copy -> rst_v[19], a_n B copy -> rst_v[20]
    wire rst_n = rst_v[16];
    localparam integer CUT1 = (CUTS >= 0) ? CUTS % 2       : (LAT >= 6) ? 1 : 0;
    localparam integer CUT2 = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 5) ? 1 : 0;
    localparam integer CUT3 = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT4 = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;
    localparam integer CUT5 = (CUTS >= 0) ? (CUTS / 16) % 2 : (LAT >= 8) ? 1 : 0;
    localparam integer CUT6 = (CUTS >= 0) ? (CUTS / 32) % 2 : (LAT >= 9) ? 1 : 0;
    localparam integer CUT7 = (CUTS >= 0) ? (CUTS / 64) % 2 : (LAT >= 10) ? 1 : 0;
    generate if (CUTS >= 0 && CUT1 + CUT2 + CUT3 + CUT4 + CUT5 + CUT6 + CUT7 + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_mul_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- S1a: decode, normalise --------------------------------------------------------------------
    // C7: field / zero / non-finite decode | LZC, power
    wire [31:0] b_in = (BCONST_EN != 0) ? BCONST : b;
    wire [68:0] c7;
    ot_hdc_w11_cut #(.W(69), .CUT(CUT7), .VB(DRST ? -1 : 69-1)) u_c7 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a, b_in, (a[30:23] == 8'd0), (b_in[30:23] == 8'd0),
            (a[30:23] == 8'hff) || (b_in[30:23] == 8'hff), (a[30:0] == 31'd0) || (b_in[30:0] == 31'd0)}), .q(c7));
    wire        x_v, x_afz, x_bfz, nonfinite, zero;
    wire [31:0] x_a, x_b;
    assign {x_v, x_a, x_b, x_afz, x_bfz, nonfinite, zero} = c7;
    wire [7:0]  a_field = x_a[30:23];
    wire [7:0]  b_field = x_b[30:23];
    wire [23:0] a_raw = {!x_afz, x_a[22:0]};
    wire [23:0] b_raw = {!x_bfz, x_b[22:0]};
    wire [5:0] a_lz, b_lz;
    // NCR: subnormal normalise by a one-hot leading-one select (each one-hot bit drives <= 24 AND legs; the binary LZC
    // count drove a 24-wide barrel shifter, 45..49 loads); lz and the shifted mantissa equal lzc32({x, 8'hff}) / x << lz.
    wire [23:0] a_norm, b_norm;
    // the a-side normalise is split over 3 drivers of the same value (a, a_nrm[31:0], a_nrm[63:32]): output bits 7:0,
    // 15:8 + lz, 23:16 (one flattened 24-bit normalise cone loaded one mantissa bit 48 times)
    wire [23:0] a_raw_n0 = a_raw, a_raw_n1 = {(a_nrm[30:23] != 8'd0), a_nrm[22:0]}, a_raw_n2 = {(a_nrm[62:55] != 8'd0), a_nrm[54:32]};
    wire [23:0] an0, an1, an2; wire [5:0] alz0, alz2;
    ot_hdc_norm24_oh u_la0 (.x(a_raw_n0), .lz(alz0), .y(an0));
    ot_hdc_norm24_oh u_la1 (.x(a_raw_n1), .lz(a_lz), .y(an1));
    ot_hdc_norm24_oh u_la2 (.x(a_raw_n2), .lz(alz2), .y(an2));
    assign a_norm = {an2[23:16], an1[15:8], an0[7:0]};
    wire [23:0] bn0,bn1,bn2;wire [5:0] blz0,blz2;
    ot_hdc_norm24_oh u_lb0(.x(b_raw),.lz(blz0),.y(bn0));
    ot_hdc_norm24_oh u_lb1(.x({(b_nrm[30:23]!=0),b_nrm[22:0]}),.lz(b_lz),.y(bn1));
    ot_hdc_norm24_oh u_lb2(.x({(b_nrm[62:55]!=0),b_nrm[54:32]}),.lz(blz2),.y(bn2));
    assign b_norm={bn2[23:16],bn1[15:8],bn0[7:0]};
    wire signed [11:0] a_power = x_afz ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = x_bfz ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    // C5: decode / LZC | normalise shift
    localparam integer W5 = 1 + 1 + 2 + 1 + 24 + 24 + 5 + 5 + 12 + 12;
    wire [W5-1:0] c5;
    ot_hdc_w11_cut #(.W(W5), .CUT(CUT5), .VB(DRST ? -1 : W5-1)) u_c5 (.clk(clk), .rst_n(rst_n),
        .d({x_v, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), x_a[31] ^ x_b[31], a_raw, b_raw, a_lz[4:0],
            b_lz[4:0], a_power, b_power}), .q(c5));
    wire        n_v, n_bz, n_sign;
    wire [1:0]  n_err;
    wire [23:0] n_ar, n_br;
    wire [4:0]  n_al, n_bl;
    wire [11:0] n_ap, n_bp;
    assign {n_v, n_bz, n_err, n_sign, n_ar, n_br, n_al, n_bl, n_ap, n_bp} = c5;
    wire [23:0] a_n = a_norm;   // CUT5 = 0 at LAT 6: n_ar == a_raw, n_al == a_lz[4:0]
    wire [23:0] b_n = b_norm;
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] c1;
    ot_hdc_w11_cut_rn #(.W(W1), .NR(4)) u_c1 (.clk(clk), .rst_n(rst_v[3:0]),
        .d({n_v, n_bz, n_err, n_sign, a_n, b_n, n_ap, n_bp}),
        .q(c1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = c1;
    // ---- S1b: rows, exponent sum ------------------------------------------------------------------
    wire [11:0] power;
    wire power_c;
    // NCR (gate-flow census: c1 b_n bit 119 / a_n bit 36 loads): with a constant b the b operand and its power are used
    // as constants (their c1 flops only differ from them in the reset window, whose payload is never read: valid is
    // reset), and the a operand is registered twice (kept copy aB on its own leaf): rows 0..11 read c1, rows 12..23 aB.
    (* keep="true",dont_touch="true" *) reg [23:0] aB;
    always @(posedge clk or negedge rst_v[20]) if (!rst_v[20]) aB <= 24'd0; else aB <= a_n;
    (* keep="true",dont_touch="true" *) reg [23:0] aC,aD,bB,bC,bD;
    always @(posedge clk or negedge rst_v[21])if(!rst_v[21])aC<=0;else aC<=a_n;
    always @(posedge clk or negedge rst_v[22])if(!rst_v[22])aD<=0;else aD<=a_n;
    always @(posedge clk or negedge rst_v[23])if(!rst_v[23])bB<=0;else bB<=b_n;
    always @(posedge clk or negedge rst_v[24])if(!rst_v[24])bC<=0;else bC<=b_n;
    always @(posedge clk or negedge rst_v[25])if(!rst_v[25])bD<=0;else bD<=b_n;
    wire [23:0] pb_u  = (BCONST_EN != 0) ? b_n  : p_b;
    wire [11:0] pbp_u = (BCONST_EN != 0) ? n_bp : p_bp;
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(p_ap), .b(pbp_u), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    generate if (KCP > 1 && CUT1 != 0) begin : g_kcp
        wire [KCP*24-1:0] ka, kb;
        genvar k;
        for (k = 0; k < KCP; k = k + 1) begin : g_c
            ot_hdc_mul_kcp48 u_k (.clk(clk), .rst_n(rst_n),
`ifdef NEGK
                .d({a_n ^ ((k == 1) ? 24'd1 : 24'd0), b_n}),   // bench negative control only
`else
                .d({a_n, b_n}),
`endif .q({ka[24*k +: 24], kb[24*k +: 24]}));
        end
        ot_hdc_mul24_rows_k #(.K(KCP)) u_rows (.a(ka), .b(kb), .rows(rows));
    end else begin : g_nokcp
        ot_hdc_mul24_rows_pvfin u_rows(.a({aD,aC,aB,p_a}),.b({bD,bC,bB,p_b}),.rows(rows));
    end endgenerate

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= p_v;
    end
    always @(posedge clk) begin
        s1_byp <= p_byp; s1_err <= p_err; s1_sign <= p_sign; s1_rows <= rows; s1_power <= power;
    end

    // ---- S2a: compress to two rows; masks ----------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
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
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    // NCR: the subnormal round / sticky masks and the shift one-hot are decoded in 6 groups of 8 indexes, each from its
    // own kept copy of s1_power (a shared shc decode drove 48..49 legs); the one-hot rides through c2 instead of shc.
    (* keep="true",dont_touch="true" *) reg signed [11:0] s1_pwc0, s1_pwc1, s1_pwc2, s1_pwc3, s1_pwc4, s1_pwc5;
    always @(posedge clk) begin s1_pwc0 <= power; s1_pwc1 <= power; s1_pwc2 <= power; s1_pwc3 <= power; s1_pwc4 <= power; s1_pwc5 <= power; end
    wire signed [12*6-1:0] pwc = {s1_pwc5, s1_pwc4, s1_pwc3, s1_pwc2, s1_pwc1, s1_pwc0};
    // R15 (KV-PVFIN15 10-20, R14 gate OT_HOLD_STALL): no zero-logic flop->flop hop.  S2a only clamps the shift amount
    // (6 b per group of 8 indexes, from its own kept s1_power copy) into c2; the round / sticky / one-hot masks are
    // decoded in S2b from the registered amount straight into s2_mr / s2_ms / s2_shoh (same expressions, same values,
    // same cycle).  c2 carries fl46 only; S2b registers fl47 = fl46 + 1 and S3a forms fl46 = fl47 - 1 (mod 2^12 exact).
    reg [35:0] m_shk;
    integer k;
    always @* begin
        for (k = 0; k < 6; k = k + 1) begin : g_mk
            reg signed [11:0] pk, shs;
            pk = pwc[12*k +: 12];
            shs = -(pk + 12'sd149);
            m_shk[6*k +: 6] = (shs > 12'sd63) ? 6'd63 : shs[5:0];
        end
    end
    localparam integer W2 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 36;
    wire [W2-1:0] c2;
    ot_hdc_w11_cut_rn #(.W(W2), .NR(10)) u_c2 (.clk(clk), .rst_n(rst_v[13:4]),
        .d({s1_v, s1_byp, s1_err, s1_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl46, m_shk}),
        .q(c2));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl46;
    wire [35:0] q_shk;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl46, q_shk} = c2;
    reg [47:0] q_mr, q_ms, q_oh;
    integer kk;
    always @* begin
        for (kk = 0; kk < 48; kk = kk + 1) begin : g_md
            reg [5:0] shk;
            shk = q_shk[6*(kk/8) +: 6];
            q_mr[kk] = ({6'd0, kk[5:0]} == {6'd0, shk} - 12'd1);
            q_ms[kk] = ({6'd0, kk[5:0]} < {6'd0, shk} - 12'd1);
            q_oh[kk] = (kk[5:0] == shk);
        end
    end
    // ---- S2b: the prefix add -----------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg signed [11:0] s2_fl47;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= q_v;
    end
    always @(posedge clk) begin
        s2_byp <= q_byp; s2_err <= q_err; s2_sign <= q_sign;
        s2_prod <= prod;
        s2_sub47 <= q_s47; s2_sub46 <= q_s46;
        s2_fl47 <= q_fl46 + 12'sd1;
        s2_mr <= q_mr; s2_ms <= q_ms;
    end
    // NCR: kept same-edge copies of the S3a select controls (census: s2_sh[0] 130, s2_prod[47] 78 loads), is_sub registered
    // (top ? sub47 : sub46 beside the S2b prefix add) and the subnormal shift amount carried ONE-HOT through c2:
    // s_main[i] = OR_k prod[i+k] & oh[k], each one-hot bit drives <= 24 AND terms.  Values identical.
    (* keep="true",dont_touch="true" *) reg [15:0] s2_top;     // [11:0]: one per 2 bits of n_main; 12..15 fl / n_rb / n_st / spare
    (* keep="true",dont_touch="true" *) reg [9:0]  s2_isc;     // is_sub = top ? sub47 : sub46, registered: [7:0] one per 3 main bits
    (* keep="true",dont_touch="true" *) reg [47:0] s2_shoh;
    wire top_n = prod[47];
`ifdef KVP3_MUT7
    wire top_d = prod[46];                             // bench mutant 7 (must FAIL): the wrong normalisation bit
`else
    wire top_d = top_n;
`endif
    always @(posedge clk) begin
        s2_top <= {16{top_d}};
        s2_isc <= {10{top_n ? q_s47 : q_s46}};
        s2_shoh <= q_oh;
    end

    // ---- S3a: select, subnormal shift, round/sticky bits ------------------------------------------
    wire is_sub = s2_isc[8];
    wire signed [11:0] s2_fl46 = s2_fl47 - 12'sd1;
    wire signed [11:0] fl = s2_top[12] ? s2_fl47 : s2_fl46;
    wire [23:0] main;
    reg  [23:0] s_main;
    integer si, sk;
    always @* begin
        for (si = 0; si < 24; si = si + 1) begin
            s_main[si] = 1'b0;
            for (sk = 0; sk + si < 48; sk = sk + 1) s_main[si] = s_main[si] | (s2_prod[si + sk] & s2_shoh[sk]);
        end
    end
    genvar gq;
    generate for (gq = 0; gq < 24; gq = gq + 1) begin : g_sel
        wire nm = s2_top[gq / 2] ? s2_prod[24 + gq] : s2_prod[23 + gq];
        assign main[gq] = s2_isc[gq / 3] ? s_main[gq] : nm;
    end endgenerate
    wire n_rb = s2_top[13] ? s2_prod[23] : s2_prod[22];
    wire n_st = s2_top[14] ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire rb = s2_isc[9] ? s_rb : n_rb;
    wire st = s2_isc[9] ? s_st : n_st;
    localparam integer W3 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W3-1:0] c3;
    ot_hdc_w11_cut_rn #(.W(W3), .NR(2)) u_c3 (.clk(clk), .rst_n(rst_v[15:14]),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, fl, main, rb && (st || main[0])}), .q(c3));
    wire        r_v, r_byp, r_sign, r_sub, r_inc;
    wire [1:0]  r_err;
    wire [11:0] r_fl;
    wire [23:0] r_main;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_fl, r_main, r_inc} = c3;
    // NCR: a second (B) copy of the c3 encode controls {byp, sign, sub, fl} on its own reset leaf: y[31:16] is encoded
    // from it, y[15:0] from c3, so the overflow / zero-result select is two cones of 16 (one cone drove 33).
    wire [14:0] c3b;
    ot_hdc_w11_cut_rn #(.W(15), .NR(1)) u_c3b (.clk(clk), .rst_n(rst_v[19:19]), .d({s2_byp, s2_sign, is_sub, fl}), .q(c3b));
    wire        b_byp, b_sign, b_sub;
    wire signed [11:0] b_fl;
    assign {b_byp, b_sign, b_sub, b_fl} = c3b;
    // ---- S3b: round ---------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k #(.W(24)) u_rnd (.a(r_main), .b(24'd0), .cin(r_inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer W4 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W4-1:0] c4;
    ot_hdc_w11_cut #(.W(W4), .CUT(CUT4), .VB(DRST ? -1 : W4-1)) u_c4 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, r_fl, rnd_w, rnd_cw}), .q(c4));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c;
    wire [1:0]  o_err;
    wire signed [11:0] o_fl;
    wire [23:0] rnd;
    assign {o_v, o_byp, o_err, o_sign, o_sub, o_fl, rnd, rnd_c} = c4;
    // ---- S3c: encode --------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = o_fl + {11'd0, carry};
    wire over = !o_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    // C6: encode | refusals -> y
    localparam integer W6 = 1 + 1 + 2 + 1 + 32;
    wire [W6-1:0] c6;
    ot_hdc_w11_cut #(.W(W6), .CUT(CUT6), .VB(DRST ? -1 : W6-1)) u_c6 (.clk(clk), .rst_n(rst_n), .d({o_v, o_byp, o_err, over, code}), .q(c6));
    wire        e_v, e_byp, e_over;
    wire [1:0]  e_err;
    wire [31:0] e_code;
    assign {e_v, e_byp, e_err, e_over, e_code} = c6;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= e_v;
            if (e_byp) err <= e_err;
            else if (e_over) err <= E_OVERFLOW;
            else err <= E_NONE;
        end
    end
    // B encode (CUT4 = CUT6 = 0 at LAT 6: o_* = r_*, e_* = o_*), same expressions on the B controls
    wire carry_b = !b_sub && rnd_c;
    wire [23:0] man_b = carry_b ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_b = b_fl + {11'd0, carry_b};
    wire over_b = !b_sub && (floor_b > 12'sd127);
    wire [7:0] field_b = floor_b[7:0] + 8'd127;
    wire sub_carry_b = b_sub && rnd[23];
    wire [31:0] code_b = b_sub ? (sub_carry_b ? {b_sign, 8'h01, 23'd0} : {b_sign, 8'h00, rnd[22:0]})
                               : {b_sign, field_b, man_b[22:0]};
    wire [31:0] y_da = e_byp ? 32'd0 : (e_over ? 32'd0 : ((e_code[30:0] == 31'd0) ? 32'd0 : e_code));
    wire [31:0] y_db = b_byp ? 32'd0 : (over_b ? 32'd0 : ((code_b[30:0] == 31'd0) ? 32'd0 : code_b));
    wire [31:0] y_d = {y_db[31:16], y_da[15:0]};
    genvar yh;
    generate for (yh = 0; yh < 2; yh = yh + 1) begin : g_y
        always @(posedge clk or negedge rst_v[17 + yh])
            if (!rst_v[17 + yh]) y[16*yh +: 16] <= 16'd0;
            else y[16*yh +: 16] <= y_d[16*yh +: 16];
    end endgenerate
endmodule

// W-bit fully reset cut (the VB < 0 ot_hdc_w11_cut), reset spread over NR leaves of <= ceil(W/NR) flops each
module ot_hdc_mul24_rows_pvfin #(parameter integer K = 4) (
    input  wire [K*24-1:0] a,
    input  wire [K*24-1:0] b,
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
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            wire [23:0] pp;
            for(genvar j=0;j<24;j=j+1)begin:g_col
             assign pp[j]=a[24*(i/6)+j]&b[24*(j/6)+i];
            end
            assign l0[48*i+:48]={24'd0,pp}<<i;
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
