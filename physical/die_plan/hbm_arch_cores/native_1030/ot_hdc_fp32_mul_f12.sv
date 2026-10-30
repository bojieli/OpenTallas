
module ot_hdc_fp32_mul_f12 #(
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
    ot_hdc_ksadd_k__u1 #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
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
    ot_hdc_ksadd_k__u1 #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));
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
    ot_hdc_inc_k__u1 #(.W(24)) u_rnd (.a(r_main), .inc(r_inc), .y(rnd_w), .co(rnd_cw));
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
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= o_v;
            if (o_byp) begin y <= 32'd0; err <= o_err; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule
