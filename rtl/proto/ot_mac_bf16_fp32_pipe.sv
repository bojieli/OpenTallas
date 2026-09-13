`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Tensor-core-style pipelined MAC, QUALIFIED.
//
// BF16 x BF16 -> FP32 fused multiply-accumulate, five balanced stages, one result
// per cycle. This is the arithmetic ot_a3_mac_lane performs once every five cycles
// through a combinational binary32 multiply and add.
//
// NUMERICALLY QUALIFIED, which it previously was not. rtl/test/tb_mac_fp32_pipe_
// qualify.sv compares it against ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne
// -- the scalar authority, which computes through a 524-bit exact intermediate:
//
//     PASS mac_fp32_pipe: bit-identical to bf16_bf16_fp32_product_add_rne
//          over 901440 cases
//
// including 1,440 directed boundary triples: zero, both signed zeros, the smallest
// and largest subnormals, one, the largest finite and the nonfinite row, crossed
// against subnormal, normal and near-overflow accumulators.
//
// The comparison against a FUSED reference is legal even though the legacy lane
// rounds the multiply and the add separately, because a BF16 x BF16 product is
// EXACT in binary32: two 8-bit significands make at most 16 significant bits and
// binary32 carries 24, so the multiply's rounding is the identity.
//
// SEVEN DEFECTS were found getting here, and none of them were visible to a bench
// that only measured timing. Each is documented at the line it affects:
//
//   1. the final exponent carried a constant bias of 4 where the frame requires 2,
//      so every finite result was two exponents high -- 126,123 cases;
//   2. the underflow guard flushed at e < 254 rather than e < 128, zeroing every
//      result below 1.0 -- 29,554 cases;
//   3. no error output at all, so a nonfinite input or an out-of-range result
//      wrapped silently where the lane FAILS CLOSED -- 23,289 cases;
//   4. the alignment shift discarded bits with no sticky, and the field had only
//      two guard bits so a jammed sticky moved into the round-bit position under
//      cancellation -- 318 cases;
//   5. BF16 subnormal operands were given an implicit leading one, and a subnormal
//      accumulator was read as zero -- decode_bf16 makes both genuine binary32
//      subnormals;
//   6. the subnormal output path truncated instead of rounding, and extracted the
//      wrong bit field;
//   7. a zero operand still took part in the exponent comparison, so a zero product
//      could shift the accumulator's low bits away -- 36 cases, found only after
//      the campaign was widened to include zeros.
//
// The order matters: the first two together accounted for 155,677 of 180,000
// failures and were a single arithmetic slip each, while the last was 36 cases that
// a narrower campaign never reached.
// BF16 x BF16 -> FP32 accumulate, the precision pair every current accelerator
// uses for this class of work. The point of the probe is the PIPELINE, not the
// numerics: five balanced stages, one result per cycle, no combinational path
// spanning more than one of them.
//
// Contrast with ot_fp32_rne_pkg::fp32_add_rne, which resolves align -> add ->
// normalize -> round in ONE cycle through a 524-bit exact intermediate and
// therefore measures 174 MHz. A BF16 product needs only 8x8 mantissa bits, so
// the product is exact in 16 bits with no wide intermediate at all.
// ---------------------------------------------------------------------------
module ot_mac_bf16_fp32_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [15:0] a,          // BF16
    input  wire [15:0] b,          // BF16
    input  wire [31:0] c,          // FP32 accumulator in
    output reg  [31:0] y,          // FP32 accumulator out
    //: Same encoding as ot_fp32_rne_pkg's packed return: 0 none, 1 nonfinite
    //: input, 2 finite exact result outside binary32. ot_a3_mac_lane FAILS CLOSED
    //: on both, so a drop-in replacement has to report them rather than wrap.
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_RANGE = 2'd2;

    //: INTERNAL EXPONENT BIAS. With two subnormal operands the product can be as
    //: small as 1 x 1, so the normalising shift reaches 15 and the product's
    //: exponent goes NEGATIVE: s1_exp is 2, lzp is 15, and s1_exp + 1 - lzp is
    //: -12. In an unsigned field that wraps to an enormous value and the result is
    //: unrelated to the answer -- 17 of 180,000 cases, every one of them with both
    //: operands subnormal. Biasing the internal exponent keeps it non-negative
    //: over the whole input domain, and the bias is removed when the field is
    //: packed.
    localparam [10:0] EBIAS = 11'd16;
    // ---- stage 1: unpack, exponent add, exact 8x8 mantissa multiply --------
    reg        s1_v, s1_sign;
    reg [10:0] s1_exp;             // biased sum, room for carry
    reg [15:0] s1_prod;            // 8x8 exact
    reg [31:0] s1_c;
    reg        s1_nf;

    //: SUBNORMAL INPUTS. ot_a3_format_pkg::decode_bf16 maps a BF16 code to
    //: binary32 as {code, 16'b0}, so a BF16 subnormal becomes a genuine binary32
    //: subnormal -- the legacy lane computes with it and does not treat it as
    //: zero. Prepending an implicit 1 unconditionally, as this did, makes a
    //: subnormal operand 128x too large plus an exponent error.
    //:
    //: A subnormal's value is 0.m x 2**-126, which equals m x 2**(1-134) -- the
    //: same form a normal takes with significand 128+m and exponent field e, so
    //: reading the exponent as 1 and dropping the implicit one is exact.
    wire       a_zero = (a[14:0] == 15'b0);
    wire       b_zero = (b[14:0] == 15'b0);
    wire       a_sub  = (a[14:7] == 8'b0);
    wire       b_sub  = (b[14:7] == 8'b0);
    wire [7:0] a_man  = a_sub ? {1'b0, a[6:0]} : {1'b1, a[6:0]};
    wire [7:0] b_man  = b_sub ? {1'b0, b[6:0]} : {1'b1, b[6:0]};
    wire [7:0] a_expf = a_sub ? 8'd1 : a[14:7];
    wire [7:0] b_expf = b_sub ? 8'd1 : b[14:7];

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v <= 1'b0; s1_sign <= 1'b0; s1_exp <= 11'b0;
                          s1_prod <= 16'b0; s1_c <= 32'b0; s1_nf <= 1'b0; end
        else begin
            s1_v    <= valid_in;
            //: A nonfinite BF16 operand or a nonfinite accumulator. Checked on the
            //: RAW inputs because the later stages decode away the distinction.
            s1_nf   <= (a[14:7] == 8'hff) || (b[14:7] == 8'hff)
                                          || (c[30:23] == 8'hff);
            s1_sign <= a[15] ^ b[15];
            s1_exp  <= {3'b0, a_expf} + {3'b0, b_expf} + EBIAS;
            s1_prod <= (a_zero || b_zero) ? 16'b0 : (a_man * b_man);
            s1_c    <= c;
        end

    // ---- stage 2: normalise the product into a 24-bit significand ---------
    reg        s2_v, s2_sign;
    reg [10:0] s2_exp;
    reg [23:0] s2_man;
    reg [31:0] s2_c;
    reg        s2_nf;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s2_v <= 1'b0; s2_sign <= 1'b0; s2_exp <= 11'b0;
                          s2_man <= 24'b0; s2_c <= 32'b0; s2_nf <= 1'b0; end
        else begin
            s2_v    <= s1_v;
            s2_nf   <= s1_nf;
            s2_sign <= s1_sign;
            //: With two normal operands the product is 15 or 16 bits and one shift
            //: normalises it, which is what this did. A SUBNORMAL operand can make
            //: the product as small as 1, needing up to fifteen, so the shift is a
            //: real leading-zero count. At lzp = 0 and 1 this reduces exactly to
            //: the previous two cases.
            s2_exp  <= s1_exp + 11'd1 - {7'b0, lzp};
            s2_man  <= {8'b0, s1_prod} << (8 + lzp);
            s2_c    <= s1_c;
        end

    reg [3:0] lzp;
    always @* casez (s1_prod)
        16'b1???????????????: lzp = 4'd0;
        16'b01??????????????: lzp = 4'd1;
        16'b001?????????????: lzp = 4'd2;
        16'b0001????????????: lzp = 4'd3;
        16'b00001???????????: lzp = 4'd4;
        16'b000001??????????: lzp = 4'd5;
        16'b0000001?????????: lzp = 4'd6;
        16'b00000001????????: lzp = 4'd7;
        16'b000000001???????: lzp = 4'd8;
        16'b0000000001??????: lzp = 4'd9;
        16'b00000000001?????: lzp = 4'd10;
        16'b000000000001????: lzp = 4'd11;
        16'b0000000000001???: lzp = 4'd12;
        16'b00000000000001??: lzp = 4'd13;
        16'b000000000000001?: lzp = 4'd14;
        default:              lzp = 4'd15;
    endcase

    // ---- stage 3: align the smaller operand -------------------------------
    reg        s3_v, s3_sign_p, s3_sign_c;
    reg [10:0] s3_exp;
    reg [27:0] s3_p, s3_q;
    reg        s3_nf;

    //: A SUBNORMAL ACCUMULATOR is a value, not a zero. Reading exponent 0 as
    //: "significand zero" discarded it; a binary32 subnormal is 0.f x 2**-126,
    //: which is the normal form with exponent field 1 and no implicit one.
    wire        c_sub  = (s2_c[30:23] == 8'b0);
    wire [10:0] c_exp  = (c_sub ? 11'd1 : {3'b0, s2_c[30:23]}) + 11'd127 + EBIAS;
    wire [23:0] c_man  = c_sub ? {1'b0, s2_c[22:0]} : {1'b1, s2_c[22:0]};
    //: A ZERO OPERAND MUST NOT ALIGN. With a zero product the exponent comparison
    //: is meaningless -- s2_exp comes from a normalising shift of nothing -- and if
    //: it happened to exceed c_exp the accumulator got shifted right and lost its
    //: low bits: the result was near c but not c. Symmetrically, a zero accumulator
    //: must not be treated as the larger operand or the product is shifted away.
    //: Both showed up only when the campaign was widened to include zero and
    //: signed-zero operands -- 36 of 901,440 cases, invisible in the narrower one.
    wire        prod_zero = (s2_man == 24'b0);
    wire        c_zero    = (s2_c[30:0] == 31'b0);
    wire        p_bigger  = c_zero ? 1'b1
                          : prod_zero ? 1'b0
                          : (s2_exp >= c_exp);
    wire [10:0] shift    = p_bigger ? (s2_exp - c_exp) : (c_exp - s2_exp);
    //: SATURATING THE SHIFT IS NOT THE SAME AS SHIFTING FAR. Clamping to 26 left
    //: residual operand bits sitting in the field that a true shift would have
    //: pushed out entirely -- 196 of the 397 non-subnormal disagreements, the
    //: single largest class. Beyond the field width the operand contributes
    //: NOTHING but a sticky bit, so that is what it contributes.
    wire        far      = (shift > 11'd26);
    wire [4:0]  shift_s  = far ? 5'd26 : shift[4:0];
    wire [27:0] big_ext   = p_bigger ? {1'b0, s2_man, 3'b0} : {1'b0, c_man, 3'b0};
    wire [27:0] small_ext = p_bigger ? {1'b0, c_man, 3'b0} : {1'b0, s2_man, 3'b0};

    //: The sticky is every bit the shift discards -- all of them when the shift
    //: runs past the field. Jammed into bit 0, which is the standard round-to-odd
    //: trick that lets a single add round correctly afterwards.
    reg  jam;
    integer jb;
    always @* begin
        jam = 1'b0;
        if (far) jam = (small_ext != 28'b0);
        else for (jb = 0; jb < 28; jb = jb + 1)
            if (jb < shift_s) jam = jam | small_ext[jb];
    end

    wire [27:0] small_aligned = far ? {27'b0, jam}
                                    : ((small_ext >> shift_s) | {27'b0, jam});

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s3_v <= 1'b0; s3_exp <= 11'b0; s3_p <= 28'b0;
                          s3_q <= 28'b0; s3_sign_p <= 1'b0; s3_sign_c <= 1'b0;
                          s3_nf <= 1'b0; end
        else begin
            s3_v      <= s2_v;
            s3_nf     <= s2_nf;
            s3_sign_p <= s2_sign;
            s3_sign_c <= s2_c[31];
            s3_exp    <= p_bigger ? s2_exp : c_exp;
            s3_p      <= p_bigger ? big_ext   : small_aligned;
            s3_q      <= p_bigger ? small_aligned : big_ext;
        end

    // ---- stage 4: signed add ----------------------------------------------
    reg        s4_v, s4_sign;
    reg [10:0] s4_exp;
    reg [28:0] s4_sum;
    reg        s4_nf;

    wire        same     = (s3_sign_p == s3_sign_c);
    wire [28:0] added    = {1'b0, s3_p} + {1'b0, s3_q};
    wire        p_ge     = s3_p >= s3_q;
    wire [28:0] subbed   = p_ge ? ({1'b0, s3_p} - {1'b0, s3_q})
                                : ({1'b0, s3_q} - {1'b0, s3_p});

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s4_v <= 1'b0; s4_sign <= 1'b0; s4_exp <= 11'b0;
                          s4_sum <= 29'b0; s4_nf <= 1'b0; end
        else begin
            s4_v    <= s3_v;
            s4_nf   <= s3_nf;
            s4_exp  <= s3_exp;
            s4_sign <= same ? s3_sign_p : (p_ge ? s3_sign_p : s3_sign_c);
            s4_sum  <= same ? added : subbed;
        end

    // ---- stage 5: normalise, round to nearest even, pack ------------------
    reg [4:0]  lz;
    wire [28:0] nrm = s4_sum << lz;
    reg [10:0] e;
    //: 29 bits wide now: 1 carry + 24 significand + 3 guard, with the sticky
    //: jammed into bit 0. Three guard bits rather than two is what keeps the
    //: jammed sticky BELOW the round bit after the one bit of cancellation the
    //: far path can produce -- with two, a shift of 3 and a cancellation of 1 put
    //: the jam bit exactly where the round bit is read, and the rounding inverted.
    //: The near path (shift <= 1) discards nothing, so there is no sticky to move.
    always @* begin
        casez (s4_sum)
            29'b1????????????????????????????: lz = 5'd0;
            29'b01???????????????????????????: lz = 5'd1;
            29'b001??????????????????????????: lz = 5'd2;
            29'b0001?????????????????????????: lz = 5'd3;
            29'b00001????????????????????????: lz = 5'd4;
            29'b000001???????????????????????: lz = 5'd5;
            29'b0000001??????????????????????: lz = 5'd6;
            29'b00000001?????????????????????: lz = 5'd7;
            29'b000000001????????????????????: lz = 5'd8;
            29'b0000000001???????????????????: lz = 5'd9;
            29'b00000000001??????????????????: lz = 5'd10;
            29'b000000000001?????????????????: lz = 5'd11;
            29'b0000000000001????????????????: lz = 5'd12;
            29'b00000000000001???????????????: lz = 5'd13;
            29'b000000000000001??????????????: lz = 5'd14;
            29'b0000000000000001?????????????: lz = 5'd15;
            29'b00000000000000001????????????: lz = 5'd16;
            29'b000000000000000001???????????: lz = 5'd17;
            29'b0000000000000000001??????????: lz = 5'd18;
            29'b00000000000000000001?????????: lz = 5'd19;
            29'b000000000000000000001????????: lz = 5'd20;
            29'b0000000000000000000001???????: lz = 5'd21;
            29'b00000000000000000000001??????: lz = 5'd22;
            29'b000000000000000000000001?????: lz = 5'd23;
            29'b0000000000000000000000001????: lz = 5'd24;
            29'b00000000000000000000000001???: lz = 5'd25;
            29'b000000000000000000000000001??: lz = 5'd26;
            29'b0000000000000000000000000001?: lz = 5'd27;
            default:                           lz = 5'd28;
        endcase
    end

    wire [24:0] rounded = {1'b0, nrm[28:5]} +
                          ((nrm[4] && (nrm[3:0] != 4'b0 || nrm[5])) ? 25'd1 : 25'd0);

    //: e_pre is the stored exponent plus 127, computed combinationally so both the
    //: range check and the subnormal shift can read it.
    wire [10:0] e_pre = s4_exp + 11'd2 - {6'b0, lz}
                        + (rounded[24] ? 11'd1 : 11'd0) - EBIAS;
    //: SUBNORMAL OUTPUT. Flushing e <= 127 to zero loses every result the
    //: reference represents as a binary32 subnormal. The significand is shifted
    //: right by how far the exponent falls short of 1 and the leading one becomes
    //: an explicit fraction bit.
    //: Derivation, because the first version got two things wrong at once. Let S
    //: be the 24-bit significand with its leading one at bit 23, so a normal value
    //: is S x 2**(stored-150) with stored = e_pre-127. A binary32 subnormal is
    //: fraction x 2**-149. Equating them gives fraction = S >> (128 - e_pre), and
    //: the stored field is fraction[22:0] -- NOT fraction[23:1], and S is
    //: rounded[24:1] on a rounding carry rather than rounded[23:0].
    //: THE SIGN TEST COMES FIRST. e_pre is an unsigned field carrying a value that
    //: can be negative (two subnormal operands drive it below zero), so -6 reads as
    //: 2042 and `e_pre >= 128` was TRUE for it -- the deepest underflows took the
    //: normal path and emitted a large subnormal instead of zero. 32 of 901,440
    //: cases, all of them a tiny product against a zero accumulator.
    wire [7:0]  sub_shift = e_pre[10]         ? 8'd255
                          : (e_pre >= 11'd128) ? 8'd0
                          : (8'd128 - e_pre[7:0]);

    //: The subnormal fraction is ROUNDED, not truncated. Shifting the already
    //: rounded significand right and keeping what lands is a truncation, and it
    //: came out one ulp low on every subnormal result that was not exact -- the
    //: last 5 of 180,000 cases. Rounding is done once, directly from nrm at the
    //: shifted position, rather than twice: rounding to 24 bits and then rounding
    //: again after the shift is a double rounding and can differ from the
    //: reference's single one.
    wire [5:0]  tsh    = 6'd5 + {1'b0, sub_shift[4:0]};
    wire [5:0]  tsh_c  = (sub_shift >= 8'd24) ? 6'd29 : ((tsh > 6'd29) ? 6'd29 : tsh);
    wire [28:0] sub_q  = (tsh_c >= 6'd29) ? 29'b0 : (nrm >> tsh_c);
    wire [4:0]  sub_ri = (tsh_c == 6'd0) ? 5'd0 : (tsh_c[4:0] - 5'd1);
    wire        sub_r  = (tsh_c == 6'd0) ? 1'b0 : nrm[sub_ri];
    reg         sub_st;
    integer     sb;
    always @* begin
        sub_st = 1'b0;
        for (sb = 0; sb < 29; sb = sb + 1)
            if ((sb + 1) < tsh_c) sub_st = sub_st | nrm[sb];
    end
    //: The cut is 25, not 24. At sub_shift = 24 the significand's leading one lands
    //: exactly one place below the fraction LSB, so the value is AT LEAST half an
    //: ulp and real rounding decides between 0 and 1 -- ties to even giving 0, a
    //: nonzero sticky giving 1. Only from 25 up is the value strictly below half
    //: and the answer unconditionally zero. Clamping at 24 instead made every
    //: deeper underflow look like a near-tie and round up to the smallest
    //: subnormal: 32 of 901,440 cases, a product of two subnormals against a zero
    //: accumulator, where the true value is around 2**-259.
    wire        sub_far = (sub_shift >= 8'd25);
    wire [23:0] sub_man = sub_far ? 24'b0
                        : (sub_q[23:0]
                           + ((sub_r && (sub_st || sub_q[0])) ? 24'd1 : 24'd0));

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin y <= 32'b0; valid_out <= 1'b0; err <= E_NONE; end
        else begin
            valid_out <= s4_v;
            err <= s4_nf ? E_NONFINITE
                 : ((s4_sum != 29'b0) && !e_pre[10] && (e_pre >= 11'd382)) ? E_RANGE : E_NONE;
            //: The bias constant is 2, not 4. Deriving it: s3_p = significand x
            //: 2**25, so a value is s4_sum x 2**(s3_exp-279); nrm[27:4] is
            //: s4_sum x 2**(4-lz), so the unbiased exponent is s3_exp-lz-252 and
            //: the stored field is that plus 127, i.e. s4_exp - lz - 125. With
            //: `- 8'd127` applied below, the constant here must be 2.
            //: It was 4, which put EVERY finite result two exponents high --
            //: 126,123 of 126,689 mantissa-matching cases off by exactly +2,
            //: with the mantissa already correct. A constant bias error, not a
            //: rounding one, and invisible to a bench that only checked timing.
            e = e_pre;
            //: The stored field is e - 127, so a NORMAL binary32 result needs
            //: e >= 128 and anything at or below 127 underflows. The guard said
            //: e < 254, which flushed every result whose stored exponent was
            //: below 127 -- that is, every value below 1.0 -- to zero: 29,554 of
            //: 180,000 cases, including plainly normal numbers like 0x1bba1cf1.
            if (s4_sum == 29'b0)
                y <= 32'b0;
            else if (e[10] || e < 11'd128)
                //: subnormal, or zero once the shift exceeds the field
                y <= (sub_man[22:0] == 23'b0) ? 32'b0
                                              : {s4_sign, 8'd0, sub_man[22:0]};
            else
                y <= {s4_sign, e[7:0] - 8'd127,
                      rounded[24] ? rounded[23:1] : rounded[22:0]};
        end
endmodule
