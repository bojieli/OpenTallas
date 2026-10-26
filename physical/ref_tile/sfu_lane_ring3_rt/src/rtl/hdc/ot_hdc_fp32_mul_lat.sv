`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_mul_lat #(LAT): the binary32 multiplier of ot_hdc_fp32_mul_fast (rtl/hdc/ot_hdc_fastfp.sv), bit for
// bit, with LAT = 3..9 register stages (W11 measurement vehicle for 1.2 GHz @ SS; see ot_hdc_fp32_add_lat).
//   S1  decode, subnormal LZC                             | C5 (LAT >= 8; margin rule 2026-10-06)
//       normalise shift                                   | C1 (LAT >= 6)
//       partial products + three carry-save levels, the exponent sum
//   S2  four carry-save levels                            | C2 (LAT >= 5)
//       the 48-bit prefix add; the subnormal masks
//   S3  select, subnormal shift, sticky/round bits        | C3 (LAT >= 4)
//       round increment (prefix add)                      | C4 (LAT >= 7)
//       encode                                            | C6 (LAT >= 9; margin rule 2026-10-06)
//       refusals -> y
// Every prefix adder is ot_hdc_ksadd_k (rtl/hdc/ot_hdc_prefix.sv, (* keep *) levels).
// Uses ot_hdc_w11_cut (rtl/hdc/ot_hdc_fp32_add_lat.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_lat #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bit k-1 = C<k> (LAT must be 3 + their count); -1: by LAT as above.
    // W11 serial domain: CUTS = 4'b0101 (C1 + C3, LAT 5) cuts the INPUT side, so an operand multiplexer in front
    // of the unit shares stage 1 with the decode / normalise instead of the partial-product rows
    parameter integer CUTS = -1
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
    localparam integer CUT1 = (CUTS >= 0) ? CUTS % 2       : (LAT >= 6) ? 1 : 0;
    localparam integer CUT2 = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 5) ? 1 : 0;
    localparam integer CUT3 = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT4 = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;
    localparam integer CUT5 = (CUTS >= 0) ? (CUTS / 16) % 2 : (LAT >= 8) ? 1 : 0;
    localparam integer CUT6 = (CUTS >= 0) ? (CUTS / 32) % 2 : (LAT >= 9) ? 1 : 0;
    generate if (CUTS >= 0 && CUT1 + CUT2 + CUT3 + CUT4 + CUT5 + CUT6 + 3 != LAT) begin : g_bad_cuts
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
    // C5: decode / LZC | normalise shift
    localparam integer W5 = 1 + 1 + 2 + 1 + 24 + 24 + 5 + 5 + 12 + 12;
    wire [W5-1:0] c5;
    ot_hdc_w11_cut #(.W(W5), .CUT(CUT5)) u_c5 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), a[31] ^ b[31], a_raw, b_raw, a_lz[4:0],
            b_lz[4:0], a_power, b_power}), .q(c5));
    wire        n_v, n_bz, n_sign;
    wire [1:0]  n_err;
    wire [23:0] n_ar, n_br;
    wire [4:0]  n_al, n_bl;
    wire [11:0] n_ap, n_bp;
    assign {n_v, n_bz, n_err, n_sign, n_ar, n_br, n_al, n_bl, n_ap, n_bp} = c5;
    wire [23:0] a_n = n_ar << n_al;
    wire [23:0] b_n = n_br << n_bl;
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] c1;
    ot_hdc_w11_cut #(.W(W1), .CUT(CUT1)) u_c1 (.clk(clk), .rst_n(rst_n),
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
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows u_rows (.a(p_a), .b(p_b), .rows(rows));

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
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W2 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W2-1:0] c2;
    ot_hdc_w11_cut #(.W(W2), .CUT(CUT2)) u_c2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(c2));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = c2;
    // ---- S2b: the prefix add -----------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= q_v;
    end
    always @(posedge clk) begin
        s2_byp <= q_byp; s2_err <= q_err; s2_sign <= q_sign;
        s2_prod <= prod;
        s2_sub47 <= q_s47; s2_sub46 <= q_s46;
        s2_fl47 <= q_fl47; s2_fl46 <= q_fl46;
        s2_sh <= q_sh; s2_mr <= q_mr; s2_ms <= q_ms;
    end

    // ---- S3a: select, subnormal shift, round/sticky bits ------------------------------------------
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
    localparam integer W3 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W3-1:0] c3;
    ot_hdc_w11_cut #(.W(W3), .CUT(CUT3)) u_c3 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, fl, main, rb && (st || main[0])}), .q(c3));
    wire        r_v, r_byp, r_sign, r_sub, r_inc;
    wire [1:0]  r_err;
    wire [11:0] r_fl;
    wire [23:0] r_main;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_fl, r_main, r_inc} = c3;
    // ---- S3b: round ---------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k #(.W(24)) u_rnd (.a(r_main), .b(24'd0), .cin(r_inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer W4 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W4-1:0] c4;
    ot_hdc_w11_cut #(.W(W4), .CUT(CUT4)) u_c4 (.clk(clk), .rst_n(rst_n),
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
    ot_hdc_w11_cut #(.W(W6), .CUT(CUT6)) u_c6 (.clk(clk), .rst_n(rst_n), .d({o_v, o_byp, o_err, over, code}), .q(c6));
    wire        e_v, e_byp, e_over;
    wire [1:0]  e_err;
    wire [31:0] e_code;
    assign {e_v, e_byp, e_err, e_over, e_code} = c6;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= e_v;
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end
endmodule

module ot_hdc_fp32_mul_lat4 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat6 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat7 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(7)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat9 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(9)) u (.*);
endmodule

// the W11 serial-domain LAT-5 multiplier: the LAT-4 cuts plus C1 (after the decode / normalise), bit-identical
module ot_hdc_fp32_mul_lat5i (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(5), .CUTS(5)) u (.*);
endmodule
