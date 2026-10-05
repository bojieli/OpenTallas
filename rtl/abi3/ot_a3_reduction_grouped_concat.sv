`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// REDUCTION.GROUPED_CONCAT -- up to four operands joined into one.
//
// Amendment A17: ``aux_id_0`` names the join axis.  ``NO_ID`` and 0 both mean
// axis 0, which lays the operands end to end; 1 joins on the feature axis of
// rank-2 operands, so output row r is input 0's row r followed by input 1's row
// r and so on.  No other axis is defined, and the reference engine faults on
// one, so this block carries no third case.
//
// ONE DATAPATH FOR BOTH AXES.  A leading-axis join is a feature join of
// single-row operands: set ``cfg_rows`` to 1 and each ``cfg_width`` to that
// operand's whole element count and the feature walk produces exactly the
// end-to-end copy.  Writing the two cases separately would be two state
// machines to keep in agreement for no gain, so the caller collapses the
// leading join and this block only walks features.
//
// NO MULTIPLIER, NO DIVIDER.  The obvious address is
// ``base[k] + row * width[k] + column``, and the obvious output-to-source map
// needs ``row = index / out_width``.  Both are avoided: the walk is a pair of
// counters that roll over, and each operand carries a row-offset accumulator
// that advances by its own width when a row completes.  On ASAP7 a 32-bit
// multiply in the address path cost the hashed placement table more than half
// its frequency (499 MHz against 1,058), which is the measurement this
// structure is chosen against.
//
// FULLY PIPELINED.  One output element per cycle with no bubble between
// operands or between rows: the read address is registered, the operand memory
// answers the next cycle, and the write is registered behind it, so the block
// issues on every cycle it is not draining.  Initiation interval is 1 and
// latency is 2.
// ---------------------------------------------------------------------------
module ot_a3_reduction_grouped_concat #(
    // A17 admits at most four inputs.  The parameter exists so a narrower
    // deployment can build a narrower block, not so a wider one can appear.
    parameter integer INPUTS = 4
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    //: Number of operands actually joined, 1..INPUTS.
    input  wire [2:0]  cfg_inputs,
    //: Output rows.  A leading-axis join sets this to 1; see the header.
    input  wire [31:0] cfg_rows,
    //: Per-operand join extent, packed little-operand-first.
    input  wire [INPUTS*32-1:0] cfg_width,
    input  wire [INPUTS*32-1:0] cfg_in_base,
    input  wire [31:0] cfg_out_base,

    //: One read port per operand.  They are driven one at a time -- the walk is
    //: sequential -- so a caller may fold them onto one memory.
    output reg  [INPUTS-1:0]    in_rd_en,
    output reg  [INPUTS*32-1:0] in_rd_addr,
    input  wire [INPUTS*32-1:0] in_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count
);
    // Package constants are re-declared rather than wildcard-imported: Icarus 11
    // turns a wildcard-imported name used only in a port connection into an
    // implicit net, and the pinned Yosys 0.68 frontend rejects ``import``
    // outright, so a wildcard import is a block that cannot be routed.
    localparam [7:0] ERR_NONE  = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    //: ``oper`` is a cycle wider than the array it selects so it can be compared
    //: against ``cfg_inputs`` without truncating; the select itself is narrowed
    //: to exactly the index the array needs.
    localparam integer SEL_W = (INPUTS <= 1) ? 1 : $clog2(INPUTS);
    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_WALK   = 3'd1;
    //: Two drain cycles, one per stage still in flight.
    localparam [2:0] S_DRAIN1 = 3'd2;
    localparam [2:0] S_DRAIN2 = 3'd3;
    localparam [2:0] S_DONE   = 3'd4;

    reg [2:0]  state;

    //: The walk: which operand, how far into its row, and which output row.
    reg [2:0]  oper;
    reg [31:0] oper_col;
    reg [31:0] row;
    reg [31:0] out_cursor;
    //: Per-operand base of the row being read, advanced by that operand's own
    //: width at every row boundary.  This is the multiplier's replacement.
    reg [31:0] row_off [0:INPUTS-1];

    //: Two stages behind the walk, not one.  ``in_rd_addr`` is registered, so
    //: the operand memory does not see an address until the cycle after the walk
    //: drives it and does not answer until the cycle after that.  A single stage
    //: writes each element to its predecessor's address, which is what the
    //: first run of the testbench showed: every output shifted by one.
    reg        s2_valid;
    //: Only the select width is carried forward; ``oper`` needs the extra bit
    //: for its comparison against ``cfg_inputs``, the pipeline register does not.
    reg [SEL_W-1:0] s2_oper;
    reg [31:0] s2_out_addr;
    reg        s3_valid;
    reg [SEL_W-1:0] s3_oper;
    reg [31:0] s3_out_addr;

    integer    i;

    wire [SEL_W-1:0] oper_sel = oper[SEL_W-1:0];

    wire [31:0] width_of_oper = cfg_width[oper_sel*32 +: 32];
    //: Last element of this operand's row, and last operand of the row.
    wire oper_last_col = (oper_col + 32'd1) >= width_of_oper;
    wire oper_is_last  = ({29'd0, oper} + 32'd1) >= {29'd0, cfg_inputs};
    wire row_last      = oper_last_col && oper_is_last;
    wire rows_done     = row_last && ((row + 32'd1) >= cfg_rows);

    //: A zero-extent operand has no element to read, so the walk would stall on
    //: it forever.  A17 requires every non-join extent to agree and the join
    //: extents to sum to the output's, which a zero width cannot satisfy for a
    //: rank-2 feature join; refuse instead of hanging.
    reg width_zero;
    always @* begin
        width_zero = 1'b0;
        for (i = 0; i < INPUTS; i = i + 1) begin
            if (({29'd0, i[2:0]} < {29'd0, cfg_inputs}) &&
                (cfg_width[i*32 +: 32] == 32'd0))
                width_zero = 1'b1;
        end
    end
    wire cfg_bad = (cfg_inputs == 3'd0) ||
                   ({29'd0, cfg_inputs} > INPUTS[31:0]) ||
                   (cfg_rows == 32'd0) || width_zero;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            oper <= 3'd0;
            oper_col <= 32'd0;
            row <= 32'd0;
            out_cursor <= 32'd0;
            s2_valid <= 1'b0;
            s2_oper <= {SEL_W{1'b0}};
            s2_out_addr <= 32'd0;
            s3_valid <= 1'b0;
            s3_oper <= {SEL_W{1'b0}};
            s3_out_addr <= 32'd0;
            in_rd_en <= {INPUTS{1'b0}};
            in_rd_addr <= {(INPUTS*32){1'b0}};
            out_we <= 1'b0;
            out_addr <= 32'd0;
            out_data <= 32'd0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 32'd0;
            for (i = 0; i < INPUTS; i = i + 1)
                row_off[i] <= 32'd0;
        end else begin
            // The write stage always reflects the previous cycle's read, so it
            // is cleared unconditionally and re-raised below.
            in_rd_en <= {INPUTS{1'b0}};
            out_we <= 1'b0;
            done <= 1'b0;

            // -- stage 3: the operand memory has answered ------------------
            if (s3_valid) begin
                out_we <= 1'b1;
                out_addr <= s3_out_addr;
                out_data <= in_rd_data[s3_oper*32 +: 32];
                out_count <= out_count + 32'd1;
            end
            // -- stage 2: the address is on the port this cycle ------------
            s3_valid <= s2_valid;
            s3_oper <= s2_oper;
            s3_out_addr <= s2_out_addr;
            s2_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        oper <= 3'd0;
                        oper_col <= 32'd0;
                        row <= 32'd0;
                        out_cursor <= 32'd0;
                        out_count <= 32'd0;
                        for (i = 0; i < INPUTS; i = i + 1)
                            row_off[i] <= 32'd0;
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
                // -- stage 1: drive one read, and advance the walk ---------
                S_WALK: begin
                    in_rd_en[oper_sel] <= 1'b1;
                    in_rd_addr[oper_sel*32 +: 32] <=
                        cfg_in_base[oper_sel*32 +: 32] + row_off[oper_sel] +
                        oper_col;
                    s2_valid <= 1'b1;
                    s2_oper <= oper_sel;
                    s2_out_addr <= cfg_out_base + out_cursor;
                    out_cursor <= out_cursor + 32'd1;

                    if (rows_done) begin
                        state <= S_DRAIN1;
                    end else if (row_last) begin
                        // Every operand's row base advances by its own width.
                        for (i = 0; i < INPUTS; i = i + 1)
                            row_off[i] <= row_off[i] + cfg_width[i*32 +: 32];
                        row <= row + 32'd1;
                        oper <= 3'd0;
                        oper_col <= 32'd0;
                    end else if (oper_last_col) begin
                        oper <= oper + 3'd1;
                        oper_col <= 32'd0;
                    end else begin
                        oper_col <= oper_col + 32'd1;
                    end
                end
                // The last read is still in flight through both stages, so the
                // block may not report done until each has retired.
                S_DRAIN1: begin
                    busy <= 1'b1;
                    state <= S_DRAIN2;
                end
                S_DRAIN2: begin
                    busy <= 1'b1;
                    state <= S_DONE;
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
