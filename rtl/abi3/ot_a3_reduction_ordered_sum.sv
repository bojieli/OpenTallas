`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// REDUCTION.ORDERED_SUM -- the architectural sum, in the declared order.
//
// ``input_view_0`` is [terms, ...]; ``input_view_1`` is an optional base with
// the output's shape, which enters the sum FIRST -- it is the accumulator's
// initial value, exactly as a partial-tile accumulator would be, and
// TA-ABI3-OPCONV-1 section 6 is explicit that this is the residual convention.
//
// ONE ORDER, AND THE OTHERS REFUSED.  The reference supports three reduction
// orders.  Every ORDERED_SUM in every shipped deployment declares
// SEQUENTIAL_ASCENDING -- 5 instructions in deepseek-v4-flash-rom and 5 in
// deepseek-v4-flash-rom-array-32, all with a base and all with one term -- so
// that is what this block implements, and a profile declaring PAIRWISE_TREE or
// BLOCKED_ASCENDING is refused rather than reduced in the wrong order.  The
// pairwise tree exists in ot_a3_reduction_expert_sum, which is where the MoE
// combine needs it; building a second copy here for no shipped operator would
// be untested machinery whose only effect is to make a wrong order look right.
//
// INACTIVE STAGES PASS THROUGH, THEY DO NOT ADD ZERO.  The accumulator is a
// chain of MAX_TERMS registered adders so the initiation interval is 1 for any
// term count.  A stage past the run's term count forwards its input unchanged
// instead of adding +0.0: -0.0 + 0.0 is +0.0, so a padded stage can turn a
// negative zero into a positive one and disagree with the reference on a value
// it is supposed to reproduce exactly.
// ---------------------------------------------------------------------------
module ot_a3_reduction_ordered_sum #(
    parameter integer MAX_TERMS = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [7:0]  cfg_terms,            //: 1..MAX_TERMS
    input  wire [31:0] cfg_count,            //: output elements
    input  wire [31:0] cfg_in_base,
    input  wire [31:0] cfg_stride,           //: elements between terms
    input  wire        cfg_has_base,
    input  wire [31:0] cfg_base_base,
    //: The profile's declared order; only SEQUENTIAL_ASCENDING is admitted.
    input  wire [7:0]  cfg_reduction_order,
    input  wire [31:0] cfg_out_base,

    output reg  [MAX_TERMS-1:0]    val_rd_en,
    output reg  [MAX_TERMS*32-1:0] val_rd_addr,
    input  wire [MAX_TERMS*32-1:0] val_rd_data,
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
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    //: runtime.abi3.constants.ReductionOrder.SEQUENTIAL_ASCENDING
    localparam [7:0] ORDER_SEQUENTIAL_ASCENDING = 8'd0;

    localparam [1:0] E_OK = 2'd0, E_NONFINITE = 2'd1, E_ACCUM = 2'd3;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_WALK  = 3'd1;
    localparam [2:0] S_DRAIN = 3'd2;
    localparam [2:0] S_DONE  = 3'd3;

    integer i, k;
    genvar  gk;

    reg [2:0]  state;
    reg [31:0] column;
    reg [31:0] drain;
    reg [31:0] lane_addr [0:MAX_TERMS-1];
    reg        a_valid, b_valid;
    reg [31:0] a_addr_out, b_addr_out;

    wire cfg_bad = (cfg_terms == 8'd0) ||
                   ({24'd0, cfg_terms} > MAX_TERMS[31:0]) ||
                   (cfg_count == 32'd0) ||
                   (cfg_stride == 32'd0) ||
                   (cfg_reduction_order != ORDER_SEQUENTIAL_ASCENDING);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            column <= 32'd0;
            drain <= 32'd0;
            val_rd_en <= {MAX_TERMS{1'b0}};
            val_rd_addr <= {(MAX_TERMS*32){1'b0}};
            base_rd_en <= 1'b0;
            base_rd_addr <= 32'd0;
            a_valid <= 1'b0; b_valid <= 1'b0;
            a_addr_out <= 32'd0; b_addr_out <= 32'd0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            for (i = 0; i < MAX_TERMS; i = i + 1)
                lane_addr[i] <= 32'd0;
        end else begin
            val_rd_en <= {MAX_TERMS{1'b0}};
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
                        // ``i`` is constant per unrolled iteration, so this is a
                        // constant multiply rather than a datapath multiplier.
                        for (i = 0; i < MAX_TERMS; i = i + 1)
                            lane_addr[i] <= cfg_in_base + cfg_stride * i[31:0];
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0;
                            done <= 1'b1;
                            state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1;
                            state <= S_WALK;
                        end
                    end
                end
                S_WALK: begin
                    val_rd_en <= {MAX_TERMS{1'b1}};
                    for (i = 0; i < MAX_TERMS; i = i + 1)
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
                    // read(2) + seed(1) + MAX_TERMS stages + narrow(1)
                    if (drain >= (MAX_TERMS[31:0] + 32'd4)) begin
                        // ONE OWNER for error_code: the pipeline latches its
                        // first numeric fault and it is folded in here, because
                        // a second always block assigning the same reg lints as
                        // a warning and then stops the ROM flow dead.
                        if (error_code == ERR_NONE) begin
                            case (first_err)
                                E_NONFINITE: error_code <= ERR_OPERAND_NONFINITE;
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

    // -- widen, then seed the accumulator ------------------------------------
    wire [33:0] decoded [0:MAX_TERMS-1];
    generate
        for (gk = 0; gk < MAX_TERMS; gk = gk + 1) begin : g_lane
            assign decoded[gk] =
                ot_a3_format_pkg::decode_bf16(val_rd_data[gk*32 +: 16]);
        end
    endgenerate
    wire [33:0] base_decoded = ot_a3_format_pkg::decode_bf16(base_rd_data[15:0]);

    //: acc[0] is the seed; acc[k+1] is stage k's output.
    reg        acc_valid [0:MAX_TERMS];
    reg [31:0] acc_addr  [0:MAX_TERMS];
    reg [31:0] acc       [0:MAX_TERMS];
    reg [1:0]  acc_err   [0:MAX_TERMS];
    //: Each stage needs the term it adds, so the whole widened rank travels.
    reg [31:0] term      [0:MAX_TERMS][0:MAX_TERMS-1];
    reg [1:0]  term_err  [0:MAX_TERMS][0:MAX_TERMS-1];
    reg [7:0]  acc_terms [0:MAX_TERMS];
    reg        acc_based [0:MAX_TERMS];

    wire [33:0] stage_sum [0:MAX_TERMS-1];
    generate
        for (gk = 0; gk < MAX_TERMS; gk = gk + 1) begin : g_stage
            assign stage_sum[gk] =
                ot_fp32_rne_pkg::fp32_add_rne(acc[gk], term[gk][gk]);
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k <= MAX_TERMS; k = k + 1) begin
                acc_valid[k] <= 1'b0;
                acc_addr[k] <= 32'd0;
                acc[k] <= 32'd0;
                acc_err[k] <= E_OK;
                acc_terms[k] <= 8'd0;
                acc_based[k] <= 1'b0;
                for (i = 0; i < MAX_TERMS; i = i + 1) begin
                    term[k][i] <= 32'd0;
                    term_err[k][i] <= E_OK;
                end
            end
        end else begin
            // -- the seed: the base if there is one, else term 0 -------------
            acc_valid[0] <= b_valid;
            acc_addr[0] <= b_addr_out;
            acc_terms[0] <= cfg_terms;
            acc_based[0] <= cfg_has_base;
            acc[0] <= cfg_has_base ? base_decoded[31:0] : decoded[0][31:0];
            acc_err[0] <= (cfg_has_base && base_decoded[33:32] != 2'd0) ? E_NONFINITE
                        : ((!cfg_has_base && decoded[0][33:32] != 2'd0) ? E_NONFINITE
                        : E_OK);
            for (i = 0; i < MAX_TERMS; i = i + 1) begin
                term[0][i] <= decoded[i][31:0];
                term_err[0][i] <= (decoded[i][33:32] != 2'd0) ? E_NONFINITE : E_OK;
            end

            // -- one registered adder per term --------------------------------
            for (k = 0; k < MAX_TERMS; k = k + 1) begin
                acc_valid[k+1] <= acc_valid[k];
                acc_addr[k+1] <= acc_addr[k];
                acc_terms[k+1] <= acc_terms[k];
                acc_based[k+1] <= acc_based[k];
                for (i = 0; i < MAX_TERMS; i = i + 1) begin
                    term[k+1][i] <= term[k][i];
                    term_err[k+1][i] <= term_err[k][i];
                end
                // Stage k adds term k -- except term 0 when there is no base,
                // which already seeded the accumulator; and except any stage at
                // or past the run's term count, which forwards unchanged.
                if ((!acc_based[k] && (k == 0)) ||
                    ({24'd0, k[7:0]} >= {24'd0, acc_terms[k]})) begin
                    acc[k+1] <= acc[k];
                    acc_err[k+1] <= acc_err[k];
                end else begin
                    acc[k+1] <= stage_sum[k][31:0];
                    acc_err[k+1] <=
                        (acc_err[k] != E_OK) ? acc_err[k]
                        : (term_err[k][k] != E_OK) ? term_err[k][k]
                        : (stage_sum[k][33:32] != 2'd0) ? E_ACCUM : E_OK;
                end
            end
        end
    end

    // -- one narrowing at the output ----------------------------------------
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(acc[MAX_TERMS]);

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
            end else if (acc_valid[MAX_TERMS]) begin
                out_we <= 1'b1;
                out_addr <= acc_addr[MAX_TERMS];
                out_data <= {16'b0, narrowed[15:0]};
                out_count <= out_count + 32'd1;
                if (narrowed[16])
                    saturation_count <= saturation_count + 32'd1;
            end
        end
    end

    //: The first numeric fault the pipeline produced, latched for the run.
    reg [1:0] first_err;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            first_err <= E_OK;
        else if (start)
            first_err <= E_OK;
        else if (acc_valid[MAX_TERMS] && first_err == E_OK) begin
            if (acc_err[MAX_TERMS] != E_OK)
                first_err <= acc_err[MAX_TERMS];
            else if (narrowed[18:17] != 2'd0)
                first_err <= E_ACCUM;
        end
    end
endmodule
