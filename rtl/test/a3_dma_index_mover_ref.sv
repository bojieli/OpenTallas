`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DMA.GATHER and DMA.SCATTER -- the datapath every weight byte and every KV
// byte crosses.  It moves *codes*, never values: a storage conversion is an
// explicit VECTOR.CONVERT, so this block never decodes an element.
//
// Two properties are the whole point of correlating it, and both are places a
// functional model and hardware normally start to disagree quietly:
//
//   * an index outside the extent it addresses is a fault, not a value to be
//     clamped or wrapped.  Every index is validated in a first pass, before
//     any element moves, so a refused transfer leaves no partial result -- the
//     same fail-closed order the functional engine takes, which range-checks
//     the whole index vector before it gathers.
//
//   * scatter applies slots in ascending slot order, so a repeated index
//     resolves deterministically to the last write, and rows no index names
//     keep their prior contents.  The destination is therefore read back
//     first, exactly as the functional engine does.
//
// Element width does not appear here.  Both operand images carry one element
// per 32-bit word, so a move is a word copy whatever the storage format is.
// ---------------------------------------------------------------------------
module ot_a3_dma_index_mover_ref (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire        cfg_scatter,      // 0 = GATHER, 1 = SCATTER
    input  wire [31:0] cfg_slots,        // index count
    input  wire [31:0] cfg_trailing,     // elements per addressed row
    input  wire [31:0] cfg_rows,         // extent the indices address
    input  wire [31:0] cfg_index_base,   // in the index image
    input  wire [31:0] cfg_source_base,  // gather: source rows; scatter: values
    input  wire [31:0] cfg_prior_base,   // scatter: destination's prior contents
    input  wire [31:0] cfg_out_base,

    output reg         idx_rd_en,
    output reg  [31:0] idx_rd_addr,
    input  wire [31:0] idx_rd_data,
    output reg         src_rd_en,
    output reg  [31:0] src_rd_addr,
    input  wire [31:0] src_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] moved_elements,
    output reg  [31:0] indices_checked
);
    // Package constants are re-declared as local parameters, and package
    // functions are called through their scope, rather than being pulled in
    // with a wildcard import.  Two reasons, both found the hard way.  Icarus 11
    // does not resolve a wildcard-imported identifier that appears only inside
    // a module-instance port connection -- it silently creates an implicit net
    // of that name, which then shadows the constant for the whole module.  And
    // the pinned Yosys 0.68 Verilog frontend rejects ``import`` outright, in
    // the header and in the body, so a wildcard import is a block that cannot
    // be synthesised or routed at all.
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_PRODUCT_RANGE = ot_a3_engine_pkg::ERR_PRODUCT_RANGE;
    localparam [7:0] ERR_ACCUMULATE_RANGE = ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SELECT_NONFINITE = ot_a3_engine_pkg::ERR_SELECT_NONFINITE;
    localparam [7:0] ERR_SCALE_RANGE = ot_a3_engine_pkg::ERR_SCALE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [3:0] S_IDLE        = 4'd0;
    localparam [3:0] S_CHECK_ISSUE = 4'd1;
    localparam [3:0] S_CHECK       = 4'd2;
    localparam [3:0] S_PRIOR_ISSUE = 4'd3;
    localparam [3:0] S_PRIOR       = 4'd4;
    localparam [3:0] S_SLOT_ISSUE  = 4'd5;
    localparam [3:0] S_SLOT        = 4'd6;
    localparam [3:0] S_MOVE_ISSUE  = 4'd7;
    localparam [3:0] S_MOVE        = 4'd8;
    localparam [3:0] S_DONE        = 4'd9;
    // The index and payload memories answer one cycle after the address is
    // driven, so every issue state parks here for exactly one cycle and
    // resumes at the state it recorded.
    localparam [3:0] S_WAIT        = 4'd10;

    reg [3:0]  state;
    reg [31:0] slot;
    reg [31:0] element;
    reg [31:0] cursor;
    reg [31:0] row_index;
    reg [3:0]  wait_next;

    wire [63:0] prior_span = {32'b0, cfg_rows} * {32'b0, cfg_trailing};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            moved_elements <= 32'b0;
            indices_checked <= 32'b0;
            idx_rd_en <= 1'b0;
            idx_rd_addr <= 32'b0;
            src_rd_en <= 1'b0;
            src_rd_addr <= 32'b0;
            out_we <= 1'b0;
            out_addr <= 32'b0;
            out_data <= 32'b0;
            slot <= 32'b0;
            element <= 32'b0;
            cursor <= 32'b0;
            row_index <= 32'b0;
            wait_next <= S_IDLE;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            idx_rd_en <= 1'b0;
            src_rd_en <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        moved_elements <= 32'b0;
                        indices_checked <= 32'b0;
                        slot <= 32'b0;
                        element <= 32'b0;
                        cursor <= 32'b0;
                        row_index <= 32'b0;
                        if ((cfg_trailing == 32'b0) || (cfg_rows == 32'b0)) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else if (cfg_slots == 32'b0) begin
                            // An empty index vector moves nothing.  A scatter
                            // still republishes the destination's prior rows.
                            state <= cfg_scatter ? S_PRIOR_ISSUE : S_DONE;
                        end else begin
                            state <= S_CHECK_ISSUE;
                        end
                    end
                end

                // -- pass one: validate every index before anything moves ----
                S_CHECK_ISSUE: begin
                    idx_rd_en <= 1'b1;
                    idx_rd_addr <= cfg_index_base + slot;
                    wait_next <= S_CHECK;
                    state <= S_WAIT;
                end

                S_CHECK: begin
                    indices_checked <= indices_checked + 32'd1;
                    if (idx_rd_data >= cfg_rows) begin
                        error_code <= ERR_INDEX_RANGE;
                        state <= S_DONE;
                    end else if (slot + 32'd1 == cfg_slots) begin
                        slot <= 32'b0;
                        state <= cfg_scatter ? S_PRIOR_ISSUE : S_SLOT_ISSUE;
                    end else begin
                        slot <= slot + 32'd1;
                        state <= S_CHECK_ISSUE;
                    end
                end

                // -- scatter pass two: republish the destination unchanged ---
                S_PRIOR_ISSUE: begin
                    src_rd_en <= 1'b1;
                    src_rd_addr <= cfg_prior_base + cursor;
                    wait_next <= S_PRIOR;
                    state <= S_WAIT;
                end

                S_PRIOR: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_out_base + cursor;
                    out_data <= src_rd_data;
                    if ({32'b0, cursor} + 64'd1 == prior_span) begin
                        cursor <= 32'b0;
                        state <= (cfg_slots == 32'b0) ? S_DONE : S_SLOT_ISSUE;
                    end else begin
                        cursor <= cursor + 32'd1;
                        state <= S_PRIOR_ISSUE;
                    end
                end

                // -- pass three: one slot at a time, in ascending slot order -
                S_SLOT_ISSUE: begin
                    idx_rd_en <= 1'b1;
                    idx_rd_addr <= cfg_index_base + slot;
                    wait_next <= S_SLOT;
                    state <= S_WAIT;
                end

                S_SLOT: begin
                    row_index <= idx_rd_data;
                    element <= 32'b0;
                    state <= S_MOVE_ISSUE;
                end

                S_MOVE_ISSUE: begin
                    src_rd_en <= 1'b1;
                    src_rd_addr <= cfg_scatter
                        ? (cfg_source_base + slot * cfg_trailing + element)
                        : (cfg_source_base + row_index * cfg_trailing + element);
                    wait_next <= S_MOVE;
                    state <= S_WAIT;
                end

                S_MOVE: begin
                    out_we <= 1'b1;
                    out_addr <= cfg_scatter
                        ? (cfg_out_base + row_index * cfg_trailing + element)
                        : (cfg_out_base + slot * cfg_trailing + element);
                    out_data <= src_rd_data;
                    moved_elements <= moved_elements + 32'd1;
                    if (element + 32'd1 == cfg_trailing) begin
                        if (slot + 32'd1 == cfg_slots) begin
                            state <= S_DONE;
                        end else begin
                            slot <= slot + 32'd1;
                            state <= S_SLOT_ISSUE;
                        end
                    end else begin
                        element <= element + 32'd1;
                        state <= S_MOVE_ISSUE;
                    end
                end

                S_WAIT: begin
                    state <= wait_next;
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
endmodule
