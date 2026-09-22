`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_fp32_rne_pkg::fp32_add_positive_rne, cut into five registered stages.
//
// WHY THIS EXISTS.  ot_a3_hc_sinkhorn20_rne_pipe is the ABI 3.0 design limiter at
// 276.9 MHz, and its four additions are ALREADY alone between registers -- the
// pair adds read the matrix, the tree add reads pair_01_q and pair_23_q, and the
// epsilon add reads pair_total_q.  So 276.9 MHz IS one combinational
// fp32_add_positive_rne plus the matrix read mux, and no rescheduling reaches
// past it.  Routing that block at a 1.8 ns target instead of 3.7 ns confirmed it:
// the tool tried twice as hard and returned 278.9 MHz, a 3.585 ns path against
// the baseline's 3.612 ns -- 0.7 percent.  The limiter is real, not a
// characterisation artifact, and the only way past it is to pipeline the adder.
//
// ot_fp32_add_rne_pipe is the SIGNED adder and is not a substitute: the two
// functions differ, and fp32_add_positive_rne's whole point is that positive
// operands cannot cancel, so it has no cancellation-normalize at all.  That is
// also why it is SHALLOWER, and why this pipe's stage 4 carries only the round
// preparation where the signed pipe carries a leading-zero count.
//
// The arithmetic is the authority's, statement for statement:
//   stage 1  decode, order by magnitude, resolve zero and the refusals
//   stage 2  align the smaller significand, JAMMING what falls off
//   stage 3  the 28-bit add and the single-bit carry renormalize
//   stage 4  round to nearest even and apply the post-round carry
//   stage 5  encode, and fail closed on overflow
//
// Refusals are CLOSED through ``err``: a negative operand, a nonfinite operand,
// or an exponent reaching 255 never encodes as a number.  The authority refuses
// a negative operand outright -- this is the POSITIVE adder -- and so does this.
// ---------------------------------------------------------------------------
module ot_fp32_add_positive_rne_pipe (
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

    // -- stage 1: decode, order by magnitude, resolve zero and the refusals ---
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    //: a zero exponent field is subnormal: exponent 1, no implicit leading one
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};

    //: the authority refuses a SIGN BIT as well as a nonfinite field, because
    //: this function is only defined on positive operands
    wire s1_nonfinite = a[31] || b[31] ||
                        (a_field == 8'hff) || (b_field == 8'hff);
    wire a_is_zero = (a_man == 24'd0);
    wire b_is_zero = (b_man == 24'd0);
    //: zero + x is x, and zero + zero is +0, exactly as the authority returns
    //: them -- the ORIGINAL code, not a recomputation
    wire s1_bypass = s1_nonfinite || a_is_zero || b_is_zero;
    wire [31:0] s1_bypass_code =
        s1_nonfinite ? 32'd0
                     : (a_is_zero ? (b_is_zero ? 32'd0 : b) : a);

    wire swap = (b_exp > a_exp) || ((b_exp == a_exp) && (b_man > a_man));
    wire [7:0]  big_exp   = swap ? b_exp : a_exp;
    wire [7:0]  small_exp = swap ? a_exp : b_exp;
    wire [23:0] big_man   = swap ? b_man : a_man;
    wire [23:0] small_man = swap ? a_man : b_man;

    reg        s1_v, s1_byp;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp, s1_dist;
    reg [27:0] s1_big, s1_small;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_v <= 1'b0; s1_byp <= 1'b0; s1_err <= E_NONE;
            s1_code <= 32'd0; s1_exp <= 8'd0; s1_dist <= 8'd0;
            s1_big <= 28'd0; s1_small <= 28'd0;
        end else begin
            s1_v <= valid_in;
            s1_byp <= s1_bypass;
            s1_err <= s1_nonfinite ? E_NONFINITE : E_NONE;
            s1_code <= s1_bypass_code;
            s1_exp <= big_exp;
            s1_dist <= big_exp - small_exp;
            s1_big <= {1'b0, big_man, 3'b000};
            s1_small <= {1'b0, small_man, 3'b000};
        end
    end

    // -- stage 2: align the smaller significand, jamming what falls off ------
    //: shift_right_jam_28: at or past 28 the whole value becomes one sticky
    //: bit; below that, every discarded bit is OR-ed into bit 0. A barrel shift
    //: and an OR-reduction of the discarded window, which is what the
    //: authority's loop computes.
    reg [27:0] s2_aligned;
    always @* begin
        if (s1_dist == 8'd0)
            s2_aligned = s1_small;
        else if (s1_dist >= 8'd28)
            s2_aligned = {27'd0, |s1_small};
        else begin
            s2_aligned = s1_small >> s1_dist;
            s2_aligned[0] = s2_aligned[0] |
                            (|(s1_small & ~({28{1'b1}} << s1_dist)));
        end
    end

    reg        s2_v, s2_byp;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [27:0] s2_big, s2_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s2_v <= 1'b0; s2_byp <= 1'b0; s2_err <= E_NONE;
            s2_code <= 32'd0; s2_exp <= 8'd0;
            s2_big <= 28'd0; s2_small <= 28'd0;
        end else begin
            s2_v <= s1_v; s2_byp <= s1_byp; s2_err <= s1_err;
            s2_code <= s1_code; s2_exp <= s1_exp;
            s2_big <= s1_big; s2_small <= s2_aligned;
        end
    end

    // -- stage 3: the add, and the single-bit carry renormalize --------------
    wire [27:0] s3_sum_w = s2_big + s2_small;
    //: a carry out of bit 27 shifts right one and JAMS the bit shifted out into
    //: bit 0, which is the authority's `normalized[0] | sum_extended[0]`
    wire [26:0] s3_norm_w = s3_sum_w[27]
                          ? {s3_sum_w[27:1] | {26'd0, s3_sum_w[0]}}
                          : s3_sum_w[26:0];
    wire [7:0]  s3_exp_w = s2_exp + (s3_sum_w[27] ? 8'd1 : 8'd0);

    reg        s3_v, s3_byp;
    reg [1:0]  s3_err;
    reg [31:0] s3_code;
    reg [7:0]  s3_exp;
    reg [26:0] s3_norm;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s3_v <= 1'b0; s3_byp <= 1'b0; s3_err <= E_NONE;
            s3_code <= 32'd0; s3_exp <= 8'd0; s3_norm <= 27'd0;
        end else begin
            s3_v <= s2_v; s3_byp <= s2_byp; s3_err <= s2_err;
            s3_code <= s2_code; s3_exp <= s3_exp_w; s3_norm <= s3_norm_w;
        end
    end

    // -- stage 4: round to nearest even, and the post-round carry ------------
    //: round up when the guard bit is set AND either a sticky bit below it is
    //: set or the unit bit above it is -- ties to even, exactly as written
    wire       s4_inc_w = s3_norm[2] && ((|s3_norm[1:0]) || s3_norm[3]);
    wire [24:0] s4_round_w = {1'b0, s3_norm[26:3]} + (s4_inc_w ? 25'd1 : 25'd0);
    //: a carry into bit 24 shifts right one and lifts the exponent
    wire [24:0] s4_mant_w = s4_round_w[24] ? (s4_round_w >> 1) : s4_round_w;
    wire [7:0]  s4_exp_w  = s3_exp + (s4_round_w[24] ? 8'd1 : 8'd0);

    reg        s4_v, s4_byp;
    reg [1:0]  s4_err;
    reg [31:0] s4_code;
    reg [7:0]  s4_exp;
    reg [24:0] s4_mant;
    //: the authority tests `large_exponent >= 255` BEFORE rounding as well as
    //: after, and a pre-round overflow returns the error with result 0
    reg        s4_pre_overflow;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s4_v <= 1'b0; s4_byp <= 1'b0; s4_err <= E_NONE;
            s4_code <= 32'd0; s4_exp <= 8'd0; s4_mant <= 25'd0;
            s4_pre_overflow <= 1'b0;
        end else begin
            s4_v <= s3_v; s4_byp <= s3_byp; s4_err <= s3_err;
            s4_code <= s3_code;
            s4_pre_overflow <= (s3_exp >= 8'hff);
            s4_exp <= s4_exp_w;
            s4_mant <= s4_mant_w;
        end
    end

    // -- stage 5: encode, and fail closed on overflow ------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;
        end else begin
            valid_out <= s4_v;
            if (s4_byp) begin
                y <= s4_code;
                err <= s4_err;
            end else if (s4_pre_overflow || (s4_exp >= 8'hff)) begin
                y <= 32'd0;
                err <= E_OVERFLOW;
            end else begin
                err <= E_NONE;
                //: exponent 1 with no implicit leading one is the subnormal
                //: encoding, and any zero result canonicalises to +0
                if ((s4_exp == 8'd1) && !s4_mant[23])
                    y <= {9'b0, s4_mant[22:0]};
                else if (({1'b0, s4_exp, s4_mant[22:0]} & 32'h7fff_ffff) == 0)
                    y <= 32'd0;
                else
                    y <= {1'b0, s4_exp, s4_mant[22:0]};
            end
        end
    end
endmodule
