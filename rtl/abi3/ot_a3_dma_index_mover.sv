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
//
// ---------------------------------------------------------------------------
// THE WALK IS PIPELINED: ONE WORD PER CYCLE, NOT ONE PER THREE
// ---------------------------------------------------------------------------
// The first form of this block parked in a wait state after every read it
// issued -- issue, wait, use -- so each index check and each moved word cost
// three cycles, and a scatter republished the whole prior plane at that rate.
// In the reduced Qwen3 decode that one loop was 6,341,464 of 12,973,713
// cycles: 49% of the token, in a block whose datapath is a word copy
// (results/architecture/abi3_control_path_breakdown.json).
//
// Every pass now issues a read every cycle and consumes the word the memory
// returns two cycles later (the address register, then the memory's own
// output register), so the check pass, the prior republish and the per-slot
// move each run at one word per cycle.  The WRITE STREAM IS UNCHANGED: the same
// addresses, the same data, in the same order -- only the spacing between
// writes shrinks.  Two things follow from reading ahead of the write:
//
//   * a read may be issued one or two words past a failing index.  Those are
//     index-vector reads inside [0, cfg_slots), so they touch nothing the first
//     form would not have been entitled to read, and nothing is written;
//   * a GATHER whose source rows alias the rows it is writing would now read a
//     word before the write two ahead of it lands.  No placement produces that
//     -- one object has one base and a gather's source and destination are
//     different objects -- and the per-element address math is otherwise the
//     same.
//
// The two row-base products (``slot * trailing`` and ``index * trailing``) are
// taken once per slot into registers, in their own state, instead of on every
// word's address path.
//
// ---------------------------------------------------------------------------
// ELIDE_IDENTITY_PRIOR: A SCATTER IN PLACE DOES NOT COPY ITS DESTINATION
// ---------------------------------------------------------------------------
// When the prior contents and the output are the SAME words (cfg_prior_base ==
// cfg_out_base), republishing the destination reads every word and writes it
// back unchanged: the final memory is identical with or without it, so the
// pass is skipped.  The issue bridge always scatters in place (its prior and
// output bases are one register, the KV plane), so there the prior pass is
// pure control overhead -- 8,256 rows x 32 words per scatter in the reduced
// decode.  The parameter defaults OFF so a bench that counts write beats keeps
// counting the republish; the bridge turns it on.  moved_elements and
// indices_checked do not count the republish either way.
// ---------------------------------------------------------------------------
module ot_a3_dma_index_mover #(
    parameter integer ELIDE_IDENTITY_PRIOR = 0
) (
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
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [3:0] S_IDLE       = 4'd0;
    localparam [3:0] S_CHECK      = 4'd1;   // pass one, pipelined
    localparam [3:0] S_PRIOR      = 4'd2;   // scatter pass two, pipelined
    localparam [3:0] S_SLOT_ISSUE = 4'd3;   // pass three: this slot's index
    localparam [3:0] S_SLOT_WAIT  = 4'd4;
    localparam [3:0] S_SLOT       = 4'd5;   // latch the index
    localparam [3:0] S_ROW        = 4'd6;   // the two row bases, registered
    localparam [3:0] S_MOVE       = 4'd7;   // this slot's row, pipelined
    localparam [3:0] S_DONE       = 4'd8;

    reg [3:0]  state;
    reg [31:0] slot;
    reg [31:0] row_index;
    reg [31:0] issue_cursor;     // next word whose read is issued
    reg [31:0] use_cursor;       // next word whose read data is consumed
    reg [31:0] src_row_base;
    reg [31:0] dst_row_base;
    reg [63:0] prior_span;
    reg        skip_prior;
    // A read presented on the port this cycle returns its word next cycle.
    reg        rd_returning;

    wire issue_more_check = issue_cursor < cfg_slots;
    wire issue_more_prior = {32'b0, issue_cursor} < prior_span;
    wire issue_more_move  = issue_cursor < cfg_trailing;
    wire [3:0] after_prior = (cfg_slots == 32'b0) ? S_DONE : S_SLOT_ISSUE;

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
            row_index <= 32'b0;
            issue_cursor <= 32'b0;
            use_cursor <= 32'b0;
            src_row_base <= 32'b0;
            dst_row_base <= 32'b0;
            prior_span <= 64'b0;
            skip_prior <= 1'b0;
            rd_returning <= 1'b0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            idx_rd_en <= 1'b0;
            src_rd_en <= 1'b0;
            rd_returning <= idx_rd_en | src_rd_en;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        moved_elements <= 32'b0;
                        indices_checked <= 32'b0;
                        slot <= 32'b0;
                        row_index <= 32'b0;
                        issue_cursor <= 32'b0;
                        use_cursor <= 32'b0;
                        prior_span <= {32'b0, cfg_rows} * {32'b0, cfg_trailing};
                        skip_prior <= (ELIDE_IDENTITY_PRIOR != 0) &&
                                      (cfg_prior_base == cfg_out_base);
                        if ((cfg_trailing == 32'b0) || (cfg_rows == 32'b0)) begin
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else if (cfg_slots == 32'b0) begin
                            // An empty index vector moves nothing.  A scatter
                            // still republishes the destination's prior rows
                            // (a no-op when they are the destination).
                            state <= !cfg_scatter ? S_DONE
                                : (((ELIDE_IDENTITY_PRIOR != 0) &&
                                    (cfg_prior_base == cfg_out_base))
                                   ? S_DONE : S_PRIOR);
                        end else begin
                            state <= S_CHECK;
                        end
                    end
                end

                // -- pass one: validate every index before anything moves ----
                S_CHECK: begin
                    if (issue_more_check) begin
                        idx_rd_en <= 1'b1;
                        idx_rd_addr <= cfg_index_base + issue_cursor;
                        issue_cursor <= issue_cursor + 32'd1;
                    end
                    if (rd_returning) begin
                        indices_checked <= indices_checked + 32'd1;
                        if (idx_rd_data >= cfg_rows) begin
                            error_code <= ERR_INDEX_RANGE;
                            state <= S_DONE;
                        end else if (use_cursor + 32'd1 == cfg_slots) begin
                            issue_cursor <= 32'b0;
                            use_cursor <= 32'b0;
                            state <= !cfg_scatter ? S_SLOT_ISSUE
                                   : (skip_prior ? S_SLOT_ISSUE : S_PRIOR);
                        end else begin
                            use_cursor <= use_cursor + 32'd1;
                        end
                    end
                end

                // -- scatter pass two: republish the destination unchanged ---
                S_PRIOR: begin
                    if (issue_more_prior) begin
                        src_rd_en <= 1'b1;
                        src_rd_addr <= cfg_prior_base + issue_cursor;
                        issue_cursor <= issue_cursor + 32'd1;
                    end
                    if (rd_returning) begin
                        out_we <= 1'b1;
                        out_addr <= cfg_out_base + use_cursor;
                        out_data <= src_rd_data;
                        if ({32'b0, use_cursor} + 64'd1 == prior_span) begin
                            issue_cursor <= 32'b0;
                            use_cursor <= 32'b0;
                            state <= after_prior;
                        end else begin
                            use_cursor <= use_cursor + 32'd1;
                        end
                    end
                end

                // -- pass three: one slot at a time, in ascending slot order -
                S_SLOT_ISSUE: begin
                    idx_rd_en <= 1'b1;
                    idx_rd_addr <= cfg_index_base + slot;
                    state <= S_SLOT_WAIT;
                end

                S_SLOT_WAIT: state <= S_SLOT;

                S_SLOT: begin
                    row_index <= idx_rd_data;
                    state <= S_ROW;
                end

                S_ROW: begin
                    src_row_base <= cfg_source_base +
                        (cfg_scatter ? slot : row_index) * cfg_trailing;
                    dst_row_base <= cfg_out_base +
                        (cfg_scatter ? row_index : slot) * cfg_trailing;
                    issue_cursor <= 32'b0;
                    use_cursor <= 32'b0;
                    state <= S_MOVE;
                end

                S_MOVE: begin
                    if (issue_more_move) begin
                        src_rd_en <= 1'b1;
                        src_rd_addr <= src_row_base + issue_cursor;
                        issue_cursor <= issue_cursor + 32'd1;
                    end
                    if (rd_returning) begin
                        out_we <= 1'b1;
                        out_addr <= dst_row_base + use_cursor;
                        out_data <= src_rd_data;
                        moved_elements <= moved_elements + 32'd1;
                        if (use_cursor + 32'd1 == cfg_trailing) begin
                            if (slot + 32'd1 == cfg_slots) begin
                                state <= S_DONE;
                            end else begin
                                slot <= slot + 32'd1;
                                state <= S_SLOT_ISSUE;
                            end
                        end else begin
                            use_cursor <= use_cursor + 32'd1;
                        end
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
endmodule
