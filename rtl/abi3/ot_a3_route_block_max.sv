`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROUTE.BLOCK_MAX (sub-opcode ot_a3_pkg::A3_ROUTE_BLOCK_MAX = 0x08), the
// blockwise maximum of the DeepSeek-V4.1-Flash candidate pool.  Kernel IR kind
// BLOCK_MAX(scores, block) -> block_scores
// (docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md section 5, row 2).
//
// WHAT IT COMPUTES.  One score per contiguous block of BLOCK positions of a
// score row, that block's maximum.  A row of N positions produces
// ceil(N / BLOCK) block scores in ascending block index; the operator selects
// no position and returns no index, which is why it is not a parameterisation
// of ROUTE.INDEX_TOPK -- INDEX_TOPK ranks POSITIONS, this reduces them.  The
// V4.1 candidate pool runs it over 2,048 blocks of 8.
//
// NON-MULTIPLE ROW LENGTH, stated because it is the one place the reference has
// a rule that a naive reduction does not.  The reference pads the row to a
// multiple of BLOCK with negative infinity and reduces the padded row, so the
// final block of a row whose length is not a multiple of BLOCK is the maximum
// over its REAL positions only, and the tail is never dropped and never padded
// with zero (a zero pad would win over a row of negative scores, which is the
// interesting case: these are masked attention scores).  The caller declares
// the real extent per block in in_valid_count; lanes at or above it are driven
// with the negative-infinity code inside this block, so the caller need not
// materialise the padding and whatever it leaves on those lanes -- including a
// NaN -- is ignored.  A partial block that is NOT the last block of its row is
// refused (DETAIL_BLOCK_MAX_PARTIAL_NOT_LAST): only a final block is partial
// under the reference, and silently accepting an interior short block would
// make the block index of everything after it disagree with the reference.
//
// PIPELINE.  STAGE COUNT = CMP_STAGES * $clog2(BLOCK) + 2; INITIATION INTERVAL
// = 1 block per cycle, unconditionally (there is no backpressure and no
// loop-carried dependence -- each block is independent, so the algorithm allows
// II = 1 and this block achieves it).  For the V4.1 defaults BLOCK = 8 and
// CMP_STAGES = 1 that is 5 stages: input register, three registered comparator
// levels, output register.  Latency from the rising edge that accepts a block
// to the rising edge that registers its block score is exactly that stage
// count LESS ONE, for every block, because the accepting edge is the input
// stage's own edge; the checkers assert that latency, per output, and
// pipeline_depth reports the stage count itself.
//
// The maximum is a REGISTERED BALANCED TREE, not a running compare: level l
// pairs (2i, 2i+1) of the previous level, so the combinational depth between
// registers is ONE comparator and the tree is $clog2(BLOCK) levels deep rather
// than BLOCK-1 comparators in series.  BLOCK need not be a power of two: the
// tree is built over NPOT = 2**$clog2(BLOCK) leaves and leaves BLOCK..NPOT-1
// are held at the negative-infinity code, which is the same padding rule the
// partial final block uses and therefore changes no result.  CMP_STAGES > 1
// inserts that many register stages per level for a shorter clock period on a
// view where one comparator does not fit; it changes latency, never a value.
// Nothing in the datapath walks the vector combinationally: the only reductions
// at the input stage are a masked OR of per-lane NaN flags and the count
// comparators, both log-depth, and both are registered before the first
// comparator level.  Style follows rtl/abi3/ot_a3_mac_lane_pipe.sv and
// rtl/abi3/ot_a3_tree_endpoint_fp32.sv (registered tree, payload travelling
// beside the datapath, fault committed at the output stage in input order).
//
// COMPARISON, contract block_max_ordered_ieee_v1 (the numeric contract of
// runtime/reference/candidate_pool.py::block_max_rows).  The order is the total
// order on the admitted codes of a sign-magnitude IEEE-754 interchange format:
// by exact value, with the negative zero below the positive zero, so
// max(-0.0, +0.0) = +0.0 and max(-0.0, -0.0) = -0.0, and the result is the
// WINNING CODE, bit for bit.  It is realised without any floating-point
// arithmetic by the standard monotone map from the code to an unsigned integer
// -- invert every bit of a negative code, set the sign bit of a non-negative
// one -- which is a bijection, so the winning key unmaps to the winning code
// exactly.  Only the comparison is defined here; no value is ever rounded,
// added or renormalised, so there is no rounding mode to agree on.
//
// ADMITTED CODES.  Every code of the format except a NaN.  Both infinities are
// admitted, because negative infinity is the reference's own padding and
// positive infinity is orderable; a NaN on a REAL lane is refused
// (DETAIL_BLOCK_MAX_SCORE_NAN, class ERR_OPERAND_NONFINITE) because the order
// is not total on NaNs and IEEE maxNum, numpy.maximum and Python max disagree
// about them -- there is no contract to implement, so it fails closed.
//
// NO FROZEN MODEL GEOMETRY.  BLOCK, the score format (SCORE_W, EXP_W, MANT_W),
// the per-row block bound MAX_BLOCKS, the block-index and tag widths, the
// extent-field width and the pipelining factor are parameters whose defaults
// are the V4.1 values.  Every predicate in the block derives its bound from a
// parameter or from the in_valid_count operand field: there is no literal
// extent anywhere below this header.  binary32 with BLOCK = 8 and
// MAX_BLOCKS = 2,048 is the V4.1 candidate pool; BF16 or FP16 scores, a
// different block, a non-power-of-two block and a different row bound
// elaborate and run unchanged, and the campaign
// (results/rtl/a3_v41_block_max_campaign.json) exercises six such shapes.
//
// FAIL-CLOSED, sticky, in input order.  Every refusal is decided at the input
// stage and travels with its block, so blocks accepted BEFORE the refused one
// retire normally; the refused block emits nothing, latches error_code (an
// ot_a3_engine_pkg class), error_detail (a DETAIL_BLOCK_MAX_* code of this
// module), error_block_id and error_tag, and from the cycle the refusal is
// DETECTED no further input is accepted, so nothing after the refusal is
// computed either.  clear restarts the block: it drops the refusal, empties the
// pipeline, and resets the row's block index; the retired counters are
// monotone and survive it.
//
// Package constants are referred to by scope, never by wildcard import (OI-43).
// ---------------------------------------------------------------------------
module ot_a3_route_block_max #(
    //: Positions per block.  V4.1 candidate pool: 8.  Any BLOCK >= 1.
    parameter integer BLOCK      = 8,
    //: Score format, a sign-magnitude IEEE-754 interchange format.
    //: SCORE_W must equal 1 + EXP_W + MANT_W.  binary32 by default; BF16 is
    //: (16, 8, 7) and FP16 is (16, 5, 10).
    parameter integer SCORE_W    = 32,
    parameter integer EXP_W      = 8,
    parameter integer MANT_W     = 23,
    //: Blocks admitted in one row.  V4.1 candidate pool: 2,048.
    parameter integer MAX_BLOCKS = 2048,
    //: Width of the block index carried with a result; must hold MAX_BLOCKS-1.
    parameter integer BLOCK_ID_W = 16,
    //: Row / pass identifier, returned with the result and with a refusal.
    parameter integer TAG_W      = 16,
    //: Width of the in_valid_count field.  Must be able to express BLOCK and
    //: at least one value above it, so an over-range extent is detectable
    //: rather than truncated into a legal one.
    parameter integer COUNT_W    = 8,
    //: Register stages per comparator level.  1 is one level per cycle.
    parameter integer CMP_STAGES = 1,
    //: Width of the retired-work counters.
    parameter integer COUNTER_W  = 32
) (
    input  wire                  clk,
    input  wire                  rst_n,

    input  wire                  in_valid,
    //: Real positions in this block: 1 .. BLOCK, positions [0, count) a
    //: contiguous prefix of the block.  Lanes at or above it are negative
    //: infinity (the reference's padding) whatever is driven on them.
    input  wire [COUNT_W-1:0]    in_valid_count,
    //: Score of lane k at [SCORE_W*k +: SCORE_W], ascending position.
    input  wire [SCORE_W*BLOCK-1:0] in_score,
    //: This block is the last of its row: the block index restarts after it.
    input  wire                  in_row_last,
    input  wire [TAG_W-1:0]      in_tag,
    input  wire                  clear,

    output reg                   out_valid,
    output reg  [SCORE_W-1:0]    out_score,
    output reg  [BLOCK_ID_W-1:0] out_block_id,
    output reg                   out_row_last,
    output reg  [TAG_W-1:0]      out_tag,

    output reg  [7:0]            error_code,
    output reg  [7:0]            error_detail,
    output reg  [BLOCK_ID_W-1:0] error_block_id,
    output reg  [TAG_W-1:0]      error_tag,
    output wire                  busy,
    output wire [31:0]           pipeline_depth,
    output reg  [COUNTER_W-1:0]  blocks_count,     // block scores retired
    output reg  [COUNTER_W-1:0]  positions_count,  // real positions reduced
    output reg  [COUNTER_W-1:0]  rows_count        // rows completed (row_last retired)
);
    // ----- error classes (ot_a3_engine_pkg) and this module's detail codes ---
    localparam [7:0] ERR_NONE              = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_SHAPE             = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [7:0] DETAIL_NONE                       = 8'd0;
    //: in_valid_count is zero or above BLOCK.  Zero is refused rather than
    //: emitting negative infinity: the reference emits ceil(N / BLOCK) blocks
    //: and never an all-padding block, so a zero extent is a caller error.
    localparam [7:0] DETAIL_BLOCK_MAX_VALID_COUNT      = 8'd1;
    //: a block with fewer than BLOCK real positions that is not row-last.
    localparam [7:0] DETAIL_BLOCK_MAX_PARTIAL_NOT_LAST = 8'd2;
    //: the row would exceed MAX_BLOCKS blocks.
    localparam [7:0] DETAIL_BLOCK_MAX_ROW_BLOCKS       = 8'd3;
    //: a NaN on a real lane; the order is not total on NaNs.
    localparam [7:0] DETAIL_BLOCK_MAX_SCORE_NAN        = 8'd4;

    function automatic [7:0] error_code_of_detail(input [7:0] detail);
        case (detail)
            DETAIL_NONE:                  error_code_of_detail = ERR_NONE;
            DETAIL_BLOCK_MAX_SCORE_NAN:   error_code_of_detail = ERR_OPERAND_NONFINITE;
            default:                      error_code_of_detail = ERR_SHAPE;
        endcase
    endfunction

    // ----- geometry, all derived from parameters -----------------------------
    localparam integer LEVELS = (BLOCK <= 1) ? 0 : $clog2(BLOCK);
    localparam integer NPOT   = 1 << LEVELS;              // >= BLOCK
    localparam integer TREE_STAGES = LEVELS * CMP_STAGES;
    localparam integer DEPTH  = TREE_STAGES + 2;          // + input + output

    //: the negative-infinity code of the format, and its order key.  The key
    //: of a negative code is its bitwise complement, so this is written out
    //: rather than calling the map in a constant expression.
    localparam [SCORE_W-1:0] NEG_INF_CODE = {1'b1, {EXP_W{1'b1}}, {MANT_W{1'b0}}};
    localparam [SCORE_W-1:0] NEG_INF_KEY  = {1'b0, {EXP_W{1'b0}}, {MANT_W{1'b1}}};

    assign pipeline_depth = DEPTH;

    initial begin
        if (SCORE_W != 1 + EXP_W + MANT_W)
            $fatal(1, "ot_a3_route_block_max: SCORE_W %0d != 1 + EXP_W %0d + MANT_W %0d",
                   SCORE_W, EXP_W, MANT_W);
        if (BLOCK < 1)
            $fatal(1, "ot_a3_route_block_max: BLOCK %0d must be at least 1", BLOCK);
        if (EXP_W < 2 || MANT_W < 1)
            $fatal(1, "ot_a3_route_block_max: EXP_W %0d MANT_W %0d is not an IEEE interchange shape",
                   EXP_W, MANT_W);
        if (CMP_STAGES < 1)
            $fatal(1, "ot_a3_route_block_max: CMP_STAGES %0d must be at least 1", CMP_STAGES);
        if (MAX_BLOCKS < 1)
            $fatal(1, "ot_a3_route_block_max: MAX_BLOCKS %0d must be at least 1", MAX_BLOCKS);
        if (BLOCK_ID_W < 1 || MAX_BLOCKS >> BLOCK_ID_W != 0)
            $fatal(1, "ot_a3_route_block_max: BLOCK_ID_W %0d cannot express the bound MAX_BLOCKS = %0d",
                   BLOCK_ID_W, MAX_BLOCKS);
        if (COUNT_W < 1 || BLOCK >> COUNT_W != 0)
            $fatal(1, "ot_a3_route_block_max: COUNT_W %0d cannot express BLOCK %0d and an over-range extent",
                   COUNT_W, BLOCK);
        if (COUNTER_W <= COUNT_W)
            $fatal(1, "ot_a3_route_block_max: COUNTER_W %0d must exceed COUNT_W %0d",
                   COUNTER_W, COUNT_W);
        //: the padding key must be the order key of the padding code: the
        //: constant is written out above, and this is the one place the two
        //: forms are checked against each other.
        if (order_key(NEG_INF_CODE) !== NEG_INF_KEY)
            $fatal(1, "ot_a3_route_block_max: padding key disagrees with the padding code");
    end

    // ----- the order key: a bijection, monotone in the format's total order --
    function automatic [SCORE_W-1:0] order_key(input [SCORE_W-1:0] code);
        order_key = code[SCORE_W-1] ? {1'b0, ~code[SCORE_W-2:0]}
                                    : {1'b1,  code[SCORE_W-2:0]};
    endfunction

    function automatic [SCORE_W-1:0] key_to_code(input [SCORE_W-1:0] key);
        key_to_code = key[SCORE_W-1] ? {1'b0,  key[SCORE_W-2:0]}
                                     : {1'b1, ~key[SCORE_W-2:0]};
    endfunction

    /* verilator lint_off UNUSEDSIGNAL */
    function automatic is_nan_code(input [SCORE_W-1:0] code);
        is_nan_code = (code[SCORE_W-2 -: EXP_W] == {EXP_W{1'b1}})
                   && (code[MANT_W-1:0]         != {MANT_W{1'b0}});
    endfunction
    /* verilator lint_on UNUSEDSIGNAL */

    // ----- input stage ------------------------------------------------------
    reg                   faulted;   // a refusal has committed at the output
    reg                   blocked;   // a refusal has been detected at the input
    reg [BLOCK_ID_W-1:0]  block_ctr; // index of the next block of this row

    //: the parameters as operand-width constants, so every predicate below
    //: compares like widths and no bound is written as a literal.
    localparam [COUNT_W-1:0]    BLOCK_EXTENT = BLOCK[COUNT_W-1:0];
    localparam [BLOCK_ID_W-1:0] ROW_BOUND    = MAX_BLOCKS[BLOCK_ID_W-1:0];

    wire count_bad   = (in_valid_count == {COUNT_W{1'b0}})
                    || (in_valid_count > BLOCK_EXTENT);
    wire partial_bad = !count_bad && (in_valid_count < BLOCK_EXTENT) && !in_row_last;
    wire row_bad     = (block_ctr >= ROW_BOUND);

    //: per-lane NaN flags, masked by the declared extent, reduced by an OR tree
    //: (log depth).  Lanes beyond the extent are padding and are not inspected.
    wire [BLOCK-1:0] lane_nan;
    genvar gk;
    generate
        for (gk = 0; gk < BLOCK; gk = gk + 1) begin : g_lane_nan
            localparam [COUNT_W-1:0] LANE_INDEX = gk;
            wire lane_real = (in_valid_count > LANE_INDEX);
            assign lane_nan[gk] = lane_real && is_nan_code(in_score[SCORE_W*gk +: SCORE_W]);
        end
    endgenerate
    wire nan_bad = !count_bad && (|lane_nan);

    //: refusal priority: extent legality, then the row bound, then the
    //: partial-block position rule, then the operand class.
    wire [7:0] in_detail = count_bad   ? DETAIL_BLOCK_MAX_VALID_COUNT
                         : row_bad     ? DETAIL_BLOCK_MAX_ROW_BLOCKS
                         : partial_bad ? DETAIL_BLOCK_MAX_PARTIAL_NOT_LAST
                         : nan_bad     ? DETAIL_BLOCK_MAX_SCORE_NAN
                                       : DETAIL_NONE;

    wire accept = in_valid && !faulted && !blocked;

    //: leaf keys: a real lane's key, or the padding key.
    wire [SCORE_W-1:0] leaf_key [0:NPOT-1];
    genvar gl;
    generate
        for (gl = 0; gl < NPOT; gl = gl + 1) begin : g_leaf
            if (gl < BLOCK) begin : g_real
                localparam [COUNT_W-1:0] LANE_INDEX = gl;
                assign leaf_key[gl] = (in_valid_count > LANE_INDEX)
                        ? order_key(in_score[SCORE_W*gl +: SCORE_W])
                        : NEG_INF_KEY;
            end else begin : g_pad
                assign leaf_key[gl] = NEG_INF_KEY;
            end
        end
    endgenerate

    // ----- the pipeline -----------------------------------------------------
    //: key_pipe[s] holds the keys after s stages; entries [0, NPOT >> level)
    //: are live at a stage that has completed `level` comparator levels.
    reg [SCORE_W-1:0]    key_pipe  [0:TREE_STAGES][0:NPOT-1];
    reg                  v_pipe    [0:TREE_STAGES];
    reg [BLOCK_ID_W-1:0] id_pipe   [0:TREE_STAGES];
    reg                  last_pipe [0:TREE_STAGES];
    reg [TAG_W-1:0]      tag_pipe  [0:TREE_STAGES];
    reg [7:0]            det_pipe  [0:TREE_STAGES];
    reg [COUNT_W-1:0]    cnt_pipe  [0:TREE_STAGES];

    integer k;
    integer s;

    always @(posedge clk) begin
        if (!rst_n) begin
            for (k = 0; k < NPOT; k = k + 1) key_pipe[0][k] <= {SCORE_W{1'b0}};
            v_pipe[0]    <= 1'b0;
            id_pipe[0]   <= {BLOCK_ID_W{1'b0}};
            last_pipe[0] <= 1'b0;
            tag_pipe[0]  <= {TAG_W{1'b0}};
            det_pipe[0]  <= DETAIL_NONE;
            cnt_pipe[0]  <= {COUNT_W{1'b0}};
            blocked      <= 1'b0;
            block_ctr    <= {BLOCK_ID_W{1'b0}};
        end else if (clear) begin
            v_pipe[0]   <= 1'b0;
            det_pipe[0] <= DETAIL_NONE;
            blocked     <= 1'b0;
            block_ctr   <= {BLOCK_ID_W{1'b0}};
        end else begin
            v_pipe[0] <= accept;
            if (accept) begin
                for (k = 0; k < NPOT; k = k + 1) key_pipe[0][k] <= leaf_key[k];
                id_pipe[0]   <= block_ctr;
                last_pipe[0] <= in_row_last;
                tag_pipe[0]  <= in_tag;
                det_pipe[0]  <= in_detail;
                cnt_pipe[0]  <= in_valid_count;
                if (in_detail != DETAIL_NONE) begin
                    blocked <= 1'b1;
                end else if (in_row_last) begin
                    block_ctr <= {BLOCK_ID_W{1'b0}};
                end else begin
                    block_ctr <= block_ctr + 1'b1;
                end
            end
        end
    end

    //: the registered comparator tree.  One level per CMP_STAGES stages; the
    //: stages of a level after the first are pure registers, which is where a
    //: slow view buys its clock period back.
    genvar gs, gi;
    generate
        for (gs = 1; gs <= TREE_STAGES; gs = gs + 1) begin : g_tree
            localparam integer LVL  = (gs - 1) / CMP_STAGES;
            localparam integer SUB  = (gs - 1) % CMP_STAGES;
            localparam integer NOUT = NPOT >> (LVL + 1);
            if (SUB == 0) begin : g_reduce
                for (gi = 0; gi < NOUT; gi = gi + 1) begin : g_cmp
                    wire [SCORE_W-1:0] a = key_pipe[gs-1][2*gi];
                    wire [SCORE_W-1:0] b = key_pipe[gs-1][2*gi+1];
                    always @(posedge clk) begin
                        if (!rst_n) key_pipe[gs][gi] <= {SCORE_W{1'b0}};
                        else        key_pipe[gs][gi] <= (a >= b) ? a : b;
                    end
                end
            end else begin : g_hold
                for (gi = 0; gi < NOUT; gi = gi + 1) begin : g_reg
                    always @(posedge clk) begin
                        if (!rst_n) key_pipe[gs][gi] <= {SCORE_W{1'b0}};
                        else        key_pipe[gs][gi] <= key_pipe[gs-1][gi];
                    end
                end
            end
        end
    endgenerate

    //: the payload travels beside the keys, one stage per cycle.
    generate
        if (TREE_STAGES > 0) begin : g_payload
            always @(posedge clk) begin
                if (!rst_n) begin
                    for (s = 1; s <= TREE_STAGES; s = s + 1) begin
                        v_pipe[s]    <= 1'b0;
                        id_pipe[s]   <= {BLOCK_ID_W{1'b0}};
                        last_pipe[s] <= 1'b0;
                        tag_pipe[s]  <= {TAG_W{1'b0}};
                        det_pipe[s]  <= DETAIL_NONE;
                        cnt_pipe[s]  <= {COUNT_W{1'b0}};
                    end
                end else if (clear) begin
                    for (s = 1; s <= TREE_STAGES; s = s + 1) begin
                        v_pipe[s]   <= 1'b0;
                        det_pipe[s] <= DETAIL_NONE;
                    end
                end else begin
                    for (s = 1; s <= TREE_STAGES; s = s + 1) begin
                        v_pipe[s]    <= v_pipe[s-1];
                        id_pipe[s]   <= id_pipe[s-1];
                        last_pipe[s] <= last_pipe[s-1];
                        tag_pipe[s]  <= tag_pipe[s-1];
                        det_pipe[s]  <= det_pipe[s-1];
                        cnt_pipe[s]  <= cnt_pipe[s-1];
                    end
                end
            end
        end
    endgenerate

    // ----- output stage: retire, or commit the refusal, in input order ------
    wire                  last_v   = v_pipe[TREE_STAGES];
    wire [7:0]            last_det = det_pipe[TREE_STAGES];
    wire [SCORE_W-1:0]    last_key = key_pipe[TREE_STAGES][0];
    wire [COUNTER_W-1:0]  retired_positions =
        {{(COUNTER_W-COUNT_W){1'b0}}, cnt_pipe[TREE_STAGES]};

    always @(posedge clk) begin
        if (!rst_n) begin
            out_valid       <= 1'b0;
            out_score       <= {SCORE_W{1'b0}};
            out_block_id    <= {BLOCK_ID_W{1'b0}};
            out_row_last    <= 1'b0;
            out_tag         <= {TAG_W{1'b0}};
            error_code      <= ERR_NONE;
            error_detail    <= DETAIL_NONE;
            error_block_id  <= {BLOCK_ID_W{1'b0}};
            error_tag       <= {TAG_W{1'b0}};
            faulted         <= 1'b0;
            blocks_count    <= {COUNTER_W{1'b0}};
            positions_count <= {COUNTER_W{1'b0}};
            rows_count      <= {COUNTER_W{1'b0}};
        end else if (clear) begin
            out_valid      <= 1'b0;
            error_code     <= ERR_NONE;
            error_detail   <= DETAIL_NONE;
            error_block_id <= {BLOCK_ID_W{1'b0}};
            error_tag      <= {TAG_W{1'b0}};
            faulted        <= 1'b0;
        end else begin
            out_valid <= 1'b0;
            if (last_v && (last_det == DETAIL_NONE) && !faulted) begin
                out_valid    <= 1'b1;
                out_score    <= key_to_code(last_key);
                out_block_id <= id_pipe[TREE_STAGES];
                out_row_last <= last_pipe[TREE_STAGES];
                out_tag      <= tag_pipe[TREE_STAGES];
                blocks_count    <= blocks_count + 1'b1;
                positions_count <= positions_count + retired_positions;
                if (last_pipe[TREE_STAGES])
                    rows_count <= rows_count + 1'b1;
            end else if (last_v && (last_det != DETAIL_NONE) && !faulted) begin
                faulted        <= 1'b1;
                error_code     <= error_code_of_detail(last_det);
                error_detail   <= last_det;
                error_block_id <= id_pipe[TREE_STAGES];
                error_tag      <= tag_pipe[TREE_STAGES];
            end
        end
    end

    //: a block is in flight anywhere in the pipeline.
    reg busy_r;
    always @(*) begin
        busy_r = 1'b0;
        for (s = 0; s <= TREE_STAGES; s = s + 1) busy_r = busy_r | v_pipe[s];
    end
    assign busy = busy_r;
endmodule
