`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// EXACT binary32 dot-product reduction, FULLY PIPELINED, REGISTERED TREE.
//
// PIPELINE: 2 + $clog2(LANES) registered stages (product/convert, one stage per
// tree level, accumulate).  INITIATION INTERVAL: 1 group of LANES pairs per
// clock.  No combinational path walks the vector, spans two stages, or contains
// a binary32 rounding: every stage is one integer operation.
//
// WHAT IT COMPUTES, and why the reduction is exact rather than sequential.
// The sum of products is accumulated in a fixed-point register wide enough to
// hold every product bit, so the reduction commits NO rounding at all and the
// caller rounds the finished sum once.  Three consequences, and they are the
// reason engram_gate_fp32_v1 is specified this way:
//
//   1. the result is INDEPENDENT OF REDUCTION ORDER, so a registered tree, a
//      serial accumulator, a different LANES, or a different lane-to-element
//      map all give the same code, and reduction order is not part of the
//      claim the campaign has to defend;
//   2. the per-stage critical path is one integer add of ACC_W bits, not a
//      binary32 add.  ot_fp32_rne_pkg::fp32_add_rne resolves align, add,
//      normalise and round through a 524-bit intermediate in one combinational
//      block and rtl/proto measures it at 174 MHz, so a tree whose nodes are
//      fp32_add_rne could not be a high-frequency tree however deeply it is
//      registered;
//   3. there is no accumulator ordering hazard, so the accumulator add is a
//      one-cycle loop-carried integer add and the pipe stays full.
//
// THE EXACTNESS WINDOW, and why it fails closed instead of rounding.
// A binary32 product spans exponents -298 to +208, which no affordable register
// holds exactly.  The window [2**ACC_EXP_MIN, 2**ACC_EXP_MAX) is therefore a
// PARAMETER pair, and a nonzero product outside it is REFUSED: the block raises
// window_error and the caller fails closed.  It never silently rounds, because a
// silently rounded reduction would make the claim "exact" false.  Defaults are
// ACC_EXP_MIN = -126, the smallest binary32 normal, so that no nonzero exact sum
// can be subnormal and the caller's rounder needs no subnormal path, and
// ACC_EXP_MAX = 64, which covers every activation magnitude the V4.1 Engram gate
// projections produce with 64 binary orders of margin.
//
// GEOMETRY.  LANES, MAX_TERMS and the window are parameters; MAX_TERMS sets only
// the accumulator's carry headroom, and the active term count comes from the
// caller's lane mask, so a shorter or longer row needs no edit here.  LANES must
// be a power of two.
// ---------------------------------------------------------------------------
module ot_a3_engram_exact_dot_tree #(
    parameter integer LANES       = 4,
    parameter integer MAX_TERMS   = 256,
    parameter integer ACC_EXP_MIN = -126,
    parameter integer ACC_EXP_MAX = 64,
    //: Width of the sign-extended summary port.  It must be at least the
    //: derived ACC_W below; 320 admits every window and term count this block is
    //: built with, and the instantiating module checks the bound it needs.
    parameter integer SUM_PORT_BITS = 320
) (
    input  wire                 clk,
    input  wire                 rst_n,
    //: Zero the accumulator and the sticky refusal flags.
    input  wire                 clear,
    input  wire                 in_valid,
    //: One bit per lane.  A masked-off lane contributes an exact zero and is
    //: excluded from every operand and window check, which is how a row whose
    //: length is not a multiple of LANES is reduced without a shape rule.
    input  wire [LANES-1:0]     in_lane_mask,
    input  wire [LANES*32-1:0]  in_left,
    input  wire [LANES*32-1:0]  in_right,
    output wire                 out_valid,
    output wire [SUM_PORT_BITS-1:0] out_sum,
    output wire                 out_nonfinite,
    output wire                 out_window
);
    localparam integer PRODUCT_BITS = 48;
    localparam integer WINDOW_BITS  = ACC_EXP_MAX - ACC_EXP_MIN;
    localparam integer COUNT_BITS   = (MAX_TERMS <= 1) ? 1 : $clog2(MAX_TERMS);
    //: Magnitude bits plus carry headroom for MAX_TERMS additions plus a sign.
    localparam integer ACC_W        = WINDOW_BITS + COUNT_BITS + 2;
    localparam integer TREE_LEVELS  = (LANES <= 1) ? 0 : $clog2(LANES);
    localparam integer EXP_W        = 12;

    // ---- stage 1: exact product per lane, converted to the fixed grid -----
    reg signed [ACC_W-1:0] leaf [0:LANES-1];
    reg                    leaf_valid;
    reg                    leaf_nonfinite;
    reg                    leaf_window;

    //: Packed decode: {nonfinite, sign, exponent[11:0], significand[23:0]},
    //: where the value is exactly significand * 2**exponent.  One function,
    //: called twice per lane, so the decode is written once.
    //:
    //: A SUBNORMAL IS LEFT UNNORMALISED, deliberately.  Its fraction is the
    //: significand and its exponent is -149, the same pair
    //: runtime/reference/engram.py::_significand_and_exponent produces.  An
    //: earlier version of this function shifted the fraction up and lowered the
    //: exponent to match, which is the same VALUE but a different EXPONENT, and
    //: the exactness-window predicate is a test on the exponent.  With the
    //: default window both forms refuse every subnormal product anyway, so the
    //: difference was invisible; at a window with ACC_EXP_MIN below -298 it
    //: would have made the block and its reference disagree about which
    //: products are representable.  Agreeing here rather than at one window is
    //: the point of deriving the predicate from parameters.
    function automatic [37:0] decode_binary32_exact;
        input [31:0] code;
        reg [7:0] biased;
        reg [22:0] fraction;
        reg [23:0] significand;
        reg signed [EXP_W-1:0] exponent;
        begin
            biased = code[30:23];
            fraction = code[22:0];
            if (biased == 8'b0) begin
                significand = {1'b0, fraction};
                exponent = -12'sd149;
            end else begin
                significand = {1'b1, fraction};
                exponent = $signed({4'b0, biased}) - 12'sd150;
            end
            decode_binary32_exact = {
                (biased == 8'hff), code[31], exponent, significand
            };
        end
    endfunction

    integer lane;
    reg [37:0] left_decoded;
    reg [37:0] right_decoded;
    reg [PRODUCT_BITS-1:0] product_magnitude;
    reg signed [EXP_W-1:0] product_exponent;
    reg [ACC_W-1:0] aligned;
    reg lane_nonfinite;
    reg lane_window;
    reg lane_zero;
    reg any_nonfinite;
    reg any_window;
    reg signed [EXP_W-1:0] shift_distance;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (lane = 0; lane < LANES; lane = lane + 1)
                leaf[lane] <= {ACC_W{1'b0}};
            leaf_valid <= 1'b0;
            leaf_nonfinite <= 1'b0;
            leaf_window <= 1'b0;
        end else begin
            leaf_valid <= in_valid;
            any_nonfinite = 1'b0;
            any_window = 1'b0;
            for (lane = 0; lane < LANES; lane = lane + 1) begin
                left_decoded = decode_binary32_exact(in_left[32*lane +: 32]);
                right_decoded = decode_binary32_exact(in_right[32*lane +: 32]);
                product_magnitude =
                    left_decoded[23:0] * right_decoded[23:0];
                product_exponent =
                    $signed(left_decoded[35:24]) + $signed(right_decoded[35:24]);
                lane_zero = (left_decoded[23:0] == 24'b0) ||
                            (right_decoded[23:0] == 24'b0);
                lane_nonfinite = left_decoded[37] || right_decoded[37];
                shift_distance =
                    product_exponent - $signed(ACC_EXP_MIN[EXP_W-1:0]);
                //: A nonzero product is representable only when its least
                //: significant bit lands on the grid and its magnitude, at most
                //: 2**(exponent+48), stays inside the window.  Both bounds come
                //: from the window parameters.
                lane_window = !lane_zero && !lane_nonfinite &&
                    ((shift_distance < 0) ||
                     (product_exponent + 12'sd48 >
                      $signed(ACC_EXP_MAX[EXP_W-1:0])));
                if (in_lane_mask[lane]) begin
                    any_nonfinite = any_nonfinite || lane_nonfinite;
                    any_window = any_window || lane_window;
                end
                if (!in_lane_mask[lane] || lane_zero || lane_nonfinite ||
                    lane_window) begin
                    aligned = {ACC_W{1'b0}};
                end else begin
                    aligned = {{(ACC_W-PRODUCT_BITS){1'b0}}, product_magnitude}
                              << shift_distance[EXP_W-2:0];
                end
                leaf[lane] <= (left_decoded[36] ^ right_decoded[36])
                    ? -$signed(aligned) : $signed(aligned);
            end
            if (clear) begin
                leaf_nonfinite <= 1'b0;
                leaf_window <= 1'b0;
            end else begin
                leaf_nonfinite <= leaf_nonfinite || (in_valid && any_nonfinite);
                leaf_window <= leaf_window || (in_valid && any_window);
            end
        end
    end

    // ---- stages 2..1+TREE_LEVELS: the registered binary tree --------------
    //: Heap indexing: node[1] is the root, node[LANES .. 2*LANES-1] the leaves.
    //: Every internal node registers the sum of its children's PREVIOUS values,
    //: which is exactly a tree pipelined one level per cycle.
    reg signed [ACC_W-1:0] node [1:(LANES < 2) ? 1 : 2*LANES-1];
    reg [TREE_LEVELS:0]    tree_valid;
    integer index;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (index = 1; index <= ((LANES < 2) ? 1 : 2*LANES-1);
                 index = index + 1)
                node[index] <= {ACC_W{1'b0}};
            tree_valid <= {(TREE_LEVELS+1){1'b0}};
        end else begin
            for (index = 0; index < LANES; index = index + 1)
                node[((LANES < 2) ? 1 : LANES) + index] <= leaf[index];
            for (index = 1; index < LANES; index = index + 1)
                node[index] <= node[2*index] + node[2*index+1];
            tree_valid[0] <= leaf_valid;
            for (index = 1; index <= TREE_LEVELS; index = index + 1)
                tree_valid[index] <= tree_valid[index-1];
        end
    end

    wire root_valid = tree_valid[TREE_LEVELS];

    // ---- final stage: the exact accumulator ------------------------------
    reg signed [ACC_W-1:0] accumulator;
    reg                    accumulator_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            accumulator <= {ACC_W{1'b0}};
            accumulator_valid <= 1'b0;
        end else if (clear) begin
            accumulator <= {ACC_W{1'b0}};
            accumulator_valid <= 1'b0;
        end else begin
            accumulator_valid <= root_valid;
            if (root_valid)
                accumulator <= accumulator + node[1];
        end
    end

    //: Sign extended to the fixed summary port so the instantiating module does
    //: not have to restate this module's width derivation.
    assign out_sum =
        {{(SUM_PORT_BITS-ACC_W){accumulator[ACC_W-1]}}, accumulator};
    assign out_valid = accumulator_valid;
    assign out_nonfinite = leaf_nonfinite;
    assign out_window = leaf_window;
endmodule
