`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Rebalanced copy of rtl/proto/ot_fp32_mul_rne_pipe.sv for the decode core.
//
// Routed inside the core's special-function units, the qualified pipe closes
// at 950-990 MHz on ASAP7, and the path is always its stage 2: the whole
// 24x24 significand multiply in one cycle, while stage 3 holds only a few
// 12-bit exponent adds.  This copy moves work across that boundary without
// changing a result bit:
//
//   stage 2  three 24x8 partial products (b split into bytes), and BOTH
//            candidate exponent/alignment decisions (leading bit 47 or 46),
//            which depend only on the exponents;
//   stage 3  the three-term sum of the partial products and a 2:1 select of
//            the precomputed decision by the product's top bit.
//
// Same latency (5), same interface, same semantics, bit for bit -- checked
// against the qualified pipe by tools/rtl_hdc_mul_equivalence.py.
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_pipe (
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

    // -- stage 2: three 24x8 partial products; both exponent decisions ---------
    //: 46 or 47, never anything else, because both significands carry bit 23;
    //: the decision for each case needs only the exponents, so both are ready
    //: before the product is.
    function automatic [24:0] decide;     // {is_sub, floor[11:0], shift[11:0]}
        input signed [11:0] power;
        input [5:0] msb;
        reg signed [11:0] fl, sh;
        reg sub;
        begin
            fl = power + $signed({6'd0, msb});
            sub = (fl < -12'sd126);
            //: The normal-result align, and the subnormal-result align in units
            //: of the binary32 subnormal LSB; the authority picks on floor >= -126.
            sh = sub ? -(power + 12'sd149) : ($signed({6'd0, msb}) - 12'sd23);
            decide = {sub, fl, sh};
        end
    endfunction

    reg        s2_v, s2_byp, s2_sign;
    reg [1:0]  s2_err;
    reg [31:0] s2_pp0, s2_pp1, s2_pp2;
    reg [24:0] s2_d47, s2_d46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s2_v <= 1'b0; s2_byp <= 1'b0; s2_sign <= 1'b0; s2_err <= E_NONE;
            s2_pp0 <= 32'd0; s2_pp1 <= 32'd0; s2_pp2 <= 32'd0; s2_d47 <= 25'd0; s2_d46 <= 25'd0;
        end else begin
            s2_v <= s1_v; s2_byp <= s1_byp; s2_sign <= s1_sign; s2_err <= s1_err;
            s2_pp0 <= {8'd0, s1_a} * {24'd0, s1_b[7:0]};
            s2_pp1 <= {8'd0, s1_a} * {24'd0, s1_b[15:8]};
            s2_pp2 <= {8'd0, s1_a} * {24'd0, s1_b[23:16]};
            s2_d47 <= decide(s1_power, 6'd47);
            s2_d46 <= decide(s1_power, 6'd46);
        end
    end

    // -- stage 3: the product, and the decision its top bit selects -----------
    wire [47:0] s3_prod = {16'd0, s2_pp0} + {8'd0, s2_pp1, 8'd0} + {s2_pp2, 16'd0};
    wire [24:0] s3_dec = s3_prod[47] ? s2_d47 : s2_d46;

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
            s3_err <= s2_err; s3_product <= s3_prod;
            s3_is_sub_q <= s3_dec[24];
            s3_floor_q <= s3_dec[23:12];
            s3_shift_q <= s3_dec[11:0];
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
