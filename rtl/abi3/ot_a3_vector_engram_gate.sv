`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// VECTOR.ENGRAM_GATE (sub-opcode 0x0d) -- numeric contract engram_gate_fp32_v1.
//
// IR kind ENGRAM_GATE(h, key, value, q, k) -> h_out.  Five operands in, one out.
// AM-E10, plan section 5 row 6; reference authority
// runtime/reference/engram.py::engram_gate.
//
// ===========================================================================
// PIPELINE AND INITIATION INTERVAL
// ===========================================================================
// The transaction has three phases and each STREAMING phase is a registered
// pipeline with II = 1.  The scalar phase between them is 5 scalar operations
// that exist once per transaction, not once per element.
//
//   phase R, the reduction        II = 1 group of LANES element pairs / cycle.
//                                 4 + $clog2(LANES) registered stages: address
//                                 register, operand-memory read register, exact
//                                 product and grid convert, one stage per
//                                 registered tree level, exact accumulate.
//                                 SIX stages at the default LANES = 4.
//   phase S, the scalar head      not streaming.  3 correctly rounded square
//                                 roots through ONE pipelined sqrt at II = 1
//                                 (the two norms are issued back to back),
//                                 1 binary32 multiply, 1 correctly rounded
//                                 divide, 1 correctly rounded sigmoid.
//   phase C, the gated combine    II = 1 group of LANES elements / cycle.
//                                 FIVE registered stages: address register,
//                                 operand-memory read register, key*value,
//                                 gate*product, h + gated registered into the
//                                 write port.
//
// TOTAL STAGE COUNT of the two streaming paths: 4 + $clog2(LANES) for phase R
// (six at LANES = 4) and five for phase C.  The shared square root is a further
// SQRT_FRAC_SHIFT + 15 stages at II = 1 (thirty at the default), used three
// times per transaction and never per element.
// NO COMBINATIONAL PATH WALKS A VECTOR.  The only long reduction is phase R's,
// and it is a registered binary tree over an EXACT fixed-point grid, so each
// stage is one integer add rather than a binary32 add through a 524-bit
// intermediate -- see ot_a3_engram_exact_dot_tree.sv for why that distinction
// decides whether a tree can be a high-frequency tree at all.
//
// WHAT IS NOT PIPELINED, stated rather than hidden.  The divider
// (ot_a3_fp32_div_rne) and the certifying sigmoid
// (ot_a3_fp32_transcendental_cr_rne) are the repository's already-qualified
// multi-cycle blocks, reused unchanged because the alternative is a second,
// unqualified implementation of the same arithmetic.  They run once per
// transaction on scalars, so they cost latency and no throughput: at the V4.1
// row width of 256 and LANES = 4, phase R is 64 issue cycles and phase C is 64
// more, and the scalar head is off the element path entirely.  The per-stage
// combinational cost of phase C is one qualified binary32 operation from
// ot_fp32_rne_pkg; rtl/proto measures that class of block at 174 MHz standalone,
// so this block's CLOSING FREQUENCY IS NOT ESTABLISHED by simulation and is not
// claimed here.  It is WP-M physical work.
//
// ===========================================================================
// THE CONTRACT, in order, every operand and result a finite binary32 code
// ===========================================================================
//   1. dot = rne(SUM q_i*k_i), nq2 = rne(SUM q_i*q_i), nk2 = rne(SUM k_i*k_i),
//      each an EXACT reduction rounded exactly once.  Exact means order
//      independent: LANES, the tree shape and the lane map cannot change the
//      code, so reduction order is not part of this block's claim.
//   2. nq = sqrt(nq2), nk = sqrt(nk2), correctly rounded.
//   3. denominator = max(rne(nq*nk), GATE_EPSILON_CODE) -- the pinned 1e-6
//      clamp, applied to the rounded norm product.
//   4. cosine = rne(dot / denominator), the normalised dot.
//   5. signed_sqrt = sign(cosine) * sqrt(|cosine|), correctly rounded, +0 for a
//      zero cosine.  The SIGNED square root: the gate argument keeps the sign
//      of the normalised dot, which sqrt of a negative value could not.
//   6. gate = sigmoid(signed_sqrt), correctly rounded.
//   7. h_out_i = rne(h_i + rne(gate * rne(key_i*value_i))).
//
// OPERAND ROLES.  q and k are the gate's query and key rows and produce ONE
// scalar gate for the row; key and value are the two halves of the Engram
// key/value projection of the gathered rows, combined elementwise; h is the
// residual stream.
//
// ===========================================================================
// NO FROZEN MODEL GEOMETRY
// ===========================================================================
// VECTOR_WIDTH is the largest row this instance is BUILT for and is the only
// thing a width predicate is derived from; the row length the block actually
// runs is cfg_count, an operand field, and every lane mask, group count and
// address comes from it.  LANES, the exactness window and the clamp code are
// parameters too.  A row of 1, 3, 255 or 256 elements runs on the same
// instance; a row longer than VECTOR_WIDTH is refused with ERR_SHAPE rather
// than truncated.  There is no 256, no 24, no 8 and no head count anywhere
// below this comment except as a parameter DEFAULT.
//
// OPERAND ADDRESSING, stated because it is visible in a memory map.  Both
// streaming phases address whole groups, so a row whose length is not a multiple
// of LANES causes up to LANES-1 words PAST THE END OF THE ROW to be READ.  Those
// lanes are masked out of every reduction, every fault check and every write, so
// they cannot affect a result -- but the reads happen, and a placement that puts
// an unmapped page immediately after a row has to know that.
//
// ===========================================================================
// FAILS CLOSED, AT A NUMBERED SITE
// ===========================================================================
// refusal_stage reports WHICH line of the contract refused, using the same
// numbering as runtime/reference/engram.py, so a trap is attributable instead
// of being "the block failed".  A refused transaction writes no further output
// word; because groups retire in order, the words already written are exactly
// the elements that precede the first refused GROUP, which is a number the
// reference predicts without knowing the pipeline depth.
// ---------------------------------------------------------------------------
module ot_a3_vector_engram_gate #(
    //: Largest row this instance is built for.  The V4.1-Flash Engram rows are
    //: 256 wide (SRC-DSV41-FLASH-INDEX: two FP8 tables of [.., 256]).  DEFAULT,
    //: not a bound on the mechanism.
    parameter integer VECTOR_WIDTH = 256,
    //: Elements per cycle in both streaming phases.  Power of two.
    parameter integer LANES = 4,
    //: Exactness window of the reduction, as exponents of two.  -126 keeps
    //: every nonzero exact sum at or above the smallest binary32 normal, so no
    //: subnormal rounding path exists in the reduction.
    parameter integer ACC_EXP_MIN = -126,
    parameter integer ACC_EXP_MAX = 64,
    //: The pinned 1e-6 clamp floor, as a binary32 code.
    parameter [31:0] GATE_EPSILON_CODE = 32'h3586_37bd,
    //: Fractional bits of the shared square-root recurrence; >= 14 is required
    //: for the root to be correctly rounded.
    parameter integer SQRT_FRAC_SHIFT = 15
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    //: Row length of THIS transaction, 1 .. VECTOR_WIDTH.
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_h_base,
    input  wire [31:0] cfg_key_base,
    input  wire [31:0] cfg_value_base,
    input  wire [31:0] cfg_q_base,
    input  wire [31:0] cfg_k_base,
    input  wire [31:0] cfg_out_base,

    //: Three LANES-word read ports.  Phase R reads q and k on ports 0 and 1;
    //: phase C reads h, key and value on ports 0, 1 and 2.  An address is an
    //: element index and the port returns LANES consecutive words one cycle
    //: later.
    output reg         r0_rd_en,
    output reg  [31:0] r0_rd_addr,
    input  wire [LANES*32-1:0] r0_rd_data,
    output reg         r1_rd_en,
    output reg  [31:0] r1_rd_addr,
    input  wire [LANES*32-1:0] r1_rd_data,
    output reg         r2_rd_en,
    output reg  [31:0] r2_rd_addr,
    input  wire [LANES*32-1:0] r2_rd_data,

    //: One write-enable bit per lane; out_addr is lane 0's element index.
    output reg  [LANES-1:0]    out_we,
    output reg  [31:0]         out_addr,
    output reg  [LANES*32-1:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [3:0]  refusal_stage,
    output reg  [31:0] out_count,
    output reg  [31:0] reduce_count,

    //: The sub-opcode this block implements, taken from the package rather than
    //: restated, so a renumbering in ot_a3_pkg.sv is caught by the scoreboard
    //: here instead of being discovered at integration.
    output wire [7:0]  sub_opcode,

    //: Every architecturally visible scalar of the contract, so the scoreboard
    //: compares the whole chain and not only the output row.
    output reg  [31:0] dbg_dot_code,
    output reg  [31:0] dbg_norm_q_square_code,
    output reg  [31:0] dbg_norm_k_square_code,
    output reg  [31:0] dbg_norm_q_code,
    output reg  [31:0] dbg_norm_k_code,
    output reg  [31:0] dbg_denominator_raw_code,
    output reg  [31:0] dbg_denominator_code,
    output reg  [31:0] dbg_cosine_code,
    output reg  [31:0] dbg_signed_sqrt_code,
    output reg  [31:0] dbg_gate_code,
    output reg         dbg_clamped
);
    // Package constants are re-declared and package functions are called
    // through their scope: the pinned Yosys 0.68 Verilog frontend rejects
    // `import`, and Icarus 11 turns a wildcard-imported identifier used only in
    // a port connection into an implicit net.
    localparam [7:0] ERR_NONE              = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE     = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE  = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE             = ot_a3_engine_pkg::ERR_SHAPE;

    assign sub_opcode = ot_a3_pkg::A3_VECTOR_ENGRAM_GATE;

    //: Refusal sites.  Identical numbering to runtime/reference/engram.py.
    localparam [3:0] SITE_NONE             = 4'd0;
    localparam [3:0] SITE_SHAPE            = 4'd1;
    localparam [3:0] SITE_REDUCE_OPERAND   = 4'd2;
    localparam [3:0] SITE_REDUCE_WINDOW    = 4'd3;
    localparam [3:0] SITE_DOT_ROUND        = 4'd4;
    localparam [3:0] SITE_NORM_ROUND       = 4'd5;
    localparam [3:0] SITE_NORM_SQRT        = 4'd6;
    localparam [3:0] SITE_DENOMINATOR      = 4'd7;
    localparam [3:0] SITE_DIVIDE           = 4'd8;
    localparam [3:0] SITE_SIGNED_SQRT      = 4'd9;
    localparam [3:0] SITE_SIGMOID          = 4'd10;
    localparam [3:0] SITE_COMBINE_OPERAND  = 4'd11;
    localparam [3:0] SITE_COMBINE_RANGE    = 4'd12;

    localparam integer LANE_LOG    = (LANES <= 1) ? 0 : $clog2(LANES);
    localparam integer WINDOW_BITS = ACC_EXP_MAX - ACC_EXP_MIN;
    localparam integer COUNT_BITS  = (VECTOR_WIDTH <= 1) ? 1 : $clog2(VECTOR_WIDTH);
    //: Must match ot_a3_engram_exact_dot_tree's derivation exactly.
    localparam integer ACC_W       = WINDOW_BITS + COUNT_BITS + 2;

    localparam [4:0] S_IDLE          = 5'd0;
    localparam [4:0] S_REDUCE        = 5'd1;
    localparam [4:0] S_REDUCE_DRAIN  = 5'd2;
    localparam [4:0] S_ROUND_DOT     = 5'd3;
    localparam [4:0] S_ROUND_NQ2     = 5'd4;
    localparam [4:0] S_ROUND_NK2     = 5'd5;
    localparam [4:0] S_SQRT_NORMS    = 5'd6;
    localparam [4:0] S_SQRT_WAIT     = 5'd7;
    localparam [4:0] S_DENOM         = 5'd8;
    localparam [4:0] S_DIV_REQ       = 5'd9;
    localparam [4:0] S_DIV_RSP       = 5'd10;
    localparam [4:0] S_SSQRT_ISSUE   = 5'd11;
    localparam [4:0] S_SSQRT_WAIT    = 5'd12;
    localparam [4:0] S_SIG_REQ       = 5'd13;
    localparam [4:0] S_SIG_RSP       = 5'd14;
    localparam [4:0] S_COMBINE       = 5'd15;
    localparam [4:0] S_COMBINE_DRAIN = 5'd16;
    localparam [4:0] S_DONE          = 5'd17;

    reg [4:0]  state;
    //: The whole request is LATCHED at start.  Nothing downstream reads the
    //: cfg_* bus again, so a request that changes after issue cannot influence a
    //: transaction in flight, and the scoreboard can poison the bus to prove it.
    reg [31:0] element_count;
    reg [31:0] base_h;
    reg [31:0] base_key;
    reg [31:0] base_value;
    reg [31:0] base_q;
    reg [31:0] base_k;
    reg [31:0] base_out;
    reg [31:0] group_count;
    reg [31:0] issue_group;
    reg [31:0] retired_group;
    reg [31:0] combine_issue_group;
    reg [31:0] combine_retired_group;
    reg        poisoned;
    reg [1:0]  sqrt_issued;
    reg [1:0]  sqrt_received;

    integer lane;
    integer bit_position;

    // -----------------------------------------------------------------------
    // Lane masks derived from cfg_count, never from a constant width.
    // -----------------------------------------------------------------------
    function automatic [LANES-1:0] lane_mask_for;
        input [31:0] group;
        input [31:0] count;
        integer index;
        reg [31:0] element;
        begin
            lane_mask_for = {LANES{1'b0}};
            for (index = 0; index < LANES; index = index + 1) begin
                element = group * LANES + index[31:0];
                lane_mask_for[index] = (element < count);
            end
        end
    endfunction

    //: Counted into a full word, not a byte: an 8-bit population count would
    //: silently cap LANES at 255, which is exactly the kind of frozen bound this
    //: block exists to not have.
    function automatic [31:0] lane_population;
        input [LANES-1:0] mask;
        integer index;
        begin
            lane_population = 32'd0;
            for (index = 0; index < LANES; index = index + 1)
                if (mask[index])
                    lane_population = lane_population + 32'd1;
        end
    endfunction

    // -----------------------------------------------------------------------
    // One rounding of an exact fixed-point sum to binary32, RNE.
    // Returned packed as {error[1:0], code[31:0]} like ot_fp32_rne_pkg.
    // -----------------------------------------------------------------------
    function automatic [33:0] exact_sum_to_fp32_rne;
        input signed [ACC_W-1:0] value;
        reg              sign;
        reg [ACC_W-1:0]  magnitude;
        reg [ACC_W-1:0]  low_mask;
        integer          msb;
        integer          index;
        integer          drop;
        reg [24:0]       truncated;
        reg [ACC_W-1:0]  shifted;
        reg              guard;
        reg              sticky;
        reg [25:0]       rounded;
        reg [23:0]       significand;
        integer          exponent;
        integer          biased;
        begin
            sign = value[ACC_W-1];
            magnitude = sign ? (~value + {{(ACC_W-1){1'b0}}, 1'b1}) : value;
            if (magnitude == {ACC_W{1'b0}}) begin
                exact_sum_to_fp32_rne = {2'd0, 32'b0};
            end else begin
                msb = 0;
                for (index = 0; index < ACC_W; index = index + 1)
                    if (magnitude[index])
                        msb = index;
                exponent = ACC_EXP_MIN + msb;
                if (msb > 23) begin
                    drop = msb - 23;
                    //: Sliced explicitly: the shifted magnitude has exactly 24
                    //: significant bits, and an implicit narrowing of a 200-bit
                    //: value into 25 is the class of width defect that a
                    //: -Wno-fatal build turns into a wrong answer.
                    shifted = magnitude >> drop;
                    truncated = {1'b0, shifted[23:0]};
                    guard = magnitude[drop-1];
                    low_mask = ({{(ACC_W-1){1'b0}}, 1'b1} << (drop - 1)) -
                               {{(ACC_W-1){1'b0}}, 1'b1};
                    sticky = |(magnitude & low_mask);
                end else begin
                    shifted = magnitude << (23 - msb);
                    truncated = {1'b0, shifted[23:0]};
                    guard = 1'b0;
                    sticky = 1'b0;
                end
                rounded = {1'b0, truncated} +
                          {25'b0, (guard && (sticky || truncated[0]))};
                if (rounded[24]) begin
                    significand = rounded[24:1];
                    exponent = exponent + 1;
                end else begin
                    significand = rounded[23:0];
                end
                biased = exponent + 127;
                if (biased > 254 || biased < 1)
                    exact_sum_to_fp32_rne = {2'd2, 32'b0};
                else
                    exact_sum_to_fp32_rne =
                        {2'd0, sign, biased[7:0], significand[22:0]};
            end
        end
    endfunction

    // -----------------------------------------------------------------------
    // Phase R: three exact reduction trees sharing one issue stream.
    // -----------------------------------------------------------------------
    reg             reduce_data_valid;
    reg [LANES-1:0] reduce_data_mask;
    //: The trees are cleared while the block is idle, so a transaction always
    //: starts from an exact zero accumulator and clean sticky flags.
    wire            tree_clear = (state == S_IDLE);

    localparam integer SUM_PORT_BITS = 320;
    wire [SUM_PORT_BITS-1:0] dot_sum_wide;
    wire [SUM_PORT_BITS-1:0] norm_q_sum_wide;
    wire [SUM_PORT_BITS-1:0] norm_k_sum_wide;
    wire dot_valid, norm_q_valid, norm_k_valid;
    wire dot_nonfinite, norm_q_nonfinite, norm_k_nonfinite;
    wire dot_window, norm_q_window, norm_k_window;

    ot_a3_engram_exact_dot_tree #(
        .LANES(LANES), .MAX_TERMS(VECTOR_WIDTH),
        .ACC_EXP_MIN(ACC_EXP_MIN), .ACC_EXP_MAX(ACC_EXP_MAX),
        .SUM_PORT_BITS(SUM_PORT_BITS)
    ) dot_tree (
        .clk(clk), .rst_n(rst_n), .clear(tree_clear),
        .in_valid(reduce_data_valid), .in_lane_mask(reduce_data_mask),
        .in_left(r0_rd_data), .in_right(r1_rd_data),
        .out_valid(dot_valid), .out_sum(dot_sum_wide),
        .out_nonfinite(dot_nonfinite), .out_window(dot_window)
    );

    ot_a3_engram_exact_dot_tree #(
        .LANES(LANES), .MAX_TERMS(VECTOR_WIDTH),
        .ACC_EXP_MIN(ACC_EXP_MIN), .ACC_EXP_MAX(ACC_EXP_MAX),
        .SUM_PORT_BITS(SUM_PORT_BITS)
    ) norm_q_tree (
        .clk(clk), .rst_n(rst_n), .clear(tree_clear),
        .in_valid(reduce_data_valid), .in_lane_mask(reduce_data_mask),
        .in_left(r0_rd_data), .in_right(r0_rd_data),
        .out_valid(norm_q_valid), .out_sum(norm_q_sum_wide),
        .out_nonfinite(norm_q_nonfinite), .out_window(norm_q_window)
    );

    ot_a3_engram_exact_dot_tree #(
        .LANES(LANES), .MAX_TERMS(VECTOR_WIDTH),
        .ACC_EXP_MIN(ACC_EXP_MIN), .ACC_EXP_MAX(ACC_EXP_MAX),
        .SUM_PORT_BITS(SUM_PORT_BITS)
    ) norm_k_tree (
        .clk(clk), .rst_n(rst_n), .clear(tree_clear),
        .in_valid(reduce_data_valid), .in_lane_mask(reduce_data_mask),
        .in_left(r1_rd_data), .in_right(r1_rd_data),
        .out_valid(norm_k_valid), .out_sum(norm_k_sum_wide),
        .out_nonfinite(norm_k_nonfinite), .out_window(norm_k_window)
    );

    wire reduce_nonfinite = dot_nonfinite || norm_q_nonfinite || norm_k_nonfinite;
    wire reduce_window = dot_window || norm_q_window || norm_k_window;

    //: One shared rounder, selected by state, rather than three instances of a
    //: 200-bit leading-one detect and shifter.
    wire signed [ACC_W-1:0] round_input =
        (state == S_ROUND_DOT) ? $signed(dot_sum_wide[ACC_W-1:0]) :
        (state == S_ROUND_NQ2) ? $signed(norm_q_sum_wide[ACC_W-1:0]) :
                                 $signed(norm_k_sum_wide[ACC_W-1:0]);
    wire [33:0] round_result = exact_sum_to_fp32_rne(round_input);

    // -----------------------------------------------------------------------
    // Phase S: the shared pipelined square root, the qualified divider and the
    // qualified certifying sigmoid.
    // -----------------------------------------------------------------------
    wire sqrt_in_valid = (state == S_SQRT_NORMS) || (state == S_SSQRT_ISSUE);
    wire [31:0] sqrt_argument =
        (state == S_SSQRT_ISSUE) ? {1'b0, dbg_cosine_code[30:0]} :
        (sqrt_issued == 2'd0) ? dbg_norm_q_square_code : dbg_norm_k_square_code;
    wire        sqrt_out_valid;
    wire [31:0] sqrt_result;
    wire [1:0]  sqrt_error;

    ot_a3_engram_fp32_sqrt_rne_pipe #(
        .FRAC_SHIFT(SQRT_FRAC_SHIFT)
    ) square_root (
        .clk(clk), .rst_n(rst_n),
        .in_valid(sqrt_in_valid), .argument_code(sqrt_argument),
        .out_valid(sqrt_out_valid), .result_code(sqrt_result),
        .result_error(sqrt_error)
    );

    wire [33:0] denominator_product =
        ot_fp32_rne_pkg::fp32_mul_rne(dbg_norm_q_code, dbg_norm_k_code);
    //: Both factors are nonnegative, so the clamp is a magnitude comparison of
    //: monotone binary32 codes and needs no arithmetic.
    wire clamp_active =
        denominator_product[30:0] < GATE_EPSILON_CODE[30:0];

    wire        divider_in_ready;
    wire        divider_out_valid;
    wire [31:0] divider_result;
    wire [1:0]  divider_error;

    ot_a3_fp32_div_rne divider (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_DIV_REQ), .in_ready(divider_in_ready),
        .numerator_code(dbg_dot_code),
        .denominator_code(dbg_denominator_code),
        .out_valid(divider_out_valid), .out_ready(state == S_DIV_RSP),
        .result_code(divider_result), .result_error(divider_error)
    );

    wire        sigmoid_in_ready;
    wire        sigmoid_out_valid;
    wire [31:0] sigmoid_result;
    wire [1:0]  sigmoid_error;

    ot_a3_fp32_transcendental_cr_rne sigmoid (
        .clk(clk), .rst_n(rst_n),
        .in_valid(state == S_SIG_REQ), .in_ready(sigmoid_in_ready),
        .operation(1'b1),
        .argument_code(dbg_signed_sqrt_code),
        .out_valid(sigmoid_out_valid), .out_ready(state == S_SIG_RSP),
        .result_code(sigmoid_result), .result_error(sigmoid_error)
    );

    // -----------------------------------------------------------------------
    // Phase C: the gated residual combine, one registered binary32 operation
    // per stage per lane.
    // -----------------------------------------------------------------------
    reg                     c1_valid;
    reg [LANES-1:0]         c1_mask;
    reg [31:0]              c1_group;
    reg [LANES*32-1:0]      c1_hidden;
    reg [LANES*32-1:0]      c1_product;
    reg [LANES-1:0]         c1_operand_fault;
    reg [LANES-1:0]         c1_range_fault;

    reg                     c2_valid;
    reg [LANES-1:0]         c2_mask;
    reg [31:0]              c2_group;
    reg [LANES*32-1:0]      c2_hidden;
    reg [LANES*32-1:0]      c2_gated;
    reg [LANES-1:0]         c2_operand_fault;
    reg [LANES-1:0]         c2_range_fault;

    //: Stage C1 arithmetic: the elementwise Engram key/value product.
    reg [33:0] stage1_product [0:LANES-1];
    reg [LANES-1:0] stage1_operand_fault;
    always @* begin
        for (lane = 0; lane < LANES; lane = lane + 1) begin
            stage1_product[lane] = ot_fp32_rne_pkg::fp32_mul_rne(
                r1_rd_data[32*lane +: 32], r2_rd_data[32*lane +: 32]
            );
            stage1_operand_fault[lane] =
                (r0_rd_data[32*lane+23 +: 8] == 8'hff) ||
                (r1_rd_data[32*lane+23 +: 8] == 8'hff) ||
                (r2_rd_data[32*lane+23 +: 8] == 8'hff);
        end
    end

    //: Stage C2 arithmetic: scale the product by the one scalar gate.
    reg [33:0] stage2_gated [0:LANES-1];
    always @* begin
        for (lane = 0; lane < LANES; lane = lane + 1)
            stage2_gated[lane] = ot_fp32_rne_pkg::fp32_mul_rne(
                dbg_gate_code, c1_product[32*lane +: 32]
            );
    end

    //: Stage C3 arithmetic: the residual add, registered into the write port.
    reg [33:0] stage3_sum [0:LANES-1];
    always @* begin
        for (lane = 0; lane < LANES; lane = lane + 1)
            stage3_sum[lane] = ot_fp32_rne_pkg::fp32_add_rne(
                c2_hidden[32*lane +: 32], c2_gated[32*lane +: 32]
            );
    end

    //: The group's verdict, resolved at the stage where every fault of every
    //: lane of that group is known, and scanned in ASCENDING lane order so the
    //: site matches the reference's element-ascending evaluation.
    reg [LANES-1:0] retire_operand_fault;
    reg [LANES-1:0] retire_range_fault;
    reg [3:0]       retire_site;
    always @* begin
        for (lane = 0; lane < LANES; lane = lane + 1) begin
            retire_operand_fault[lane] =
                c2_operand_fault[lane] && c2_mask[lane];
            retire_range_fault[lane] =
                (c2_range_fault[lane] || (stage3_sum[lane][33:32] != 2'd0)) &&
                c2_mask[lane];
        end
        retire_site = SITE_NONE;
        for (bit_position = LANES - 1; bit_position >= 0;
             bit_position = bit_position - 1) begin
            if (retire_operand_fault[bit_position])
                retire_site = SITE_COMBINE_OPERAND;
            else if (retire_range_fault[bit_position])
                retire_site = SITE_COMBINE_RANGE;
        end
    end

    // -----------------------------------------------------------------------
    // Control and both streaming pipelines, in ONE sequential block so every
    // register has exactly one driver.
    //
    // Operand-memory timing, matching every other engine block here: an address
    // registered at the end of cycle t is on the bus during t+1, the memory
    // registers its word at the end of t+1, and the data is on the bus during
    // t+2.  The valid/mask chain therefore has two stages before the first
    // arithmetic stage, in both phases.
    // -----------------------------------------------------------------------
    wire reduce_issuing = (state == S_REDUCE) && (issue_group < group_count);
    wire combine_issuing = (state == S_COMBINE) && !poisoned &&
                           (combine_issue_group < group_count);

    reg             reduce_addr_valid;
    reg [LANES-1:0] reduce_addr_mask;
    reg             combine_addr_valid;
    reg [LANES-1:0] combine_addr_mask;
    reg [31:0]      combine_addr_group;
    reg             combine_data_valid;
    reg [LANES-1:0] combine_data_mask;
    reg [31:0]      combine_data_group;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            refusal_stage <= SITE_NONE;
            out_count <= 32'b0;
            reduce_count <= 32'b0;
            element_count <= 32'b0;
            group_count <= 32'b0;
            base_h <= 32'b0;
            base_key <= 32'b0;
            base_value <= 32'b0;
            base_q <= 32'b0;
            base_k <= 32'b0;
            base_out <= 32'b0;
            issue_group <= 32'b0;
            retired_group <= 32'b0;
            combine_issue_group <= 32'b0;
            combine_retired_group <= 32'b0;
            poisoned <= 1'b0;
            sqrt_issued <= 2'd0;
            sqrt_received <= 2'd0;
            r0_rd_en <= 1'b0;
            r1_rd_en <= 1'b0;
            r2_rd_en <= 1'b0;
            r0_rd_addr <= 32'b0;
            r1_rd_addr <= 32'b0;
            r2_rd_addr <= 32'b0;
            out_we <= {LANES{1'b0}};
            out_addr <= 32'b0;
            out_data <= {(LANES*32){1'b0}};
            reduce_addr_valid <= 1'b0;
            reduce_addr_mask <= {LANES{1'b0}};
            reduce_data_valid <= 1'b0;
            reduce_data_mask <= {LANES{1'b0}};
            combine_addr_valid <= 1'b0;
            combine_addr_mask <= {LANES{1'b0}};
            combine_addr_group <= 32'b0;
            combine_data_valid <= 1'b0;
            combine_data_mask <= {LANES{1'b0}};
            combine_data_group <= 32'b0;
            c1_valid <= 1'b0;
            c1_mask <= {LANES{1'b0}};
            c1_group <= 32'b0;
            c1_hidden <= {(LANES*32){1'b0}};
            c1_product <= {(LANES*32){1'b0}};
            c1_operand_fault <= {LANES{1'b0}};
            c1_range_fault <= {LANES{1'b0}};
            c2_valid <= 1'b0;
            c2_mask <= {LANES{1'b0}};
            c2_group <= 32'b0;
            c2_hidden <= {(LANES*32){1'b0}};
            c2_gated <= {(LANES*32){1'b0}};
            c2_operand_fault <= {LANES{1'b0}};
            c2_range_fault <= {LANES{1'b0}};
            dbg_dot_code <= 32'b0;
            dbg_norm_q_square_code <= 32'b0;
            dbg_norm_k_square_code <= 32'b0;
            dbg_norm_q_code <= 32'b0;
            dbg_norm_k_code <= 32'b0;
            dbg_denominator_raw_code <= 32'b0;
            dbg_denominator_code <= 32'b0;
            dbg_cosine_code <= 32'b0;
            dbg_signed_sqrt_code <= 32'b0;
            dbg_gate_code <= 32'b0;
            dbg_clamped <= 1'b0;
        end else begin
            done <= 1'b0;
            out_we <= {LANES{1'b0}};
            r0_rd_en <= 1'b0;
            r1_rd_en <= 1'b0;
            r2_rd_en <= 1'b0;
            c1_valid <= 1'b0;
            c2_valid <= 1'b0;

            // ---- the two-stage operand-memory valid/mask chains ----------
            reduce_addr_valid <= reduce_issuing;
            reduce_addr_mask <= lane_mask_for(issue_group, element_count);
            reduce_data_valid <= reduce_addr_valid;
            reduce_data_mask <= reduce_addr_mask;

            combine_addr_valid <= combine_issuing;
            combine_addr_mask <=
                lane_mask_for(combine_issue_group, element_count);
            combine_addr_group <= combine_issue_group;
            combine_data_valid <= combine_addr_valid;
            combine_data_mask <= combine_addr_mask;
            combine_data_group <= combine_addr_group;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        refusal_stage <= SITE_NONE;
                        out_count <= 32'b0;
                        reduce_count <= 32'b0;
                        issue_group <= 32'b0;
                        retired_group <= 32'b0;
                        combine_issue_group <= 32'b0;
                        combine_retired_group <= 32'b0;
                        poisoned <= 1'b0;
                        sqrt_issued <= 2'd0;
                        sqrt_received <= 2'd0;
                        dbg_dot_code <= 32'b0;
                        dbg_norm_q_square_code <= 32'b0;
                        dbg_norm_k_square_code <= 32'b0;
                        dbg_norm_q_code <= 32'b0;
                        dbg_norm_k_code <= 32'b0;
                        dbg_denominator_raw_code <= 32'b0;
                        dbg_denominator_code <= 32'b0;
                        dbg_cosine_code <= 32'b0;
                        dbg_signed_sqrt_code <= 32'b0;
                        dbg_gate_code <= 32'b0;
                        dbg_clamped <= 1'b0;
                        element_count <= cfg_count;
                        group_count <= (cfg_count + LANES - 1) >> LANE_LOG;
                        base_h <= cfg_h_base;
                        base_key <= cfg_key_base;
                        base_value <= cfg_value_base;
                        base_q <= cfg_q_base;
                        base_k <= cfg_k_base;
                        base_out <= cfg_out_base;
                        //: The only width predicate, and it is derived from a
                        //: parameter, not from a model dimension.
                        if (cfg_count == 32'b0 || cfg_count > VECTOR_WIDTH)
                            begin
                                refusal_stage <= SITE_SHAPE;
                                error_code <= ERR_SHAPE;
                                state <= S_DONE;
                            end
                        else
                            state <= S_REDUCE;
                    end
                end

                // ---- phase R --------------------------------------------
                S_REDUCE: begin
                    if (reduce_issuing) begin
                        r0_rd_en <= 1'b1;
                        r1_rd_en <= 1'b1;
                        r0_rd_addr <= base_q + (issue_group << LANE_LOG);
                        r1_rd_addr <= base_k + (issue_group << LANE_LOG);
                        issue_group <= issue_group + 32'd1;
                    end else begin
                        state <= S_REDUCE_DRAIN;
                    end
                end

                S_REDUCE_DRAIN: begin
                    if (retired_group == group_count) begin
                        if (reduce_nonfinite)
                            begin
                                refusal_stage <= SITE_REDUCE_OPERAND;
                                error_code <= ERR_OPERAND_NONFINITE;
                                state <= S_DONE;
                            end
                        else if (reduce_window)
                            begin
                                refusal_stage <= SITE_REDUCE_WINDOW;
                                error_code <= ERR_ACCUMULATE_RANGE;
                                state <= S_DONE;
                            end
                        else
                            state <= S_ROUND_DOT;
                    end
                end

                // ---- one rounding per state, one shared rounder ----------
                S_ROUND_DOT: begin
                    if (round_result[33:32] != 2'd0)
                        begin
                            refusal_stage <= SITE_DOT_ROUND;
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end
                    else begin
                        dbg_dot_code <= round_result[31:0];
                        state <= S_ROUND_NQ2;
                    end
                end

                S_ROUND_NQ2: begin
                    if (round_result[33:32] != 2'd0)
                        begin
                            refusal_stage <= SITE_NORM_ROUND;
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end
                    else begin
                        dbg_norm_q_square_code <= round_result[31:0];
                        state <= S_ROUND_NK2;
                    end
                end

                S_ROUND_NK2: begin
                    if (round_result[33:32] != 2'd0)
                        begin
                            refusal_stage <= SITE_NORM_ROUND;
                            error_code <= ERR_ACCUMULATE_RANGE;
                            state <= S_DONE;
                        end
                    else begin
                        dbg_norm_k_square_code <= round_result[31:0];
                        sqrt_issued <= 2'd0;
                        sqrt_received <= 2'd0;
                        state <= S_SQRT_NORMS;
                    end
                end

                //: The two norms are issued on CONSECUTIVE cycles through one
                //: square-root pipe: the II = 1 claim, exercised.
                S_SQRT_NORMS: begin
                    if (sqrt_issued == 2'd0) begin
                        sqrt_issued <= 2'd1;
                    end else begin
                        sqrt_issued <= 2'd2;
                        state <= S_SQRT_WAIT;
                    end
                end

                S_SQRT_WAIT: begin
                    if (sqrt_out_valid) begin
                        if (sqrt_error != 2'd0) begin
                            begin
                                refusal_stage <= SITE_NORM_SQRT;
                                error_code <= ERR_PRODUCT_RANGE;
                                state <= S_DONE;
                            end
                        end else if (sqrt_received == 2'd0) begin
                            dbg_norm_q_code <= sqrt_result;
                            sqrt_received <= 2'd1;
                        end else begin
                            dbg_norm_k_code <= sqrt_result;
                            sqrt_received <= 2'd2;
                            state <= S_DENOM;
                        end
                    end
                end

                S_DENOM: begin
                    if (denominator_product[33:32] != 2'd0) begin
                        begin
                            refusal_stage <= SITE_DENOMINATOR;
                            error_code <= ERR_PRODUCT_RANGE;
                            state <= S_DONE;
                        end
                    end else begin
                        dbg_denominator_raw_code <= denominator_product[31:0];
                        dbg_denominator_code <= clamp_active
                            ? GATE_EPSILON_CODE : denominator_product[31:0];
                        dbg_clamped <= clamp_active;
                        state <= S_DIV_REQ;
                    end
                end

                S_DIV_REQ: if (divider_in_ready) state <= S_DIV_RSP;

                S_DIV_RSP: begin
                    if (divider_out_valid) begin
                        if (divider_error != 2'd0) begin
                            begin
                                refusal_stage <= SITE_DIVIDE;
                                error_code <= ERR_PRODUCT_RANGE;
                                state <= S_DONE;
                            end
                        end else begin
                            dbg_cosine_code <= divider_result;
                            state <= S_SSQRT_ISSUE;
                        end
                    end
                end

                S_SSQRT_ISSUE: state <= S_SSQRT_WAIT;

                S_SSQRT_WAIT: begin
                    if (sqrt_out_valid) begin
                        if (sqrt_error != 2'd0) begin
                            begin
                                refusal_stage <= SITE_SIGNED_SQRT;
                                error_code <= ERR_PRODUCT_RANGE;
                                state <= S_DONE;
                            end
                        end else begin
                            //: The signed square root: magnitude from the pipe,
                            //: sign from the normalised dot, canonical +0 for a
                            //: zero root.
                            dbg_signed_sqrt_code <= (sqrt_result == 32'b0)
                                ? 32'b0
                                : {dbg_cosine_code[31], sqrt_result[30:0]};
                            state <= S_SIG_REQ;
                        end
                    end
                end

                S_SIG_REQ: if (sigmoid_in_ready) state <= S_SIG_RSP;

                S_SIG_RSP: begin
                    if (sigmoid_out_valid) begin
                        if (sigmoid_error != 2'd0) begin
                            begin
                                refusal_stage <= SITE_SIGMOID;
                                error_code <= ERR_PRODUCT_RANGE;
                                state <= S_DONE;
                            end
                        end else begin
                            dbg_gate_code <= sigmoid_result;
                            state <= S_COMBINE;
                        end
                    end
                end

                // ---- phase C --------------------------------------------
                S_COMBINE: begin
                    if (combine_issuing) begin
                        r0_rd_en <= 1'b1;
                        r1_rd_en <= 1'b1;
                        r2_rd_en <= 1'b1;
                        r0_rd_addr <=
                            base_h + (combine_issue_group << LANE_LOG);
                        r1_rd_addr <=
                            base_key + (combine_issue_group << LANE_LOG);
                        r2_rd_addr <=
                            base_value + (combine_issue_group << LANE_LOG);
                        combine_issue_group <= combine_issue_group + 32'd1;
                    end else begin
                        state <= S_COMBINE_DRAIN;
                    end
                end

                S_COMBINE_DRAIN: begin
                    if (poisoned || combine_retired_group == group_count)
                        state <= S_DONE;
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase

            // ---- phase R retirement, counted from the tree's own valid ----
            if (dot_valid) begin
                retired_group <= retired_group + 32'd1;
                reduce_count <= reduce_count + lane_population(
                    lane_mask_for(retired_group, element_count));
            end

            // ---- phase C arithmetic stages -------------------------------
            if (combine_data_valid) begin
                c1_valid <= 1'b1;
                c1_mask <= combine_data_mask;
                c1_group <= combine_data_group;
                c1_hidden <= r0_rd_data;
                for (lane = 0; lane < LANES; lane = lane + 1) begin
                    c1_product[32*lane +: 32] <= stage1_product[lane][31:0];
                    c1_range_fault[lane] <=
                        (stage1_product[lane][33:32] != 2'd0);
                    c1_operand_fault[lane] <= stage1_operand_fault[lane];
                end
            end

            if (c1_valid) begin
                c2_valid <= 1'b1;
                c2_mask <= c1_mask;
                c2_group <= c1_group;
                c2_hidden <= c1_hidden;
                c2_operand_fault <= c1_operand_fault;
                for (lane = 0; lane < LANES; lane = lane + 1) begin
                    c2_gated[32*lane +: 32] <= stage2_gated[lane][31:0];
                    c2_range_fault[lane] <= c1_range_fault[lane] ||
                        (stage2_gated[lane][33:32] != 2'd0);
                end
            end

            if (c2_valid && !poisoned) begin
                combine_retired_group <= combine_retired_group + 32'd1;
                if (retire_site != SITE_NONE) begin
                    poisoned <= 1'b1;
                    refusal_stage <= retire_site;
                    error_code <= (retire_site == SITE_COMBINE_OPERAND)
                        ? ERR_OPERAND_NONFINITE : ERR_PRODUCT_RANGE;
                end else begin
                    out_we <= c2_mask;
                    out_addr <= base_out + (c2_group << LANE_LOG);
                    for (lane = 0; lane < LANES; lane = lane + 1)
                        out_data[32*lane +: 32] <= stage3_sum[lane][31:0];
                    out_count <= out_count + lane_population(c2_mask);
                end
            end
        end
    end
endmodule
