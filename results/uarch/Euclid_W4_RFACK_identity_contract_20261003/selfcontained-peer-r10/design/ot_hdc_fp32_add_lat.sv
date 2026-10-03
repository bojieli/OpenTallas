`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_add_lat #(LAT): the binary32 adder of ot_hdc_fp32_add_fast (rtl/hdc/ot_hdc_fastfp.sv), bit for bit,
// with LAT = 3..6 register stages.  A MEASUREMENT vehicle for the 1.2 GHz @ SS decision (W11, 2026-09-30): the
// same logic is cut at up to three extra boundaries, so the SS fmax against LAT shows the flop overhead.
//   A1  decode, magnitude compare, exponent differences        | cut C_A  (LAT >= 5)
//   A2  both jammed alignments, the swap pick
//   B1  28-bit sum and difference (prefix adders)               | cut C_B  (LAT >= 4)
//   B2  normalise: sentinel LZC, shift, exponent adjust
//   C1  round increment (prefix adder)                          | cut C_C  (LAT >= 6)
//   C2  encode, subnormal, overflow, canonical zero -> y
//   (B2 is cut after the sentinel LZC when LAT >= 7)
// Every prefix adder is ot_hdc_ksadd_k (rtl/hdc/ot_hdc_prefix.sv): (* keep *) Kogge-Stone levels, so ABC cannot
// re-ripple the carries inside a parent block (W13: the plain form closed standalone and failed in context).
// LAT 3 has the cuts of ot_hdc_fp32_add_fast (after A, after B, after C).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_lat #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bits {D, C, B, A} (LAT must be 3 + their count); -1: by LAT.
    // W11 serial domain: CUTS = 4'b0001 (C_A, LAT 4) cuts the INPUT side, so an operand multiplexer in front of
    // the unit shares stage 1 with the decode / compare instead of the alignment
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
    localparam integer CUT_A = (CUTS >= 0) ? CUTS % 2       : (LAT >= 5) ? 1 : 0;
    localparam integer CUT_B = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT_C = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 6) ? 1 : 0;
    localparam integer CUT_D = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;     // inside B2: after the sentinel LZC
    generate if (CUTS >= 0 && CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_add_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
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
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 boundary bundle
    localparam integer WA = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] a1 = {valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
                        a_exp, b_exp, a_man, b_man, dab, dba} ;
    wire          a1_swap = !cmp_c;
    wire [WA:0]   a2_in;
    ot_hdc_w11_cut #(.W(WA + 1), .CUT(CUT_A)) u_ca (.clk(clk), .rst_n(rst_n), .d({a1_swap, a1}), .q(a2_in));
    // ---- A2 ----------------------------------------------------------------------------------------
    wire        x_v, x_byp, x_sub, x_as, x_bs, x_swap;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_swap, x_v, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = a2_in;
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
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_err <= x_err;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
        s1_small <= x_swap ? small_a : small_b;
    end

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer WB = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [WB-1:0] b2_in;
    ot_hdc_w11_cut #(.W(WB), .CUT(CUT_B)) u_cb (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(b2_in));
    // ---- B2 ----------------------------------------------------------------------------------------
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = b2_in;
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32 u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    // B2a -> B2b boundary (LAT >= 7)
    localparam integer WD = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [WD-1:0] d2_in;
    ot_hdc_w11_cut #(.W(WD), .CUT(CUT_D)) u_cd (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(d2_in));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = d2_in;
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_err <= w_err; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer WC = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [WC-1:0] c2_in;
    ot_hdc_w11_cut #(.W(WC), .CUT(CUT_C)) u_cc (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(c2_in));
    // ---- C2 ----------------------------------------------------------------------------------------
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = c2_in;
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= u_v;
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// a W-bit bundle, registered when CUT = 1 (bit 0... the bundle's MSB is the valid, reset to 0), else passed through
module ot_hdc_w11_cut #(parameter integer W = 1, parameter integer CUT = 0) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

// fixed tops for the hardening sweep
// the W11 serial-domain LAT-4 adder: the LAT-3 cuts plus C_A (after the decode / compare), bit-identical
module ot_hdc_fp32_add_lat4i (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(4), .CUTS(1)) u (.*);
endmodule
module ot_hdc_fp32_add_lat3 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(3)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_lat5 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_add_lat6 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_add_lat7 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(7)) u (.*);
endmodule
