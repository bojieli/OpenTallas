`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VECTOR.CONVERT, DEQUANTIZE of the DeepSeek-V4.1-Flash main KV latent.
// Contract: fp4_e2m1_s16_e4m3_to_fp8_v1  (plan section 5 row 1, section 7).
//
// WHAT IT COMPUTES.  E2M1 elements carrying ONE E4M3FN scale per SCALE GROUP
// (16 by default) are dequantized to FP8 E4M3FN:
//
//     out[i] = rne_e4m3fn( e2m1(code[i]) * e4m3fn(scale[i / group]) )
//
// This is NOT mxfp4_e2m1, whose scale is E8M0 and whose group is 32.  The
// pinned vendor behaviour is fp4_act_quant(latent, 16, True,
// scale_dtype=float8_e4m3fn) in inference/model.py (docs/SOURCES.md,
// SRC-DSV41-FLASH-MODEL); the independent oracle is runtime/reference/fp4_kv.py.
//
// WHY ONE ROUNDING IS THE WHOLE CONTRACT.  An E2M1 magnitude is M*2**-1 with M
// in {0,1,2,3,4,6,8,12}; an E4M3FN magnitude is S*2**E with S in 0..15 and E in
// [-9,5].  The product significand M*S is at most 180 -- eight significant bits
// -- and the product exponent lies in [-10,4].  Every product is therefore
// EXACT in this datapath's 22-bit fixed-point alignment register, and the only
// rounding in the block is the single saturating round-to-nearest-even that
// encodes the E4M3FN result.  There is no intermediate-precision degree of
// freedom to declare, and no accumulation.
//
// PIPELINE.  STAGE COUNT 7, INITIATION INTERVAL 1.
//   issue                      : beat registers (LANES codes, one scale)
//   lane s1 decode             : E2M1 magnitude table, E4M3FN significand/exponent
//   lane s2 multiply           : 4x4 -> 8-bit significand product
//   lane s3 align              : left shift into the exact 22-bit fixed point
//   lane s4 normalize          : leading-one index (priority encode)
//   lane s5 extract            : truncated significand, round bit, sticky OR
//   lane s6 round and encode   : RNE increment, carry, saturate, sign
// Every stage is registered.  No combinational path walks a vector, a group or
// a lane array: the longest one is a 22-bit shift plus a 22-input sticky OR
// tree, whose depth is fixed by the FORMATS, not by any extent.  LANES
// elements retire every cycle, back to back, once the fetch pipeline is full;
// the block reports stall_cycles so that II=1 is measured rather than claimed.
//
// NO FROZEN MODEL GEOMETRY.  LANES, the default scale group, the element
// extent bound and every derived port width are PARAMETERS; the scale group
// itself is an OPERAND FIELD (cfg_group, 0 selecting the parameter default), so
// a group of 8, 32 or 64 needs no re-elaboration.  The only constants below are
// the two FORMAT definitions -- E2M1 and E4M3FN -- which are the contract, and
// the widths derived from them.  cfg_count is bounded by MAX_ELEMENTS, never by
// a model dimension; head_dim=512 appears nowhere in this file.
//
// OPERANDS, matching the IR's three-input DEQUANTIZE.  Slot 1 is the packed
// E2M1 code stream (CODE_BITS-wide elements, low nibble of a word first, as
// runtime.reference.formats.decode_packed_e2m1 defines).  Slot 2 is the
// scale-group operand (one E4M3FN byte per group, low byte of a word first).
// Slot 3 is the optional PASSTHROUGH operand: cfg_passthrough trailing elements
// copied verbatim as FP8, which is what the vendor's partial QDQ does to the
// channels it does not quantize.  cfg_passthrough=0 is the full-vector form
// this contract uses for the main latent.
//
// FAIL-CLOSED ATOMICITY.  A group whose scale is one of the two E4M3FN NaN
// encodings has no defined value, so the block SCANS the scale operand first
// (SCALES_PER_WORD codes per cycle) and leaves the destination completely
// untouched on poison, exactly as ot_a3_vector_convert does.  E2M1 has no
// exceptional encoding, so the code stream needs no scan.  Result saturation
// (|product| > 448) is COUNTED, not an error: the destination format is
// finite-only FP8 and the vendor path clamps as well.
//
// MEMORY CONTRACT.  Every read port is synchronous with ONE cycle of latency:
// data for an address presented with rd_en in cycle t is valid in cycle t+1.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// One dequantize lane.  Registered, 6 stages, II=1, one element per cycle.
// ---------------------------------------------------------------------------
module ot_a3_fp4kv_dequant_lane #(
    //: The FORMATS are the contract, not geometry: these exist so the widths
    //: below are named rather than magic, and an instance that changes them is
    //: refused at elaboration instead of computing something else silently.
    parameter integer CODE_BITS   = 4,   // E2M1
    parameter integer SCALE_BITS  = 8,   // E4M3FN
    parameter integer RESULT_BITS = 8    // E4M3FN
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    in_valid,
    input  wire [CODE_BITS-1:0]    in_code,
    input  wire [SCALE_BITS-1:0]   in_scale,
    input  wire                    in_bypass,
    input  wire [RESULT_BITS-1:0]  in_bypass_code,
    output reg                     out_valid,
    output reg  [RESULT_BITS-1:0]  out_code,
    output reg                     out_saturated,
    output reg                     out_scale_nonfinite
);
    // E2M1: magnitudes {0,.5,1,1.5,2,3,4,6} = M/2, M in {0,1,2,3,4,6,8,12}.
    localparam integer MAG_BITS   = 4;
    // E4M3FN: significand S in 0..15 (implicit bit included), exponent E in
    // [-9,5]; ESH = E+9 in [0,14] makes the alignment shift unsigned.
    localparam integer SIG_BITS   = 4;
    localparam integer ESH_BITS   = 4;
    localparam integer ESH_MAX    = 14;
    localparam integer PROD_BITS  = MAG_BITS + SIG_BITS;          // 8
    // Exact fixed point in units of 2**-10, the smallest product quantum.
    localparam integer ALIGN_BITS = PROD_BITS + ESH_MAX;          // 22
    localparam integer PIDX_BITS  = 5;                            // 0..21
    localparam integer SH_BITS    = 5;
    //: The largest FINITE E4M3FN magnitude, in the same 2**-10 units as the
    //: alignment register: significand 14 -- 15 with exponent field 15 is the
    //: NaN encoding -- at exponent field 15, i.e. 14*2**5 = 448.  Derived from
    //: the format, never written as a decimal literal.
    localparam integer MAX_SIGNIFICAND = (1 << (SIG_BITS - 1)) +
                                        ((1 << (SIG_BITS - 1)) - 2);
    localparam [ALIGN_BITS-1:0] MAX_FINITE_UNITS =
        MAX_SIGNIFICAND << (ESH_MAX + 1);

    initial begin
        if (CODE_BITS != 4 || SCALE_BITS != 8 || RESULT_BITS != 8)
            $fatal(1, "ot_a3_fp4kv_dequant_lane implements E2M1 x E4M3FN -> E4M3FN");
    end

    function automatic [MAG_BITS-1:0] e2m1_double_magnitude(input [2:0] index);
        case (index)
            3'd0: e2m1_double_magnitude = 4'd0;
            3'd1: e2m1_double_magnitude = 4'd1;
            3'd2: e2m1_double_magnitude = 4'd2;
            3'd3: e2m1_double_magnitude = 4'd3;
            3'd4: e2m1_double_magnitude = 4'd4;
            3'd5: e2m1_double_magnitude = 4'd6;
            3'd6: e2m1_double_magnitude = 4'd8;
            default: e2m1_double_magnitude = 4'd12;
        endcase
    endfunction

    function automatic [PIDX_BITS-1:0] leading_one(input [ALIGN_BITS-1:0] value);
        integer bit_index;
        begin
            leading_one = {PIDX_BITS{1'b0}};
            for (bit_index = 0; bit_index < ALIGN_BITS; bit_index = bit_index + 1)
                if (value[bit_index])
                    leading_one = bit_index[PIDX_BITS-1:0];
        end
    endfunction

    // ---- stage 1: decode --------------------------------------------------
    wire [2:0]           code_magnitude_index = in_code[2:0];
    wire                 code_sign            = in_code[CODE_BITS-1];
    wire [3:0]           scale_exponent_field = in_scale[6:3];
    wire [2:0]           scale_fraction       = in_scale[2:0];
    wire                 scale_sign           = in_scale[SCALE_BITS-1];
    wire                 scale_subnormal      = (scale_exponent_field == 4'd0);
    wire [SIG_BITS-1:0]  scale_significand    =
        scale_subnormal ? {1'b0, scale_fraction} : {1'b1, scale_fraction};
    wire [ESH_BITS-1:0]  scale_align_shift    =
        scale_subnormal ? {ESH_BITS{1'b0}} : (scale_exponent_field - 4'd1);
    wire                 scale_nonfinite      =
        (scale_exponent_field == 4'hf) && (scale_fraction == 3'h7);

    reg                    s1_valid, s1_sign, s1_nonfinite, s1_bypass;
    reg [MAG_BITS-1:0]     s1_magnitude;
    reg [SIG_BITS-1:0]     s1_significand;
    reg [ESH_BITS-1:0]     s1_shift;
    reg [RESULT_BITS-1:0]  s1_bypass_code;

    // ---- stage 2: multiply ------------------------------------------------
    reg                    s2_valid, s2_sign, s2_nonfinite, s2_bypass;
    reg [PROD_BITS-1:0]    s2_product;
    reg [ESH_BITS-1:0]     s2_shift;
    reg [RESULT_BITS-1:0]  s2_bypass_code;

    // ---- stage 3: align ---------------------------------------------------
    reg                    s3_valid, s3_sign, s3_nonfinite, s3_bypass;
    reg [ALIGN_BITS-1:0]   s3_aligned;
    reg [RESULT_BITS-1:0]  s3_bypass_code;

    // ---- stage 4: normalize ----------------------------------------------
    reg                    s4_valid, s4_sign, s4_nonfinite, s4_bypass, s4_zero;
    reg [ALIGN_BITS-1:0]   s4_aligned;
    reg [PIDX_BITS-1:0]    s4_leading;
    reg [RESULT_BITS-1:0]  s4_bypass_code;

    // ---- stage 5: extract -------------------------------------------------
    reg                    s5_valid, s5_sign, s5_nonfinite, s5_bypass, s5_zero;
    reg                    s5_normal, s5_round, s5_sticky, s5_exceeds;
    reg [SIG_BITS:0]       s5_truncated;     // 0..16
    reg [PIDX_BITS:0]      s5_exponent;      // pre-round E4M3FN exponent field
    reg [RESULT_BITS-1:0]  s5_bypass_code;

    wire                    s4_normal_w  = (s4_leading >= 5'd4);
    wire [SH_BITS-1:0]      shift_amount =
        s4_normal_w ? (s4_leading - 5'd3) : {{(SH_BITS-1){1'b0}}, 1'b1};
    wire [ALIGN_BITS-1:0]   truncated_w  = s4_aligned >> shift_amount;
    wire [ALIGN_BITS:0]     sticky_mask  =
        (({{ALIGN_BITS{1'b0}}, 1'b1}) << (shift_amount - 1)) - 1'b1;
    wire                    round_bit_w  =
        (s4_aligned >> (shift_amount - 1)) & 1'b1;
    wire                    sticky_w     =
        |(s4_aligned & sticky_mask[ALIGN_BITS-1:0]);
    //: Saturation is a property of the EXACT product, not of the rounded
    //: result: runtime.reference.formats.encode_e4m3fn_rne reports it when the
    //: magnitude exceeds the finite range, including magnitudes above 448 that
    //: would round back down to it.  One 22-bit comparison settles it, and it
    //: also makes the encode branch below unreachable for out-of-range inputs.
    wire                    exceeds_max_w = (s4_aligned > MAX_FINITE_UNITS);

    // ---- stage 6: round, carry, saturate, encode -------------------------
    wire [SIG_BITS+1:0]  round_increment =
        {{(SIG_BITS+1){1'b0}}, (s5_round & (s5_sticky | s5_truncated[0]))};
    wire [SIG_BITS+1:0]  rounded         = {1'b0, s5_truncated} + round_increment;
    wire [PIDX_BITS:0]   exponent_carry  = s5_exponent + 1'b1;
    wire                 significand_carry = s5_normal && (rounded == 6'd16);
    wire [PIDX_BITS:0]   final_exponent  =
        significand_carry ? exponent_carry : s5_exponent;
    wire [2:0]           final_fraction  =
        s5_normal ? (significand_carry ? 3'd0 : rounded[2:0]) : 3'd0;
    wire                 overflow        = s5_exceeds;
    // The subnormal branch needs no field split at all: an E4M3FN code's low
    // seven bits ARE exponent*8+fraction, and the subnormal rounding result is
    // 0..8, so the code equals it -- 8 being exactly the smallest normal.
    wire [6:0]           magnitude_code  =
        overflow ? {{(SIG_BITS){1'b1}}, 3'b110}
                 : (s5_normal ? {final_exponent[3:0], final_fraction}
                              : {2'b0, rounded[SIG_BITS:0]});
    wire [RESULT_BITS-1:0] encoded =
        (s5_zero || (magnitude_code == 7'd0)) ? {RESULT_BITS{1'b0}}
                                             : {s5_sign, magnitude_code};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_valid <= 1'b0; s1_sign <= 1'b0; s1_nonfinite <= 1'b0;
            s1_bypass <= 1'b0; s1_magnitude <= 0; s1_significand <= 0;
            s1_shift <= 0; s1_bypass_code <= 0;
            s2_valid <= 1'b0; s2_sign <= 1'b0; s2_nonfinite <= 1'b0;
            s2_bypass <= 1'b0; s2_product <= 0; s2_shift <= 0;
            s2_bypass_code <= 0;
            s3_valid <= 1'b0; s3_sign <= 1'b0; s3_nonfinite <= 1'b0;
            s3_bypass <= 1'b0; s3_aligned <= 0; s3_bypass_code <= 0;
            s4_valid <= 1'b0; s4_sign <= 1'b0; s4_nonfinite <= 1'b0;
            s4_bypass <= 1'b0; s4_zero <= 1'b0; s4_aligned <= 0;
            s4_leading <= 0; s4_bypass_code <= 0;
            s5_valid <= 1'b0; s5_sign <= 1'b0; s5_nonfinite <= 1'b0;
            s5_bypass <= 1'b0; s5_zero <= 1'b0; s5_normal <= 1'b0;
            s5_round <= 1'b0; s5_sticky <= 1'b0; s5_truncated <= 0;
            s5_exponent <= 0; s5_bypass_code <= 0;
            out_valid <= 1'b0; out_code <= 0; out_saturated <= 1'b0;
            out_scale_nonfinite <= 1'b0;
        end else begin
            s1_valid       <= in_valid;
            s1_sign        <= code_sign ^ scale_sign;
            s1_nonfinite   <= scale_nonfinite && !in_bypass;
            s1_bypass      <= in_bypass;
            s1_magnitude   <= e2m1_double_magnitude(code_magnitude_index);
            s1_significand <= scale_significand;
            s1_shift       <= scale_align_shift;
            s1_bypass_code <= in_bypass_code;

            s2_valid       <= s1_valid;
            s2_sign        <= s1_sign;
            s2_nonfinite   <= s1_nonfinite;
            s2_bypass      <= s1_bypass;
            s2_product     <= s1_magnitude * s1_significand;
            s2_shift       <= s1_shift;
            s2_bypass_code <= s1_bypass_code;

            s3_valid       <= s2_valid;
            s3_sign        <= s2_sign;
            s3_nonfinite   <= s2_nonfinite;
            s3_bypass      <= s2_bypass;
            s3_aligned     <= {{(ALIGN_BITS-PROD_BITS){1'b0}}, s2_product}
                              << s2_shift;
            s3_bypass_code <= s2_bypass_code;

            s4_valid       <= s3_valid;
            s4_sign        <= s3_sign;
            s4_nonfinite   <= s3_nonfinite;
            s4_bypass      <= s3_bypass;
            s4_zero        <= (s3_aligned == {ALIGN_BITS{1'b0}});
            s4_aligned     <= s3_aligned;
            s4_leading     <= leading_one(s3_aligned);
            s4_bypass_code <= s3_bypass_code;

            s5_valid       <= s4_valid;
            s5_sign        <= s4_sign;
            s5_nonfinite   <= s4_nonfinite;
            s5_bypass      <= s4_bypass;
            s5_zero        <= s4_zero;
            s5_normal      <= s4_normal_w && !s4_zero;
            s5_exceeds     <= exceeds_max_w;
            s5_round       <= s4_zero ? 1'b0 : round_bit_w;
            s5_sticky      <= s4_zero ? 1'b0 : sticky_w;
            s5_truncated   <= s4_zero ? {(SIG_BITS+1){1'b0}}
                                      : truncated_w[SIG_BITS:0];
            s5_exponent    <= (s4_normal_w && !s4_zero)
                              ? ({1'b0, s4_leading} - 6'd3)
                              : {(PIDX_BITS+1){1'b0}};
            s5_bypass_code <= s4_bypass_code;

            out_valid           <= s5_valid;
            out_code            <= s5_bypass ? s5_bypass_code : encoded;
            out_saturated       <= s5_valid && !s5_bypass && overflow;
            out_scale_nonfinite <= s5_valid && s5_nonfinite;
        end
    end
endmodule


// ---------------------------------------------------------------------------
// In-order fetch stream: one synchronous read port, at most one outstanding
// read, a two-entry skid buffer and a same-cycle bypass so the consumer can
// take one port beat EVERY cycle without a bubble.
// ---------------------------------------------------------------------------
module ot_a3_fp4kv_fetch #(
    parameter integer PORT_BITS = 32,
    parameter integer WORD_BITS = 32,
    parameter integer ADDR_BITS = 32,
    parameter integer COUNT_BITS = 20
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  load,
    input  wire [ADDR_BITS-1:0]  load_base,
    input  wire [COUNT_BITS-1:0] load_reads,
    output reg                   rd_en,
    output reg  [ADDR_BITS-1:0]  rd_addr,
    input  wire [PORT_BITS-1:0]  rd_data,
    input  wire                  pop,
    output wire                  head_valid,
    output wire [PORT_BITS-1:0]  head_data
);
    localparam integer PORT_WORDS = PORT_BITS / WORD_BITS;

    reg [PORT_BITS-1:0]  slot0, slot1;
    reg [1:0]            count;
    reg                  arriving;
    reg [COUNT_BITS-1:0] remaining;
    reg [ADDR_BITS-1:0]  next_addr;

    assign head_valid = (count != 2'd0) || arriving;
    assign head_data  = (count != 2'd0) ? slot0 : rd_data;

    wire       consume    = pop && head_valid;
    wire       push       = arriving && !(consume && (count == 2'd0));
    wire [1:0] base       = count - ((consume && (count != 2'd0)) ? 2'd1 : 2'd0);
    wire [2:0] count_next = {1'b0, base} + (push ? 3'd1 : 3'd0);
    //: A read issued NOW is presented next cycle and lands the cycle after
    //: that, so the read already in flight (rd_en) must be counted against the
    //: two slots as well.  Without that term the buffer over-fetches and a
    //: port beat is lost -- which, for a stream consumed one whole beat per
    //: cycle, silently skips an operand word.  The invariant this keeps is
    //: count + arriving <= 2 at every cycle, which is what makes the
    //: same-cycle bypass below safe.
    wire       issue      =
        ((count_next + (rd_en ? 3'd1 : 3'd0)) <= 3'd1) && (remaining != 0);

    reg [PORT_BITS-1:0] next_slot0, next_slot1;
    always @* begin
        next_slot0 = (consume && (count != 2'd0)) ? slot1 : slot0;
        next_slot1 = slot1;
        if (push) begin
            if (base == 2'd0) next_slot0 = rd_data;
            else              next_slot1 = rd_data;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            slot0 <= 0; slot1 <= 0; count <= 2'd0; arriving <= 1'b0;
            remaining <= 0; next_addr <= 0; rd_en <= 1'b0; rd_addr <= 0;
        end else if (load) begin
            slot0     <= 0;
            slot1     <= 0;
            count     <= 2'd0;
            arriving  <= 1'b0;
            rd_en     <= (load_reads != 0);
            rd_addr   <= load_base;
            next_addr <= load_base + PORT_WORDS;
            remaining <= (load_reads != 0) ? (load_reads - 1'b1) : load_reads;
        end else begin
            slot0    <= next_slot0;
            slot1    <= next_slot1;
            count    <= count_next[1:0];
            arriving <= rd_en;
            rd_en    <= issue;
            if (issue) begin
                rd_addr   <= next_addr;
                next_addr <= next_addr + PORT_WORDS;
                remaining <= remaining - 1'b1;
            end
        end
    end
endmodule


// ---------------------------------------------------------------------------
// The operator.
// ---------------------------------------------------------------------------
module ot_a3_vector_fp4kv_dequant #(
    //: Elements dequantized per cycle.  A wider instance is THIS parameter and
    //: nothing else: every port width, fetch ratio and alignment predicate
    //: below is derived from it.  Must be a power of two.
    parameter integer LANES = 4,
    //: Scale group used when the operand field cfg_group is zero.  The V4.1
    //: main latent's group, and a default only -- cfg_group overrides it.
    parameter integer SCALE_GROUP_DEFAULT = 16,
    //: Element-extent bound.  A capacity, not a model dimension.
    parameter integer MAX_ELEMENTS = 2048,
    //: Format widths.  These ARE the contract fp4_e2m1_s16_e4m3_to_fp8_v1.
    parameter integer CODE_BITS   = 4,
    parameter integer SCALE_BITS  = 8,
    parameter integer RESULT_BITS = 8,
    parameter integer WORD_BITS   = 32
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    //: operand fields
    input  wire [31:0]             cfg_count,        // total output elements
    input  wire [31:0]             cfg_group,        // 0 selects the default
    input  wire [31:0]             cfg_passthrough,  // trailing FP8 copies
    input  wire [31:0]             cfg_code_base,
    input  wire [31:0]             cfg_scale_base,
    input  wire [31:0]             cfg_pass_base,
    input  wire [31:0]             cfg_out_base,

    output wire                    a_rd_en,
    output wire [31:0]             a_rd_addr,
    input  wire [(((LANES*CODE_BITS) > WORD_BITS) ? (LANES*CODE_BITS) : WORD_BITS)-1:0] a_rd_data,
    output wire                    s_rd_en,
    output wire [31:0]             s_rd_addr,
    input  wire [WORD_BITS-1:0]    s_rd_data,
    output wire                    p_rd_en,
    output wire [31:0]             p_rd_addr,
    input  wire [(((LANES*RESULT_BITS) > WORD_BITS) ? (LANES*RESULT_BITS) : WORD_BITS)-1:0] p_rd_data,

    output reg                     out_we,
    output reg  [31:0]             out_addr,
    output reg  [(((LANES*RESULT_BITS) > WORD_BITS) ? (LANES*RESULT_BITS) : WORD_BITS)-1:0] out_data,

    output reg                     busy,
    output reg                     done,
    output reg  [7:0]              error_code,
    output reg  [31:0]             out_count,          // words written
    output reg  [31:0]             element_count,      // elements produced
    output reg  [31:0]             saturation_count,
    output reg  [31:0]             issue_beats,        // lane beats issued
    output reg  [31:0]             stall_cycles,       // II violations, must be 0
    output reg  [31:0]             scan_cycles
);
    localparam [7:0] ERR_NONE              = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_SHAPE             = ot_a3_engine_pkg::ERR_SHAPE;

    localparam integer CODES_PER_WORD    = WORD_BITS / CODE_BITS;
    localparam integer SCALES_PER_WORD   = WORD_BITS / SCALE_BITS;
    localparam integer RESULTS_PER_WORD  = WORD_BITS / RESULT_BITS;
    localparam integer BEAT_CODE_BITS    = LANES * CODE_BITS;
    localparam integer BEAT_RESULT_BITS  = LANES * RESULT_BITS;
    localparam integer A_PORT_BITS       =
        (BEAT_CODE_BITS > WORD_BITS) ? BEAT_CODE_BITS : WORD_BITS;
    localparam integer A_PORT_WORDS      = A_PORT_BITS / WORD_BITS;
    localparam integer CODES_PER_PORT    = A_PORT_BITS / CODE_BITS;
    localparam integer A_BEATS           = CODES_PER_PORT / LANES;
    localparam integer O_PORT_BITS       =
        (BEAT_RESULT_BITS > WORD_BITS) ? BEAT_RESULT_BITS : WORD_BITS;
    localparam integer O_PORT_WORDS      = O_PORT_BITS / WORD_BITS;
    localparam integer RESULTS_PER_PORT  = O_PORT_BITS / RESULT_BITS;
    localparam integer O_BEATS           = RESULTS_PER_PORT / LANES;
    localparam integer COUNT_W           = $clog2(MAX_ELEMENTS + 1);
    localparam integer READS_W           = COUNT_W + 1;
    localparam integer A_SUB_W           = (A_BEATS > 1) ? $clog2(A_BEATS) : 1;
    localparam integer O_SUB_W           = (O_BEATS > 1) ? $clog2(O_BEATS) : 1;
    localparam integer S_SUB_W           =
        (SCALES_PER_WORD > 1) ? $clog2(SCALES_PER_WORD) : 1;
    //: Alignment predicates as MASKS and extent divisions as SHIFTS.  LANES is
    //: a power of two by elaboration check and both port element counts are
    //: WORD_BITS/element_bits scaled by it, so every one of these is exact --
    //: and none of them depends on a synthesis tool folding a modulo away.
    localparam [31:0]  LANE_MASK         = LANES - 1;
    localparam [31:0]  CODE_PORT_MASK    = CODES_PER_PORT - 1;
    localparam [31:0]  RESULT_PORT_MASK  = RESULTS_PER_PORT - 1;
    localparam integer CODE_PORT_SHIFT   = $clog2(CODES_PER_PORT);
    localparam integer RESULT_PORT_SHIFT = $clog2(RESULTS_PER_PORT);
    localparam [A_SUB_W-1:0] CODE_SUB_LAST   = A_BEATS - 1;
    localparam [O_SUB_W-1:0] RESULT_SUB_LAST = O_BEATS - 1;
    localparam [S_SUB_W-1:0] SCALE_SUB_LAST  = SCALES_PER_WORD - 1;

    initial begin
        if (WORD_BITS != 32 || CODE_BITS != 4 || SCALE_BITS != 8 ||
            RESULT_BITS != 8)
            $fatal(1, "ot_a3_vector_fp4kv_dequant is E2M1 x E4M3FN -> E4M3FN in 32-bit words");
        if (LANES < 1 || (LANES & (LANES - 1)) != 0)
            $fatal(1, "LANES must be a power of two");
        if (SCALE_GROUP_DEFAULT < 1 || (SCALE_GROUP_DEFAULT % LANES) != 0)
            $fatal(1, "SCALE_GROUP_DEFAULT must be a positive multiple of LANES");
        if (MAX_ELEMENTS < 1)
            $fatal(1, "MAX_ELEMENTS must be positive");
    end

    localparam [3:0] S_IDLE  = 4'd0;
    localparam [3:0] S_CHECK = 4'd1;
    localparam [3:0] S_SCAN  = 4'd2;
    localparam [3:0] S_FILL  = 4'd3;
    localparam [3:0] S_RUN   = 4'd4;
    localparam [3:0] S_DRAIN = 4'd5;
    localparam [3:0] S_DONE  = 4'd6;

    reg [3:0]          state;
    reg [COUNT_W-1:0]  total_elements;
    reg [COUNT_W-1:0]  pass_elements;
    reg [COUNT_W-1:0]  dq_elements;
    reg [COUNT_W-1:0]  group_size;
    reg [READS_W-1:0]  scale_words;

    // ---- shape legality, every bound derived from a parameter or an operand
    wire [COUNT_W-1:0] group_w =
        (cfg_group == 0) ? SCALE_GROUP_DEFAULT[COUNT_W-1:0] : cfg_group[COUNT_W-1:0];
    wire [31:0]        dq_w    = cfg_count - cfg_passthrough;
    wire               shape_ok =
        (cfg_count != 0) && (cfg_count <= MAX_ELEMENTS) &&
        (cfg_passthrough <= cfg_count) &&
        (cfg_group <= MAX_ELEMENTS) &&
        (group_w != 0) &&
        (({{(32-COUNT_W){1'b0}}, group_w} & LANE_MASK) == 0) &&
        ((dq_w & CODE_PORT_MASK) == 0) &&
        ((cfg_passthrough & RESULT_PORT_MASK) == 0) &&
        ((cfg_count & RESULT_PORT_MASK) == 0);

    // ---- scale scan (SCALES_PER_WORD codes per cycle, II=1) ---------------
    reg                 scan_rd_en;
    reg [31:0]          scan_rd_addr;
    reg [READS_W-1:0]   scan_issued;
    reg [COUNT_W:0]     scan_issue_covered;
    reg [COUNT_W:0]     scan_check_covered;
    reg                 scan_checking;
    reg                 scan_poison;
    //: dq_elements must be a whole number of groups.  Testing it with a
    //: modulo would put a RUNTIME DIVIDER in the shape predicate for a
    //: runtime group; instead the scan's own accumulator witnesses it -- some
    //: group boundary must land exactly on dq_elements -- which costs one
    //: comparator per scale lane and no divider anywhere.
    reg                 scan_exact;

    // ---- code stream ------------------------------------------------------
    wire                     code_head_valid;
    wire [A_PORT_BITS-1:0]   code_head_data;
    wire                     code_pop;
    reg                      code_load;
    reg [READS_W-1:0]        code_reads;
    reg [A_PORT_BITS-1:0]    code_hold;
    reg                      code_hold_valid;
    reg [A_SUB_W-1:0]        code_sub;

    ot_a3_fp4kv_fetch #(
        .PORT_BITS(A_PORT_BITS), .WORD_BITS(WORD_BITS), .ADDR_BITS(32),
        .COUNT_BITS(READS_W)
    ) u_code_fetch (
        .clk(clk), .rst_n(rst_n), .load(code_load),
        .load_base(cfg_code_base), .load_reads(code_reads),
        .rd_en(a_rd_en), .rd_addr(a_rd_addr), .rd_data(a_rd_data),
        .pop(code_pop), .head_valid(code_head_valid), .head_data(code_head_data)
    );

    // ---- passthrough stream ----------------------------------------------
    wire                     pass_head_valid;
    wire [O_PORT_BITS-1:0]   pass_head_data;
    wire                     pass_pop;
    reg                      pass_load;
    reg [READS_W-1:0]        pass_reads;
    reg [O_PORT_BITS-1:0]    pass_hold;
    reg                      pass_hold_valid;
    reg [O_SUB_W-1:0]        pass_sub;

    ot_a3_fp4kv_fetch #(
        .PORT_BITS(O_PORT_BITS), .WORD_BITS(WORD_BITS), .ADDR_BITS(32),
        .COUNT_BITS(READS_W)
    ) u_pass_fetch (
        .clk(clk), .rst_n(rst_n), .load(pass_load),
        .load_base(cfg_pass_base), .load_reads(pass_reads),
        .rd_en(p_rd_en), .rd_addr(p_rd_addr), .rd_data(p_rd_data),
        .pop(pass_pop), .head_valid(pass_head_valid), .head_data(pass_head_data)
    );

    // ---- scale stream during RUN -----------------------------------------
    wire                     scale_head_valid;
    wire [WORD_BITS-1:0]     scale_head_data;
    wire                     scale_pop;
    reg                      scale_load;
    wire                     scale_fetch_rd_en;
    wire [31:0]              scale_fetch_rd_addr;
    reg [WORD_BITS-1:0]      scale_hold;
    reg                      scale_hold_valid;
    reg [S_SUB_W-1:0]        scale_sub;

    ot_a3_fp4kv_fetch #(
        .PORT_BITS(WORD_BITS), .WORD_BITS(WORD_BITS), .ADDR_BITS(32),
        .COUNT_BITS(READS_W)
    ) u_scale_fetch (
        .clk(clk), .rst_n(rst_n), .load(scale_load),
        .load_base(cfg_scale_base), .load_reads(scale_words),
        .rd_en(scale_fetch_rd_en), .rd_addr(scale_fetch_rd_addr),
        .rd_data(s_rd_data),
        .pop(scale_pop), .head_valid(scale_head_valid),
        .head_data(scale_head_data)
    );

    assign s_rd_en   = (state == S_SCAN) ? scan_rd_en   : scale_fetch_rd_en;
    assign s_rd_addr = (state == S_SCAN) ? scan_rd_addr : scale_fetch_rd_addr;

    // ---- issue ------------------------------------------------------------
    reg [COUNT_W-1:0]      elements_issued;
    reg [COUNT_W-1:0]      group_position;
    reg                    beat_valid;
    reg                    beat_bypass;
    reg [SCALE_BITS-1:0]   beat_scale;
    reg [BEAT_CODE_BITS-1:0]   beat_codes;
    reg [BEAT_RESULT_BITS-1:0] beat_pass_codes;

    wire in_passthrough = (elements_issued >= dq_elements);
    wire [BEAT_CODE_BITS-1:0] code_slice =
        code_hold[(code_sub * BEAT_CODE_BITS) +: BEAT_CODE_BITS];
    wire [BEAT_RESULT_BITS-1:0] pass_slice =
        pass_hold[(pass_sub * BEAT_RESULT_BITS) +: BEAT_RESULT_BITS];
    wire [SCALE_BITS-1:0] scale_slice =
        scale_hold[(scale_sub * SCALE_BITS) +: SCALE_BITS];

    wire operands_ready = in_passthrough
        ? pass_hold_valid
        : (code_hold_valid && scale_hold_valid);
    wire code_last_slice = (A_BEATS == 1) || (code_sub == CODE_SUB_LAST);
    wire pass_last_slice = (O_BEATS == 1) || (pass_sub == RESULT_SUB_LAST);
    wire group_last_beat = ((group_position + LANES) >= group_size);
    wire scale_last_slice = (SCALES_PER_WORD == 1) ||
        (scale_sub == SCALE_SUB_LAST);
    wire work_remaining = (elements_issued < total_elements);
    wire issue_beat = (state == S_RUN) && work_remaining && operands_ready;
    //: A consumed head must be retired in the SAME cycle it is read, or the
    //: next cycle re-reads it.  These are the only pop sources.
    wire code_consume  = issue_beat && !in_passthrough && code_last_slice;
    wire pass_consume  = issue_beat &&  in_passthrough && pass_last_slice;
    wire scale_consume = issue_beat && !in_passthrough && group_last_beat &&
                         scale_last_slice;
    wire fill_code  = (state == S_FILL) && !code_hold_valid  && code_head_valid;
    wire fill_scale = (state == S_FILL) && !scale_hold_valid && scale_head_valid;
    wire fill_pass  = (state == S_FILL) && !pass_hold_valid  && pass_head_valid;
    assign code_pop  = code_consume  || fill_code;
    assign pass_pop  = pass_consume  || fill_pass;
    assign scale_pop = scale_consume || fill_scale;

    // ---- lanes ------------------------------------------------------------
    wire [LANES-1:0]      lane_valid;
    wire [LANES-1:0]      lane_saturated;
    wire [LANES-1:0]      lane_nonfinite;
    wire [BEAT_RESULT_BITS-1:0] lane_codes;

    genvar lane;
    generate
        for (lane = 0; lane < LANES; lane = lane + 1) begin : g_lane
            wire [RESULT_BITS-1:0] lane_code;
            ot_a3_fp4kv_dequant_lane #(
                .CODE_BITS(CODE_BITS), .SCALE_BITS(SCALE_BITS),
                .RESULT_BITS(RESULT_BITS)
            ) u_lane (
                .clk(clk), .rst_n(rst_n),
                .in_valid(beat_valid),
                .in_code(beat_codes[(lane * CODE_BITS) +: CODE_BITS]),
                .in_scale(beat_scale),
                .in_bypass(beat_bypass),
                .in_bypass_code(beat_pass_codes[(lane * RESULT_BITS) +: RESULT_BITS]),
                .out_valid(lane_valid[lane]),
                .out_code(lane_code),
                .out_saturated(lane_saturated[lane]),
                .out_scale_nonfinite(lane_nonfinite[lane])
            );
            assign lane_codes[(lane * RESULT_BITS) +: RESULT_BITS] = lane_code;
        end
    endgenerate

    // ---- result packing ---------------------------------------------------
    reg [O_PORT_BITS-1:0] pack;
    reg [O_PORT_BITS-1:0] pack_next;
    reg [O_SUB_W-1:0]     pack_sub;
    reg [31:0]            write_addr;
    reg [COUNT_W:0]       lanes_retired;
    reg                   poison_seen;

    reg [15:0] saturated_now;
    integer lane_index;

    always @* begin
        pack_next = pack;
        pack_next[(pack_sub * BEAT_RESULT_BITS) +: BEAT_RESULT_BITS] =
            lane_codes;
    end
    always @* begin
        saturated_now = 16'd0;
        for (lane_index = 0; lane_index < LANES; lane_index = lane_index + 1)
            if (lane_saturated[lane_index]) saturated_now = saturated_now + 16'd1;
    end

    // ---- scan lane validity, constant multipliers only -------------------
    reg [SCALES_PER_WORD-1:0] scan_lane_used;
    reg [SCALES_PER_WORD-1:0] scan_lane_poison;
    reg [SCALES_PER_WORD:0]   scan_lane_exact;
    //: Group boundaries inside one scale word, as a chain of ADDS.  Writing
    //: them as scan_index*group_size would put a multiplier in the shape
    //: predicate for a runtime group; this way the control path holds no
    //: multiplier and no divider at all.
    reg [COUNT_W:0]           scan_boundary [0:SCALES_PER_WORD];
    integer scan_index;
    always @* begin
        scan_boundary[0] = scan_check_covered;
        for (scan_index = 1; scan_index <= SCALES_PER_WORD;
             scan_index = scan_index + 1)
            scan_boundary[scan_index] =
                scan_boundary[scan_index-1] + {1'b0, group_size};
        for (scan_index = 0; scan_index < SCALES_PER_WORD;
             scan_index = scan_index + 1) begin
            scan_lane_used[scan_index] =
                scan_boundary[scan_index] < {1'b0, dq_elements};
            scan_lane_poison[scan_index] =
                ((s_rd_data[(scan_index * SCALE_BITS) +: SCALE_BITS] & 8'h7f)
                 == 8'h7f);
        end
        for (scan_index = 0; scan_index <= SCALES_PER_WORD;
             scan_index = scan_index + 1)
            scan_lane_exact[scan_index] =
                scan_boundary[scan_index] == {1'b0, dq_elements};
    end

    //: One scale word covers SCALES_PER_WORD groups.  Accumulated by adds for
    //: the same reason as the boundaries above.
    reg [COUNT_W:0] group_span;
    integer span_index;
    always @* begin
        group_span = {(COUNT_W+1){1'b0}};
        for (span_index = 0; span_index < SCALES_PER_WORD;
             span_index = span_index + 1)
            group_span = group_span + {1'b0, group_size};
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            total_elements <= 0; pass_elements <= 0; dq_elements <= 0;
            group_size <= SCALE_GROUP_DEFAULT[COUNT_W-1:0]; scale_words <= 0;
            scan_rd_en <= 1'b0; scan_rd_addr <= 0; scan_issued <= 0;
            scan_issue_covered <= 0; scan_check_covered <= 0;
            scan_checking <= 1'b0; scan_poison <= 1'b0; scan_exact <= 1'b0;
            code_load <= 1'b0; code_reads <= 0;
            code_hold <= 0; code_hold_valid <= 1'b0; code_sub <= 0;
            pass_load <= 1'b0; pass_reads <= 0;
            pass_hold <= 0; pass_hold_valid <= 1'b0; pass_sub <= 0;
            scale_load <= 1'b0; scale_hold <= 0;
            scale_hold_valid <= 1'b0; scale_sub <= 0;
            elements_issued <= 0; group_position <= 0;
            beat_valid <= 1'b0; beat_bypass <= 1'b0; beat_scale <= 0;
            beat_codes <= 0; beat_pass_codes <= 0;
            pack <= 0; pack_sub <= 0; write_addr <= 0; lanes_retired <= 0;
            poison_seen <= 1'b0;
            out_we <= 1'b0; out_addr <= 0; out_data <= 0;
            busy <= 1'b0; done <= 1'b0; error_code <= ERR_NONE;
            out_count <= 0; element_count <= 0; saturation_count <= 0;
            issue_beats <= 0; stall_cycles <= 0; scan_cycles <= 0;
        end else begin
            done       <= 1'b0;
            out_we     <= 1'b0;
            code_load  <= 1'b0;
            pass_load  <= 1'b0;
            scale_load <= 1'b0;
            scan_rd_en <= 1'b0;
            beat_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        out_count <= 0;
                        element_count <= 0;
                        saturation_count <= 0;
                        issue_beats <= 0;
                        stall_cycles <= 0;
                        scan_cycles <= 0;
                        elements_issued <= 0;
                        group_position <= 0;
                        lanes_retired <= 0;
                        poison_seen <= 1'b0;
                        pack <= 0;
                        pack_sub <= 0;
                        code_sub <= 0;
                        pass_sub <= 0;
                        scale_sub <= 0;
                        code_hold_valid <= 1'b0;
                        pass_hold_valid <= 1'b0;
                        scale_hold_valid <= 1'b0;
                        scan_issued <= 0;
                        scan_issue_covered <= 0;
                        scan_check_covered <= 0;
                        scan_checking <= 1'b0;
                        scan_poison <= 1'b0;
                        scan_exact <= 1'b0;
                        write_addr <= cfg_out_base;
                        state <= S_CHECK;
                    end
                end

                S_CHECK: begin
                    if (!shape_ok) begin
                        error_code <= ERR_SHAPE;
                        state <= S_DONE;
                    end else begin
                        total_elements <= cfg_count[COUNT_W-1:0];
                        pass_elements  <= cfg_passthrough[COUNT_W-1:0];
                        dq_elements    <= dq_w[COUNT_W-1:0];
                        group_size     <= group_w;
                        if (dq_w == 0) begin
                            // A pure passthrough needs no scale operand.
                            scale_words <= 0;
                            code_reads  <= 0;
                            pass_reads  <= cfg_passthrough[COUNT_W-1:0]
                                           >> RESULT_PORT_SHIFT;
                            code_load   <= 1'b1;
                            pass_load   <= 1'b1;
                            scale_load  <= 1'b1;
                            state       <= S_FILL;
                        end else begin
                            state <= S_SCAN;
                        end
                    end
                end

                // One scale WORD per cycle: issue while elements remain
                // uncovered, check the word issued in the previous cycle.  The
                // covered accumulators replace a divider: nothing here needs
                // dq_elements / group_size.
                S_SCAN: begin
                    scan_cycles <= scan_cycles + 1;
                    if (scan_issue_covered < {1'b0, dq_elements}) begin
                        scan_rd_en   <= 1'b1;
                        scan_rd_addr <= cfg_scale_base + scan_issued;
                        scan_issued  <= scan_issued + 1'b1;
                        scan_issue_covered <= scan_issue_covered + group_span;
                    end
                    if (scan_checking) begin
                        if (|(scan_lane_poison & scan_lane_used))
                            scan_poison <= 1'b1;
                        if (|scan_lane_exact)
                            scan_exact <= 1'b1;
                        scan_check_covered <= scan_check_covered + group_span;
                    end
                    scan_checking <= scan_rd_en;
                    if (scan_poison) begin
                        error_code <= ERR_OPERAND_NONFINITE;
                        state <= S_DONE;
                    end else if (!scan_rd_en && !scan_checking &&
                                 (scan_issue_covered >= {1'b0, dq_elements})) begin
                        if (!scan_exact) begin
                            //: no group boundary landed on dq_elements, i.e.
                            //: the quantized extent is not a whole number of
                            //: groups.  Nothing has been written.
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            scale_words <= scan_issued;
                            code_reads  <= {1'b0, dq_elements}
                                           >> CODE_PORT_SHIFT;
                            pass_reads  <= {1'b0, pass_elements}
                                           >> RESULT_PORT_SHIFT;
                            code_load   <= 1'b1;
                            pass_load   <= 1'b1;
                            scale_load  <= 1'b1;
                            state       <= S_FILL;
                        end
                    end
                end

                // Pipeline fill: adopt the first port beat of every stream the
                // request needs.  Fill is latency, never initiation interval.
                S_FILL: begin
                    if (fill_code) begin
                        code_hold       <= code_head_data;
                        code_hold_valid <= 1'b1;
                    end
                    if (fill_scale) begin
                        scale_hold       <= scale_head_data;
                        scale_hold_valid <= 1'b1;
                    end
                    if (fill_pass) begin
                        pass_hold       <= pass_head_data;
                        pass_hold_valid <= 1'b1;
                    end
                    if (((dq_elements == 0) ||
                         (code_hold_valid && scale_hold_valid)) &&
                        ((pass_elements == 0) || pass_hold_valid))
                        state <= S_RUN;
                end

                S_RUN: begin
                    if (issue_beat) begin
                        beat_valid      <= 1'b1;
                        beat_bypass     <= in_passthrough;
                        beat_codes      <= code_slice;
                        beat_scale      <= scale_slice;
                        beat_pass_codes <= pass_slice;
                        issue_beats     <= issue_beats + 1'b1;
                        elements_issued <= elements_issued + LANES;

                        if (in_passthrough) begin
                            if (pass_last_slice) begin
                                pass_hold       <= pass_head_data;
                                pass_hold_valid <= pass_head_valid;
                                pass_sub        <= 0;
                            end else begin
                                pass_sub <= pass_sub + 1'b1;
                            end
                        end else begin
                            if (code_last_slice) begin
                                code_hold       <= code_head_data;
                                code_hold_valid <= code_head_valid;
                                code_sub        <= 0;
                            end else begin
                                code_sub <= code_sub + 1'b1;
                            end
                            if (group_last_beat) begin
                                group_position <= 0;
                                if (scale_last_slice) begin
                                    scale_hold       <= scale_head_data;
                                    scale_hold_valid <= scale_head_valid;
                                    scale_sub        <= 0;
                                end else begin
                                    scale_sub <= scale_sub + 1'b1;
                                end
                            end else begin
                                group_position <= group_position + LANES;
                            end
                            // The last quantized beat hands the lanes over to
                            // the passthrough operand; its first slice is
                            // already resident from S_FILL.
                        end
                    end else if (work_remaining) begin
                        stall_cycles <= stall_cycles + 1'b1;
                    end
                    if (!work_remaining)
                        state <= S_DRAIN;
                end

                S_DRAIN: begin
                    if (lanes_retired >= {1'b0, total_elements})
                        state <= S_DONE;
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    if (poison_seen)
                        error_code <= ERR_OPERAND_NONFINITE;
                    state <= S_IDLE;
                end

                default: begin
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase

            // ---- retire: pack LANES results per cycle into port writes ----
            if (lane_valid[0]) begin
                lanes_retired    <= lanes_retired + LANES;
                element_count    <= element_count + LANES;
                saturation_count <= saturation_count + {16'b0, saturated_now};
                if (|lane_nonfinite)
                    poison_seen <= 1'b1;
                pack <= pack_next;
                if ((O_BEATS == 1) || (pack_sub == RESULT_SUB_LAST)) begin
                    pack_sub   <= 0;
                    out_we     <= 1'b1;
                    out_addr   <= write_addr;
                    out_data   <= pack_next;
                    write_addr <= write_addr + O_PORT_WORDS;
                    out_count  <= out_count + O_PORT_WORDS;
                end else begin
                    pack_sub <= pack_sub + 1'b1;
                end
            end
        end
    end
endmodule
