`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The ABI 3.0 engine datapaths, behind one dispatch.
//
// W8.1 and W8.2 built the control plane -- the microsequencer, the queue, the
// event scoreboard and the state controller -- and W8.6 correlated it against
// the functional simulator over sixty-four generated programs.  That campaign
// deliberately stubbed every engine, so what it proved is that the *sequence*
// is right.  This block is the other half: given the operation the sequencer
// issued and the operand views it resolved, does the arithmetic produce the
// same bytes the functional simulator produced?
//
// Four families are implemented, chosen because each is a place where being
// wrong changes a published result rather than a cycle count:
//
//   TENSOR.MATMUL      every contraction in both models
//   DMA.GATHER/SCATTER every weight and every KV byte that moves
//   VECTOR.ADD         the residual, at every layer boundary
//   SELECTION.ARGMAX   the token itself
//
// Dispatch is fail-closed: a (family, subopcode) pair this block does not
// implement raises ERR_SHAPE and executes nothing, rather than falling through
// to whichever datapath happened to be wired up.
// ---------------------------------------------------------------------------
module ot_a3_engine_array (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [7:0]  cfg_family,
    input  wire [7:0]  cfg_sub,
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,
    input  wire [15:0] cfg_depth,
    input  wire [31:0] cfg_count,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [31:0] cfg_a_base,
    input  wire [31:0] cfg_b_base,
    input  wire [31:0] cfg_c_base,
    input  wire [31:0] cfg_out_base,
    input  wire        cfg_scale_a,
    input  wire        cfg_scale_b,
    input  wire [15:0] cfg_block_a,
    input  wire [15:0] cfg_block_b,
    input  wire [15:0] cfg_block_rows_a,
    input  wire [15:0] cfg_block_rows_b,
    input  wire [31:0] cfg_scale_a_base,
    input  wire [31:0] cfg_scale_b_base,
    input  wire [31:0] cfg_slots,
    input  wire [31:0] cfg_trailing,
    input  wire [31:0] cfg_extent,

    // operand image ports -- one element per 32-bit word, one cycle latency
    output wire        m0_rd_en,
    output wire [31:0] m0_rd_addr,
    input  wire [31:0] m0_rd_data,
    output wire        m1_rd_en,
    output wire [31:0] m1_rd_addr,
    input  wire [31:0] m1_rd_data,
    output wire        m2_rd_en,
    output wire [31:0] m2_rd_addr,
    input  wire [31:0] m2_rd_data,
    output wire        m3_rd_en,
    output wire [31:0] m3_rd_addr,
    input  wire [31:0] m3_rd_data,

    output wire        out_we,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,

    output wire        busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] result_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] work_count,
    output reg  [31:0] token,
    output reg  [31:0] tie_multiplicity
);
    // Package constants are re-declared as local parameters and never pulled
    // in with a wildcard import.  Under Icarus 11, a wildcard-imported
    // identifier that appears only inside a module-instance port-connection
    // expression is not resolved against the import: Icarus creates an
    // implicit one-bit net of that name instead, and the net then shadows the
    // constant for the whole module.  ``DMA_SCATTER`` read as z, every scatter
    // dispatched as unimplemented, and ``DMA_GATHER`` -- which never appeared
    // in a port connection -- kept working, so three of twenty-nine cases
    // failed and the rest passed.  Verilator resolved the constant correctly;
    // the two-simulator rule is the only reason the disagreement was visible.
    // The pinned Yosys 0.68 frontend rejects ``import`` outright, so the same
    // change is what makes this block synthesisable at all.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SELECT_NONFINITE = ot_a3_engine_pkg::ERR_SELECT_NONFINITE;
    localparam [7:0] ERR_SCALE_RANGE = ot_a3_engine_pkg::ERR_SCALE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;
    localparam [7:0] FAMILY_DMA = ot_a3_engine_pkg::FAMILY_DMA;
    localparam [7:0] FAMILY_TENSOR = ot_a3_engine_pkg::FAMILY_TENSOR;
    localparam [7:0] FAMILY_VECTOR = ot_a3_engine_pkg::FAMILY_VECTOR;
    localparam [7:0] FAMILY_SELECTION = ot_a3_engine_pkg::FAMILY_SELECTION;
    localparam [7:0] DMA_GATHER = ot_a3_engine_pkg::DMA_GATHER;
    localparam [7:0] DMA_SCATTER = ot_a3_engine_pkg::DMA_SCATTER;
    localparam [7:0] TENSOR_MATMUL = ot_a3_engine_pkg::TENSOR_MATMUL;
    localparam [7:0] VECTOR_ADD = ot_a3_engine_pkg::VECTOR_ADD;
    localparam [7:0] SELECTION_ARGMAX = ot_a3_engine_pkg::SELECTION_ARGMAX;

    wire dma_is_scatter = (cfg_sub == DMA_SCATTER);

    wire select_mac = (cfg_family == FAMILY_TENSOR) && (cfg_sub == TENSOR_MATMUL);
    wire select_sel = (cfg_family == FAMILY_SELECTION) &&
                      (cfg_sub == SELECTION_ARGMAX);
    wire select_dma = (cfg_family == FAMILY_DMA) &&
                      ((cfg_sub == DMA_GATHER) || dma_is_scatter);
    wire select_add = (cfg_family == FAMILY_VECTOR) && (cfg_sub == VECTOR_ADD);
    wire implemented = select_mac | select_sel | select_dma | select_add;

    // -- TENSOR.MATMUL ---------------------------------------------------
    wire        mac_a_en, mac_b_en, mac_s_en, mac_t_en, mac_we, mac_busy, mac_done;
    wire [31:0] mac_a_addr, mac_b_addr, mac_s_addr, mac_t_addr;
    wire [31:0] mac_addr, mac_data, mac_out_count, mac_sat, mac_macs;
    wire [7:0]  mac_error;

    ot_a3_mac_lane mac (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_mac),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(cfg_block_rows_b),
        .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(cfg_scale_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(mac_a_en), .a_rd_addr(mac_a_addr), .a_rd_data(m0_rd_data),
        .b_rd_en(mac_b_en), .b_rd_addr(mac_b_addr), .b_rd_data(m1_rd_data),
        .s_rd_en(mac_s_en), .s_rd_addr(mac_s_addr), .s_rd_data(m2_rd_data),
        .t_rd_en(mac_t_en), .t_rd_addr(mac_t_addr), .t_rd_data(m3_rd_data),
        .out_we(mac_we), .out_addr(mac_addr), .out_data(mac_data),
        .busy(mac_busy), .done(mac_done), .error_code(mac_error),
        .out_count(mac_out_count), .saturation_count(mac_sat),
        .mac_count(mac_macs)
    );

    // -- SELECTION.ARGMAX ------------------------------------------------
    wire        sel_a_en, sel_we, sel_busy, sel_done;
    wire [31:0] sel_a_addr, sel_addr, sel_data, sel_token, sel_ties, sel_read;
    wire [7:0]  sel_error;

    ot_a3_selection_argmax selection (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_sel),
        .cfg_count(cfg_count), .cfg_dtype(cfg_dtype_a),
        .cfg_in_base(cfg_a_base), .cfg_out_base(cfg_out_base),
        .a_rd_en(sel_a_en), .a_rd_addr(sel_a_addr), .a_rd_data(m0_rd_data),
        .out_we(sel_we), .out_addr(sel_addr), .out_data(sel_data),
        .busy(sel_busy), .done(sel_done), .error_code(sel_error),
        .token(sel_token), .tie_multiplicity(sel_ties),
        .elements_read(sel_read)
    );

    // -- DMA.GATHER and DMA.SCATTER --------------------------------------
    wire        dma_idx_en, dma_src_en, dma_we, dma_busy, dma_done;
    wire [31:0] dma_idx_addr, dma_src_addr, dma_addr, dma_data;
    wire [31:0] dma_moved, dma_checked;
    wire [7:0]  dma_error;

    ot_a3_dma_index_mover mover (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_dma),
        .cfg_scatter(dma_is_scatter),
        .cfg_slots(cfg_slots), .cfg_trailing(cfg_trailing),
        .cfg_rows(cfg_extent),
        .cfg_index_base(cfg_a_base), .cfg_source_base(cfg_b_base),
        .cfg_prior_base(cfg_c_base), .cfg_out_base(cfg_out_base),
        .idx_rd_en(dma_idx_en), .idx_rd_addr(dma_idx_addr),
        .idx_rd_data(m0_rd_data),
        .src_rd_en(dma_src_en), .src_rd_addr(dma_src_addr),
        .src_rd_data(m1_rd_data),
        .out_we(dma_we), .out_addr(dma_addr), .out_data(dma_data),
        .busy(dma_busy), .done(dma_done), .error_code(dma_error),
        .moved_elements(dma_moved), .indices_checked(dma_checked)
    );

    // -- VECTOR.ADD ------------------------------------------------------
    wire        add_a_en, add_b_en, add_we, add_busy, add_done;
    wire [31:0] add_a_addr, add_b_addr, add_addr, add_data;
    wire [31:0] add_out_count, add_sat;
    wire [7:0]  add_error;

    ot_a3_vector_add adder (
        .clk(clk), .rst_n(rst_n),
        .start(start & select_add),
        .cfg_count(cfg_count),
        .cfg_left_base(cfg_a_base), .cfg_right_base(cfg_b_base),
        .cfg_out_base(cfg_out_base),
        .a_rd_en(add_a_en), .a_rd_addr(add_a_addr), .a_rd_data(m0_rd_data),
        .b_rd_en(add_b_en), .b_rd_addr(add_b_addr), .b_rd_data(m1_rd_data),
        .out_we(add_we), .out_addr(add_addr), .out_data(add_data),
        .busy(add_busy), .done(add_done), .error_code(add_error),
        .out_count(add_out_count), .saturation_count(add_sat)
    );

    // -- operand and result port arbitration -----------------------------
    assign m0_rd_en = mac_a_en | sel_a_en | dma_idx_en | add_a_en;
    assign m0_rd_addr = select_mac ? mac_a_addr
                      : select_sel ? sel_a_addr
                      : select_dma ? dma_idx_addr
                      : add_a_addr;
    assign m1_rd_en = mac_b_en | dma_src_en | add_b_en;
    assign m1_rd_addr = select_mac ? mac_b_addr
                      : select_dma ? dma_src_addr
                      : add_b_addr;
    assign m2_rd_en = mac_s_en;
    assign m2_rd_addr = mac_s_addr;
    assign m3_rd_en = mac_t_en;
    assign m3_rd_addr = mac_t_addr;

    assign out_we = mac_we | sel_we | dma_we | add_we;
    assign out_addr = select_mac ? mac_addr
                    : select_sel ? sel_addr
                    : select_dma ? dma_addr
                    : add_addr;
    assign out_data = select_mac ? mac_data
                    : select_sel ? sel_data
                    : select_dma ? dma_data
                    : add_data;
    assign busy = mac_busy | sel_busy | dma_busy | add_busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            done <= 1'b0;
            error_code <= ERR_NONE;
            result_count <= 32'b0;
            saturation_count <= 32'b0;
            work_count <= 32'b0;
            token <= 32'b0;
            tie_multiplicity <= 32'b0;
        end else begin
            done <= 1'b0;
            if (start && !implemented) begin
                // Fail closed on an operation this array does not implement.
                error_code <= ERR_SHAPE;
                result_count <= 32'b0;
                saturation_count <= 32'b0;
                work_count <= 32'b0;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (mac_done) begin
                error_code <= mac_error;
                result_count <= mac_out_count;
                saturation_count <= mac_sat;
                work_count <= mac_macs;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (sel_done) begin
                error_code <= sel_error;
                result_count <= (sel_error == ERR_NONE) ? 32'd1 : 32'd0;
                saturation_count <= 32'b0;
                work_count <= sel_read;
                token <= sel_token;
                tie_multiplicity <= sel_ties;
                done <= 1'b1;
            end else if (dma_done) begin
                error_code <= dma_error;
                result_count <= dma_moved;
                saturation_count <= 32'b0;
                work_count <= dma_checked;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end else if (add_done) begin
                error_code <= add_error;
                result_count <= add_out_count;
                saturation_count <= add_sat;
                work_count <= add_out_count;
                token <= 32'b0;
                tie_multiplicity <= 32'b0;
                done <= 1'b1;
            end
        end
    end
endmodule
