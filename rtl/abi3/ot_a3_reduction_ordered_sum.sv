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
// THE ACCUMULATOR IS THE QUALIFIED PIPELINED MAC, NOT A COMBINATIONAL ADD.
// Built first on ot_fp32_rne_pkg::fp32_add_rne -- one call per stage, which
// looks like one adder -- it closed at 155.3 MHz on ASAP7, missing 1.5 ns by
// 4.94 ns, and the path report named exactly one combinational binary32 add:
// term[63] -> fp32_add_rne -> acc[8].  That function is about 6.4 ns of logic.
// ot_mac_bf16_fp32_pipe is the same arithmetic in five balanced stages at one
// result per cycle, and it is qualified bit-identical to
// bf16_bf16_fp32_product_add_rne over 901,440 cases, so the chain is built out
// of it: stage k computes RN(term_k * 1.0 + acc), which is RN(term_k + acc)
// because the product is exact.
//
// AND AN INACTIVE STAGE ADDS MINUS ZERO, WHICH IS THE IDENTITY.  A stage past
// the run's term count must not change the accumulator.  Feeding +0.0 is
// almost right: (+0.0) + (-0.0) is +0.0 under RNE, so a padded stage turns a
// negative zero positive.  Feeding -0.0 is exact for every finite accumulator
// including both signed zeros -- (-0.0) + (-0.0) = -0.0 and (-0.0) + (+0.0) =
// +0.0 -- so every stage stays identical and no bypass path is needed.
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
                    // read(2) + seed(1) + MAC_LAT per stage + narrow(1) + out(1)
                    if (drain >= (MAC_LAT[31:0] * MAX_TERMS[31:0] + 32'd5)) begin
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

    // -- widen, seed, then the MAC chain ------------------------------------
    //: The MAC's own latency; its valid_in reaches valid_out through s1..s4.
    localparam integer MAC_LAT = 5;
    //: BF16 +1.0 and BF16 -0.0.
    localparam [15:0] BF16_ONE = 16'h3F80;
    localparam [15:0] BF16_NEG_ZERO = 16'h8000;

    wire [33:0] decoded [0:MAX_TERMS-1];
    generate
        for (gk = 0; gk < MAX_TERMS; gk = gk + 1) begin : g_lane
            assign decoded[gk] =
                ot_a3_format_pkg::decode_bf16(val_rd_data[gk*32 +: 16]);
        end
    endgenerate
    wire [33:0] base_decoded = ot_a3_format_pkg::decode_bf16(base_rd_data[15:0]);

    //: Stage k is fed MAC_LAT*k cycles after the seed, so lane k's BF16 code is
    //: delayed by exactly that much.  Staggering the reads instead would save
    //: these registers and couple every lane's address counter to the MAC's
    //: latency; 16 bits per cycle of delay is the cheaper coupling.
    localparam integer TERM_DELAY = MAC_LAT * MAX_TERMS;
    reg [15:0] term_delay [0:MAX_TERMS-1][0:TERM_DELAY];
    reg [1:0]  term_derr  [0:MAX_TERMS-1][0:TERM_DELAY];

    //: The seed: the base if there is one, else term 0.
    reg        seed_valid;
    reg [31:0] seed_acc;
    reg [1:0]  seed_err;
    reg [7:0]  seed_terms;
    reg        seed_based;

    //: One addr per element in flight, aligned to the chain's total latency.
    //: An element's address enters at ``addr_pipe[0]`` on the same cycle the
    //: seed takes it, so it sits at ``addr_pipe[MAC_LAT*MAX_TERMS]`` exactly
    //: when the last stage's ``valid_out`` presents that element's result.
    //: Indexing one shallower writes every value to its successor's address,
    //: which is what the first run of the testbench showed: all seven values
    //: right and all seven addresses off by one.
    localparam integer ADDR_DEPTH = MAC_LAT * MAX_TERMS;
    reg [31:0] addr_pipe [0:ADDR_DEPTH];
    reg [1:0]  err_pipe  [0:ADDR_DEPTH];

    integer d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            seed_valid <= 1'b0;
            seed_acc <= 32'd0;
            seed_err <= E_OK;
            seed_terms <= 8'd0;
            seed_based <= 1'b0;
            for (k = 0; k < MAX_TERMS; k = k + 1)
                for (d = 0; d <= TERM_DELAY; d = d + 1) begin
                    term_delay[k][d] <= 16'd0;
                    term_derr[k][d] <= E_OK;
                end
            for (d = 0; d <= ADDR_DEPTH; d = d + 1) begin
                addr_pipe[d] <= 32'd0;
                err_pipe[d] <= E_OK;
            end
        end else begin
            seed_valid <= b_valid;
            seed_terms <= cfg_terms;
            seed_based <= cfg_has_base;
            seed_acc <= cfg_has_base ? base_decoded[31:0] : decoded[0][31:0];
            seed_err <= (cfg_has_base && base_decoded[33:32] != 2'd0) ? E_NONFINITE
                      : ((!cfg_has_base && decoded[0][33:32] != 2'd0) ? E_NONFINITE
                      : E_OK);
            for (k = 0; k < MAX_TERMS; k = k + 1) begin
                term_delay[k][0] <= val_rd_data[k*32 +: 16];
                term_derr[k][0] <= (decoded[k][33:32] != 2'd0) ? E_NONFINITE : E_OK;
                for (d = 0; d < TERM_DELAY; d = d + 1) begin
                    term_delay[k][d+1] <= term_delay[k][d];
                    term_derr[k][d+1] <= term_derr[k][d];
                end
            end
            addr_pipe[0] <= b_addr_out;
            err_pipe[0] <= E_OK;
            for (d = 0; d < ADDR_DEPTH; d = d + 1) begin
                addr_pipe[d+1] <= addr_pipe[d];
                err_pipe[d+1] <= err_pipe[d];
            end
        end
    end

    //: The chain.  Stage k's accumulator input is stage k-1's output, and its
    //: valid follows the same path, so the whole thing is one long pipeline
    //: with an initiation interval of 1.
    wire [31:0] mac_y     [0:MAX_TERMS-1];
    wire [1:0]  mac_err   [0:MAX_TERMS-1];
    wire        mac_valid [0:MAX_TERMS-1];
    wire [31:0] mac_c     [0:MAX_TERMS-1];
    wire        mac_vin   [0:MAX_TERMS-1];
    wire [15:0] mac_a     [0:MAX_TERMS-1];

    generate
        for (gk = 0; gk < MAX_TERMS; gk = gk + 1) begin : g_mac
            //: Stage 0 adds term 0 only when a base seeded the accumulator;
            //: without a base term 0 *is* the seed and must not be added twice.
            wire stage_active = ({24'd0, gk[7:0]} < {24'd0, seed_terms}) &&
                                !((gk == 0) && !seed_based);
            assign mac_a[gk] = stage_active
                             ? term_delay[gk][MAC_LAT*gk]
                             : BF16_NEG_ZERO;
            assign mac_c[gk] = (gk == 0) ? seed_acc : mac_y[gk-1];
            assign mac_vin[gk] = (gk == 0) ? seed_valid : mac_valid[gk-1];
            ot_mac_bf16_fp32_pipe stage (
                .clk(clk),
                .rst_n(rst_n),
                .valid_in(mac_vin[gk]),
                .a(mac_a[gk]),
                .b(BF16_ONE),
                .c(mac_c[gk]),
                .y(mac_y[gk]),
                .err(mac_err[gk]),
                .valid_out(mac_valid[gk])
            );
        end
    endgenerate

    //: Any stage's range fault, and any operand's nonfiniteness, latched for
    //: the element as it leaves the chain.
    wire chain_err_any = (mac_err[MAX_TERMS-1] != 2'd0);

    // -- one narrowing at the output ----------------------------------------
    wire [18:0] narrowed =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(mac_y[MAX_TERMS-1]);

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
            end else if (mac_valid[MAX_TERMS-1]) begin
                out_we <= 1'b1;
                out_addr <= addr_pipe[ADDR_DEPTH];
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
        else if (mac_valid[MAX_TERMS-1] && first_err == E_OK) begin
            if (seed_err != E_OK)
                first_err <= seed_err;
            else if (chain_err_any)
                first_err <= E_ACCUM;
            else if (narrowed[18:17] != 2'd0)
                first_err <= E_ACCUM;
        end
    end
endmodule
