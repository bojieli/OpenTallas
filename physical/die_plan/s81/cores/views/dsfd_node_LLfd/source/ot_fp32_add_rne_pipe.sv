`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Pipelined binary32 adder, one result per cycle.
//
// This is the arithmetic ``ot_fp32_rne_pkg::fp32_add_rne`` performs
// COMBINATIONALLY.  That function is the project's scalar authority and stays
// so; what it is not is fast.  Placed inside ot_a3_reduction_expert_sum it set
// the whole engine's clock at 157.6 MHz, because decode, a 28-bit jamming
// align, the add, a 27-bit normalizing shift and the round all sit in one cone.
// Cut into five stages the same cone closes an order of magnitude higher, and
// the engines that need binary32 addition stop paying for it.
//
// WHY THE ENGINES CANNOT USE THE MAC INSTEAD.  ot_mac_bf16_fp32_pipe computes
// RN(a*b + c) at II=1 with a BF16 ``a`` and an FP32 ``c``, so ``b = BF16 1.0``
// turns it into an adder -- but only when one addend is BF16.  Every shipped
// ROUTE.WEIGHT_NORMALIZE is FP32-in/FP32-out, and ROUTE.EXPERT_SUM accumulates
// FP32, so both need two FP32 addends and neither fits.
//
// A SEQUENTIAL FOLD DOES NOT GET FASTER BY BEING PIPELINED -- acc = acc + w is
// loop-carried, so one group still costs LATENCY cycles per term.  What
// pipelining buys is the clock, and the right to interleave INDEPENDENT
// reductions (WEIGHT_NORMALIZE ships 262,144 groups) through the same adder at
// one per cycle.  Callers that fold a single long chain should expect
// LATENCY-cycle spacing and schedule other work into the gaps.
//
// BIT-IDENTICAL TO THE AUTHORITY, INCLUDING WHERE THE AUTHORITY IS NOT IEEE.
// Two behaviours here are deliberately not what a fresh IEEE implementation
// would do, and are reproduced because the authority is the contract:
//
//   * (-0) + (-0) is +0.  The authority takes the ``left_mantissa == 0`` branch,
//     sees a zero right operand and returns a literal 32'b0.  IEEE-754 says -0.
//   * every zero result is canonical +0, from the closing
//     ``if (result[30:0] == 0) result = 0``.
//
// A nonfinite operand and a result that rounds past the finite range FAIL
// CLOSED through ``err``; they are never encoded as an infinity.
// ---------------------------------------------------------------------------
module ot_fp32_add_rne_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    integer k;

    // -- stage 1: decode, order by magnitude, resolve the zero operands ------
    wire        a_sign = a[31];
    wire        b_sign = b[31];
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    //: A zero exponent field means subnormal: exponent 1, no implicit leading
    //: one. The authority does exactly this, so a subnormal operand is a genuine
    //: subnormal here and not a flushed zero.
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};

    wire s1_nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_is_zero = (a_man == 24'd0);
    wire b_is_zero = (b_man == 24'd0);
    //: The authority's own order: left-zero first, so (+-0) + (+-0) is +0 and
    //: not the IEEE -0 that a symmetric implementation would produce.
    wire s1_bypass = s1_nonfinite || a_is_zero || b_is_zero;
    wire [31:0] s1_bypass_code =
        s1_nonfinite ? 32'd0
                     : (a_is_zero ? (b_is_zero ? 32'd0 : b)
                                  : a);

    //: |b| > |a| decides the swap; on equal magnitude the left operand stays
    //: large, which is what fixes the result sign for a cancelling pair.
    wire swap = (b_exp > a_exp) || ((b_exp == a_exp) && (b_man > a_man));
    wire [7:0]  big_exp = swap ? b_exp : a_exp;
    wire [7:0]  small_exp = swap ? a_exp : b_exp;
    wire [23:0] big_man = swap ? b_man : a_man;
    wire [23:0] small_man = swap ? a_man : b_man;

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
            s1_v <= valid_in;
            s1_byp <= s1_bypass;
            s1_err <= s1_nonfinite ? E_NONFINITE : E_NONE;
            s1_code <= s1_bypass_code;
            s1_sub <= (a_sign != b_sign);
            s1_sign <= swap ? b_sign : a_sign;
            s1_exp <= big_exp;
            //: Both fields are 8 bits and big >= small, so the difference cannot
            //: borrow; the jam shifter saturates it past 28 on its own.
            s1_dist <= big_exp - small_exp;
            s1_big <= big_man;
            s1_small <= small_man;
        end
    end

    // -- stage 2: align the smaller significand, jamming what falls off ------
    //: Three guard bits below the significand, and everything shifted out is
    //: OR-ed into the lowest of them. Without that sticky a cancellation moves a
    //: dropped bit into the round position and the last bit comes out wrong.
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
    wire [27:0] s3_sum = s2_big + s2_small;
    wire [27:0] s3_dif = s2_big - s2_small;
    wire [27:0] s3_arith = s2_sub ? s3_dif : s3_sum;
    //: A carry out of bit 27 shifts one right and keeps the lost bit sticky.
    wire        s3_carry = !s2_sub && s3_sum[27];
    //: Written out rather than as a part-select of a part-select: Verilator
    //: accepts that form and the pinned Yosys 0.68 frontend rejects it.
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
            //: An exactly cancelling subtraction is +0 and skips the rest.
            s3_zero <= s2_sub && (s3_dif == 28'd0);
            s3_exp <= s3_carry ? (s2_exp + 8'd1) : s2_exp;
            s3_val <= s3_carry ? s3_shifted : s3_arith[26:0];
        end
    end

    // -- stage 4: the cancellation normalize --------------------------------
    //: The authority shifts left one bit at a time while bit 26 is clear AND the
    //: exponent is above 1, at most 27 times. So the shift is the leading-zero
    //: count CLAMPED BY THE EXPONENT FLOOR -- a large cancellation near the
    //: bottom of the range stops at exponent 1 and stays subnormal rather than
    //: normalizing into an exponent it cannot encode.
    reg [4:0] s4_lz;
    always @* begin
        s4_lz = 5'd27;
        //: ASCENDING, so the LAST assignment is the HIGHEST set bit. Counting
        //: down leaves the lowest set bit instead, which normalizes a cancelling
        //: subtraction by far too much and is wrong on every case that cancels.
        for (k = 0; k <= 26; k = k + 1)
            if (s3_val[k]) s4_lz = 5'd26 - k[4:0];
    end
    wire [7:0] s4_room = s3_exp - 8'd1;
    wire [7:0] s4_shift = ({3'd0, s4_lz} > s4_room) ? s4_room : {3'd0, s4_lz};
    wire       s4_apply = s3_sub && !s3_zero && !s3_byp;

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
            s4_v <= s3_v; s4_byp <= s3_byp; s4_sign <= s3_sign;
            s4_zero <= s3_zero; s4_err <= s3_err; s4_code <= s3_code;
            s4_exp <= s4_apply ? (s3_exp - s4_shift) : s3_exp;
            s4_val <= s4_apply ? (s3_val << s4_shift) : s3_val;
        end
    end

    // -- stage 5: round to nearest even, encode, fail closed on overflow -----
    wire [24:0] s5_trunc = {1'b0, s4_val[26:3]};
    //: Ties to EVEN: increment on the round bit only when something below it is
    //: set or the retained bit is already odd.
    wire        s5_inc = s4_val[2] && ((|s4_val[1:0]) || s4_val[3]);
    wire [24:0] s5_round = s5_trunc + {24'd0, s5_inc};
    wire        s5_carry = s5_round[24];
    wire [23:0] s5_man = s5_carry ? s5_round[24:1] : s5_round[23:0];
    wire [7:0]  s5_exp = s5_carry ? (s4_exp + 8'd1) : s4_exp;
    //: Exponent 1 with no leading one left is the subnormal encoding: field 0.
    wire        s5_subnormal = (s5_exp == 8'd1) && !s5_man[23];
    wire [31:0] s5_code = {s4_sign, s5_subnormal ? 8'd0 : s5_exp, s5_man[22:0]};
    //: Overflow before rounding and after it are both refusals, never infinity.
    wire        s5_over = (s4_exp >= 8'hff) || (s5_exp >= 8'hff);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;
        end else begin
            valid_out <= s4_v;
            if (s4_byp) begin
                y <= s4_code;
                err <= s4_err;
            end else if (s4_zero) begin
                y <= 32'd0;
                err <= E_NONE;
            end else if (s5_over) begin
                y <= 32'd0;
                err <= E_OVERFLOW;
            end else begin
                //: The authority's closing canonicalization: any zero is +0.
                y <= (s5_code[30:0] == 31'd0) ? 32'd0 : s5_code;
                err <= E_NONE;
            end
        end
    end
endmodule
