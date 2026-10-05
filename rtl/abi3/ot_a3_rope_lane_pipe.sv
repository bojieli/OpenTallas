`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VECTOR.ROPE lane, PIPELINED and MULTI-POSITION.
//
// STAGE COUNT 6.  INITIATION INTERVAL 1 (one rotated element per cycle), for
// every launch with two or more heads per position; see THE ONE PLACE II IS NOT
// ONE below for the single-head case, which is bandwidth-bound rather than
// pipeline-bound.
//
// WHY THIS EXISTS.  ot_ta_rope_bf16_sram_engine is the qualified RoPE datapath
// and it is not touched by this file.  Two things are wrong with it for prefill:
//
//   1. ONE LAUNCH IS EXACTLY ONE POSITION.  Its coefficient row is loaded once
//      per command and on the last coefficient index falls through to the input
//      stage, so nothing iterates positions.  A 16-token prefill issues the same
//      83 launches as decode, each covering a span of 16 positions, and the
//      qualified core cannot retire one.
//
//   2. IT IS NOT A PIPELINE AT ALL.  Its STATE_COMPUTE resolves, in ONE
//      combinational cycle, fp32_mul_rne twice, then fp32_to_bf16_rne twice,
//      then fp32_add_rne, then fp32_to_bf16_rne again -- four dependent
//      binary32 operations end to end.  It then spends two cycles per operand
//      word (REQ, WAIT) and a further cycle per element draining the output
//      buffer, so it retires one element every four cycles through the longest
//      combinational path in the engine.
//
// This lane retires one element per CYCLE through a path of ONE of those
// operations.  The arithmetic is the same six ot_fp32_rne_pkg calls in the same
// order -- one per registered stage -- so the result is bit-identical to the
// qualified core by construction, not by a numeric argument.  That is the whole
// reason the stages are cut where they are:
//
//   stage 1  index generation: position, head, column, bank selects (registered
//            counters; the operand banks are read combinationally off them)
//   stage 2  operand capture: x[c], the partner x[c^half] with the sign flip and
//            signed-zero canonicalisation applied, cos[c], sin[c]
//   stage 3  fp32_mul_rne(x, cos) and fp32_mul_rne(rot, sin), in parallel
//   stage 4  fp32_to_bf16_rne of each product, in parallel
//   stage 5  fp32_add_rne of the two BF16-rounded products
//   stage 6  fp32_to_bf16_rne of the sum, registered into the output block
//
// There is no reduction anywhere in RoPE -- every output element depends on
// exactly two input elements and two coefficients -- so there is no
// loop-carried dependence to break and no adder tree to build.  That is why
// II 1 is reachable here without the interleaving ot_a3_mac_lane_pipe needs.
//
// The Fmax this lane can close at is therefore set by its slowest single stage,
// which is stage 5, ot_fp32_rne_pkg::fp32_add_rne.  That function resolves
// align/add/normalise/round through a 524-bit exact intermediate and is
// measured elsewhere in this repository at 174 MHz (see the header of
// rtl/proto/ot_mac_bf16_fp32_pipe.sv).  This lane does NOT claim 500 MHz: it
// claims the same arithmetic at one quarter of the combinational depth and one
// quarter of the cycles, which is a measured 4x on both axes.  Closing the
// remaining gap means replacing stage 5 with rtl/proto/ot_bf16_add_pipe.sv,
// which is five balanced stages and is SAT-proven equal to ot_bf16_add_rne --
// but NOT yet proven equal to the fp32_add_rne + fp32_to_bf16_rne pair that the
// qwen3_rope_fp32_bf16_v1 contract actually names.  Substituting it is a
// numeric requalification, not a pipelining change, and it is deliberately not
// done here where a wrong answer would be indistinguishable from a fast one.
//
// HOW A SPAN IS RETIRED, and why nothing multiplies.  The three operand regions
// of a span-S launch are plain contiguous sweeps, because that is exactly what
// the bridge's own RoPE view predicates already require:
//
//   input        S blocks of heads*cols BF16 words   (view stride0 = heads*cols)
//   coefficient  S rows  of 2*cols FP32 words        (view stride0 = 2*cols)
//   output       S blocks of heads*cols BF16 words   (view stride0 = heads*cols)
//
// So all three address generators are linear counters seeded from their base,
// and the position/head/column structure is needed only to pick banks and to
// mark block boundaries.  There is no multiplier and no divider in this module.
//
// FOUR ENGINES RUN CONCURRENTLY, coupled by two-deep ping-pong flags:
//
//   coefficient prefetch  fills cos/sin bank ~b while the pipe reads bank b, so
//                         position p+1's coefficient row lands DURING position
//                         p's work.  This is the answer to "the coefficient
//                         reload must overlap the previous position work": it
//                         costs 2*cols of the position's heads*cols cycles.
//   row prefetch          fills head-row bank ~b while the pipe reads bank b.
//                         A row is cols words and yields cols elements, so at
//                         one word per cycle the row fetch exactly keeps up.
//   compute pipe          the six stages above, one element per cycle.
//   block drain           writes position p's finished block out at one word
//                         per cycle while the pipe computes position p+1.
//
// WHAT A WHOLE LAUNCH COSTS, which is not the same number as the II.  Steady
// state is one element per cycle, and around it sit one coefficient row of
// prologue (2*cols, before the first element can issue) and one output block of
// epilogue (heads*cols, because the last position's block is written only after
// it validates -- see ATOMICITY).  So a span-S launch costs about
//
//     2*cols + (S + 1) * heads*cols
//
// and cycles per element approaches 1 from above as S grows.  MEASURED, at
// 8 heads x 16 columns: 1.106 at span 16, 1.034 at span 128, and 1.018 at span
// 128 with three output blocks.  At the shipped 32 x 128 geometry a 16-position
// prefill measures 69,945 cycles for 65,536 elements, against 16 x 21,012 for
// the qualified core.
//
// THE ONE PLACE II IS NOT ONE.  A position needs 2*cols coefficient words to
// produce heads*cols elements.  With heads >= 2 the prefetch hides completely.
// With heads == 1 the launch is coefficient-bandwidth-bound and II is 2: one
// coefficient port word per element is the floor, and no amount of pipelining
// changes it.  Stated rather than hidden, and measured: a 1 x 2 head at span 16
// retires in 97 cycles for 32 elements.
//
// ATOMICITY.  The qualified core validates and buffers all of a launch's
// elements before its first destination write.  This lane keeps that property
// PER POSITION: a block is drained only after its last element has retired
// without fault, so a faulting launch leaves whole validated positions and
// never a torn one.  At span 1 -- every decode launch -- per-position and
// per-launch atomicity are the same statement.  Buffering a whole 16-position
// span instead would cost 16x the output block for no property a per-position
// guarantee does not already give, since the positions are independent.
//
// NO FROZEN GEOMETRY.  Every bound is a parameter and every index is $clog2 of
// its bound.  MAX_HEADS and MAX_HEAD_WIDTH are handed down from the wrapper's
// own geometry, so they cannot disagree with it.  MAX_POSITION_SPAN bounds only
// the position counters -- no array is sized by it, because positions stream --
// which is why its default is large enough not to be a policy.
// ---------------------------------------------------------------------------
module ot_a3_rope_lane_pipe #(
    //: Heads per position.  The wrapper passes max(QUERY_HEADS, KEY_HEADS): a
    //: VECTOR.ROPE launch declares one operand, never both.
    parameter [31:0] MAX_HEADS = 32'd32,
    parameter [31:0] MAX_HEAD_WIDTH = 32'd128,
    //: Positions per launch.  A bound, not geometry: it sizes the position
    //: counters and nothing else, so raising it costs $clog2 flip-flops.  The
    //: default covers any prefill chunk this ABI can describe.
    parameter [31:0] MAX_POSITION_SPAN = 32'd65536,
    //: BUFFER DEPTHS, and the row depth is the one that matters.  A bank read
    //: answers two cycles after the engine decides to issue it, and the input
    //: port has NO headroom -- a row is cols words and yields exactly cols
    //: elements -- so a two-deep ping-pong forces the row fetch idle at every
    //: row boundary and loses those two cycles for good, measured as 1.22
    //: cycles per element instead of 1.  Three banks are enough for the fetch
    //: to issue continuously across a row boundary; four leaves margin and
    //: costs one more half-row pair.
    parameter integer ROW_BUFFERS = 4,
    //: A position needs 2*cols coefficient words per heads*cols elements, so
    //: from three heads up the prefetch has a whole row of slack and two banks
    //: hide it completely.
    parameter integer COEF_BUFFERS = 2,
    //: Output blocks are the expensive buffer -- heads*cols words each.  A
    //: block is drainable only once its last element has VALIDATED, so the
    //: drain runs one pipeline depth behind the compute and two blocks cost
    //: three cycles per position: measured 1.0338 cycles per element at span
    //: 128 against 1.0184 with three.  Three buffers remove the bubble and buy
    //: 1.5% for another heads*cols words, which is not worth 4,096 words at the
    //: shipped geometry and is worth it at a small one.  The parameter is here
    //: so that is a deployment's choice rather than this file's.
    parameter integer OUT_BUFFERS = 2
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,

    //: Per launch.  cfg_span is the resolved view extent: 1 for decode.
    input  wire [31:0] cfg_heads,
    input  wire [31:0] cfg_cols,
    input  wire [31:0] cfg_span,
    input  wire [31:0] cfg_input_base,
    input  wire [31:0] cfg_coefficient_base,
    input  wire [31:0] cfg_output_base,

    output reg         input_rd_en,
    output reg  [31:0] input_rd_addr,
    input  wire [31:0] input_rd_data,
    output reg         coefficient_rd_en,
    output reg  [31:0] coefficient_rd_addr,
    input  wire [31:0] coefficient_rd_data,
    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] result_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] work_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    //: INDEX WIDTHS, every one $clog2 of the bound above it.  A hand-sized
    //: index is how the RMS normaliser turned a raised ceiling into a hang
    //: instead of a refusal, so none of these is written down.
    localparam integer CW = (MAX_HEAD_WIDTH <= 1) ? 1 : $clog2(MAX_HEAD_WIDTH);
    localparam integer HALFW =
        (MAX_HEAD_WIDTH <= 2) ? 1 : $clog2(MAX_HEAD_WIDTH / 2);
    localparam integer HIW = (MAX_HEADS <= 1) ? 1 : $clog2(MAX_HEADS);
    localparam integer PSW =
        (MAX_POSITION_SPAN <= 1) ? 1 : $clog2(MAX_POSITION_SPAN);
    localparam integer BLOCK_MAX = MAX_HEADS * MAX_HEAD_WIDTH;
    localparam integer EIW = (BLOCK_MAX <= 1) ? 1 : $clog2(BLOCK_MAX);
    localparam integer HALF_MAX = (MAX_HEAD_WIDTH < 2) ? 1 : MAX_HEAD_WIDTH / 2;
    localparam integer RBW = (ROW_BUFFERS <= 1) ? 1 : $clog2(ROW_BUFFERS);
    localparam integer CBW = (COEF_BUFFERS <= 1) ? 1 : $clog2(COEF_BUFFERS);
    localparam integer OBW = (OUT_BUFFERS <= 1) ? 1 : $clog2(OUT_BUFFERS);
    //: The last bank index, at exactly the width of a bank index.  Subtracting
    //: one from the 32-bit parameter and letting the assignment truncate is the
    //: shape of defect a -Wno-fatal build turns into a wrong answer, so the
    //: parameter is narrowed FIRST and the decrement happens at index width --
    //: which is exact, because $clog2(N) bits always hold N-1.
    localparam [31:0] ROW_BUFFERS_W = ROW_BUFFERS;
    localparam [31:0] COEF_BUFFERS_W = COEF_BUFFERS;
    localparam [31:0] OUT_BUFFERS_W = OUT_BUFFERS;
    localparam [RBW-1:0] LAST_ROW_BANK = ROW_BUFFERS_W[RBW-1:0] - 1'b1;
    localparam [CBW-1:0] LAST_COEF_BANK = COEF_BUFFERS_W[CBW-1:0] - 1'b1;
    localparam [OBW-1:0] LAST_OUT_BANK = OUT_BUFFERS_W[OBW-1:0] - 1'b1;

    // ---- launch configuration, latched ------------------------------------
    reg [CW:0]    cols_q;        // 1..MAX_HEAD_WIDTH
    reg [CW-1:0]  half_q;        // cols/2
    reg [CW+1:0]  coef_len_q;    // 2*cols
    reg [HIW:0]   heads_q;       // 1..MAX_HEADS
    reg [PSW:0]   span_q;        // 1..MAX_POSITION_SPAN
    reg [31:0]    total_q;       // words the drain must write, counted not multiplied

    // ---- operand storage, two banks of everything --------------------------
    //: cos and sin are separate arrays so the pipe reads both in one cycle
    //: without a two-read-port memory.  The head row is split at the half
    //: boundary for the same reason: an element needs x[c] and x[c^half], which
    //: is exactly one word from each half.
    reg [15:0] cos_bank [0:COEF_BUFFERS-1][0:MAX_HEAD_WIDTH-1];
    reg [15:0] sin_bank [0:COEF_BUFFERS-1][0:MAX_HEAD_WIDTH-1];
    reg [15:0] low_bank [0:ROW_BUFFERS-1][0:HALF_MAX-1];
    reg [15:0] upp_bank [0:ROW_BUFFERS-1][0:HALF_MAX-1];
    reg [15:0] out_block [0:OUT_BUFFERS-1][0:BLOCK_MAX-1];

    reg [COEF_BUFFERS-1:0] coef_ready;   // coefficient row complete in bank b
    reg [ROW_BUFFERS-1:0]  row_ready;    // head row complete in bank b
    reg [OUT_BUFFERS-1:0]  block_ready;  // output block validated in bank b

    // ---- coefficient prefetch ---------------------------------------------
    reg        cf_active;
    reg [31:0] cf_addr;
    reg [CW+1:0] cf_issue;       // 0..2*cols, words requested for this row
    reg [CBW-1:0] cf_bank;
    reg [PSW:0] cf_pos;
    reg        cf_s0_v, cf_s1_v;
    reg [CBW-1:0] cf_s0_bank, cf_s1_bank;
    reg [CW+1:0] cf_s0_idx, cf_s1_idx;
    reg        cf_s0_last, cf_s1_last;

    // ---- head-row prefetch -------------------------------------------------
    reg        rf_active;
    reg [31:0] rf_addr;
    reg [CW:0] rf_issue;         // 0..cols
    reg [RBW-1:0] rf_bank;
    reg [HIW:0] rf_head;
    reg [PSW:0] rf_pos;
    reg        rf_s0_v, rf_s1_v;
    reg [RBW-1:0] rf_s0_bank, rf_s1_bank;
    reg [CW:0] rf_s0_idx, rf_s1_idx;
    reg        rf_s0_last, rf_s1_last;

    // ---- compute pipe ------------------------------------------------------
    reg        cp_active;
    reg [CW-1:0] cp_col;
    reg [HIW:0] cp_head;
    reg [PSW:0] cp_pos;
    reg [RBW-1:0] cp_rbank;      // head-row bank being consumed
    reg [CBW-1:0] cp_cbank;      // coefficient bank being consumed
    reg [OBW-1:0] cp_obank;      // output block being filled

    reg        p2_v, p2_last;
    reg [OBW-1:0] p2_obank;
    reg [15:0] p2_x, p2_rot, p2_cos, p2_sin;
    reg        p3_v, p3_last;
    reg [OBW-1:0] p3_obank;
    reg [31:0] p3_direct, p3_rotated;
    reg        p4_v, p4_last;
    reg [OBW-1:0] p4_obank;
    reg [15:0] p4_direct, p4_rotated;
    reg        p5_v, p5_last;
    reg [OBW-1:0] p5_obank;
    reg [31:0] p5_sum;
    reg [EIW-1:0] wr_index [0:OUT_BUFFERS-1];

    // ---- block drain -------------------------------------------------------
    reg        dr_active;
    reg [31:0] dr_addr;
    reg [EIW-1:0] dr_index;
    reg [CW-1:0] dr_col;
    reg [HIW:0] dr_head;
    reg [PSW:0] dr_pos;
    reg [OBW-1:0] dr_bank;

    reg        fault;
    reg [7:0]  fault_code;

    // ---- combinational operand selection (the stage 1 to 2 path) -----------
    wire [CW-1:0] pair_index =
        (cp_col < half_q) ? cp_col : (cp_col - half_q);
    wire [HALFW-1:0] pair_addr = pair_index[HALFW-1:0];
    wire [15:0] low_word = low_bank[cp_rbank][pair_addr];
    wire [15:0] upp_word = upp_bank[cp_rbank][pair_addr];
    wire        col_lower = cp_col < half_q;
    wire [15:0] direct_code = col_lower ? low_word : upp_word;
    wire [15:0] partner_code = col_lower ? upp_word : low_word;
    //: concat(-second_half, first_half), with signed zero canonicalised, which
    //: is the pinned Qwen half-rotation the qualified core implements.
    wire [15:0] rotated_code = col_lower
        ? ((partner_code[14:0] != 0) ? (partner_code ^ 16'h8000) : 16'h0000)
        : partner_code;
    wire [15:0] cos_code = cos_bank[cp_cbank][cp_col];
    wire [15:0] sin_code = sin_bank[cp_cbank][cp_col];

    //: cols_q-1, not half_q+half_q-1: the doubled half overflows a
    //: $clog2(MAX_HEAD_WIDTH)-bit adder at the widest admitted head.
    wire [CW:0] last_column = cols_q - 1'b1;
    wire cp_last_col = {1'b0, cp_col} == last_column;
    wire cp_last_head = cp_head == (heads_q - 1'b1);
    wire cp_issue = cp_active && !fault &&
                    coef_ready[cp_cbank] && row_ready[cp_rbank] &&
                    !block_ready[cp_obank];

    // ---- the six arithmetic stages, one ot_fp32_rne_pkg call each -----------
    wire [33:0] stage3_direct = ot_fp32_rne_pkg::fp32_mul_rne(
        {p2_x, 16'b0}, {p2_cos, 16'b0}
    );
    wire [33:0] stage3_rotated = ot_fp32_rne_pkg::fp32_mul_rne(
        {p2_rot, 16'b0}, {p2_sin, 16'b0}
    );
    wire [18:0] stage4_direct =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(p3_direct);
    wire [18:0] stage4_rotated =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(p3_rotated);
    wire [33:0] stage5_sum = ot_fp32_rne_pkg::fp32_add_rne(
        {p4_direct, 16'b0}, {p4_rotated, 16'b0}
    );
    wire [18:0] stage6_result =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(p5_sum);

    //: The qualified core raises ERR_ARITHMETIC_OVERFLOW if ANY of these six
    //: reports a non-representable result, before it writes anything.  Each is
    //: checked in the stage that produces it, and the fault suppresses the
    //: whole position, so the observable behaviour is the core's.
    wire stage3_error = (stage3_direct[33:32] != 2'd0) ||
                        (stage3_rotated[33:32] != 2'd0);
    wire stage4_error = (stage4_direct[18:17] != 2'd0) ||
                        (stage4_rotated[18:17] != 2'd0);
    wire stage5_error = stage5_sum[33:32] != 2'd0;
    wire stage6_error = stage6_result[18:17] != 2'd0;

    // ---- coefficient narrowing at the adapter boundary ---------------------
    //: ABI 3.0 coefficient rows are FP32 and the contract rotates BF16, so the
    //: row narrows RNE here exactly as the wrapper narrows it for the core.  A
    //: narrowing that cannot be represented is the core's nonfinite operand.
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(coefficient_rd_data);
    wire narrowed_nonfinite =
        (narrowed[18:17] != 2'd0) || (narrowed[14:7] == 8'hff);

    wire input_nonfinite = input_rd_data[14:7] == 8'hff;

    //: Bank offsets as named wires: a bit-select of an expression is not legal
    //: Verilog, and the silent alternative is a truncation.
    wire [CW+1:0] cf_sine_offset = cf_s1_idx - {1'b0, cols_q};
    wire [CW:0]   rf_upper_offset = rf_s1_idx - {1'b0, half_q};

    //: Bank rotation, written once.  Not a mask, so a non-power-of-two depth is
    //: legal and costs a comparator rather than a wrong index.
    wire [CBW-1:0] cf_next_bank =
        (cf_bank == LAST_COEF_BANK) ? {CBW{1'b0}} : cf_bank + 1'b1;
    wire [RBW-1:0] rf_next_bank =
        (rf_bank == LAST_ROW_BANK) ? {RBW{1'b0}} : rf_bank + 1'b1;
    wire [RBW-1:0] cp_next_rbank =
        (cp_rbank == LAST_ROW_BANK) ? {RBW{1'b0}} : cp_rbank + 1'b1;
    wire [CBW-1:0] cp_next_cbank =
        (cp_cbank == LAST_COEF_BANK) ? {CBW{1'b0}} : cp_cbank + 1'b1;
    wire [OBW-1:0] cp_next_obank =
        (cp_obank == LAST_OUT_BANK) ? {OBW{1'b0}} : cp_obank + 1'b1;
    wire [OBW-1:0] dr_next_bank =
        (dr_bank == LAST_OUT_BANK) ? {OBW{1'b0}} : dr_bank + 1'b1;

    wire cf_hold = coef_ready[cf_bank] && (cf_issue == 0);
    wire cf_go = cf_active && !fault && !cf_hold &&
                 (cf_issue < coef_len_q);
    wire rf_hold = row_ready[rf_bank] && (rf_issue == 0);
    wire rf_go = rf_active && !fault && !rf_hold &&
                 (rf_issue < cols_q);
    wire dr_go = dr_active && block_ready[dr_bank];

    wire pipe_busy = p2_v || p3_v || p4_v || p5_v;
    wire all_drained = dr_pos == span_q;

    integer bank_index;
    integer word_index;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cols_q <= 0; half_q <= 0; coef_len_q <= 0; heads_q <= 0;
            span_q <= 0; total_q <= 0;
            coef_ready <= 0; row_ready <= 0; block_ready <= 0;
            cf_active <= 1'b0; cf_addr <= 0; cf_issue <= 0; cf_bank <= 0;
            cf_pos <= 0; cf_s0_v <= 1'b0; cf_s1_v <= 1'b0;
            cf_s0_bank <= 0; cf_s1_bank <= 0;
            cf_s0_idx <= 0; cf_s1_idx <= 0;
            cf_s0_last <= 1'b0; cf_s1_last <= 1'b0;
            rf_active <= 1'b0; rf_addr <= 0; rf_issue <= 0; rf_bank <= 0;
            rf_head <= 0; rf_pos <= 0; rf_s0_v <= 1'b0; rf_s1_v <= 1'b0;
            rf_s0_bank <= 0; rf_s1_bank <= 0;
            rf_s0_idx <= 0; rf_s1_idx <= 0;
            rf_s0_last <= 1'b0; rf_s1_last <= 1'b0;
            cp_active <= 1'b0; cp_col <= 0; cp_head <= 0; cp_pos <= 0;
            cp_rbank <= 0; cp_cbank <= 0; cp_obank <= 0;
            p2_v <= 1'b0; p3_v <= 1'b0; p4_v <= 1'b0; p5_v <= 1'b0;
            p2_obank <= 0; p3_obank <= 0; p4_obank <= 0; p5_obank <= 0;
            p2_last <= 1'b0; p3_last <= 1'b0; p4_last <= 1'b0; p5_last <= 1'b0;
            p2_x <= 0; p2_rot <= 0; p2_cos <= 0; p2_sin <= 0;
            p3_direct <= 0; p3_rotated <= 0;
            p4_direct <= 0; p4_rotated <= 0; p5_sum <= 0;
            for (bank_index = 0; bank_index < OUT_BUFFERS;
                 bank_index = bank_index + 1)
                wr_index[bank_index] <= 0;
            dr_active <= 1'b0; dr_addr <= 0; dr_index <= 0; dr_col <= 0;
            dr_head <= 0; dr_pos <= 0; dr_bank <= 0;
            fault <= 1'b0; fault_code <= ERR_NONE;
            input_rd_en <= 1'b0; input_rd_addr <= 0;
            coefficient_rd_en <= 1'b0; coefficient_rd_addr <= 0;
            out_we <= 1'b0; out_addr <= 0; out_data <= 0;
            busy <= 1'b0; done <= 1'b0; error_code <= ERR_NONE;
            result_count <= 0; saturation_count <= 0; work_count <= 0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;

            // ================= launch =====================================
            if (start && !busy) begin
                error_code <= ERR_NONE;
                result_count <= 0;
                saturation_count <= 0;
                work_count <= 0;
                fault <= 1'b0;
                fault_code <= ERR_NONE;
                coef_ready <= 0; row_ready <= 0; block_ready <= 0;
                cf_issue <= 0; cf_bank <= 0; cf_pos <= 0;
                cf_s0_v <= 1'b0; cf_s1_v <= 1'b0;
                rf_issue <= 0; rf_bank <= 0; rf_head <= 0; rf_pos <= 0;
                rf_s0_v <= 1'b0; rf_s1_v <= 1'b0;
                cp_col <= 0; cp_head <= 0; cp_pos <= 0;
                cp_rbank <= 0; cp_cbank <= 0; cp_obank <= 0;
                p2_v <= 1'b0; p3_v <= 1'b0; p4_v <= 1'b0; p5_v <= 1'b0;
                for (bank_index = 0; bank_index < OUT_BUFFERS;
                     bank_index = bank_index + 1)
                    wr_index[bank_index] <= 0;
                dr_index <= 0; dr_col <= 0; dr_head <= 0; dr_pos <= 0;
                dr_bank <= 0;
                cf_addr <= cfg_coefficient_base;
                rf_addr <= cfg_input_base;
                dr_addr <= cfg_output_base;
                cols_q <= cfg_cols[CW:0];
                half_q <= cfg_cols[CW:1];
                coef_len_q <= {cfg_cols[CW:0], 1'b0};
                heads_q <= cfg_heads[HIW:0];
                span_q <= cfg_span[PSW:0];
                total_q <= 0;
                //: SHAPE.  Every bound is checked against its parameter, and an
                //: odd head width is refused because the half-rotation has no
                //: partner column -- the same predicate the qualified core
                //: applies to PROFILE_HEAD_WIDTH, applied to a launch.
                if ((cfg_cols == 0) || (cfg_cols[0] != 1'b0) ||
                    (cfg_cols > MAX_HEAD_WIDTH) ||
                    (cfg_heads == 0) || (cfg_heads > MAX_HEADS) ||
                    (cfg_span == 0) || (cfg_span > MAX_POSITION_SPAN)) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    error_code <= ERR_SHAPE;
                end else begin
                    busy <= 1'b1;
                    cf_active <= 1'b1;
                    rf_active <= 1'b1;
                    cp_active <= 1'b1;
                    dr_active <= 1'b1;
                end
            end

            // ================= coefficient prefetch =======================
            coefficient_rd_en <= cf_go;
            coefficient_rd_addr <= cf_addr;
            if (cf_go) begin
                cf_addr <= cf_addr + 32'd1;
                cf_s0_v <= 1'b1;
                cf_s0_bank <= cf_bank;
                cf_s0_idx <= cf_issue;
                cf_s0_last <= (cf_issue + 1'b1) == coef_len_q;
                //: THE ISSUE SIDE ADVANCES ON THE REQUEST, not on the response.
                //: Waiting for a row's last response before requesting the next
                //: row's first word idles the port for the two cycles of read
                //: latency at EVERY boundary, and neither port has headroom to
                //: give those cycles back -- one input word buys exactly one
                //: element.  Measured at eight heads of sixteen columns over a
                //: span of 16, that single coupling was 1.208 cycles per element
                //: against 1.106, and adding banks did not move it by one cycle:
                //: depth is irrelevant while the engine refuses to issue.
                if ((cf_issue + 1'b1) == coef_len_q) begin
                    cf_issue <= 0;
                    cf_bank <= cf_next_bank;
                    cf_pos <= cf_pos + 1'b1;
                    if ((cf_pos + 1'b1) == span_q)
                        cf_active <= 1'b0;
                end else begin
                    cf_issue <= cf_issue + 1'b1;
                end
            end else begin
                cf_s0_v <= 1'b0;
            end
            cf_s1_v <= cf_s0_v;
            cf_s1_bank <= cf_s0_bank;
            cf_s1_idx <= cf_s0_idx;
            cf_s1_last <= cf_s0_last;
            if (cf_s1_v) begin
                if (narrowed[16])
                    saturation_count <= saturation_count + 1'b1;
                if (narrowed_nonfinite) begin
                    if (!fault) begin
                        fault <= 1'b1;
                        fault_code <= ERR_OPERAND_NONFINITE;
                    end
                end else begin
                    if (cf_s1_idx < {1'b0, cols_q})
                        cos_bank[cf_s1_bank][cf_s1_idx[CW-1:0]] <=
                            narrowed[15:0];
                    else
                        sin_bank[cf_s1_bank][cf_sine_offset[CW-1:0]] <=
                            narrowed[15:0];
                end
                //: The response side only publishes the finished row.
                if (cf_s1_last)
                    coef_ready[cf_s1_bank] <= 1'b1;
            end

            // ================= head-row prefetch ==========================
            input_rd_en <= rf_go;
            input_rd_addr <= rf_addr;
            if (rf_go) begin
                rf_addr <= rf_addr + 32'd1;
                rf_s0_v <= 1'b1;
                rf_s0_bank <= rf_bank;
                rf_s0_idx <= rf_issue;
                rf_s0_last <= (rf_issue + 1'b1) == cols_q;
                if ((rf_issue + 1'b1) == cols_q) begin
                    rf_issue <= 0;
                    rf_bank <= rf_next_bank;
                    if (rf_head == (heads_q - 1'b1)) begin
                        rf_head <= 0;
                        rf_pos <= rf_pos + 1'b1;
                        if ((rf_pos + 1'b1) == span_q)
                            rf_active <= 1'b0;
                    end else begin
                        rf_head <= rf_head + 1'b1;
                    end
                end else begin
                    rf_issue <= rf_issue + 1'b1;
                end
            end else begin
                rf_s0_v <= 1'b0;
            end
            rf_s1_v <= rf_s0_v;
            rf_s1_bank <= rf_s0_bank;
            rf_s1_idx <= rf_s0_idx;
            rf_s1_last <= rf_s0_last;
            if (rf_s1_v) begin
                if (input_nonfinite) begin
                    if (!fault) begin
                        fault <= 1'b1;
                        fault_code <= ERR_OPERAND_NONFINITE;
                    end
                end else if (rf_s1_idx < {1'b0, half_q}) begin
                    low_bank[rf_s1_bank][rf_s1_idx[HALFW-1:0]] <=
                        input_rd_data[15:0];
                end else begin
                    upp_bank[rf_s1_bank][rf_upper_offset[HALFW-1:0]] <=
                        input_rd_data[15:0];
                end
                if (rf_s1_last)
                    row_ready[rf_s1_bank] <= 1'b1;
            end

            // ================= stage 1: index generation ==================
            if (cp_issue) begin
                if (cp_last_col) begin
                    cp_col <= 0;
                    row_ready[cp_rbank] <= 1'b0;
                    cp_rbank <= cp_next_rbank;
                    if (cp_last_head) begin
                        cp_head <= 0;
                        coef_ready[cp_cbank] <= 1'b0;
                        cp_cbank <= cp_next_cbank;
                        cp_obank <= cp_next_obank;
                        cp_pos <= cp_pos + 1'b1;
                        if ((cp_pos + 1'b1) == span_q)
                            cp_active <= 1'b0;
                    end else begin
                        cp_head <= cp_head + 1'b1;
                    end
                end else begin
                    cp_col <= cp_col + 1'b1;
                end
            end

            // ================= stage 2: operand capture ===================
            p2_v <= cp_issue;
            p2_obank <= cp_obank;
            p2_last <= cp_last_col && cp_last_head;
            p2_x <= direct_code;
            p2_rot <= rotated_code;
            p2_cos <= cos_code;
            p2_sin <= sin_code;

            // ================= stage 3: the two products ==================
            p3_v <= p2_v;
            p3_obank <= p2_obank;
            p3_last <= p2_last;
            //: Only the value crosses the stage boundary; the packed error
            //: bits are consumed in the cycle that produces them, below.
            p3_direct <= stage3_direct[31:0];
            p3_rotated <= stage3_rotated[31:0];
            if (p2_v && stage3_error && !fault) begin
                fault <= 1'b1;
                fault_code <= ERR_ACCUMULATE_RANGE;
            end

            // ================= stage 4: narrow each product ===============
            p4_v <= p3_v;
            p4_obank <= p3_obank;
            p4_last <= p3_last;
            p4_direct <= stage4_direct[15:0];
            p4_rotated <= stage4_rotated[15:0];
            if (p3_v && stage4_error && !fault) begin
                fault <= 1'b1;
                fault_code <= ERR_ACCUMULATE_RANGE;
            end

            // ================= stage 5: the sum ===========================
            p5_v <= p4_v;
            p5_obank <= p4_obank;
            p5_last <= p4_last;
            p5_sum <= stage5_sum[31:0];
            if (p4_v && stage5_error && !fault) begin
                fault <= 1'b1;
                fault_code <= ERR_ACCUMULATE_RANGE;
            end

            // ================= stage 6: narrow and retire =================
            if (p5_v) begin
                if (stage6_error && !fault) begin
                    fault <= 1'b1;
                    fault_code <= ERR_ACCUMULATE_RANGE;
                end
                out_block[p5_obank][wr_index[p5_obank]] <= stage6_result[15:0];
                if (p5_last) begin
                    wr_index[p5_obank] <= 0;
                    //: The block becomes drainable only here, once its LAST
                    //: element has retired without fault.  That is the
                    //: qualified core's validate-before-write, per position.
                    if (!fault && !stage6_error)
                        block_ready[p5_obank] <= 1'b1;
                end else begin
                    wr_index[p5_obank] <= wr_index[p5_obank] + 1'b1;
                end
            end

            // ================= block drain ================================
            if (dr_go) begin
                out_we <= 1'b1;
                out_addr <= dr_addr;
                out_data <= {16'd0, out_block[dr_bank][dr_index]};
                dr_addr <= dr_addr + 32'd1;
                total_q <= total_q + 32'd1;
                if ({1'b0, dr_col} == last_column) begin
                    dr_col <= 0;
                    if (dr_head == (heads_q - 1'b1)) begin
                        dr_head <= 0;
                        dr_index <= 0;
                        block_ready[dr_bank] <= 1'b0;
                        dr_bank <= dr_next_bank;
                        dr_pos <= dr_pos + 1'b1;
                    end else begin
                        dr_head <= dr_head + 1'b1;
                        dr_index <= dr_index + 1'b1;
                    end
                end else begin
                    dr_col <= dr_col + 1'b1;
                    dr_index <= dr_index + 1'b1;
                end
            end

            // ================= completion =================================
            if (busy) begin
                if (fault && !dr_go && (block_ready == 0)) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    error_code <= fault_code;
                    result_count <= total_q;
                    work_count <= total_q;
                    cf_active <= 1'b0; rf_active <= 1'b0;
                    cp_active <= 1'b0; dr_active <= 1'b0;
                end else if (!fault && all_drained && !cp_active &&
                             !pipe_busy) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    error_code <= ERR_NONE;
                    result_count <= total_q;
                    work_count <= total_q;
                    dr_active <= 1'b0;
                end
            end
        end
    end

    //: Deliberately unconsumed.  The high half of a verification-bank word
    //: carries no BF16 code; pair_index's top bit is provably zero because the
    //: index is below the half width; and the product and sum SATURATION bits
    //: are what the wrapper has always discarded -- it reports only the
    //: coefficient narrowing's saturation count.
    //: The three offsets appear whole rather than as their high slice: at the
    //: narrowest admitted head width the slice degenerates to a reversed part
    //: select, and a sink that only elaborates at some parameter values is worse
    //: than no sink.
    wire _unused_lane = &{1'b0, input_rd_data[31:16], pair_index,
        stage3_direct[33:32], stage3_rotated[33:32],
        stage4_direct[18:16], stage4_rotated[18:16],
        stage5_sum[33:32], stage6_result[18:16],
        cf_sine_offset, rf_upper_offset, narrowed[18:17]};

    //: Initialising the banks keeps a four-state simulation of a launch that
    //: refuses on shape from propagating X out of an unwritten word.
    initial begin
        for (bank_index = 0; bank_index < COEF_BUFFERS;
             bank_index = bank_index + 1)
            for (word_index = 0; word_index < MAX_HEAD_WIDTH;
                 word_index = word_index + 1) begin
                cos_bank[bank_index][word_index] = 16'd0;
                sin_bank[bank_index][word_index] = 16'd0;
            end
        for (bank_index = 0; bank_index < ROW_BUFFERS;
             bank_index = bank_index + 1)
            for (word_index = 0; word_index < HALF_MAX;
                 word_index = word_index + 1) begin
                low_bank[bank_index][word_index] = 16'd0;
                upp_bank[bank_index][word_index] = 16'd0;
            end
        for (bank_index = 0; bank_index < OUT_BUFFERS;
             bank_index = bank_index + 1)
            for (word_index = 0; word_index < BLOCK_MAX;
                 word_index = word_index + 1)
                out_block[bank_index][word_index] = 16'd0;
    end
endmodule
