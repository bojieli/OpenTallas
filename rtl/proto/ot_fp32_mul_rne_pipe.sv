`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Pipelined binary32 multiplier, one result per cycle.
//
// The companion to ot_fp32_add_rne_pipe, and the arithmetic
// ``ot_fp32_rne_pkg::fp32_mul_rne`` performs combinationally.  That function is
// the scalar authority and stays so; in a datapath it puts a 24x24 multiply, a
// 48-bit leading-bit search, a variable align with a 48-wide sticky reduce and
// the round all in one cone.
//
// ATTENTION.SPARSE IS WHY THIS EXISTS.  Its QK and AV reductions are fused
// product-adds, which ot_mac_bf16_fp32_pipe already covers -- but three of its
// multiplies are FP32 x FP32 and cannot go through a BF16-input MAC: the
// softmax scale applied to every score, the online rescale applied to the
// running denominator, and the same rescale applied to the accumulator.
//
// ONE SIMPLIFICATION THE AUTHORITY DOES NOT TAKE.  It searches all 48 product
// bits for the leading one.  It does not need to: the authority's own subnormal
// normalization leaves bit 23 set in BOTH significands, so the product is at
// least 2**46 and less than 2**48, and the leading bit is 47 or 46 -- never
// anything else.  The search collapses to one bit test, which is the difference
// between a 48-input priority encoder and a wire.  The zero-operand case, where
// no leading bit exists, is resolved before this and bypasses it.
//
// BIT-IDENTICAL TO THE AUTHORITY, INCLUDING ITS NON-IEEE EDGES: a zero operand
// gives canonical +0 whatever the signs, every zero result is +0, and a
// nonfinite operand or an overflowing result FAILS CLOSED through ``err``
// rather than being encoded as an infinity.
// ---------------------------------------------------------------------------
module ot_fp32_mul_rne_pipe (
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

    // -- stage 1: decode, normalize subnormals, resolve zero and nonfinite ----
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire        s1_nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire        s1_zero = (a_raw == 24'd0) || (b_raw == 24'd0);

    //: A subnormal is shifted up until bit 23 is set, its exponent following it
    //: down -- exactly the authority's 23-iteration loop, as one shift.
    function automatic [4:0] lead_shift_24;
        input [23:0] value;
        reg [4:0] shift;
        integer bit_index;
        begin
            shift = 5'd23;
            for (bit_index = 0; bit_index <= 23; bit_index = bit_index + 1)
                if (value[bit_index]) shift = 5'd23 - bit_index[4:0];
            lead_shift_24 = shift;
        end
    endfunction
    wire [4:0] a_shift = lead_shift_24(a_raw);
    wire [4:0] b_shift = lead_shift_24(b_raw);
    //: The authority's powers: field - 150 for a normal, -149 for a subnormal,
    //: then one less for every normalizing shift.
    wire signed [11:0] a_power = (a_field == 8'd0)
        ? (-12'sd149 - {7'd0, a_shift})
        : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0)
        ? (-12'sd149 - {7'd0, b_shift})
        : ($signed({4'd0, b_field}) - 12'sd150);

    reg        s1_v, s1_byp;
    reg [1:0]  s1_err;
    reg        s1_sign;
    reg [23:0] s1_a, s1_b;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_v <= 1'b0; s1_byp <= 1'b0; s1_err <= E_NONE; s1_sign <= 1'b0;
            s1_a <= 24'd0; s1_b <= 24'd0; s1_power <= 12'sd0;
        end else begin
            s1_v <= valid_in;
            s1_byp <= s1_nonfinite || s1_zero;
            s1_err <= s1_nonfinite ? E_NONFINITE : E_NONE;
            s1_sign <= a[31] ^ b[31];
            s1_a <= a_raw << a_shift;
            s1_b <= b_raw << b_shift;
            s1_power <= a_power + b_power;
        end
    end

    // -- stage 2: the 24x24 significand multiply, alone in its own stage ------
    reg        s2_v, s2_byp, s2_sign;
    reg [1:0]  s2_err;
    reg [47:0] s2_product;
    reg signed [11:0] s2_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s2_v <= 1'b0; s2_byp <= 1'b0; s2_sign <= 1'b0; s2_err <= E_NONE;
            s2_product <= 48'd0; s2_power <= 12'sd0;
        end else begin
            s2_v <= s1_v; s2_byp <= s1_byp; s2_sign <= s1_sign;
            s2_err <= s1_err; s2_power <= s1_power;
            //: Both operands widened first, so the product width is not left to
            //: the tool's expression sizing -- the authority makes the same note.
            s2_product <= {24'd0, s1_a} * {24'd0, s1_b};
        end
    end

    // -- stage 3: the exponent and which of the two alignments applies --------
    //: 46 or 47, never anything else, because both significands carry bit 23.
    wire [5:0] s3_msb = s2_product[47] ? 6'd47 : 6'd46;
    wire signed [11:0] s3_floor = s2_power + $signed({6'd0, s3_msb});
    //: The normal-result align, and the subnormal-result align in units of the
    //: binary32 subnormal LSB. The authority picks between them on floor >= -126.
    wire signed [11:0] s3_norm_shift = $signed({6'd0, s3_msb}) - 12'sd23;
    wire signed [11:0] s3_sub_shift = -(s2_power + 12'sd149);
    wire        s3_is_sub = (s3_floor < -12'sd126);
    wire signed [11:0] s3_shift = s3_is_sub ? s3_sub_shift : s3_norm_shift;

    reg        s3_v, s3_byp, s3_sign, s3_is_sub_q;
    reg [1:0]  s3_err;
    reg [47:0] s3_product;
    reg signed [11:0] s3_floor_q, s3_shift_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s3_v <= 1'b0; s3_byp <= 1'b0; s3_sign <= 1'b0; s3_is_sub_q <= 1'b0;
            s3_err <= E_NONE; s3_product <= 48'd0;
            s3_floor_q <= 12'sd0; s3_shift_q <= 12'sd0;
        end else begin
            s3_v <= s2_v; s3_byp <= s2_byp; s3_sign <= s2_sign;
            s3_err <= s2_err; s3_product <= s2_product;
            s3_is_sub_q <= s3_is_sub;
            s3_floor_q <= s3_floor;
            s3_shift_q <= s3_shift;
        end
    end

    // -- stage 4: align, extract round and sticky, round to nearest even ------
    //: The authority's shift_right_48_to_24: bits outside the product are zero,
    //: so a distance at or past 48 leaves nothing.
    function automatic [23:0] shift_48_to_24;
        input [47:0] value;
        input signed [11:0] distance;
        reg [23:0] taken;
        reg signed [11:0] source;
        integer bit_index;
        begin
            taken = 24'd0;
            for (bit_index = 0; bit_index < 24; bit_index = bit_index + 1) begin
                source = $signed({4'd0, bit_index[7:0]}) + distance;
                //: Narrowed to the product's own index width only where the
                //: guard has already put it in range.
                if ((source >= 12'sd0) && (source < 12'sd48))
                    taken[bit_index] = value[source[5:0]];
            end
            shift_48_to_24 = taken;
        end
    endfunction
    //: ``sticky`` is every bit strictly below the round bit.
    function automatic sticky_below;
        input [47:0] value;
        input signed [11:0] distance;
        reg found;
        integer bit_index;
        begin
            found = 1'b0;
            for (bit_index = 0; bit_index < 48; bit_index = bit_index + 1)
                if ($signed({4'd0, bit_index[7:0]}) < distance - 12'sd1)
                    found = found | value[bit_index];
            sticky_below = found;
        end
    endfunction

    wire [23:0] s4_main = (s3_is_sub_q && (s3_shift_q >= 12'sd48))
                        ? 24'd0
                        : shift_48_to_24(s3_product, s3_shift_q);
    //: Named so the index is narrowed once, inside the range the guard proves.
    wire signed [11:0] s4_round_index = s3_shift_q - 12'sd1;
    wire s4_round_in_range = (s3_shift_q > 12'sd0) && (s3_shift_q <= 12'sd48);
    wire s4_round_bit = s4_round_in_range &&
                        s3_product[s4_round_in_range ? s4_round_index[5:0]
                                                     : 6'd0];
    wire s4_sticky = sticky_below(s3_product, s3_shift_q);
    wire [24:0] s4_rounded =
        {1'b0, s4_main} +
        {24'd0, (s4_round_bit && (s4_sticky || s4_main[0]))};

    reg        s4_v, s4_byp, s4_sign, s4_is_sub;
    reg [1:0]  s4_err;
    reg [24:0] s4_mant;
    reg signed [11:0] s4_floor;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s4_v <= 1'b0; s4_byp <= 1'b0; s4_sign <= 1'b0; s4_is_sub <= 1'b0;
            s4_err <= E_NONE; s4_mant <= 25'd0; s4_floor <= 12'sd0;
        end else begin
            s4_v <= s3_v; s4_byp <= s3_byp; s4_sign <= s3_sign;
            s4_err <= s3_err; s4_is_sub <= s3_is_sub_q;
            s4_mant <= s4_rounded;
            s4_floor <= s3_floor_q;
        end
    end

    // -- stage 5: the post-round carry, the encoding, and the refusals --------
    //: A carry out of bit 24 moves the leading bit up one exponent.
    wire        s5_carry = !s4_is_sub && s4_mant[24];
    wire [23:0] s5_man = s5_carry ? s4_mant[24:1] : s4_mant[23:0];
    wire signed [11:0] s5_floor = s4_floor + $signed({11'd0, s5_carry});
    wire        s5_over = !s4_is_sub && (s5_floor > 12'sd127);
    wire [7:0]  s5_field = s5_floor[7:0] + 8'd127;
    //: The subnormal path rounds in LSB units, so a mantissa reaching 2**23 has
    //: rounded UP into the smallest normal and is encoded with field 1.
    wire        s5_sub_carry = s4_is_sub && (s4_mant >= 25'h080_0000);
    wire [31:0] s5_code =
        s4_is_sub ? (s5_sub_carry ? {s4_sign, 8'h01, 23'd0}
                                  : {s4_sign, 8'h00, s4_mant[22:0]})
                  : {s4_sign, s5_field, s5_man[22:0]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;
        end else begin
            valid_out <= s4_v;
            if (s4_byp) begin
                //: A zero operand gives +0 whatever the signs; nonfinite gives
                //: the refusal and a zero code, never an infinity.
                y <= 32'd0;
                err <= s4_err;
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
