`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact Qwen3-8B grouped-query attention datapath for a span of query rows.
//
// This engine implements qwen3_gqa_fp32_softmax_bf16_v1 for the ABI 3.0
// geometry [S,32,128] x [C,8,128].  Query heads 4*h..4*h+3 select KV head h.
// S is the resolved query SPAN: 1 for a decode launch, 16 for the reduced
// prefill launch.  Decode is the S=1 special case and is bit-identical to the
// pre-span engine -- see THE S=1 EQUIVALENCE below.
//
// C is a *runtime* length inside a compile-time bound, not a constant.  It
// was a constant 17, which expressed exactly one generated token: the
// governed workload's three decode positions run at contexts 17, 18 and 19,
// and the second and third were inexpressible.  ``MAX_CONTEXT`` now sizes the
// score, exponential and probability buffers, and ``cfg_context_length`` is
// checked against the closed interval [MIN_CONTEXT, MAX_CONTEXT] at start.
//
// The lower bound is not decoration.  The softmax denominator is the frozen
// eight-lane reduction, and ``binary32_lanes8_sum`` reduces a row shorter
// than eight *sequentially* -- a different association, and therefore
// potentially a different last bit.  This datapath implements the eight-lane
// branch only, so a context below eight is refused with ERR_CONFIG rather
// than reduced in an order the contract does not name.  Dot products and value reductions run in increasing logical index;
// every product/add rounds to binary32, the dot and scale round to BF16, and
// softmax uses the specified eight-lane reduction.  Exponential is delegated
// to the shared certifying transcendental engine and reciprocal to the shared
// correctly-rounded divider.
//
// ---------------------------------------------------------------------------
// THE QUERY ROW, AND WHERE THE CAUSAL BOUNDARY COMES FROM
// ---------------------------------------------------------------------------
// The loop nest was three deep with HEADS outermost and no token index at all:
// every row of a span would have re-read query row 0.  The nest is four deep
// now -- row, head, dimension, context -- and the row is the outermost level,
// because the softmax of row i head j depends on that row's own query vector
// and on nothing else in the span.
//
// A prefill of span S computes S query rows against one KV plane of C rows,
// and row i may attend only to context positions up to and including its own
// absolute sequence position.  The boundary is therefore ONE ABSOLUTE BASE
// POSITION plus the row index, ``cfg_first_position + i``, and NOT a per-row
// bound operand.  Three reasons, in order of weight:
//
//   1. It is what the contract already says.  The oracle
//      (runtime.reference.tensor_accelerator_attention.gqa_causal_attention_bf16)
//      computes ``visible_tokens = committed.length + query_index + 1`` and
//      masks key_index >= that.  ``cfg_first_position`` IS that committed KV
//      length.  A per-row bound vector would be a second, independent
//      statement of a quantity the oracle derives, and the two could disagree.
//   2. It costs one configuration word and no memory traffic.  A per-row bound
//      operand needs an S-word fetch phase, a buffer sized to MAX_QUERY_SPAN,
//      and its own fail-closed path, to express masks that no shipped view
//      needs -- every admitted attention in this ABI is causal.
//   3. It is checkable against the bridge's own admission rule.  The bridge
//      already refuses an attention unless the index view resolves position
//      C-1 (``observed_index_value + 1 == cfg_context_length``), and a causal
//      span ends at the end of its KV plane, so ``cfg_first_position + S == C``
//      identically.  This engine RE-DERIVES that and refuses ERR_CONFIG when
//      it does not hold, which turns a bridge that forgets to drive
//      cfg_first_position into a refusal instead of a wrong answer.
//
// Neither the position nor the span is a constant: both are configuration
// inputs, and MAX_QUERY_SPAN is only the compile-time bound their buffers are
// sized from.
//
// The mask itself is the contract's, not a convenience: the pinned finite BF16
// code 0xff7f (the most negative finite BF16) is ADDED to the scaled score of
// a masked position and the sum is rounded back to BF16, exactly as
// CAUSAL_MASK_BF16_CODE is in the oracle.  The subsequent exp of
// (0xff7f - row maximum) is +0.0 -- the shared transcendental engine returns
// zero without error for any argument at or below -150 -- so a masked position
// contributes an exact zero to the eight-lane denominator, to its probability,
// and to the value reduction.  Nothing downstream of the score needs a mask
// case, and the eight-lane reduction still runs over the full C-length row, so
// a row with fewer than eight visible positions never reaches the sequential
// short-row association this datapath refuses to implement.
//
// The row maximum is taken over the VISIBLE positions only.  That is not an
// approximation of the oracle's maximum over all masked codes, it equals it: a
// masked code is 0xff7f whether the mask addition rounds exactly (it does,
// whenever |scaled| is below 2**119) or saturates (the BF16 saturating clamp
// of a negative overflow is 0xff7f as well), and 0xff7f is the minimum finite
// BF16, so it can never be the maximum unless every visible code is also
// 0xff7f -- in which case the maximum is 0xff7f either way.  Position 0 is
// visible for every row, so the row maximum always has at least one visible
// candidate to initialise from.
//
// ---------------------------------------------------------------------------
// THE S=1 EQUIVALENCE (decode is heavily evidenced; it must not move)
// ---------------------------------------------------------------------------
// With MAX_QUERY_SPAN at its default 1 -- every elaboration that exists today
// -- the span dimension is ELABORATED AWAY, not merely idle.  Four predicates
// are written against the bound so that they are elaboration constants there:
//   * span_request folds to 1 and first_position_request to C-1, so neither
//     cfg_query_span nor cfg_first_position is read and an unconnected port
//     cannot reach the datapath,
//   * span_tail_aligned folds to 1 (C-1 + 1 == C for every 32-bit C), so the
//     admission rule gains no new refusal and no new adder,
//   * context_masked folds to 0, so the maximum register's enable is the
//     pre-span expression with no added gate, and nothing branches to S_MASK,
//   * S_MASK's body folds to a refusal, so the mask adder loses its reader and
//     is not synthesised at all.
// The row base registers therefore never advance and the query address, the
// output buffer index and the publish bound are the pre-span expressions.
// Measured, not asserted: at the default parameters the yosys longest
// topological path is 1243 cells before and after, and the whole cell delta is
// three registers, four adders and 26 muxes -- the row and publish counters.
// A deployment that raises MAX_QUERY_SPAN must drive both new inputs; one that
// raises it and leaves them undriven gets ERR_CONFIG, because config_ok is
// tested in the positive sense and an unknown span fails it.
//
// ---------------------------------------------------------------------------
// PIPELINE STRUCTURE: STAGES AND INITIATION INTERVAL
// ---------------------------------------------------------------------------
// This engine is a registered elementwise datapath, not a vector pipeline, and
// the span dimension does not change that.  Stated exactly:
//   * Score phase: one registered stage per operand word -- multiply, one
//     binary32 add into dot_accumulator_q, one rounding.  Arithmetic II = 1
//     word/cycle; the achieved rate is one word per two cycles because the
//     memory protocol is one-outstanding request/response (S_KEY_REQ,
//     S_KEY_RSP), which is the interface's limit and not the datapath's.
//   * Causal mask: ONE registered stage (S_MASK), entered only for a masked
//     position.  Its combinational depth is one binary32 add plus one BF16
//     rounding, and it appends NOTHING to the score path's existing
//     add -> round -> scale -> round chain, which is the module's critical
//     path.  Putting the mask addition into that chain instead would have cost
//     frequency on every launch, including decode.  It costs one cycle per
//     masked position and none per visible one: at the reduced geometry a
//     16-row whole-context prefill measures 212,286 cycles against 17,178 for
//     one decode row, 12.4x for 16x the rows.
//   * Softmax denominator: a registered 3-stage 8 -> 4 -> 2 -> 1 tree
//     (S_REDUCE_HALF, S_REDUCE_QUARTER, S_REDUCE_DENOM).  No serial chain.
//   * Value phase: one registered stage per operand word, II as the score
//     phase.  Exponential and reciprocal are separate registered engines.
//   * The row dimension adds NO combinational depth and NO multiplier: the
//     query base, the output buffer base and the row's visible bound are
//     registered accumulators advanced once per row, so the fetch address
//     stays base + head*HEAD_WIDTH + dimension exactly as before.
// No combinational path walks a vector; the longest new path is one add and
// one rounding between registers.
//
// ---------------------------------------------------------------------------
// WHAT THE BRIDGE MUST PASS FOR A SPAN OF S (ot_a3_engine_issue_bridge)
// ---------------------------------------------------------------------------
//   cfg_query_span      = S, the sequencer's resolved extent on the query
//                         view's sequence axis (1 for decode).
//   cfg_first_position  = C - S, equivalently observed_index_value + 1 - S.
//                         The bridge's index view resolves the LAST row's
//                         position, C-1; the first row's is C-S.
//   GQA_MAX_QUERY_SPAN  >= S at elaboration (new parameter to forward here).
//   query view extent   = S on axis 0, where the admission rule now requires 1.
//   Query operand layout is [S][QUERY_HEADS][HEAD_WIDTH] row-major, so the row
//   stride is QUERY_HEADS*HEAD_WIDTH; the output is [S][QUERY_HEADS][HEAD_WIDTH]
//   row-major and therefore still one contiguous run from cfg_output_base.
// The counts the bridge self-checks against scale by S exactly, because the
// mask is additive and the work stays rectangular (the oracle's accounting is
// rectangular too -- it evaluates an exponential for every one of the
// S*C*QUERY_HEADS scores):
//   mapped_work_words   (score_multiply_count) = S * C * QUERY_HEADS * HEAD_WIDTH
//   mapped_result_words (output_write_count)   = S * QUERY_HEADS * HEAD_WIDTH
//   memory_read_count   = S * QUERY_HEADS * HEAD_WIDTH * (1 + 2*C)
//   exponential_count   = S * QUERY_HEADS * C
//   value_multiply_count = S * C * QUERY_HEADS * HEAD_WIDTH
// At S=1 every one of these is the expression the bridge already derives.
//
// Memory is one-outstanding-request ready/valid.  Every BF16 operand is checked
// before use.  No external output becomes visible until the complete
// S*QUERY_HEADS*HEAD_WIDTH-word result is buffered, so a late memory or numeric
// fault produces zero writes; that all-or-nothing guarantee is why the output
// buffer is sized by MAX_QUERY_SPAN rather than streamed per row.
// Output valid/address/data remain stable under backpressure.
// ---------------------------------------------------------------------------
module ot_a3_qwen_gqa #(
    // The largest context this instance's buffers hold.  The reference caps a
    // Qwen KV cache at runtime.reference.tensor_accelerator_attention.
    // MAX_CONTEXT_TOKENS = 8192; a verification instance sizes itself to the
    // contexts its campaign actually issues.
    parameter integer MAX_CONTEXT = 32,

    // The largest query span this instance's output buffer holds.  1 is decode
    // and is what every existing elaboration wants, so it is the default and
    // the pre-span behaviour is untouched.  The cost of raising it is
    // MAX_QUERY_SPAN * QUERY_HEADS * HEAD_WIDTH BF16 words of result buffer,
    // which the atomic-write guarantee requires; nothing else scales with it.
    parameter integer MAX_QUERY_SPAN = 1,

    // The attention geometry this instance is elaborated for.  Defaults are
    // Qwen3-8B's, so every existing instantiation is unchanged.
    //
    // Rung G1f measured this engine having "no geometry input": at the reduced
    // regression model's shape it still read a full-model attention row, 32x
    // what the reduced row is.  These make the reduced configuration a
    // different ELABORATION of the same RTL, which is what a small-config
    // nightly regression is, rather than a runtime mode.  Runtime geometry
    // would turn the fixed address strides below into variable multipliers,
    // which is a timing cost on a design whose routed control plane already
    // does not close.
    //
    // SCALE_CODE is part of the geometry and not an independent knob: it is
    // bf16(1 / sqrt(HEAD_WIDTH)) widened to binary32.  0x3db5 is
    // bf16(1/sqrt(128)); the reduced 16-wide head needs bf16(1/sqrt(16)) =
    // 0x3e80, which is 0.25 exactly.  Changing HEAD_WIDTH without changing
    // this would silently compute a different attention.
    parameter integer QUERY_HEADS = 32,
    parameter integer KV_HEADS    = 8,
    parameter integer HEAD_WIDTH  = 128,
    parameter [31:0]  SCALE_CODE  = 32'h3db5_0000
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_context_length,
    // The resolved query span S, and the absolute sequence position of query
    // row 0 (the committed KV length).  Both are ignored when
    // MAX_QUERY_SPAN == 1; see THE S=1 EQUIVALENCE.
    input  wire [31:0] cfg_query_span,
    input  wire [31:0] cfg_first_position,
    input  wire [31:0] cfg_query_base,
    input  wire [31:0] cfg_key_base,
    input  wire [31:0] cfg_value_base,
    input  wire [31:0] cfg_output_base,

    output wire        mem_req_valid,
    input  wire        mem_req_ready,
    output wire [31:0] mem_req_addr,
    input  wire        mem_rsp_valid,
    input  wire [31:0] mem_rsp_data,

    output wire        out_valid,
    input  wire        out_ready,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg         failed,
    output reg  [7:0]  error_code,
    output reg  [31:0] memory_read_count,
    output reg  [31:0] output_write_count,
    output reg  [31:0] score_multiply_count,
    output reg  [31:0] exponential_count,
    output reg  [31:0] value_multiply_count,
    output reg  [31:0] saturation_count
);
    localparam [7:0] ERR_NONE = 8'd0;
    localparam [7:0] ERR_CONFIG = 8'd1;
    localparam [7:0] ERR_INPUT = 8'd2;
    localparam [7:0] ERR_NUMERIC = 8'd3;

    // The eight-lane softmax reduction the contract names is defined for
    // rows of eight or more; below that the reference reduces sequentially.
    localparam integer MIN_CONTEXT = 8;
    localparam integer KV_ROW_WORDS = KV_HEADS * HEAD_WIDTH;
    // One query row's worth of result, and of query operand: the span's row
    // stride on both sides.
    localparam integer OUTPUT_WORDS = QUERY_HEADS * HEAD_WIDTH;
    localparam integer QUERY_ROW_WORDS = QUERY_HEADS * HEAD_WIDTH;
    localparam integer SPAN_OUTPUT_WORDS = MAX_QUERY_SPAN * OUTPUT_WORDS;
    // Query heads per KV head -- the GQA sharing factor.  Derived, because the
    // head index used to be advanced by a hardcoded ">> 2" that is only correct
    // at 32/8.
    localparam integer QUERY_HEADS_PER_KV_HEAD = QUERY_HEADS / KV_HEADS;
    localparam integer KV_SHARE_SHIFT = $clog2(QUERY_HEADS_PER_KV_HEAD);
    localparam [31:0] FP32_ONE = 32'h3f80_0000;
    // CAUSAL_MASK_BF16_CODE in the oracle: the most negative finite BF16, and
    // also the value a negative BF16 overflow saturates to.
    localparam [15:0] CAUSAL_MASK_CODE = 16'hff7f;

    // EVERY index width is $clog2 of the bound it indexes, never a literal.
    // A hand-sized index is how a raised ceiling turns into a terminator that
    // never matches and an engine that hangs instead of refusing.  The (<= 1)
    // guards exist because $clog2(1) is 0 and a zero-width register is not a
    // register.
    localparam integer CTX_W     = (MAX_CONTEXT <= 1) ? 1 : $clog2(MAX_CONTEXT);
    localparam integer CTX_LEN_W = $clog2(MAX_CONTEXT + 1);
    localparam integer DIM_W     = (HEAD_WIDTH <= 1) ? 1 : $clog2(HEAD_WIDTH);
    localparam integer QH_W      = (QUERY_HEADS <= 1) ? 1 : $clog2(QUERY_HEADS);
    localparam integer KVH_W     = (KV_HEADS <= 1) ? 1 : $clog2(KV_HEADS);
    localparam integer ROW_W     = (MAX_QUERY_SPAN <= 1)
                                  ? 1 : $clog2(MAX_QUERY_SPAN);
    localparam integer PUB_W     = (SPAN_OUTPUT_WORDS <= 1)
                                  ? 1 : $clog2(SPAN_OUTPUT_WORDS);

    localparam [5:0] S_IDLE = 6'd0;
    localparam [5:0] S_QUERY_REQ = 6'd1;
    localparam [5:0] S_QUERY_RSP = 6'd2;
    localparam [5:0] S_KEY_REQ = 6'd3;
    localparam [5:0] S_KEY_RSP = 6'd4;
    localparam [5:0] S_EXP_REQ = 6'd5;
    localparam [5:0] S_EXP_RSP = 6'd6;
    localparam [5:0] S_REDUCE_HALF = 6'd7;
    localparam [5:0] S_REDUCE_QUARTER = 6'd8;
    localparam [5:0] S_REDUCE_DENOM = 6'd9;
    localparam [5:0] S_DIV_REQ = 6'd10;
    localparam [5:0] S_DIV_RSP = 6'd11;
    localparam [5:0] S_PROBABILITY = 6'd12;
    localparam [5:0] S_VALUE_REQ = 6'd13;
    localparam [5:0] S_VALUE_RSP = 6'd14;
    localparam [5:0] S_PUBLISH = 6'd15;
    localparam [5:0] S_FINISH = 6'd16;
    // The causal mask's own registered stage, reached only from S_KEY_RSP and
    // only for a masked position.
    localparam [5:0] S_MASK = 6'd17;

    reg [5:0] state;
    reg [31:0] query_row_base_q;
    reg [31:0] key_base_q;
    reg [31:0] value_base_q;
    reg [31:0] output_base_q;
    reg [ROW_W-1:0] query_row_q;
    reg [ROW_W-1:0] span_last_q;
    reg [QH_W-1:0] query_head_q;
    reg [KVH_W-1:0] kv_head_q;
    reg [DIM_W-1:0] dimension_q;
    reg [CTX_W-1:0] context_index_q;
    reg [CTX_LEN_W-1:0] context_length_q;
    // The last context position query row query_row_q may attend to:
    // cfg_first_position + query_row_q, advanced by one per row.
    reg [CTX_W-1:0] row_visible_last_q;
    wire [CTX_LEN_W-1:0] context_minus_one = context_length_q - 1'b1;
    wire [CTX_W-1:0] context_last = context_minus_one[CTX_W-1:0];
    // Is this context position beyond what the current query row may attend
    // to?  One registered comparison, and at a one-row bound the constant 0 --
    // so the maximum register's enable, the branch into S_MASK and the mask
    // arithmetic all fold away and a decode-only instance is the pre-span
    // netlist.
    wire context_masked = (MAX_QUERY_SPAN == 1)
        ? 1'b0
        : (context_index_q > row_visible_last_q);
    // The row and head advances, sliced to their own register widths rather
    // than truncated implicitly.  Each sum is in range by construction: the
    // output row base reaches (span-1)*OUTPUT_WORDS and the KV head reaches
    // (QUERY_HEADS-1)/QUERY_HEADS_PER_KV_HEAD.
    wire [QH_W:0] next_query_head = {1'b0, query_head_q} + 1'b1;
    wire [QH_W:0] next_kv_head = next_query_head >> KV_SHARE_SHIFT;
    reg [PUB_W-1:0] publish_index_q;
    reg [PUB_W-1:0] publish_last_q;
    reg [PUB_W-1:0] output_row_base_q;
    wire [31:0] next_output_row_base = output_row_base_q + OUTPUT_WORDS;

    reg [15:0] query_buffer [0:HEAD_WIDTH-1];
    reg [15:0] score_buffer [0:MAX_CONTEXT-1];
    reg [31:0] exponential_buffer [0:MAX_CONTEXT-1];
    reg [15:0] probability_buffer [0:MAX_CONTEXT-1];
    reg [15:0] output_buffer [0:SPAN_OUTPUT_WORDS-1];
    reg [31:0] softmax_lanes [0:7];
    reg [31:0] softmax_half [0:3];
    reg [31:0] softmax_quarter [0:1];
    reg [31:0] maximum_code_q;
    reg [31:0] dot_accumulator_q;
    reg [31:0] value_accumulator_q;
    reg [31:0] inverse_denominator_q;

    // The span and the base position, folded to their decode values when this
    // instance is elaborated for one row.  The ternary is constant at
    // elaboration, so at MAX_QUERY_SPAN == 1 neither configuration input is
    // read and an unconnected port cannot reach the datapath.
    wire [31:0] span_request = (MAX_QUERY_SPAN == 1) ? 32'd1 : cfg_query_span;
    wire [31:0] first_position_request = (MAX_QUERY_SPAN == 1)
        ? (cfg_context_length - 32'd1) : cfg_first_position;
    wire [31:0] span_last_wide = span_request - 32'd1;
    wire [31:0] publish_last_wide = span_request * OUTPUT_WORDS - 32'd1;
    // A causal span ends at the end of its KV plane, which is the oracle's own
    // invariant (committed length + prepared length == total tokens).  Checking
    // it here is what makes an undriven cfg_first_position a refusal.
    // At a one-row bound this is a tautology -- (C-1) + 1 == C holds for every
    // 32-bit C, including 0 -- so it folds to a constant and the adder and
    // comparator are not elaborated into a decode-only instance.
    wire span_tail_aligned = (MAX_QUERY_SPAN == 1)
        ? 1'b1
        : (first_position_request + span_request == cfg_context_length);
    //: THE TAIL TEST ALONE IS MODULAR, AND THAT IS NOT SAFE.
    //:
    //: ``first_position_request + span_request == cfg_context_length`` is a
    //: 32-bit comparison, so it also holds when a caller computed the first
    //: position as C - S in unsigned arithmetic with S > C: that underflows to
    //: 2**32-(S-C), and 2**32-(S-C) + S == C exactly, modulo 2**32.  The engine
    //: then accepted the launch -- and because row_visible_last_q takes
    //: ``first_position_request[CTX_W-1:0]``, the truncated bound sat ABOVE
    //: every context index, so nothing was masked and the engine retired a full
    //: span of non-causal rows.  Measured before this guard existed, at
    //: MAX_QUERY_SPAN=16 / MIN_CONTEXT=8: context 8 with span 16 and first
    //: position 0xfffffff8 gave err=0 and wrote all 2,048 words.
    //:
    //: The hole needed MAX_QUERY_SPAN > MIN_CONTEXT, so it was unreachable in
    //: every elaboration that exists today and live in exactly the one prefill
    //: needs.  One non-modular comparator closes it: a span can never exceed
    //: the context it is a tail of.
    wire span_within_context = (MAX_QUERY_SPAN == 1)
        ? 1'b1
        : (span_request <= cfg_context_length);
    wire config_ok =
        (cfg_context_length >= MIN_CONTEXT) &&
        (cfg_context_length <= MAX_CONTEXT) &&
        (span_request >= 32'd1) &&
        (span_request <= MAX_QUERY_SPAN) &&
        span_within_context &&
        span_tail_aligned;

    wire request_is_query = state == S_QUERY_REQ;
    wire request_is_key = state == S_KEY_REQ;
    wire request_is_value = state == S_VALUE_REQ;
    assign mem_req_valid = request_is_query || request_is_key ||
        request_is_value;
    assign mem_req_addr = request_is_query
        ? query_row_base_q + query_head_q * HEAD_WIDTH + dimension_q
        : request_is_key
          ? key_base_q + context_index_q * KV_ROW_WORDS +
            kv_head_q * HEAD_WIDTH + dimension_q
          : value_base_q + context_index_q * KV_ROW_WORDS +
            kv_head_q * HEAD_WIDTH + dimension_q;

    assign out_valid = state == S_PUBLISH;
    assign out_addr = output_base_q + publish_index_q;
    assign out_data = {16'd0, output_buffer[publish_index_q]};

    wire response_nonfinite = mem_rsp_data[14:7] == 8'hff;
    wire [31:0] query_fp32 = {query_buffer[dimension_q], 16'd0};
    wire [31:0] response_fp32 = {mem_rsp_data[15:0], 16'd0};

    wire [33:0] score_product = ot_fp32_rne_pkg::fp32_mul_rne(
        query_fp32, response_fp32
    );
    wire [33:0] score_sum = ot_fp32_rne_pkg::fp32_add_rne(
        dot_accumulator_q, score_product[31:0]
    );
    wire [18:0] score_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        score_sum[31:0]
    );
    wire [33:0] scaled_score = ot_fp32_rne_pkg::fp32_mul_rne(
        {score_bf16[15:0], 16'd0}, SCALE_CODE
    );
    wire [18:0] scaled_score_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        scaled_score[31:0]
    );

    // The causal mask addition, in its own stage so that it is not on the
    // score chain above.  Its operand is the scaled score this row's key phase
    // has already registered into score_buffer.
    wire [33:0] masked_score = ot_fp32_rne_pkg::fp32_add_rne(
        {score_buffer[context_index_q], 16'd0}, {CAUSAL_MASK_CODE, 16'd0}
    );
    wire [18:0] masked_score_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        masked_score[31:0]
    );

    function automatic fp32_greater;
        input [31:0] left;
        input [31:0] right;
        begin
            if ((left[30:0] == 0) && (right[30:0] == 0))
                fp32_greater = 1'b0;
            else if (left[31] != right[31])
                fp32_greater = right[31];
            else if (!left[31])
                fp32_greater = left[30:0] > right[30:0];
            else
                fp32_greater = left[30:0] < right[30:0];
        end
    endfunction

    function automatic [31:0] negate_fp32;
        input [31:0] value;
        begin
            negate_fp32 = value[30:0] == 0 ? 32'd0 :
                {~value[31], value[30:0]};
        end
    endfunction

    wire [33:0] shifted_score = ot_fp32_rne_pkg::fp32_add_rne(
        {score_buffer[context_index_q], 16'd0}, negate_fp32(maximum_code_q)
    );

    wire exp_in_ready;
    wire exp_out_valid;
    wire [31:0] exp_result;
    wire [1:0] exp_error;
    ot_a3_fp32_transcendental_cr_rne exponential (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_EXP_REQ), .in_ready(exp_in_ready),
        .operation(1'b0), .argument_code(shifted_score[31:0]),
        .out_valid(exp_out_valid), .out_ready(state == S_EXP_RSP),
        .result_code(exp_result), .result_error(exp_error)
    );

    wire [33:0] lane_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[context_index_q[2:0]], exp_result
    );
    wire [33:0] half_add_0 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[0], softmax_lanes[4]
    );
    wire [33:0] half_add_1 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[1], softmax_lanes[5]
    );
    wire [33:0] half_add_2 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[2], softmax_lanes[6]
    );
    wire [33:0] half_add_3 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_lanes[3], softmax_lanes[7]
    );
    wire [33:0] quarter_add_0 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_half[0], softmax_half[2]
    );
    wire [33:0] quarter_add_1 = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_half[1], softmax_half[3]
    );
    wire [33:0] denominator_add = ot_fp32_rne_pkg::fp32_add_positive_rne(
        softmax_quarter[0], softmax_quarter[1]
    );

    wire divider_in_ready;
    wire divider_out_valid;
    wire [31:0] divider_result;
    wire [1:0] divider_error;
    ot_a3_fp32_div_rne divider (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_DIV_REQ), .in_ready(divider_in_ready),
        .numerator_code(FP32_ONE),
        .denominator_code(denominator_add[31:0]),
        .out_valid(divider_out_valid), .out_ready(state == S_DIV_RSP),
        .result_code(divider_result), .result_error(divider_error)
    );

    wire [33:0] probability_product = ot_fp32_rne_pkg::fp32_mul_rne(
        exponential_buffer[context_index_q], inverse_denominator_q
    );
    wire [18:0] probability_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        probability_product[31:0]
    );
    wire [33:0] value_product = ot_fp32_rne_pkg::fp32_mul_rne(
        {probability_buffer[context_index_q], 16'd0}, response_fp32
    );
    wire [33:0] value_sum = ot_fp32_rne_pkg::fp32_add_rne(
        value_accumulator_q, value_product[31:0]
    );
    wire [18:0] output_bf16 = ot_fp32_rne_pkg::fp32_to_bf16_rne(
        value_sum[31:0]
    );

    task automatic fail_numeric;
        begin
            failed <= 1'b1;
            error_code <= ERR_NUMERIC;
            state <= S_FINISH;
        end
    endtask

    // Advance to the next context position of this row and head, or to the
    // softmax once the whole C-length row of scores exists.  Shared by
    // S_KEY_RSP and the mask stage so the two cannot drift apart.
    task automatic advance_context;
        begin
            if (context_index_q == context_last) begin
                context_index_q <= 0;
                state <= S_EXP_REQ;
            end else begin
                context_index_q <= context_index_q + 1'b1;
                state <= S_KEY_REQ;
            end
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            query_row_base_q <= 0;
            key_base_q <= 0;
            value_base_q <= 0;
            output_base_q <= 0;
            query_row_q <= 0;
            span_last_q <= 0;
            query_head_q <= 0;
            kv_head_q <= 0;
            dimension_q <= 0;
            context_index_q <= 0;
            context_length_q <= 0;
            row_visible_last_q <= 0;
            publish_index_q <= 0;
            publish_last_q <= 0;
            output_row_base_q <= 0;
            maximum_code_q <= 0;
            dot_accumulator_q <= 0;
            value_accumulator_q <= 0;
            inverse_denominator_q <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            failed <= 1'b0;
            error_code <= ERR_NONE;
            memory_read_count <= 0;
            output_write_count <= 0;
            score_multiply_count <= 0;
            exponential_count <= 0;
            value_multiply_count <= 0;
            saturation_count <= 0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        query_row_base_q <= cfg_query_base;
                        key_base_q <= cfg_key_base;
                        value_base_q <= cfg_value_base;
                        output_base_q <= cfg_output_base;
                        query_row_q <= 0;
                        query_head_q <= 0;
                        kv_head_q <= 0;
                        dimension_q <= 0;
                        context_index_q <= 0;
                        publish_index_q <= 0;
                        output_row_base_q <= 0;
                        maximum_code_q <= 0;
                        dot_accumulator_q <= 0;
                        value_accumulator_q <= 0;
                        inverse_denominator_q <= 0;
                        busy <= 1'b1;
                        failed <= 1'b0;
                        error_code <= ERR_NONE;
                        memory_read_count <= 0;
                        output_write_count <= 0;
                        score_multiply_count <= 0;
                        exponential_count <= 0;
                        value_multiply_count <= 0;
                        saturation_count <= 0;
                        context_length_q <= cfg_context_length[CTX_LEN_W-1:0];
                        span_last_q <= span_last_wide[ROW_W-1:0];
                        publish_last_q <= publish_last_wide[PUB_W-1:0];
                        row_visible_last_q <=
                            first_position_request[CTX_W-1:0];
                        // Tested in the POSITIVE sense deliberately: an
                        // unknown configuration makes config_ok unknown, and
                        // `if (config_ok)` refuses it where `if (!config_ok)`
                        // would have started arithmetic on it.  That is the
                        // difference between a raised MAX_QUERY_SPAN whose
                        // span pin nobody drove refusing and running.
                        if (config_ok) begin
                            state <= S_QUERY_REQ;
                        end else begin
                            failed <= 1'b1;
                            error_code <= ERR_CONFIG;
                            state <= S_FINISH;
                        end
                    end
                end

                S_QUERY_REQ: begin
                    if (mem_req_ready)
                        state <= S_QUERY_RSP;
                end

                S_QUERY_RSP: begin
                    if (mem_rsp_valid) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        if (response_nonfinite) begin
                            failed <= 1'b1;
                            error_code <= ERR_INPUT;
                            state <= S_FINISH;
                        end else begin
                            query_buffer[dimension_q] <= mem_rsp_data[15:0];
                            if (dimension_q == HEAD_WIDTH-1) begin
                                dimension_q <= 0;
                                context_index_q <= 0;
                                dot_accumulator_q <= 0;
                                state <= S_KEY_REQ;
                            end else begin
                                dimension_q <= dimension_q + 1'b1;
                                state <= S_QUERY_REQ;
                            end
                        end
                    end
                end

                S_KEY_REQ: begin
                    if (mem_req_ready)
                        state <= S_KEY_RSP;
                end

                S_KEY_RSP: begin
                    if (mem_rsp_valid) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        score_multiply_count <= score_multiply_count + 1'b1;
                        if (response_nonfinite ||
                            score_product[33:32] != 0 ||
                            score_sum[33:32] != 0) begin
                            failed <= 1'b1;
                            error_code <= response_nonfinite
                                ? ERR_INPUT : ERR_NUMERIC;
                            state <= S_FINISH;
                        end else if (dimension_q == HEAD_WIDTH-1) begin
                            if (score_bf16[18:17] != 0 ||
                                scaled_score[33:32] != 0 ||
                                scaled_score_bf16[18:17] != 0) begin
                                fail_numeric();
                            end else begin
                                score_buffer[context_index_q] <=
                                    scaled_score_bf16[15:0];
                                saturation_count <= saturation_count +
                                    score_bf16[16] + scaled_score_bf16[16];
                                // The row maximum is over visible positions.
                                // Position 0 is visible for every row, so the
                                // initialising case needs no mask term.
                                if (!context_masked &&
                                    ((context_index_q == 0) ||
                                     fp32_greater(
                                        {scaled_score_bf16[15:0], 16'd0},
                                        maximum_code_q
                                     )))
                                    maximum_code_q <= {
                                        scaled_score_bf16[15:0], 16'd0
                                    };
                                dimension_q <= 0;
                                dot_accumulator_q <= 0;
                                if (context_masked)
                                    state <= S_MASK;
                                else
                                    advance_context();
                            end
                        end else begin
                            dot_accumulator_q <= score_sum[31:0];
                            dimension_q <= dimension_q + 1'b1;
                            state <= S_KEY_REQ;
                        end
                    end
                end

                // One registered stage, entered only for a position this row
                // may not attend to: add the contract's finite mask code to
                // the scaled score and round once, exactly as the oracle does.
                // The exponential of the result minus the row maximum is
                // +0.0, so every later phase needs no mask case.
                S_MASK: begin
                    if (MAX_QUERY_SPAN == 1) begin
                        // A one-row bound has no masked position, so this state
                        // is unreachable and this constant branch is the only
                        // one elaborated: the mask adder loses its reader and
                        // is not synthesised into a decode-only instance at
                        // all.  Refusing rather than computing keeps the
                        // impossible case fail-closed.
                        failed <= 1'b1;
                        error_code <= ERR_CONFIG;
                        state <= S_FINISH;
                    end else if (masked_score[33:32] != 0 ||
                        masked_score_bf16[18:17] != 0) begin
                        fail_numeric();
                    end else begin
                        score_buffer[context_index_q] <=
                            masked_score_bf16[15:0];
                        saturation_count <= saturation_count +
                            masked_score_bf16[16];
                        advance_context();
                    end
                end

                S_EXP_REQ: begin
                    if (shifted_score[33:32] != 0) begin
                        fail_numeric();
                    end else if (exp_in_ready) begin
                        state <= S_EXP_RSP;
                    end
                end

                S_EXP_RSP: begin
                    if (exp_out_valid) begin
                        if (exp_error != 0) begin
                            fail_numeric();
                        end else begin
                            exponential_count <= exponential_count + 1'b1;
                            exponential_buffer[context_index_q] <= exp_result;
                            if (context_index_q < 8) begin
                                softmax_lanes[context_index_q[2:0]] <=
                                    exp_result;
                            end else if (lane_add[33:32] != 0) begin
                                fail_numeric();
                            end else begin
                                softmax_lanes[context_index_q[2:0]] <=
                                    lane_add[31:0];
                            end
                            if (exp_error == 0 &&
                                (context_index_q < 8 ||
                                 lane_add[33:32] == 0)) begin
                                if (context_index_q == context_last) begin
                                    state <= S_REDUCE_HALF;
                                end else begin
                                    context_index_q <=
                                        context_index_q + 1'b1;
                                    state <= S_EXP_REQ;
                                end
                            end
                        end
                    end
                end

                S_REDUCE_HALF: begin
                    if ((half_add_0[33:32] != 0) ||
                        (half_add_1[33:32] != 0) ||
                        (half_add_2[33:32] != 0) ||
                        (half_add_3[33:32] != 0)) begin
                        fail_numeric();
                    end else begin
                        softmax_half[0] <= half_add_0[31:0];
                        softmax_half[1] <= half_add_1[31:0];
                        softmax_half[2] <= half_add_2[31:0];
                        softmax_half[3] <= half_add_3[31:0];
                        state <= S_REDUCE_QUARTER;
                    end
                end

                S_REDUCE_QUARTER: begin
                    if ((quarter_add_0[33:32] != 0) ||
                        (quarter_add_1[33:32] != 0)) begin
                        fail_numeric();
                    end else begin
                        softmax_quarter[0] <= quarter_add_0[31:0];
                        softmax_quarter[1] <= quarter_add_1[31:0];
                        state <= S_REDUCE_DENOM;
                    end
                end

                S_REDUCE_DENOM: begin
                    if (denominator_add[33:32] != 0 ||
                        denominator_add[30:0] == 0) begin
                        fail_numeric();
                    end else begin
                        state <= S_DIV_REQ;
                    end
                end

                S_DIV_REQ: begin
                    if (divider_in_ready)
                        state <= S_DIV_RSP;
                end

                S_DIV_RSP: begin
                    if (divider_out_valid) begin
                        if (divider_error != 0) begin
                            fail_numeric();
                        end else begin
                            inverse_denominator_q <= divider_result;
                            context_index_q <= 0;
                            state <= S_PROBABILITY;
                        end
                    end
                end

                S_PROBABILITY: begin
                    if (probability_product[33:32] != 0 ||
                        probability_bf16[18:17] != 0) begin
                        fail_numeric();
                    end else begin
                        probability_buffer[context_index_q] <=
                            probability_bf16[15:0];
                        saturation_count <= saturation_count +
                            probability_bf16[16];
                        if (context_index_q == context_last) begin
                            context_index_q <= 0;
                            dimension_q <= 0;
                            value_accumulator_q <= 0;
                            state <= S_VALUE_REQ;
                        end else begin
                            context_index_q <= context_index_q + 1'b1;
                        end
                    end
                end

                S_VALUE_REQ: begin
                    if (mem_req_ready)
                        state <= S_VALUE_RSP;
                end

                S_VALUE_RSP: begin
                    if (mem_rsp_valid) begin
                        memory_read_count <= memory_read_count + 1'b1;
                        value_multiply_count <= value_multiply_count + 1'b1;
                        if (response_nonfinite ||
                            value_product[33:32] != 0 ||
                            value_sum[33:32] != 0) begin
                            failed <= 1'b1;
                            error_code <= response_nonfinite
                                ? ERR_INPUT : ERR_NUMERIC;
                            state <= S_FINISH;
                        end else if (context_index_q == context_last) begin
                            if (output_bf16[18:17] != 0) begin
                                fail_numeric();
                            end else begin
                                output_buffer[
                                    output_row_base_q +
                                    query_head_q * HEAD_WIDTH + dimension_q
                                ] <= output_bf16[15:0];
                                saturation_count <= saturation_count +
                                    output_bf16[16];
                                context_index_q <= 0;
                                value_accumulator_q <= 0;
                                if (dimension_q == HEAD_WIDTH-1) begin
                                    dimension_q <= 0;
                                    if (query_head_q == QUERY_HEADS-1) begin
                                        if (query_row_q == span_last_q) begin
                                            publish_index_q <= 0;
                                            state <= S_PUBLISH;
                                        end else begin
                                            // Next query row: one registered
                                            // increment per base, so no
                                            // multiplier reaches the address
                                            // or buffer index path.
                                            query_row_q <= query_row_q + 1'b1;
                                            query_head_q <= 0;
                                            kv_head_q <= 0;
                                            query_row_base_q <=
                                                query_row_base_q +
                                                QUERY_ROW_WORDS;
                                            output_row_base_q <=
                                                next_output_row_base[
                                                    PUB_W-1:0];
                                            row_visible_last_q <=
                                                row_visible_last_q + 1'b1;
                                            state <= S_QUERY_REQ;
                                        end
                                    end else begin
                                        query_head_q <=
                                            next_query_head[QH_W-1:0];
                                        kv_head_q <=
                                            next_kv_head[KVH_W-1:0];
                                        state <= S_QUERY_REQ;
                                    end
                                end else begin
                                    dimension_q <= dimension_q + 1'b1;
                                    state <= S_VALUE_REQ;
                                end
                            end
                        end else begin
                            value_accumulator_q <= value_sum[31:0];
                            context_index_q <= context_index_q + 1'b1;
                            state <= S_VALUE_REQ;
                        end
                    end
                end

                S_PUBLISH: begin
                    if (out_ready) begin
                        output_write_count <= output_write_count + 1'b1;
                        if (publish_index_q == publish_last_q)
                            state <= S_FINISH;
                        else
                            publish_index_q <= publish_index_q + 1'b1;
                    end
                end

                S_FINISH: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    failed <= 1'b1;
                    error_code <= ERR_CONFIG;
                    state <= S_FINISH;
                end
            endcase
        end
    end
endmodule
