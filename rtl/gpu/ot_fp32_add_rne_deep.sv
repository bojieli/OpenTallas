`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Deep-pipelined binary32 add, bit-identical to the qualified
// rtl/proto/ot_fp32_add_rne_pipe.sv (RNE, gradual underflow, canonical +0,
// fail-closed nonfinite / overflow), for 1.2 GHz at the SS corner
// (AGENTS.md sign-off corners).  The five qualified stages are kept, and
// three of them can be cut once more (SPLIT bits):
//   bit 0  stage 1: decode and magnitude compare | swap and exponent distance
//   bit 1  stage 4: leading-zero count and clamp | normalize shift
//   bit 2  stage 5: round increment | carry, encode, overflow, canonicalize
// LATENCY = 5 + popcount(SPLIT).  Every cut only moves a register boundary:
// the combinational functions are the qualified ones.
// ---------------------------------------------------------------------------
module ot_optreg #(
    parameter integer W  = 1,
    parameter integer EN = 1,
    parameter integer RST = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (EN == 0) begin : g_w
            assign q = d;
        end else if (RST != 0) begin : g_r
            reg [W-1:0] r;
            always @(posedge clk or negedge rst_n) if (!rst_n) r <= {W{1'b0}}; else r <= d;
            assign q = r;
        end else begin : g_n
            reg [W-1:0] r;
            always @(posedge clk) r <= d;
            assign q = r;
        end
    endgenerate
endmodule

module ot_fp32_add_rne_deep #(
    parameter integer SPLIT = 3'b111,
    parameter integer KS = 0                 // 1: stage-3 sum / difference and stage-5 round increment as kept Kogge-Stone
                                             // adders (rtl/hdc/ot_hdc_prefix.sv: ABC re-ripples a behavioural add in
                                             // context, S81-PH tile_m2 s2 -> s3 MAJ chain -162 ps); same function
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
    localparam integer S1 = SPLIT & 1;
    localparam integer S4 = (SPLIT >> 1) & 1;
    localparam integer S5 = (SPLIT >> 2) & 1;
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;
    integer k;

    // -- stage 1a: decode, compare magnitudes, resolve the zero operands -----
    wire        a_sign = a[31];
    wire        b_sign = b[31];
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire        nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire        a_is_zero = (a_man == 24'd0);
    wire        b_is_zero = (b_man == 24'd0);
    wire        bypass = nonfinite || a_is_zero || b_is_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_is_zero ? (b_is_zero ? 32'd0 : b) : a);
    wire        swap = (b_exp > a_exp) || ((b_exp == a_exp) && (b_man > a_man));
    // stage 1a -> 1b register (optional)
    wire        q_v;
    wire [1+32+1+1+1+1+8+8+24+24-1:0] q1;
    ot_optreg #(.W(1), .EN(S1), .RST(1)) u_v1 (.clk(clk), .rst_n(rst_n), .d(valid_in), .q(q_v));
    ot_optreg #(.W(1+32+1+1+1+1+8+8+24+24), .EN(S1)) u_r1 (.clk(clk), .rst_n(rst_n),
        .d({bypass, bypass_code, nonfinite, a_sign, b_sign, swap, a_exp, b_exp, a_man, b_man}), .q(q1));
    wire        r_byp, r_nf, r_as, r_bs, r_swap;
    wire [31:0] r_code;
    wire [7:0]  r_ae, r_be;
    wire [23:0] r_am, r_bm;
    assign {r_byp, r_code, r_nf, r_as, r_bs, r_swap, r_ae, r_be, r_am, r_bm} = q1;
    // -- stage 1b: swap, exponent distance ------------------------------------
    wire [7:0]  big_exp = r_swap ? r_be : r_ae;
    wire [7:0]  small_exp = r_swap ? r_ae : r_be;
    wire [23:0] big_man = r_swap ? r_bm : r_am;
    wire [23:0] small_man = r_swap ? r_am : r_bm;
    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp, s1_dist;
    reg [23:0] s1_big, s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_v <= 1'b0; s1_byp <= 1'b0; s1_sub <= 1'b0; s1_sign <= 1'b0;
            s1_err <= E_NONE; s1_code <= 32'd0; s1_exp <= 8'd0;
            s1_dist <= 8'd0; s1_big <= 24'd0; s1_small <= 24'd0;
        end else begin
            s1_v <= q_v;
            s1_byp <= r_byp;
            s1_err <= r_nf ? E_NONFINITE : E_NONE;
            s1_code <= r_code;
            s1_sub <= (r_as != r_bs);
            s1_sign <= r_swap ? r_bs : r_as;
            s1_exp <= big_exp;
            s1_dist <= big_exp - small_exp;
            s1_big <= big_man;
            s1_small <= small_man;
        end
    end

    // -- stage 2: align the smaller significand, jamming what falls off ------
    function automatic [27:0] shift_right_jam_28;
        input [27:0] value;
        input [7:0]  distance;
        reg discarded;
        reg [27:0] shifted;
        integer bit_index;
        begin
            discarded = 1'b0;
            shifted = 28'd0;
            if (distance == 8'd0) begin
                shifted = value;
            end else if (distance >= 8'd28) begin
                shifted[0] = |value;
            end else begin
                shifted = value >> distance;
                for (bit_index = 0; bit_index < 28; bit_index = bit_index + 1)
                    if ({24'd0, bit_index[7:0]} < distance)
                        discarded = discarded | value[bit_index];
                shifted[0] = shifted[0] | discarded;
            end
            shift_right_jam_28 = shifted;
        end
    endfunction
    reg        s2_v, s2_byp, s2_sub, s2_sign;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [27:0] s2_big, s2_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s2_v <= 1'b0; s2_byp <= 1'b0; s2_sub <= 1'b0; s2_sign <= 1'b0;
            s2_err <= E_NONE; s2_code <= 32'd0; s2_exp <= 8'd0;
            s2_big <= 28'd0; s2_small <= 28'd0;
        end else begin
            s2_v <= s1_v; s2_byp <= s1_byp; s2_sub <= s1_sub;
            s2_sign <= s1_sign; s2_err <= s1_err; s2_code <= s1_code;
            s2_exp <= s1_exp;
            s2_big <= {1'b0, s1_big, 3'b000};
            s2_small <= shift_right_jam_28({1'b0, s1_small, 3'b000}, s1_dist);
        end
    end

    // -- stage 3: the add or subtract, and the add's single-bit renormalize --
    wire [27:0] s3_sum, s3_dif;
    generate if (KS != 0) begin : g_ks3
        wire unused_c0, unused_c1;
        ot_hdc_ksadd_k #(.W(28)) u_sum (.a(s2_big), .b(s2_small), .cin(1'b0), .s(s3_sum), .cout(unused_c0));
        ot_hdc_ksadd_k #(.W(28)) u_dif (.a(s2_big), .b(~s2_small), .cin(1'b1), .s(s3_dif), .cout(unused_c1));
    end else begin : g_b3
        assign s3_sum = s2_big + s2_small;
        assign s3_dif = s2_big - s2_small;
    end endgenerate
    wire [27:0] s3_arith = s2_sub ? s3_dif : s3_sum;
    wire        s3_carry = !s2_sub && s3_sum[27];
    wire [26:0] s3_shifted = {s3_sum[27:2], s3_sum[1] | s3_sum[0]};
    reg        s3_v, s3_byp, s3_sub, s3_sign, s3_zero;
    reg [1:0]  s3_err;
    reg [31:0] s3_code;
    reg [7:0]  s3_exp;
    reg [26:0] s3_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s3_v <= 1'b0; s3_byp <= 1'b0; s3_sub <= 1'b0; s3_sign <= 1'b0;
            s3_zero <= 1'b0; s3_err <= E_NONE; s3_code <= 32'd0;
            s3_exp <= 8'd0; s3_val <= 27'd0;
        end else begin
            s3_v <= s2_v; s3_byp <= s2_byp; s3_sub <= s2_sub;
            s3_sign <= s2_sign; s3_err <= s2_err; s3_code <= s2_code;
            s3_zero <= s2_sub && (s3_dif == 28'd0);
            s3_exp <= s3_carry ? (s2_exp + 8'd1) : s2_exp;
            s3_val <= s3_carry ? s3_shifted : s3_arith[26:0];
        end
    end

    // -- stage 4a: the leading-zero count clamped by the exponent floor ------
    reg [4:0] s4_lz;
    always @* begin
        s4_lz = 5'd27;
        for (k = 0; k <= 26; k = k + 1)
            if (s3_val[k]) s4_lz = 5'd26 - k[4:0];
    end
    wire [7:0] s4_room = s3_exp - 8'd1;
    wire [7:0] s4_shift_c = ({3'd0, s4_lz} > s4_room) ? s4_room : {3'd0, s4_lz};
    wire       s4_apply_c = s3_sub && !s3_zero && !s3_byp;
    wire       t_v;
    wire [1+1+1+2+32+8+27+8+1-1:0] q4;
    ot_optreg #(.W(1), .EN(S4), .RST(1)) u_v4 (.clk(clk), .rst_n(rst_n), .d(s3_v), .q(t_v));
    ot_optreg #(.W(1+1+1+2+32+8+27+8+1), .EN(S4)) u_r4 (.clk(clk), .rst_n(rst_n),
        .d({s3_byp, s3_sign, s3_zero, s3_err, s3_code, s3_exp, s3_val, s4_shift_c, s4_apply_c}), .q(q4));
    wire        t_byp, t_sign, t_zero, t_apply;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp, t_shift;
    wire [26:0] t_val;
    assign {t_byp, t_sign, t_zero, t_err, t_code, t_exp, t_val, t_shift, t_apply} = q4;
    // -- stage 4b: the cancellation normalize ----------------------------------
    reg        s4_v, s4_byp, s4_sign, s4_zero;
    reg [1:0]  s4_err;
    reg [31:0] s4_code;
    reg [7:0]  s4_exp;
    reg [26:0] s4_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s4_v <= 1'b0; s4_byp <= 1'b0; s4_sign <= 1'b0; s4_zero <= 1'b0;
            s4_err <= E_NONE; s4_code <= 32'd0; s4_exp <= 8'd0; s4_val <= 27'd0;
        end else begin
            s4_v <= t_v; s4_byp <= t_byp; s4_sign <= t_sign;
            s4_zero <= t_zero; s4_err <= t_err; s4_code <= t_code;
            s4_exp <= t_apply ? (t_exp - t_shift) : t_exp;
            s4_val <= t_apply ? (t_val << t_shift) : t_val;
        end
    end

    // -- stage 5a: round to nearest even ---------------------------------------
    wire [24:0] s5_trunc = {1'b0, s4_val[26:3]};
    wire        s5_inc = s4_val[2] && ((|s4_val[1:0]) || s4_val[3]);
    wire [24:0] s5_round_c;
    generate if (KS != 0) begin : g_ks5
        wire unused_c5;
        ot_hdc_inc_k #(.W(25)) u_rnd (.a(s5_trunc), .inc(s5_inc), .y(s5_round_c), .co(unused_c5));
    end else begin : g_b5
        assign s5_round_c = s5_trunc + {24'd0, s5_inc};
    end endgenerate
    wire        u_v;
    wire [1+1+1+2+32+8+25-1:0] q5;
    ot_optreg #(.W(1), .EN(S5), .RST(1)) u_v5 (.clk(clk), .rst_n(rst_n), .d(s4_v), .q(u_v));
    ot_optreg #(.W(1+1+1+2+32+8+25), .EN(S5)) u_r5 (.clk(clk), .rst_n(rst_n),
        .d({s4_byp, s4_sign, s4_zero, s4_err, s4_code, s4_exp, s5_round_c}), .q(q5));
    wire        u_byp, u_sign, u_zero;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [24:0] s5_round;
    assign {u_byp, u_sign, u_zero, u_err, u_code, u_exp, s5_round} = q5;
    // -- stage 5b: carry, encode, fail closed on overflow ----------------------
    wire        s5_carry = s5_round[24];
    wire [23:0] s5_man = s5_carry ? s5_round[24:1] : s5_round[23:0];
    wire [7:0]  s5_exp = s5_carry ? (u_exp + 8'd1) : u_exp;
    wire        s5_subnormal = (s5_exp == 8'd1) && !s5_man[23];
    wire [31:0] s5_code = {u_sign, s5_subnormal ? 8'd0 : s5_exp, s5_man[22:0]};
    wire        s5_over = (u_exp >= 8'hff) || (s5_exp >= 8'hff);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;
        end else begin
            valid_out <= u_v;
            if (u_byp) begin
                y <= u_code;
                err <= u_err;
            end else if (u_zero) begin
                y <= 32'd0;
                err <= E_NONE;
            end else if (s5_over) begin
                y <= 32'd0;
                err <= E_OVERFLOW;
            end else begin
                y <= (s5_code[30:0] == 31'd0) ? 32'd0 : s5_code;
                err <= E_NONE;
            end
        end
    end
endmodule
