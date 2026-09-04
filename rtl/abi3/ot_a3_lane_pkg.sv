`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Numeric helpers for the format-scaled pipelined contraction lane
// (rtl/abi3/ot_a3_lane_pipelined.sv, CHIP_ARCHITECTURE_DESIGN.md section 4.2).
//
// Everything here is written against the same three authorities the
// sequential lane transcribes -- runtime/reference/formats.py for the storage
// formats, rtl/ot_fp32_rne_pkg.sv for binary32 round-to-nearest-even, and
// runtime/sim/backend.py for the contraction contract -- but it is a second,
// independent implementation of them.  Gate D1 compares the lane built from
// these functions against rtl/abi3/ot_a3_mac_lane.sv, which is untouched and
// uses the package functions directly, by running both on one operand set.
//
// Representation.  An operand element is carried as
//
//     value = (-1)**sign * mag * 2**pow
//
// with ``mag`` the format's own integer significand, right-aligned at its
// natural width -- 8 bits for BF16 (hidden bit plus seven), 4 bits for
// E4M3FN, 2 bits for E2M1 -- and ``pow`` a signed power of two.  A binary32
// value is likewise ``mag * 2**pow`` with a 24-bit significand.  Products are
// therefore integer products of narrow significands with an exponent add,
// which is why an 8 x 8 partial-product field is exact for every supported
// pair: no product carries more than 16 significant bits and binary32 holds
// 24.  Rounding only happens where the contract says it does -- a scaled
// operand or a g = 1 product that lands in the binary32 subnormal range is
// rounded to that grid (np.float32 semantics, as the sequential lane's
// fp32_mul_rne does), and the accumulation is rounded once per group.
//
// Packed records.  Verilog-2005 functions return vectors, so the records
// below are packed with fixed field positions:
//
//   element  [29:22] fault detail, [21] sign, [20] zero, [19:12] mag, [11:0] pow
//   product  [29:22] fault detail, [21] sign, [20] zero, [19:4] mag, [3:0] unused
//            (the product's 16-bit magnitude and 12-bit power are carried in
//            the lane's own registers; see the module)
//
// Fault details are one code per way an operation can be refused.  They are
// finer than the sequential lane's error codes -- two failure modes that the
// reference reports with one ERR_OPERAND_NONFINITE are told apart here -- and
// map onto the reference's codes by ``error_code_of_detail`` so that gate D1
// compares the class and gate D5 compares the mode.
// ---------------------------------------------------------------------------
package ot_a3_lane_pkg;
    // -- widths --------------------------------------------------------------
    localparam integer MAG_BITS   = 8;    // operand significand, natural width
    localparam integer POW_BITS   = 12;   // signed power of two
    localparam integer PROD_BITS  = 16;   // exact product magnitude
    localparam integer GROUP_BITS = 48;   // exact aligned group-sum magnitude
    localparam integer FRAME_BITS = 52;   // accumulate adder frame
    localparam integer FRAME_MSB  = 49;   // operands enter with their MSB here
    localparam integer NORM_MSB   = 50;   // the sum is normalised to this bit

    // -- fault details (gate D5) ----------------------------------------------
    localparam [7:0] DETAIL_NONE            = 8'd0;
    localparam [7:0] DETAIL_A_NONFINITE     = 8'd1;   // BF16 NaN / infinity, operand A
    localparam [7:0] DETAIL_B_NONFINITE     = 8'd2;   // BF16 NaN / infinity, operand B
    localparam [7:0] DETAIL_A_RESERVED      = 8'd3;   // E4M3FN 0x7f / 0xff, operand A
    localparam [7:0] DETAIL_B_RESERVED      = 8'd4;   // E4M3FN 0x7f / 0xff, operand B
    localparam [7:0] DETAIL_SCALE_A_RESERVED= 8'd5;   // E8M0 0xff, operand A scale
    localparam [7:0] DETAIL_SCALE_B_RESERVED= 8'd6;   // E8M0 0xff, operand B scale
    localparam [7:0] DETAIL_SCALE_A_RANGE   = 8'd7;   // scaled operand A left binary32
    localparam [7:0] DETAIL_SCALE_B_RANGE   = 8'd8;   // scaled operand B left binary32
    localparam [7:0] DETAIL_PRODUCT_RANGE   = 8'd9;   // a product left binary32
    localparam [7:0] DETAIL_ACCUMULATE_RANGE= 8'd10;  // an accumulation left binary32
    localparam [7:0] DETAIL_SHAPE           = 8'd11;  // degenerate or unsupported extent
    localparam [7:0] DETAIL_ALIGNER         = 8'd12;  // group aligner span exceeded (cannot happen for admitted formats; fails closed)

    // The sequential lane's error codes, re-declared here so this package
    // does not import ot_a3_engine_pkg (Icarus wildcard-import trap, OI-43).
    localparam [7:0] ERR_NONE              = 8'd0;
    localparam [7:0] ERR_OPERAND_NONFINITE = 8'd1;
    localparam [7:0] ERR_PRODUCT_RANGE     = 8'd2;
    localparam [7:0] ERR_ACCUMULATE_RANGE  = 8'd3;
    localparam [7:0] ERR_SCALE_RANGE       = 8'd6;
    localparam [7:0] ERR_SHAPE             = 8'd7;

    // Storage-format identifiers (runtime/abi3/constants.DType).
    localparam [7:0] FMT_BF16       = 8'h10;
    localparam [7:0] FMT_FP8_E4M3FN = 8'h20;
    localparam [7:0] FMT_MXFP4_E2M1 = 8'h30;

    function automatic [7:0] error_code_of_detail;
        input [7:0] detail;
        begin
            case (detail)
                DETAIL_NONE:             error_code_of_detail = ERR_NONE;
                DETAIL_A_NONFINITE,
                DETAIL_B_NONFINITE,
                DETAIL_A_RESERVED,
                DETAIL_B_RESERVED,
                DETAIL_SCALE_A_RESERVED,
                DETAIL_SCALE_B_RESERVED: error_code_of_detail = ERR_OPERAND_NONFINITE;
                DETAIL_SCALE_A_RANGE,
                DETAIL_SCALE_B_RANGE:    error_code_of_detail = ERR_SCALE_RANGE;
                DETAIL_PRODUCT_RANGE:    error_code_of_detail = ERR_PRODUCT_RANGE;
                DETAIL_ACCUMULATE_RANGE: error_code_of_detail = ERR_ACCUMULATE_RANGE;
                default:                 error_code_of_detail = ERR_SHAPE;
            endcase
        end
    endfunction

    // -- element record accessors ----------------------------------------------
    function automatic [29:0] pack_element;
        input [7:0]  detail;
        input        sign;
        input        zero;
        input [7:0]  mag;
        input [11:0] pow;
        begin
            pack_element = {detail, sign, zero, mag, pow};
        end
    endfunction

    // Element width in bits of one storage code, for slicing packed words.
    function automatic integer element_width;
        input [7:0] format;
        begin
            case (format)
                FMT_BF16:       element_width = 16;
                FMT_FP8_E4M3FN: element_width = 8;
                FMT_MXFP4_E2M1: element_width = 4;
                default:        element_width = 16;
            endcase
        end
    endfunction

    // Significand width of one storage format, in bits (with the hidden bit).
    function automatic integer significand_width;
        input [7:0] format;
        begin
            case (format)
                FMT_BF16:       significand_width = 8;
                FMT_FP8_E4M3FN: significand_width = 4;
                FMT_MXFP4_E2M1: significand_width = 2;
                default:        significand_width = 8;
            endcase
        end
    endfunction

    // -- unpack one storage code into (sign, mag, pow) --------------------------
    //    BF16:   sign(1) exponent(8, bias 127) fraction(7); exponent 0xff is
    //            NaN or infinity and is refused; exponent 0 is subnormal,
    //            value fraction * 2**-133.
    //    E4M3FN: sign(1) exponent(4, bias 7) fraction(3); exponent 15 with
    //            fraction 7 is reserved; exponent 0 is subnormal, fraction * 2**-9.
    //    E2M1:   sign(1) exponent(2, bias 1) fraction(1); no reserved code;
    //            exponent 0 is subnormal, fraction * 2**-1.
    //    Zero is canonical positive in every format (the value is zero and the
    //    lane never lets a zero's sign reach a product).
    function automatic [29:0] unpack_element;
        input [7:0]  format;
        input [15:0] code;
        input        is_b;      // selects the A or B fault detail
        reg [7:0]  detail;
        reg        sign;
        reg        zero;
        reg [7:0]  mag;
        integer    pow;
        begin
            detail = DETAIL_NONE;
            sign = 1'b0;
            zero = 1'b1;
            mag = 8'b0;
            pow = 0;
            case (format)
                FMT_BF16: begin
                    sign = code[15];
                    if (code[14:7] == 8'hff) begin
                        detail = is_b ? DETAIL_B_NONFINITE : DETAIL_A_NONFINITE;
                    end else if (code[14:7] == 8'h00) begin
                        mag = {1'b0, code[6:0]};
                        pow = -133;
                        zero = (code[6:0] == 7'b0);
                    end else begin
                        mag = {1'b1, code[6:0]};
                        pow = {24'b0, code[14:7]};
                        pow = pow - 134;
                        zero = 1'b0;
                    end
                end
                FMT_FP8_E4M3FN: begin
                    sign = code[7];
                    if ((code[6:3] == 4'hf) && (code[2:0] == 3'h7)) begin
                        detail = is_b ? DETAIL_B_RESERVED : DETAIL_A_RESERVED;
                    end else if (code[6:3] == 4'h0) begin
                        mag = {5'b0, code[2:0]};
                        pow = -9;
                        zero = (code[2:0] == 3'b0);
                    end else begin
                        mag = {4'b0, 1'b1, code[2:0]};
                        pow = {28'b0, code[6:3]};
                        pow = pow - 10;
                        zero = 1'b0;
                    end
                end
                FMT_MXFP4_E2M1: begin
                    sign = code[3];
                    if (code[2:1] == 2'b00) begin
                        mag = {7'b0, code[0]};
                        pow = -1;
                        zero = (code[0] == 1'b0);
                    end else begin
                        mag = {6'b0, 1'b1, code[0]};
                        pow = {30'b0, code[2:1]};
                        pow = pow - 2;
                        zero = 1'b0;
                    end
                end
                default: begin
                    detail = DETAIL_SHAPE;
                end
            endcase
            if (zero) begin
                sign = 1'b0;
                mag = 8'b0;
                pow = 0;
            end
            unpack_element = pack_element(detail, sign, zero, mag, pow[11:0]);
        end
    endfunction

    // Position of the leading one of an 8-bit magnitude (0 for the value 1).
    function automatic integer msb8;
        input [7:0] value;
        integer bit_index;
        begin
            msb8 = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (value[bit_index])
                    msb8 = bit_index;
        end
    endfunction

    function automatic integer msb16;
        input [15:0] value;
        integer bit_index;
        begin
            msb16 = 0;
            for (bit_index = 0; bit_index < 16; bit_index = bit_index + 1)
                if (value[bit_index])
                    msb16 = bit_index;
        end
    endfunction

    function automatic integer msb24;
        input [23:0] value;
        integer bit_index;
        begin
            msb24 = 0;
            for (bit_index = 0; bit_index < 24; bit_index = bit_index + 1)
                if (value[bit_index])
                    msb24 = bit_index;
        end
    endfunction

    function automatic integer msb48;
        input [47:0] value;
        integer bit_index;
        begin
            msb48 = 0;
            for (bit_index = 0; bit_index < 48; bit_index = bit_index + 1)
                if (value[bit_index])
                    msb48 = bit_index;
        end
    endfunction

    function automatic integer msb52;
        input [51:0] value;
        integer bit_index;
        begin
            msb52 = 0;
            for (bit_index = 0; bit_index < 52; bit_index = bit_index + 1)
                if (value[bit_index])
                    msb52 = bit_index;
        end
    endfunction

    // -- fold an E8M0 block scale into an element --------------------------------
    //    The scale is 2**(code - 127); code 0xff is reserved.  Multiplying by
    //    a power of two is an exponent add, exact unless the scaled value
    //    leaves binary32: above 2**128 it is refused (the sequential lane's
    //    fp32_mul_rne reports overflow, ERR_SCALE_RANGE), and below the
    //    binary32 subnormal grid it is rounded to that grid, ties to even,
    //    which is what np.multiply(..., dtype=np.float32) does in
    //    runtime/sim/engines/tensor.py and what fp32_mul_rne does in the
    //    sequential lane.  A zero stays zero whatever the scale.
    function automatic [29:0] fold_scale;
        input [29:0] element;
        input [7:0]  scale_code;
        input        enable;
        input        is_b;
        reg [7:0]  detail;
        reg        sign;
        reg        zero;
        reg [7:0]  mag;
        reg [7:0]  shifted;
        reg        round_bit;
        reg        sticky;
        integer    pow;
        integer    scale_pow;
        integer    value_exponent;
        integer    distance;
        integer    bit_index;
        begin
            detail = element[29:22];
            sign = element[21];
            zero = element[20];
            mag = element[19:12];
            pow = {{20{element[11]}}, element[11:0]};
            shifted = 8'b0;
            round_bit = 1'b0;
            sticky = 1'b0;
            scale_pow = 0;
            value_exponent = 0;
            distance = 0;
            if (enable && (detail == DETAIL_NONE)) begin
                if (scale_code == 8'hff) begin
                    detail = is_b ? DETAIL_SCALE_B_RESERVED : DETAIL_SCALE_A_RESERVED;
                end else if (!zero) begin
                    scale_pow = {24'b0, scale_code};
                    scale_pow = scale_pow - 127;
                    pow = pow + scale_pow;
                    value_exponent = pow + msb8(mag);
                    if (value_exponent > 127) begin
                        detail = is_b ? DETAIL_SCALE_B_RANGE : DETAIL_SCALE_A_RANGE;
                    end else if (pow < -149) begin
                        // Round to the 2**-149 grid, ties to even.
                        distance = -149 - pow;
                        if (distance > 8) begin
                            shifted = 8'b0;
                            round_bit = 1'b0;
                            sticky = |mag;
                        end else begin
                            shifted = mag >> distance;
                            round_bit = mag[distance - 1];
                            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                                if (bit_index < distance - 1)
                                    sticky = sticky | mag[bit_index];
                        end
                        if (round_bit && (sticky || shifted[0]))
                            shifted = shifted + 8'd1;
                        mag = shifted;
                        pow = -149;
                        if (mag == 8'b0) begin
                            zero = 1'b1;
                            sign = 1'b0;
                            pow = 0;
                        end
                    end
                end
            end
            fold_scale = pack_element(detail, sign, zero, mag, pow[11:0]);
        end
    endfunction

    // -- the reconfigurable 8 x 8 partial-product field ----------------------------
    //    Four 2 x 8 partial-product rows.  In mode 0 (g = 1) they are the four
    //    two-bit slices of one 8-bit operand against one 8-bit operand, summed
    //    with shifts 0, 2, 4, 6 into one 16-bit product.  In mode 1 (g = 2)
    //    rows {0,1} and {2,3} form two 4 x 4 products.  In mode 2 (g = 4) each
    //    row is one 2 x 8 product on its own.  The narrow-side operand j is
    //    ``a_mags[j*8 +: 8]`` and the wide-side operand j is ``b_mags[j*8 +: 8]``;
    //    the lane puts the E2M1 operand on the narrow side for g = 4.
    //    Returns four 16-bit products, product j at [j*16 +: 16].
    function automatic [63:0] multiplier_field;
        input [1:0]  mode;
        input [31:0] a_mags;
        input [31:0] b_mags;
        reg [1:0]  a_slice;
        reg [7:0]  b_operand;
        reg [9:0]  pp0, pp1, pp2, pp3;
        reg [15:0] p0, p1, p2, p3;
        begin
            // row 0
            case (mode)
                2'd0: begin a_slice = a_mags[1:0];  b_operand = b_mags[7:0]; end
                2'd1: begin a_slice = a_mags[1:0];  b_operand = {4'b0, b_mags[3:0]}; end
                default: begin a_slice = a_mags[1:0]; b_operand = b_mags[7:0]; end
            endcase
            pp0 = a_slice * b_operand;
            // row 1
            case (mode)
                2'd0: begin a_slice = a_mags[3:2];  b_operand = b_mags[7:0]; end
                2'd1: begin a_slice = a_mags[3:2];  b_operand = {4'b0, b_mags[3:0]}; end
                default: begin a_slice = a_mags[9:8]; b_operand = b_mags[15:8]; end
            endcase
            pp1 = a_slice * b_operand;
            // row 2
            case (mode)
                2'd0: begin a_slice = a_mags[5:4];  b_operand = b_mags[7:0]; end
                2'd1: begin a_slice = a_mags[9:8];  b_operand = {4'b0, b_mags[11:8]}; end
                default: begin a_slice = a_mags[17:16]; b_operand = b_mags[23:16]; end
            endcase
            pp2 = a_slice * b_operand;
            // row 3
            case (mode)
                2'd0: begin a_slice = a_mags[7:6];  b_operand = b_mags[7:0]; end
                2'd1: begin a_slice = a_mags[11:10]; b_operand = {4'b0, b_mags[11:8]}; end
                default: begin a_slice = a_mags[25:24]; b_operand = b_mags[31:24]; end
            endcase
            pp3 = a_slice * b_operand;
            case (mode)
                2'd0: begin
                    p0 = {6'b0, pp0} + {4'b0, pp1, 2'b0} + {2'b0, pp2, 4'b0} + {pp3, 6'b0};
                    p1 = 16'b0;
                    p2 = 16'b0;
                    p3 = 16'b0;
                end
                2'd1: begin
                    p0 = {6'b0, pp0} + {4'b0, pp1, 2'b0};
                    p1 = {6'b0, pp2} + {4'b0, pp3, 2'b0};
                    p2 = 16'b0;
                    p3 = 16'b0;
                end
                default: begin
                    p0 = {6'b0, pp0};
                    p1 = {6'b0, pp1};
                    p2 = {6'b0, pp2};
                    p3 = {6'b0, pp3};
                end
            endcase
            multiplier_field = {p3, p2, p1, p0};
        end
    endfunction

    // -- round one exact product to binary32 (g = 1 only) ------------------------
    //    The product is exact; binary32 rounding can only act in the
    //    subnormal range, where the value is rounded to the 2**-149 grid, ties
    //    to even, exactly as fp32_mul_rne does.  Above 2**128 it is refused.
    //    Returns {detail[7:0], sign, zero, mag[16:0], pow[11:0]} = 39 bits:
    //    detail [38:31], sign [30], zero [29], mag [28:12], pow [11:0].
    function automatic [38:0] round_product;
        input        sign;
        input        zero;
        input [15:0] mag;
        input [11:0] pow_code;
        reg [7:0]  detail;
        reg        out_sign;
        reg        out_zero;
        reg [16:0] shifted;
        reg        round_bit;
        reg        sticky;
        integer    pow;
        integer    value_exponent;
        integer    distance;
        integer    bit_index;
        begin
            detail = DETAIL_NONE;
            out_sign = sign;
            out_zero = zero | (mag == 16'b0);
            shifted = {1'b0, mag};
            round_bit = 1'b0;
            sticky = 1'b0;
            pow = {{20{pow_code[11]}}, pow_code};
            value_exponent = 0;
            distance = 0;
            if (!out_zero) begin
                value_exponent = pow + msb16(mag);
                if (value_exponent > 127) begin
                    detail = DETAIL_PRODUCT_RANGE;
                end else if (pow < -149) begin
                    distance = -149 - pow;
                    if (distance > 16) begin
                        shifted = 17'b0;
                        round_bit = 1'b0;
                        sticky = |mag;
                    end else begin
                        shifted = {1'b0, mag} >> distance;
                        round_bit = mag[distance - 1];
                        for (bit_index = 0; bit_index < 16; bit_index = bit_index + 1)
                            if (bit_index < distance - 1)
                                sticky = sticky | mag[bit_index];
                    end
                    if (round_bit && (sticky || shifted[0]))
                        shifted = shifted + 17'd1;
                    pow = -149;
                    if (shifted == 17'b0)
                        out_zero = 1'b1;
                end
            end
            if (out_zero) begin
                out_sign = 1'b0;
                shifted = 17'b0;
                pow = 0;
            end
            round_product = {detail, out_sign, out_zero, shifted, pow[11:0]};
        end
    endfunction

    // -- shift right with a jammed sticky bit ---------------------------------------
    function automatic [51:0] shift_right_jam_52;
        input [51:0] value;
        input integer distance;
        integer bit_index;
        reg discarded;
        reg [51:0] shifted;
        begin
            discarded = 1'b0;
            shifted = 52'b0;
            if (distance <= 0) begin
                shifted = value;
            end else if (distance >= 52) begin
                shifted[0] = |value;
            end else begin
                shifted = value >> distance;
                for (bit_index = 0; bit_index < 52; bit_index = bit_index + 1)
                    if (bit_index < distance)
                        discarded = discarded | value[bit_index];
                shifted[0] = shifted[0] | discarded;
            end
            shift_right_jam_52 = shifted;
        end
    endfunction

    // -- accumulate adder, piece 1: decode the accumulator and align -----------
    //    The second operand is the group sum, already normalised to a 48-bit
    //    magnitude with its leading one at bit 47 and a signed power such that
    //    value = mag * 2**pow.  Both operands are placed in a 52-bit frame
    //    with their leading one at bit FRAME_MSB; the smaller-exponent one is
    //    shifted right with a jammed sticky bit.  Because the frame holds the
    //    whole of either operand below the anchor with two bits to spare, an
    //    exponent difference of at most one -- the only case in which the
    //    subtraction can cancel more than one leading bit -- loses nothing,
    //    and any larger difference leaves the result within one bit of the
    //    larger operand, far above the jam.
    //    Returns {subtract, big_sign, small_sign, big_frame[51:0],
    //             small_frame[51:0], e_big[11:0]} = 3 + 104 + 12 = 119 bits.
    function automatic [118:0] acc_align;
        input [31:0] acc_code;
        input        s_zero;
        input        s_sign;
        input [47:0] s_mag;
        input [11:0] s_pow_code;
        reg [7:0]  a_exp;
        reg [23:0] a_mag;
        reg        a_zero;
        reg        a_sign;
        reg [51:0] a_frame;
        reg [51:0] s_frame;
        reg [51:0] big_frame;
        reg [51:0] small_frame;
        reg        big_sign;
        reg        small_sign;
        reg        subtract;
        integer    a_pow;
        integer    a_msb;
        integer    e_a;
        integer    e_s;
        integer    e_big;
        integer    e_small;
        integer    distance;
        begin
            a_exp = acc_code[30:23];
            a_sign = acc_code[31];
            a_mag = (a_exp == 8'h00) ? {1'b0, acc_code[22:0]} : {1'b1, acc_code[22:0]};
            a_zero = (a_mag == 24'b0);
            a_pow = (a_exp == 8'h00) ? -149 : ({24'b0, a_exp} - 150);
            a_msb = msb24(a_mag);
            e_a = a_zero ? -4096 : (a_pow + a_msb);
            e_s = s_zero ? -4096 : ({{20{s_pow_code[11]}}, s_pow_code} + 47);
            a_frame = {28'b0, a_mag} << (FRAME_MSB - a_msb);
            s_frame = {4'b0, s_mag} << (FRAME_MSB - 47);
            if (a_zero) begin
                a_frame = 52'b0;
                a_sign = 1'b0;
            end
            if (s_zero)
                s_frame = 52'b0;
            if (e_a >= e_s) begin
                big_frame = a_frame;
                small_frame = s_frame;
                big_sign = a_sign;
                small_sign = s_zero ? 1'b0 : s_sign;
                e_big = e_a;
                e_small = e_s;
            end else begin
                big_frame = s_frame;
                small_frame = a_frame;
                big_sign = s_sign;
                small_sign = a_sign;
                e_big = e_s;
                e_small = e_a;
            end
            distance = e_big - e_small;
            if (distance > 63)
                distance = 63;
            small_frame = shift_right_jam_52(small_frame, distance);
            subtract = big_sign ^ small_sign;
            if (a_zero && s_zero)
                e_big = 0;
            acc_align = {subtract, big_sign, small_sign, big_frame, small_frame,
                         e_big[11:0]};
        end
    endfunction

    // -- accumulate adder, piece 2: add or subtract, then normalise ------------
    //    Returns {sign, zero, norm[51:0], e_res[11:0]} = 66 bits, with the
    //    leading one of ``norm`` at bit NORM_MSB and e_res its exponent.
    function automatic [65:0] acc_sum_normalise;
        input [118:0] aligned;
        reg        subtract;
        reg        big_sign;
        reg        small_sign;
        reg [51:0] big_frame;
        reg [51:0] small_frame;
        reg [51:0] result;
        reg        sign;
        reg        zero;
        integer    e_big;
        integer    msb;
        integer    e_res;
        begin
            subtract = aligned[118];
            big_sign = aligned[117];
            small_sign = aligned[116];
            big_frame = aligned[115:64];
            small_frame = aligned[63:12];
            e_big = {{20{aligned[11]}}, aligned[11:0]};
            sign = big_sign;
            if (subtract) begin
                if (big_frame >= small_frame) begin
                    result = big_frame - small_frame;
                    sign = big_sign;
                end else begin
                    result = small_frame - big_frame;
                    sign = small_sign;
                end
            end else begin
                result = big_frame + small_frame;
            end
            zero = (result == 52'b0);
            msb = msb52(result);
            e_res = e_big + (msb - FRAME_MSB);
            result = result << (NORM_MSB - msb);
            if (zero) begin
                sign = 1'b0;
                e_res = 0;
                result = 52'b0;
            end
            acc_sum_normalise = {sign, zero, result, e_res[11:0]};
        end
    endfunction

    // -- accumulate adder, piece 3: round to binary32 and pack -------------------
    //    Rounds at 24 significant bits, or at the 2**-149 grid when the
    //    result is below the normal range, ties to even; canonical positive
    //    zero; a result at or above 2**128 is refused as
    //    ERR_ACCUMULATE_RANGE.  Returns {error[1:0], code[31:0]} in the
    //    ot_fp32_rne_pkg convention.
    function automatic [33:0] acc_round_pack;
        input [65:0] normalised;
        reg        sign;
        reg        zero;
        reg [51:0] norm;
        reg [51:0] shifted;
        reg        discarded;
        reg [23:0] significand;
        reg        guard;
        reg        rest;
        reg [24:0] rounded;
        reg [7:0]  exponent_field;
        reg [1:0]  error;
        reg [31:0] code;
        integer    e_res;
        integer    distance;
        integer    bit_index;
        begin
            sign = normalised[65];
            zero = normalised[64];
            norm = normalised[63:12];
            e_res = {{20{normalised[11]}}, normalised[11:0]};
            error = 2'd0;
            code = 32'b0;
            discarded = 1'b0;
            shifted = norm;
            distance = 0;
            rounded = 25'b0;
            exponent_field = 8'b0;
            if (!zero) begin
                if (e_res < -126) begin
                    distance = -126 - e_res;
                    if (distance > 63)
                        distance = 63;
                    if (distance >= 52) begin
                        discarded = |norm;
                        shifted = 52'b0;
                    end else begin
                        shifted = norm >> distance;
                        for (bit_index = 0; bit_index < 52; bit_index = bit_index + 1)
                            if (bit_index < distance)
                                discarded = discarded | norm[bit_index];
                    end
                end
                significand = shifted[NORM_MSB:NORM_MSB-23];
                guard = shifted[NORM_MSB-24];
                rest = (|shifted[NORM_MSB-25:0]) | discarded;
                rounded = {1'b0, significand};
                if (guard && (rest || significand[0]))
                    rounded = rounded + 25'd1;
                if (e_res < -126) begin
                    // Subnormal result; a round-up to 2**23 is the smallest
                    // normal, whose exponent field is one.
                    exponent_field = rounded[23] ? 8'd1 : 8'd0;
                    code = {sign, exponent_field, rounded[22:0]};
                end else begin
                    if (rounded[24]) begin
                        rounded = rounded >> 1;
                        e_res = e_res + 1;
                    end
                    if (e_res > 127) begin
                        error = 2'd2;
                        code = 32'b0;
                    end else begin
                        exponent_field = e_res[7:0] + 8'd127;
                        code = {sign, exponent_field, rounded[22:0]};
                    end
                end
                if (code[30:0] == 31'b0)
                    code = 32'b0;
            end
            acc_round_pack = {error, code};
        end
    endfunction
endpackage
