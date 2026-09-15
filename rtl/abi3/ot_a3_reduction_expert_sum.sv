`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// REDUCTION.EXPERT_SUM -- the MoE combine, in the declared order.
//
// ``input_view_0`` is [experts, width] of contributions in ascending selected
// slot order, ``input_view_1`` an optional [experts] routing-weight vector and
// ``input_view_2`` an optional base.  The engine forms weight*contribution in
// binary32 and reduces in the profile's declared order, which is what makes a
// MoE layer's output independent of the order its experts finished in.
//
// Amendment A10 makes the weight vector optional: the released DeepSeek expert
// multiplies by its routing weight before the down projection, so an operator
// that leaves input_view_1 unbound is declaring the weight is already applied,
// and re-applying it here would square it.
//
// THE TREE IS SHAPED AT RUNTIME, NOT PADDED.  All 49 EXPERT_SUM instructions in
// deepseek-v41-flash-rom-wafer-2 declare PAIRWISE_TREE: 33 over 4 experts with
// weights, 16 over 6 with a base.  The reference folds pairs and lets an odd
// last term pass to the next level untouched.  Padding a power-of-two tree with
// +0.0 is *almost* the same number and the exception is reachable -- -0.0 + 0.0
// is +0.0, so a level whose pair sums to -0.0 meets a completed -0.0 and yields
// +0.0 where the reference yields -0.0 -- so every level carries its own term
// count and passes its own odd tail through.  Hardcoding 4 and 6 would be
// smaller and is exactly the frozen-geometry defect that froze the bridge's
// admission predicates to Qwen3's shapes, so the count is an input.
//
// A LEAF BASE RESHAPES THE TREE.  TA-ABI3-OPCONV-1 section 6 puts an optional
// base *first*, as one more leaf, and the reference prepends it -- so the tree
// then has experts+1 leaves and every level's shape moves.  The DeepSeek expert
// contract instead adds the base to the completed sum. Those are different
// numbers, not one number written twice, so the leaf count is
// ``experts + (base && !base_after_terms)`` and the tree is built one leaf wider
// than EXPERTS to hold it.
//
// FULLY PIPELINED.  One output element per cycle: the lanes read in parallel,
// weighting is one registered stage, each tree level is one more, and the
// trailing base add and the BF16 narrowing are the last two.
// ---------------------------------------------------------------------------
module ot_a3_reduction_expert_sum #(
    parameter integer EXPERTS = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [7:0]  cfg_experts,          //: 1..EXPERTS
    input  wire [31:0] cfg_count,            //: output elements = view width
    input  wire [31:0] cfg_in_base,
    input  wire [31:0] cfg_stride,           //: elements per expert row
    input  wire        cfg_has_weights,
    input  wire [31:0] cfg_weight_base,
    input  wire        cfg_has_base,
    input  wire [31:0] cfg_base_base,
    input  wire        cfg_base_after_terms,
    input  wire [31:0] cfg_out_base,

    output reg  [EXPERTS-1:0]    val_rd_en,
    output reg  [EXPERTS*32-1:0] val_rd_addr,
    input  wire [EXPERTS*32-1:0] val_rd_data,
    output reg         wgt_rd_en,
    output reg  [31:0] wgt_rd_addr,
    input  wire [31:0] wgt_rd_data,
    output reg         base_rd_en,
    output reg  [31:0] base_rd_addr,
    input  wire [31:0] base_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count
);
    // Re-declared rather than wildcard-imported: Icarus 11 turns a
    // wildcard-imported name used only in a port connection into an implicit
    // net, and the pinned Yosys 0.68 frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    //: One leaf wider than EXPERTS so a base folded in as a leaf fits.
    localparam integer LEAVES = EXPERTS + 1;
    localparam integer LEVELS = $clog2(LEAVES);
    //: Index widths for the two arrays, so a wide counter can be compared
    //: against a config field without truncating and still select cleanly.
    localparam integer EW = (EXPERTS <= 1) ? 1 : $clog2(EXPERTS);
    localparam integer LW = (LEAVES  <= 1) ? 1 : $clog2(LEAVES);

    //: Per-stage error class, carried alongside the value.
    localparam [1:0] E_OK = 2'd0, E_NONFINITE = 2'd1, E_PRODUCT = 2'd2,
                     E_ACCUM = 2'd3;

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_WEIGHT = 3'd1;
    localparam [2:0] S_WALK   = 3'd2;
    localparam [2:0] S_DRAIN  = 3'd3;
    localparam [2:0] S_DONE   = 3'd4;

    integer i, l;
    genvar  gl, gi;

    // -- the tree's shape, combinational from the run's leaf count ----------
    wire       base_is_leaf = cfg_has_base && !cfg_base_after_terms;
    wire [8:0] leaf_count = {1'b0, cfg_experts} + {8'd0, base_is_leaf};
    wire [8:0] level_count [0:LEVELS];
    assign level_count[0] = leaf_count;
    generate
        for (gl = 0; gl < LEVELS; gl = gl + 1) begin : g_shape
            assign level_count[gl+1] = (level_count[gl] + 9'd1) >> 1;
        end
    endgenerate

    reg [2:0]  state;
    reg [31:0] column;
    reg [31:0] drain;
    reg [31:0] weight [0:EXPERTS-1];
    reg [7:0]  wload;
    reg        wload_pending;
    reg [31:0] lane_addr [0:EXPERTS-1];

    //: The address register sits on the port, so an operand answers two cycles
    //: after the walk drives it: one stage to reach the memory, one to return.
    reg        a_valid, b_valid;
    reg [31:0] a_addr_out, b_addr_out;

    wire cfg_bad = (cfg_experts == 8'd0) ||
                   ({24'd0, cfg_experts} > EXPERTS[31:0]) ||
                   (cfg_count == 32'd0) ||
                   (cfg_stride == 32'd0);

    // -- the walk -----------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            column <= 32'd0;
            drain <= 32'd0;
            wload <= 8'd0;
            wload_pending <= 1'b0;
            val_rd_en <= {EXPERTS{1'b0}};
            val_rd_addr <= {(EXPERTS*32){1'b0}};
            wgt_rd_en <= 1'b0;
            wgt_rd_addr <= 32'd0;
            base_rd_en <= 1'b0;
            base_rd_addr <= 32'd0;
            a_valid <= 1'b0; b_valid <= 1'b0;
            a_addr_out <= 32'd0; b_addr_out <= 32'd0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            for (i = 0; i < EXPERTS; i = i + 1)
                lane_addr[i] <= 32'd0;
        end else begin
            val_rd_en <= {EXPERTS{1'b0}};
            wgt_rd_en <= 1'b0;
            base_rd_en <= 1'b0;
            done <= 1'b0;
            b_valid <= a_valid;
            b_addr_out <= a_addr_out;
            a_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        column <= 32'd0;
                        drain <= 32'd0;
                        wload <= 8'd0;
                        // ``i`` is constant in each unrolled iteration, so this
                        // is a constant multiply, not a datapath multiplier.
                        for (i = 0; i < EXPERTS; i = i + 1)
                            lane_addr[i] <= cfg_in_base + cfg_stride * i[31:0];
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0;
                            done <= 1'b1;
                            state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1;
                            wload_pending <= cfg_has_weights;
                            state <= cfg_has_weights ? S_WEIGHT : S_WALK;
                        end
                    end
                end
                S_WEIGHT: begin
                    if (wload_pending) begin
                        wgt_rd_en <= 1'b1;
                        wgt_rd_addr <= cfg_weight_base + {24'd0, wload};
                        if ({24'd0, wload} + 32'd1 >= {24'd0, cfg_experts})
                            wload_pending <= 1'b0;
                        else
                            wload <= wload + 8'd1;
                    end else if (drain >= 32'd2) begin
                        // The last weight read is two cycles behind its address.
                        drain <= 32'd0;
                        state <= S_WALK;
                    end else begin
                        drain <= drain + 32'd1;
                    end
                end
                S_WALK: begin
                    val_rd_en <= {EXPERTS{1'b1}};
                    for (i = 0; i < EXPERTS; i = i + 1)
                        val_rd_addr[i*32 +: 32] <= lane_addr[i] + column;
                    if (cfg_has_base) begin
                        base_rd_en <= 1'b1;
                        base_rd_addr <= cfg_base_base + column;
                    end
                    a_valid <= 1'b1;
                    a_addr_out <= cfg_out_base + column;
                    if (column + 32'd1 >= cfg_count) begin
                        drain <= 32'd0;
                        state <= S_DRAIN;
                    end else begin
                        column <= column + 32'd1;
                    end
                end
                S_DRAIN: begin
                    busy <= 1'b1;
                    // read(2) + leaf(1) + LEVELS + trailing add(1) +
                    // narrow(1) + the output register
                    if (drain >= (LEVELS[31:0] + 32'd6)) begin
                        // ONE OWNER FOR error_code.  A numeric fault is latched
                        // by the pipeline in ``first_err`` and folded in here,
                        // rather than in a second always block.  Two blocks
                        // assigning one reg lint as a mere warning and stop the
                        // ROM flow dead: "multiple conflicting drivers for
                        // ...error_code[0]", and then an internal assert in the
                        // pinned Yosys 0.68 OPT passes at 39,159 cells.
                        // Synthesis is the only place this showed up.
                        if (error_code == ERR_NONE) begin
                            case (first_err)
                                E_NONFINITE: error_code <= ERR_OPERAND_NONFINITE;
                                E_PRODUCT:   error_code <= ERR_PRODUCT_RANGE;
                                E_ACCUM:     error_code <= ERR_ACCUMULATE_RANGE;
                                default:     error_code <= ERR_NONE;
                            endcase
                        end
                        state <= S_DONE;
                    end else begin
                        drain <= drain + 32'd1;
                    end
                end
                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

    // -- the weight preamble's capture path ---------------------------------
    // Its port is registered like the operands', so the answer is two cycles
    // behind the address and the destination index has to travel with it.
    // ONE STAGE, NOT TWO.  ``wgt_rd_addr`` is registered, so it is on the port
    // the cycle after the preamble drives it and the memory answers the cycle
    // after that -- which is exactly when ``wgt_v1``, taken from ``wgt_rd_en``,
    // is high.  Capturing a stage later reads the *next* weight into this
    // index, and the testbench showed precisely that: every multi-weight case
    // wrong and the single-weight case right, because with one weight the port
    // stops changing and the late read still finds the right value.
    reg       wgt_v1;
    reg [7:0] wgt_i1;
    //: Named, not indexed in place: the pinned Yosys 0.68 Verilog frontend
    //: rejects a part-select applied to a function call ("syntax error,
    //: unexpected '['") even though Verilator accepts it, so a block that
    //: indexes decode_bf16(...) directly lints clean and then cannot be
    //: synthesised or routed at all.
    wire [33:0] wgt_decoded =
        ot_a3_format_pkg::decode_bf16(wgt_rd_data[15:0]);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wgt_v1 <= 1'b0; wgt_i1 <= 8'd0;
            for (i = 0; i < EXPERTS; i = i + 1)
                weight[i] <= 32'd0;
        end else begin
            wgt_v1 <= wgt_rd_en;
            wgt_i1 <= wgt_rd_addr[7:0] - cfg_weight_base[7:0];
            if (wgt_v1 && ({24'd0, wgt_i1} < EXPERTS[31:0]))
                weight[wgt_i1[EW-1:0]] <= wgt_decoded[31:0];
        end
    end

    // -- leaf stage: widen, weight, and place the base leaf if there is one --
    wire [33:0] decoded [0:EXPERTS-1];
    wire [33:0] product [0:EXPERTS-1];
    generate
        for (gi = 0; gi < EXPERTS; gi = gi + 1) begin : g_lane
            assign decoded[gi] =
                ot_a3_format_pkg::decode_bf16(val_rd_data[gi*32 +: 16]);
            assign product[gi] =
                ot_fp32_rne_pkg::fp32_mul_rne(decoded[gi][31:0], weight[gi]);
        end
    endgenerate
    wire [33:0] base_decoded = ot_a3_format_pkg::decode_bf16(base_rd_data[15:0]);

    //: node[0] is the leaf rank; node[l+1] is level l's output.
    reg        n_valid [0:LEVELS];
    reg [31:0] n_addr  [0:LEVELS];
    reg [31:0] n_trail [0:LEVELS];
    reg [1:0]  n_err   [0:LEVELS];
    reg [31:0] node    [0:LEVELS][0:LEAVES-1];

    //: The last active index at each level, narrowed to the array's own width.
    //: A part-select of an expression is not legal Verilog, so the subtraction
    //: gets a name.
    wire [8:0] level_last [0:LEVELS];
    wire [LW-1:0] level_last_sel [0:LEVELS];
    generate
        for (gl = 0; gl <= LEVELS; gl = gl + 1) begin : g_last
            assign level_last[gl] = level_count[gl] - 9'd1;
            assign level_last_sel[gl] = level_last[gl][LW-1:0];
        end
    endgenerate

    //: Level l's pair sums, combinational between two registered ranks.
    wire [33:0] pair [0:LEVELS-1][0:LEAVES-1];
    generate
        for (gl = 0; gl < LEVELS; gl = gl + 1) begin : g_level
            for (gi = 0; gi < LEAVES/2 + 1; gi = gi + 1) begin : g_pair
                if (2*gi + 1 < LEAVES) begin : g_real
                    assign pair[gl][gi] = ot_fp32_rne_pkg::fp32_add_rne(
                        node[gl][2*gi], node[gl][2*gi+1]);
                end else begin : g_none
                    assign pair[gl][gi] = 34'd0;
                end
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (l = 0; l <= LEVELS; l = l + 1) begin
                n_valid[l] <= 1'b0;
                n_addr[l] <= 32'd0;
                n_trail[l] <= 32'd0;
                n_err[l] <= E_OK;
                for (i = 0; i < LEAVES; i = i + 1)
                    node[l][i] <= 32'd0;
            end
        end else begin
            // -- the leaf rank ------------------------------------------------
            n_valid[0] <= b_valid;
            n_addr[0] <= b_addr_out;
            //: The trailing base, held until every level has retired.
            n_trail[0] <= (cfg_has_base && cfg_base_after_terms)
                          ? base_decoded[31:0] : 32'd0;
            n_err[0] <= E_OK;
            for (i = 0; i < LEAVES; i = i + 1)
                node[0][i] <= 32'd0;
            if (base_is_leaf)
                node[0][0] <= base_decoded[31:0];
            for (i = 0; i < EXPERTS; i = i + 1) begin
                if ({24'd0, i[7:0]} < {24'd0, cfg_experts}) begin
                    node[0][i + (base_is_leaf ? 1 : 0)] <=
                        cfg_has_weights ? product[i][31:0] : decoded[i][31:0];
                end
            end
            // One error class for the whole leaf rank: a nonfinite operand
            // outranks an overflowed product, because the product of a
            // nonfinite is not a range fault about the weighting.
            if (b_valid) begin
                n_err[0] <= E_OK;
                for (i = 0; i < EXPERTS; i = i + 1) begin
                    if ({24'd0, i[7:0]} < {24'd0, cfg_experts}) begin
                        if (decoded[i][33:32] != 2'd0)
                            n_err[0] <= E_NONFINITE;
                        else if (cfg_has_weights && product[i][33:32] != 2'd0 &&
                                 n_err[0] != E_NONFINITE)
                            n_err[0] <= E_PRODUCT;
                    end
                end
                if (cfg_has_base && base_decoded[33:32] != 2'd0)
                    n_err[0] <= E_NONFINITE;
            end

            // -- one registered rank per level --------------------------------
            for (l = 0; l < LEVELS; l = l + 1) begin
                n_valid[l+1] <= n_valid[l];
                n_addr[l+1] <= n_addr[l];
                n_trail[l+1] <= n_trail[l];
                n_err[l+1] <= n_err[l];
                for (i = 0; i < LEAVES; i = i + 1)
                    node[l+1][i] <= 32'd0;
                for (i = 0; i < LEAVES/2 + 1; i = i + 1) begin
                    if ({23'd0, i[8:0]} < {23'd0, (level_count[l] >> 1)}) begin
                        node[l+1][i] <= pair[l][i][31:0];
                        if (pair[l][i][33:32] != 2'd0 && n_err[l] == E_OK)
                            n_err[l+1] <= E_ACCUM;
                    end else if (level_count[l][0] &&
                                 ({23'd0, i[8:0]} == {23'd0, (level_count[l] >> 1)})) begin
                        // The odd tail passes through untouched; folding a
                        // +0.0 into it here is what would lose a signed zero.
                        node[l+1][i] <= node[l][level_last_sel[l]];
                    end
                end
            end
        end
    end

    // -- trailing base add, THEN, one cycle later, the narrowing ------------
    // These were one combinational stage and ASAP7 said so: the worst path ran
    // n_trail[4] -> fp32_add_rne -> fp32_to_bf16_rne -> saturation_count and
    // missed a 1.2 ns target by 5.45 ns, because a full IEEE add and a full
    // IEEE narrowing in series is roughly 6.6 ns of logic.  Each is now its own
    // stage.  The initiation interval is unchanged -- this adds one cycle of
    // latency, not one cycle per element.
    wire [33:0] with_trail = ot_fp32_rne_pkg::fp32_add_rne(
        node[LEVELS][0], n_trail[LEVELS]);

    reg        f_valid_q;
    reg [31:0] f_addr_q;
    reg [31:0] f_total_q;
    reg [1:0]  f_err_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            f_valid_q <= 1'b0;
            f_addr_q <= 32'd0;
            f_total_q <= 32'd0;
            f_err_q <= E_OK;
        end else begin
            f_valid_q <= n_valid[LEVELS];
            f_addr_q <= n_addr[LEVELS];
            f_total_q <= (n_trail[LEVELS] != 32'd0) ? with_trail[31:0]
                                                    : node[LEVELS][0];
            f_err_q <=
                (n_err[LEVELS] != E_OK) ? n_err[LEVELS]
                : ((n_trail[LEVELS] != 32'd0) && (with_trail[33:32] != 2'd0))
                  ? E_ACCUM : E_OK;
        end
    end

    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(f_total_q);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_we <= 1'b0;
            out_addr <= 32'd0;
            out_data <= 32'd0;
            out_count <= 32'd0;
            saturation_count <= 32'd0;
        end else begin
            out_we <= 1'b0;
            if (start) begin
                out_count <= 32'd0;
                saturation_count <= 32'd0;
            end else if (f_valid_q) begin
                out_we <= 1'b1;
                out_addr <= f_addr_q;
                out_data <= {16'b0, narrowed[15:0]};
                out_count <= out_count + 32'd1;
                if (narrowed[16])
                    saturation_count <= saturation_count + 32'd1;
            end
        end
    end

    //: The first error class the pipeline produced, latched for the run.
    reg [1:0] first_err;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            first_err <= E_OK;
        else if (start)
            first_err <= E_OK;
        else if (f_valid_q && first_err == E_OK) begin
            if (f_err_q != E_OK)
                first_err <= f_err_q;
            else if (narrowed[18:17] != 2'd0)
                first_err <= E_ACCUM;
        end
    end
endmodule
