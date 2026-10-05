`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ATTENTION.SPARSE's online softmax, one source block at a time.
//
// Given a block of LANES scores for one (query row, head), a per-lane validity
// mask, and the running maximum carried from the blocks before it, this produces
// the three things the rest of the operator needs:
//
//     updated maximum    max(running, max over the block's VALID lanes)
//     rescale            exp(running - updated), the factor the accumulator and
//                        the denominator must both be multiplied by
//     probabilities      exp(score - updated) per valid lane, +0 per invalid one
//
// transcribed from the reference's own six lines
// (runtime/tensor_accelerator/sparse_attention.py::_execute_tile):
//
//     masked  = where(lane_valid, scores, -inf); block_max = masked.max(axis=2)
//     updated = maximum(maxima, block_max); updated = where(updated==0, +0, updated)
//     rescale = exp_cr32(maxima - updated)
//     offsets = where(lane_valid, scores - updated, -inf)
//     probabilities = exp_cr32(offsets)
//
// FOUR THINGS THE REFERENCE DOES THAT ARE EASY TO DROP, and each is a defect if
// dropped:
//
//   * THE FIRST BLOCK'S RESCALE IS ZERO, NOT ONE.  The reference sets it to
//     binary32 +0 for block 0 and the denominator then computes
//     ``sums * rescale + block_sum`` from a zero ``sums`` -- so 0 * 0 + s is
//     right and 1 would be too, but only because sums is zero. cfg_first makes
//     the intent explicit rather than relying on that.
//   * A ZERO MAXIMUM IS CANONICALISED to +0. -0 and +0 compare equal, so a block
//     whose maximum is -0 would otherwise carry a sign into every offset.
//   * AN INVALID LANE'S PROBABILITY IS +0 AND NEVER REACHES THE EXPONENTIAL.
//     The reference's offset for such a lane is -inf and exp_cr32(-inf) is 0,
//     but ot_a3_fp32_transcendental_cr_rne admits FINITE x <= 0 only and REFUSES
//     a nonfinite argument with ERR_ARGUMENT. Feeding it the masked offset would
//     fail the whole block closed on a padding lane. +0 is also exactly what
//     ot_a3_reduction_balanced_sum needs its pad to be.
//   * EVERY OFFSET IS NON-POSITIVE BY CONSTRUCTION, which is what makes
//     OP_EXP_NONPOS the right primitive: the updated maximum is >= every valid
//     score and >= the running maximum, so both ``score - updated`` and
//     ``running - updated`` are <= 0. A score equal to the maximum gives exactly
//     0 and exp(0) = 1, which is in the unit's domain.
//
// SUBTRACTION IS THE PIPELINED ADDER WITH ONE SIGN BIT FLIPPED.  a - b is
// a + (-b) and ot_fp32_add_rne_pipe is bit-identical to the scalar authority, so
// no second unit is needed. Flipping the sign of a NaN or infinity would be
// wrong, and cannot arise: the caller's scores are finite or the block is
// refused before this point.
//
// THE EXPONENTIAL IS THE THROUGHPUT COST AND IT IS NOT PIPELINED.
// ot_a3_fp32_transcendental_cr_rne certifies each result by enclosing it in an
// interval and refusing when the interval is too wide, and it accepts one
// argument at a time. A block therefore costs LANES + 1 sequential exponentials,
// and that is the honest cost of a correctly-rounded softmax rather than an
// approximated one. Exact last-result reuse avoids repeated service for
// identical lane offsets; it does not approximate or reorder evaluations.
// ---------------------------------------------------------------------------
module ot_a3_attention_softmax_block #(
    //: The frozen sparse-attention source block is 64.
    parameter integer LANES = 64,
    parameter bit EXP_REUSE = 1
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    //: 1 for the first source block of a (row, head), where there is no running
    //: maximum to rescale against.
    input  wire        cfg_first,
    input  wire [31:0] cfg_running_max,
    input  wire [LANES-1:0]    lane_valid,
    input  wire [LANES*32-1:0] scores,

    output reg         busy,
    output reg         done,
    output reg  [31:0] updated_max,
    output reg  [31:0] rescale,
    output reg  [LANES*32-1:0] probabilities,
    output reg  [7:0]  error_code,
    output reg  [31:0] exp_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] ERR_SELECT_NONFINITE = ot_a3_engine_pkg::ERR_SELECT_NONFINITE;

    localparam OP_EXP_NONPOS = 1'b0;

    integer i;

    localparam [3:0] S_IDLE   = 4'd0;
    localparam [3:0] S_MAX    = 4'd1;
    localparam [3:0] S_SUBMAX = 4'd2;
    localparam [3:0] S_RESC_S = 4'd3;
    localparam [3:0] S_RESC_W = 4'd4;
    localparam [3:0] S_OFF_S  = 4'd5;
    localparam [3:0] S_OFF_W  = 4'd6;
    localparam [3:0] S_EXP_S  = 4'd7;
    localparam [3:0] S_EXP_W  = 4'd8;
    localparam [3:0] S_DONE   = 4'd9;
    reg [3:0] state;

    localparam integer LW = (LANES <= 1) ? 1 : $clog2(LANES);
    localparam integer LCW = (LANES <= 1) ? 1 : $clog2(LANES + 1);
    reg [LCW-1:0] lane;
    //: THE SUBTRACT'S OWN HANDSHAKE.  Keying the issue off ``sub_valid_in``
    //: instead LIVELOCKS: that register is high for exactly one cycle and the
    //: result is five away, so the issue re-fires every second cycle and the
    //: result always lands on a cycle where the re-issue branch is taken --
    //: forever. This is the same defect ot_a3_route_weight_normalize's fold had,
    //: reintroduced here, which is why it now gets an explicit flag both times.
    reg        sub_pending;
    //: Narrowed once, where the cursor is already bounded by the guard above.
    wire [LW-1:0] lane_sel = lane[LW-1:0];
    reg [31:0] offset_q;
    reg [31:0] block_max;
    reg        any_valid;

    //: Finite binary32 compares as an unsigned integer under this map, and EVERY
    //: ZERO MAPS TO ONE POINT because -0 == +0 -- the same rule
    //: ot_a3_route_biased_topk needs, and for the same reason.
    //:
    //: HERE IT IS DEFENSIVE AND UNREACHABLE, which is recorded rather than
    //: claimed as covered: a mutant that drops the zero collapse passes every
    //: case. The canonicalisation below forces any zero maximum to +0, so
    //: whichever zero the map happens to rank higher, this block's output is the
    //: same -- checked over both zeros against a positive, a negative and a zero
    //: running maximum. It stays because ot_a3_route_biased_topk's copy of this
    //: function IS observable there, and two spellings of one rule invite a
    //: divergence.
    function automatic [31:0] monotonic;
        input [31:0] code;
        begin
            monotonic = (code[30:0] == 31'd0)
                        ? 32'h8000_0000
                        : (code[31] ? ~code : (code | 32'h8000_0000));
        end
    endfunction

    //: The block's maximum over its VALID lanes, as a BALANCED TREE.
    //:
    //: It used to be a fold -- one loop carrying ``max_scan`` across its
    //: iterations -- and a carried accumulator is a CHAIN, not a tree: at
    //: LANES = 64 that is sixty-four 32-bit compare-and-select stages in series.
    //: The routed record said so exactly: worst path scores[47] to block_max[30]
    //: through 2,610 cells, WNS -31.83 ns at a 3.4 ns target, and the block came
    //: back at 28.4 MHz over 137,537 cells. The old comment here guessed that
    //: "the comparison is not what sets this block's throughput"; it was.
    //:
    //: The tree is log2(LANES) = 6 levels and is BIT-IDENTICAL, not merely
    //: equivalent. The fold replaced only on STRICTLY greater while walking
    //: ascending, so it kept the LOWEST-INDEX maximal lane; each tree node below
    //: keeps its left child on a tie, and the left child is always the lower
    //: index, so the tree keeps the lowest-index maximal lane too. That holds
    //: without appealing to the zero canonicalisation further down -- which
    //: matters, because ``monotonic`` is injective EXCEPT that +0 and -0 both map
    //: to 32'h8000_0000, and a tie between those two is the one case where
    //: "which maximal lane" would otherwise be observable.
    //:
    //: Lanes beyond LANES are padded unseen, so a non-power-of-two LANES needs no
    //: special case: an unseen node contributes nothing at every level.
    localparam integer TREE_LEVELS = LW;
    localparam integer TREE_WIDTH = 1 << LW;
    reg [31:0] tree_value [0:TREE_LEVELS][0:TREE_WIDTH-1];
    reg        tree_seen  [0:TREE_LEVELS][0:TREE_WIDTH-1];
    integer tree_level;
    integer tree_node;
    reg [31:0] max_scan;
    reg        max_seen;
    always @* begin
        for (tree_node = 0; tree_node < TREE_WIDTH; tree_node = tree_node + 1) begin
            tree_value[0][tree_node] =
                (tree_node < LANES) ? monotonic(scores[tree_node*32 +: 32]) : 32'd0;
            tree_seen[0][tree_node] =
                (tree_node < LANES) ? lane_valid[tree_node] : 1'b0;
        end
        for (tree_level = 0; tree_level < TREE_LEVELS;
             tree_level = tree_level + 1) begin
            for (tree_node = 0;
                 tree_node < (TREE_WIDTH >> (tree_level + 1));
                 tree_node = tree_node + 1) begin
                if (!tree_seen[tree_level][2*tree_node]) begin
                    tree_value[tree_level+1][tree_node] =
                        tree_value[tree_level][2*tree_node+1];
                    tree_seen[tree_level+1][tree_node] =
                        tree_seen[tree_level][2*tree_node+1];
                end else if (!tree_seen[tree_level][2*tree_node+1]) begin
                    tree_value[tree_level+1][tree_node] =
                        tree_value[tree_level][2*tree_node];
                    tree_seen[tree_level+1][tree_node] = 1'b1;
                end else begin
                    //: strictly greater, so a tie keeps the LEFT child
                    tree_value[tree_level+1][tree_node] =
                        (tree_value[tree_level][2*tree_node+1] >
                         tree_value[tree_level][2*tree_node])
                        ? tree_value[tree_level][2*tree_node+1]
                        : tree_value[tree_level][2*tree_node];
                    tree_seen[tree_level+1][tree_node] = 1'b1;
                end
            end
        end
        // Keys stay ordered through the tree; decode only the winning key.
        // Both input zeros map to the +0 result required by canonicalization.
        max_scan = tree_value[TREE_LEVELS][0][31]
            ? (tree_value[TREE_LEVELS][0] & 32'h7fff_ffff)
            : ~tree_value[TREE_LEVELS][0];
        max_seen = tree_seen[TREE_LEVELS][0];
    end
    //: Any nonfinite score is refused before it can poison a maximum.
    //: A lane's exponent field goes through a named reg. Indexing a part-select
    //: is the construct Verilator accepts and Icarus 11 rejects, and it has cost
    //: this session four separate compile failures -- three of them found only
    //: after a campaign had run for an hour.
    reg score_nonfinite;
    reg [31:0] scan_code;
    always @* begin
        score_nonfinite = 1'b0;
        for (i = 0; i < LANES; i = i + 1) begin
            scan_code = scores[i*32 +: 32];
            if (lane_valid[i] && (scan_code[30:23] == 8'hff))
                score_nonfinite = 1'b1;
        end
    end

    //: ``updated = maximum(running, block_max)``, then the zero canonicalisation.
    wire [31:0] merged =
        cfg_first ? block_max
                  : ((monotonic(block_max) > monotonic(cfg_running_max))
                     ? block_max : cfg_running_max);
    wire [31:0] canonical = (merged[30:0] == 31'd0) ? 32'd0 : merged;

    // -- one subtractor, shared by the rescale and every offset --------------
    reg         sub_valid_in;
    reg  [31:0] sub_a, sub_b;
    wire [31:0] sub_y;
    wire [1:0]  sub_err;
    wire        sub_valid_out;
    ot_fp32_add_rne_pipe subtract (
        .clk(clk), .rst_n(rst_n), .valid_in(sub_valid_in),
        .a(sub_a), .b({~sub_b[31], sub_b[30:0]}),
        .y(sub_y), .err(sub_err), .valid_out(sub_valid_out)
    );

    // One exact last-result entry. The operation and arithmetic configuration
    // are immutable; a bit-identical argument can reuse a certified result
    // across lanes/blocks. Errors never install entries. Only validity resets.
    reg exp_cache_valid;
    reg [31:0] exp_cache_argument, exp_cache_result;
    wire exp_cache_hit = EXP_REUSE && exp_cache_valid && offset_q == exp_cache_argument;
    always @(posedge clk) begin
        if (exp_out_valid && exp_error == 0 &&
            (state == S_RESC_W || state == S_EXP_W)) begin
            exp_cache_argument <= exp_argument;
            exp_cache_result <= exp_result;
        end
    end

    // -- one certifying exponential, shared by all of them -------------------
    reg         exp_in_valid;
    reg  [31:0] exp_argument;
    wire        exp_in_ready;
    wire        exp_out_valid;
    wire [31:0] exp_result;
    wire [1:0]  exp_error;
    ot_a3_fp32_transcendental_cr_rne #(.ENABLE_SIGMOID(0)) exponential (
        .clk(clk), .rst_n(rst_n),
        .in_valid(exp_in_valid), .in_ready(exp_in_ready),
        .operation(OP_EXP_NONPOS), .argument_code(exp_argument),
        .out_valid(exp_out_valid), .out_ready(state == S_RESC_W || state == S_EXP_W),
        .result_code(exp_result), .result_error(exp_error)
    );

    // A single 32-bit result bus feeds locally decoded lane enables. Avoid
    // lowering variable part-select writes into a full-width shift/mask mux.
    // Start clears every lane, so skipped padding already contains exact +0.
    wire probability_write = (state == S_OFF_W && exp_cache_hit) ||
        (state == S_EXP_W && exp_out_valid && exp_error == 0);
    wire [31:0] probability_value = state == S_OFF_W ? exp_cache_result : exp_result;
    genvar probability_lane;
    generate for (probability_lane = 0; probability_lane < LANES;
                  probability_lane = probability_lane + 1) begin : lane_output
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) probabilities[probability_lane*32 +: 32] <= 0;
            else if (state == S_IDLE && start)
                probabilities[probability_lane*32 +: 32] <= 0;
            else if (probability_write && lane == probability_lane)
                probabilities[probability_lane*32 +: 32] <= probability_value;
        end
    end endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            exp_cache_valid <= 0;
            state <= S_IDLE;
            lane <= {LCW{1'b0}}; offset_q <= 32'd0; block_max <= 32'd0;
            any_valid <= 1'b0;
            busy <= 1'b0; done <= 1'b0;
            updated_max <= 32'd0; rescale <= 32'd0;
            error_code <= ERR_NONE; exp_count <= 32'd0;
            sub_valid_in <= 1'b0; sub_a <= 32'd0; sub_b <= 32'd0;
            sub_pending <= 1'b0;
            exp_in_valid <= 1'b0; exp_argument <= 32'd0;
        end else begin
            sub_valid_in <= 1'b0;
            exp_in_valid <= 1'b0;
            done <= 1'b0;
            if (exp_out_valid && exp_error == 0 &&
                (state == S_RESC_W || state == S_EXP_W)) exp_cache_valid <= 1;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        exp_count <= 32'd0;
                        error_code <= ERR_NONE;
                        //: The reference refuses a first block with no valid
                        //: lane; a later block may legally be all padding.
                        if (score_nonfinite) begin
                            error_code <= ERR_OPERAND_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else if (cfg_first && !max_seen) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            busy <= 1'b1;
                            sub_pending <= 1'b0;
                            state <= S_MAX;
                        end
                    end
                end

                S_MAX: begin
                    any_valid <= max_seen;
                    //: An all-padding later block leaves the running maximum
                    //: exactly where it was.
                    block_max <= max_seen ? max_scan : cfg_running_max;
                    state <= S_SUBMAX;
                end

                S_SUBMAX: begin
                    updated_max <= canonical;
                    lane <= {LCW{1'b0}};
                    if (cfg_first) begin
                        //: +0, which is what the reference uses for block 0.
                        rescale <= 32'd0;
                        state <= S_OFF_S;
                    end else begin
                        state <= S_RESC_S;
                    end
                end

                //: rescale = exp(running - updated)
                S_RESC_S: begin
                    if (!sub_pending) begin
                        sub_valid_in <= 1'b1;
                        sub_a <= cfg_running_max;
                        sub_b <= canonical;
                        sub_pending <= 1'b1;
                    end else if (sub_valid_out) begin
                        sub_pending <= 1'b0;
                        if (sub_err != 2'd0) begin
                            error_code <= ERR_SELECT_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else if (exp_in_ready) begin
                            exp_in_valid <= 1'b1;
                            exp_argument <= sub_y;
                            state <= S_RESC_W;
                        end
                    end
                end

                S_RESC_W: begin
                    if (exp_out_valid) begin
                        exp_count <= exp_count + 32'd1;
                        if (exp_error != 2'd0) begin
                            error_code <= ERR_SELECT_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            rescale <= exp_result;
                            state <= S_OFF_S;
                        end
                    end
                end

                //: offset = score - updated, for the lane under the cursor.
                S_OFF_S: begin
                    if (lane >= LANES[31:0]) begin
                        busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                    end else if (!lane_valid[lane_sel]) begin
                        //: +0 WITHOUT TOUCHING THE EXPONENTIAL, which would
                        //: refuse the -inf the reference masks with.
                        lane <= lane + 1'b1;
                    end else if (!sub_pending) begin
                        sub_valid_in <= 1'b1;
                        sub_a <= scores[lane_sel*32 +: 32];
                        sub_b <= updated_max;
                        sub_pending <= 1'b1;
                    end else if (sub_valid_out) begin
                        sub_pending <= 1'b0;
                        offset_q <= sub_y;
                        state <= S_OFF_W;
                    end
                end

                S_OFF_W: begin
                    if (exp_cache_hit) begin
                        lane <= lane + 1'b1;
                        // exp_count counts logical evaluations, including hits.
                        exp_count <= exp_count + 32'd1;
                        state <= S_OFF_S;
                    end else if (exp_in_ready) begin
                        exp_in_valid <= 1'b1;
                        exp_argument <= offset_q;
                        state <= S_EXP_W;
                    end
                end

                S_EXP_W: begin
                    if (exp_out_valid) begin
                        exp_count <= exp_count + 32'd1;
                        if (exp_error != 2'd0) begin
                            error_code <= ERR_SELECT_NONFINITE;
                            busy <= 1'b0; done <= 1'b1; state <= S_DONE;
                        end else begin
                            lane <= lane + 1'b1;
                            state <= S_OFF_S;
                        end
                    end
                end

                S_DONE: begin
                    busy <= 1'b0; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
