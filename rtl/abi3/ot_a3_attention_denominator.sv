`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ATTENTION.SPARSE's across-block online denominator.
//
// This is where an online softmax actually goes wrong, so it is a block of its
// own rather than control folded into a larger state machine. For each source
// block of one (query row, head) the reference does:
//
//     <max, rescale, probabilities> = the online softmax of this block
//     block_sum = _balanced_sum(zero-padded probabilities)
//     sums = RN(sums * rescale)          <- one rounding
//     sums = RN(sums + block_sum)        <- and a second
//
// TWO ROUNDINGS, NOT A FUSED MULTIPLY-ADD.  ``np.multiply(sums, rescale,
// out=sums)`` then ``np.add(sums, block_sum, out=sums)`` is two binary32
// boundaries, and a fused ``sums * rescale + block_sum`` is a different number.
// ot_mac_bf16_fp32_pipe would have been the obvious unit and is the wrong one --
// it fuses, and its operands are BF16 besides. The multiply is
// ot_fp32_mul_rne_pipe and the add ot_fp32_add_rne_pipe, each qualified
// bit-identical to its scalar authority over 898,081 cases.
//
// THE FIRST BLOCK'S RESCALE IS +0 AND THAT IS LOAD-BEARING.  ot_a3_attention_
// softmax_block emits binary32 +0 there, and with ``sums`` starting at +0 the
// first update is RN(0 * 0) + block_sum = block_sum. A rescale of 1.0 would give
// the same answer only because sums is zero, so the zero is kept: it is what the
// reference writes, and it makes the first block need no special case here.
//
// THE PAD MUST BE +0, WHICH THE SOFTMAX BLOCK ALREADY GUARANTEES.  A short final
// block is zero-extended before the balanced tree, and
// ot_a3_reduction_balanced_sum's contract is that padding lanes are +0 -- -0
// would change the sum where a partial is exactly zero. The softmax block writes
// +0 for every invalid lane, so the two contracts already meet and nothing here
// has to arrange it.
//
// The composition is the point: this instantiates the two qualified blocks rather
// than reimplementing either, so a divergence in the maximum, the rescale, the
// probabilities or the association shows up as this block's failure.
// ---------------------------------------------------------------------------
module ot_a3_attention_denominator #(
    parameter integer LANES = 64
) (
    input  wire        clk,
    input  wire        rst_n,

    //: Raised once per source block, with that block's scores and mask.
    input  wire        block_valid,
    input  wire        block_first,
    input  wire [LANES-1:0]    lane_valid,
    input  wire [LANES*32-1:0] scores,
    output reg         block_ready,

    output reg  [31:0] running_max,
    output reg  [31:0] running_sums,
    //: The block just retired, so a caller can drive AV with the same values.
    output wire [31:0] block_rescale,
    output wire [LANES*32-1:0] block_probabilities,
    output reg         block_done,

    output reg         busy,
    output reg  [7:0]  error_code,
    output reg  [31:0] blocks_retired
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;

    localparam [3:0] S_IDLE  = 4'd0;
    localparam [3:0] S_SOFT  = 4'd1;
    localparam [3:0] S_TREE  = 4'd2;
    localparam [3:0] S_SCALE = 4'd3;
    localparam [3:0] S_ADD   = 4'd4;
    localparam [3:0] S_RETIRE = 4'd5;
    reg [3:0] state;

    reg        soft_start;
    reg        tree_start;
    reg        mul_pending;
    reg        add_pending;
    reg [31:0] scaled_sums;

    // -- the qualified online softmax, instantiated not reimplemented --------
    wire        soft_busy, soft_done;
    wire [31:0] soft_max;
    wire [7:0]  soft_error;
    wire [31:0] soft_exp_count;
    ot_a3_attention_softmax_block #(.LANES(LANES)) softmax (
        .clk(clk), .rst_n(rst_n),
        .start(soft_start),
        .cfg_first(block_first),
        .cfg_running_max(running_max),
        .lane_valid(lane_valid), .scores(scores),
        .busy(soft_busy), .done(soft_done),
        .updated_max(soft_max), .rescale(block_rescale),
        .probabilities(block_probabilities),
        .error_code(soft_error), .exp_count(soft_exp_count)
    );

    // -- and the qualified balanced tree, over the probabilities -------------
    wire        tree_busy, tree_done;
    wire [31:0] tree_total;
    wire [1:0]  tree_error;
    wire [31:0] tree_adds;
    ot_a3_reduction_balanced_sum #(.LANES(LANES)) tree (
        .clk(clk), .rst_n(rst_n),
        .start(tree_start),
        //: Already +0 on every invalid lane, which is the tree's pad contract.
        .lanes(block_probabilities),
        .busy(tree_busy), .done(tree_done),
        .total(tree_total), .error_code(tree_error), .add_count(tree_adds)
    );

    reg         mul_valid_in;
    wire [31:0] mul_y;
    wire [1:0]  mul_err;
    wire        mul_valid_out;
    ot_fp32_mul_rne_pipe rescale_mul (
        .clk(clk), .rst_n(rst_n), .valid_in(mul_valid_in),
        .a(running_sums), .b(block_rescale),
        .y(mul_y), .err(mul_err), .valid_out(mul_valid_out)
    );

    reg         add_valid_in;
    wire [31:0] add_y;
    wire [1:0]  add_err;
    wire        add_valid_out;
    ot_fp32_add_rne_pipe sum_add (
        .clk(clk), .rst_n(rst_n), .valid_in(add_valid_in),
        .a(scaled_sums), .b(tree_total),
        .y(add_y), .err(add_err), .valid_out(add_valid_out)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            soft_start <= 1'b0; tree_start <= 1'b0;
            mul_pending <= 1'b0; add_pending <= 1'b0;
            mul_valid_in <= 1'b0; add_valid_in <= 1'b0;
            scaled_sums <= 32'd0;
            running_max <= 32'd0; running_sums <= 32'd0;
            block_ready <= 1'b1; block_done <= 1'b0;
            busy <= 1'b0; error_code <= ERR_NONE; blocks_retired <= 32'd0;
        end else begin
            soft_start <= 1'b0;
            tree_start <= 1'b0;
            mul_valid_in <= 1'b0;
            add_valid_in <= 1'b0;
            block_done <= 1'b0;

            case (state)
                S_IDLE: begin
                    block_ready <= 1'b1;
                    if (block_valid) begin
                        //: A first block resets the carried state; a later one
                        //: continues from it.
                        if (block_first) begin
                            running_sums <= 32'd0;
                            blocks_retired <= 32'd0;
                            error_code <= ERR_NONE;
                        end
                        block_ready <= 1'b0;
                        busy <= 1'b1;
                        soft_start <= 1'b1;
                        state <= S_SOFT;
                    end
                end

                S_SOFT: begin
                    if (soft_done) begin
                        if (soft_error != ERR_NONE) begin
                            error_code <= soft_error;
                            busy <= 1'b0; block_ready <= 1'b1;
                            state <= S_IDLE;
                        end else begin
                            running_max <= soft_max;
                            tree_start <= 1'b1;
                            state <= S_TREE;
                        end
                    end
                end

                S_TREE: begin
                    if (tree_done) begin
                        if (tree_error != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            busy <= 1'b0; block_ready <= 1'b1;
                            state <= S_IDLE;
                        end else begin
                            state <= S_SCALE;
                        end
                    end
                end

                //: FIRST ROUNDING: sums * rescale.
                S_SCALE: begin
                    if (!mul_pending) begin
                        mul_valid_in <= 1'b1;
                        mul_pending <= 1'b1;
                    end else if (mul_valid_out) begin
                        mul_pending <= 1'b0;
                        if (mul_err != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            busy <= 1'b0; block_ready <= 1'b1;
                            state <= S_IDLE;
                        end else begin
                            scaled_sums <= mul_y;
                            state <= S_ADD;
                        end
                    end
                end

                //: SECOND ROUNDING: that, plus the block's balanced sum.
                S_ADD: begin
                    if (!add_pending) begin
                        add_valid_in <= 1'b1;
                        add_pending <= 1'b1;
                    end else if (add_valid_out) begin
                        add_pending <= 1'b0;
                        if (add_err != 2'd0) begin
                            error_code <= ERR_ACCUMULATE_RANGE;
                            busy <= 1'b0; block_ready <= 1'b1;
                            state <= S_IDLE;
                        end else begin
                            running_sums <= add_y;
                            blocks_retired <= blocks_retired + 32'd1;
                            state <= S_RETIRE;
                        end
                    end
                end

                S_RETIRE: begin
                    block_done <= 1'b1;
                    busy <= 1'b0;
                    block_ready <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
