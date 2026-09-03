`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 tensor output-coordinate to physical-lane wave mapper.
//
// This controller implements the deterministic row-folding decision in
// docs/ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md without changing the
// ABI 3.0 wire format.  It accepts already-resolved logical output extents and
// the existing schedule's tile_rows, tile_cols and issue_window values.  Each
// accepted wave describes one row-major rectangle of at most 256 independent
// output accumulators:
//
//   lane = local_row * wave_cols_per_row + local_col
//   row  = wave_row_base + local_row
//   col  = wave_col_base + local_col
//
// lane_valid is therefore a contiguous low-lane mask.  Four 64-lane issue
// groups may consume the same metadata; the mask gates every absent lane.
// A consumer must retain each lane's accumulator across the complete K walk.
// This module maps output coordinates only and cannot authorize split-K or a
// change in numeric association.
//
// Column tiles may be packed only inside a group of
// tile_cols * issue_window columns.  issue_window=1 therefore never crosses a
// column-tile boundary, while the common tile_cols=64, issue_window=4 case can
// fill all 256 lanes for a one-row decode.  Row tiles are never packed across
// their boundary.  Every logical (row,col) coordinate is emitted once.
//
// Backpressure is lossless: all wave metadata and the lane mask remain stable
// while wave_valid && !wave_ready.  Counters advance only on a wave handshake.
// Degenerate extents/schedule fields fail before emitting a wave.
// ---------------------------------------------------------------------------
module ot_a3_tensor_lane_mapper #(
    parameter integer LANES = 256,
    parameter integer ISSUE_GROUPS = 4,
    parameter integer LANES_PER_GROUP = 64
) (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         start,
    input  wire [31:0]  cfg_rows,
    input  wire [31:0]  cfg_cols,
    input  wire [31:0]  cfg_tile_rows,
    input  wire [31:0]  cfg_tile_cols,
    input  wire [31:0]  cfg_issue_window,

    output wire         wave_valid,
    input  wire         wave_ready,
    output wire [31:0]  wave_row_base,
    output wire [31:0]  wave_col_base,
    output wire [8:0]   wave_rows,
    output wire [8:0]   wave_cols_per_row,
    output wire [8:0]   wave_active_lanes,
    output wire [255:0] lane_valid,
    output wire [27:0]  issue_group_active_counts,
    output wire         wave_last,

    output reg          busy,
    output reg          done,
    output reg  [7:0]   error_code,
    output reg  [63:0]  wave_count,
    output reg  [63:0]  logical_output_count,
    output reg  [63:0]  active_lane_slots,
    output reg  [63:0]  masked_lane_slots,
    output reg  [63:0]  row_folded_output_count
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_PREPARE = 2'd1;
    localparam [1:0] S_HOLD = 2'd2;

    reg [1:0] state;

    reg [31:0] rows_q;
    reg [31:0] cols_q;
    reg [31:0] tile_rows_q;
    reg [31:0] tile_cols_q;
    reg [31:0] issue_window_q;

    reg [31:0] row_tile_base_q;
    reg [31:0] row_slice_offset_q;
    reg [31:0] col_group_base_q;
    reg [31:0] col_cursor_q;

    reg [31:0] wave_row_base_q;
    reg [31:0] wave_col_base_q;
    reg [8:0] wave_rows_q;
    reg [8:0] wave_cols_q;
    reg [8:0] wave_active_q;
    reg wave_last_q;

    reg [63:0] row_tile_remaining;
    reg [63:0] row_slice_remaining;
    reg [63:0] group_span;
    reg [63:0] group_end;
    reg [63:0] column_remaining;
    reg [63:0] column_capacity;
    reg [63:0] chosen_rows;
    reg [63:0] chosen_cols;
    reg [63:0] chosen_active;

    integer lane_index;
    integer group_index;
    reg [255:0] lane_valid_comb;
    reg [27:0] group_counts_comb;
    integer group_remaining;
    integer group_base;

    assign wave_valid = (state == S_HOLD);
    assign wave_row_base = wave_row_base_q;
    assign wave_col_base = wave_col_base_q;
    assign wave_rows = wave_rows_q;
    assign wave_cols_per_row = wave_cols_q;
    assign wave_active_lanes = wave_active_q;
    assign lane_valid = lane_valid_comb;
    assign issue_group_active_counts = group_counts_comb;
    assign wave_last = wave_last_q;

    // Contiguous lane validity makes the mask cheap to distribute and gives
    // each 64-lane issue group an exact 0..64 active count.
    always @* begin
        lane_valid_comb = 256'd0;
        group_remaining = 0;
        group_base = 0;
        for (lane_index = 0; lane_index < LANES; lane_index = lane_index + 1)
            if (lane_index < wave_active_q)
                lane_valid_comb[lane_index] = 1'b1;

        group_counts_comb = 28'd0;
        for (group_index = 0; group_index < ISSUE_GROUPS;
             group_index = group_index + 1) begin
            group_base = group_index * LANES_PER_GROUP;
            if ({23'd0, wave_active_q} > group_base) begin
                group_remaining = {23'd0, wave_active_q} - group_base;
                if (group_remaining > LANES_PER_GROUP)
                    group_counts_comb[group_index*7 +: 7] =
                        7'd64;
                else
                    group_counts_comb[group_index*7 +: 7] =
                        group_remaining[6:0];
            end else begin
                group_counts_comb[group_index*7 +: 7] = 7'd0;
            end
        end
    end

    // The widened scratch registers below are blocking combinational
    // temporaries inside the clocked transaction step; architectural state
    // uses nonblocking assignments exclusively.
    /* verilator lint_off BLKSEQ */
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            rows_q <= 32'd0;
            cols_q <= 32'd0;
            tile_rows_q <= 32'd0;
            tile_cols_q <= 32'd0;
            issue_window_q <= 32'd0;
            row_tile_base_q <= 32'd0;
            row_slice_offset_q <= 32'd0;
            col_group_base_q <= 32'd0;
            col_cursor_q <= 32'd0;
            wave_row_base_q <= 32'd0;
            wave_col_base_q <= 32'd0;
            wave_rows_q <= 9'd0;
            wave_cols_q <= 9'd0;
            wave_active_q <= 9'd0;
            wave_last_q <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            wave_count <= 64'd0;
            logical_output_count <= 64'd0;
            active_lane_slots <= 64'd0;
            masked_lane_slots <= 64'd0;
            row_folded_output_count <= 64'd0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        error_code <= ERR_NONE;
                        wave_count <= 64'd0;
                        logical_output_count <= 64'd0;
                        active_lane_slots <= 64'd0;
                        masked_lane_slots <= 64'd0;
                        row_folded_output_count <= 64'd0;
                        wave_rows_q <= 9'd0;
                        wave_cols_q <= 9'd0;
                        wave_active_q <= 9'd0;
                        wave_last_q <= 1'b0;
                        if ((cfg_rows == 0) || (cfg_cols == 0) ||
                            (cfg_tile_rows == 0) || (cfg_tile_cols == 0) ||
                            (cfg_issue_window == 0) ||
                            (LANES != ISSUE_GROUPS * LANES_PER_GROUP) ||
                            (LANES != 256)) begin
                            busy <= 1'b0;
                            error_code <= ERR_SHAPE;
                            done <= 1'b1;
                        end else begin
                            rows_q <= cfg_rows;
                            cols_q <= cfg_cols;
                            tile_rows_q <= cfg_tile_rows;
                            tile_cols_q <= cfg_tile_cols;
                            issue_window_q <= cfg_issue_window;
                            row_tile_base_q <= 32'd0;
                            row_slice_offset_q <= 32'd0;
                            col_group_base_q <= 32'd0;
                            col_cursor_q <= 32'd0;
                            busy <= 1'b1;
                            state <= S_PREPARE;
                        end
                    end
                end

                S_PREPARE: begin
                    // All arithmetic is widened before subtraction/product so
                    // even maximum legal 32-bit schedule fields cannot wrap.
                    row_tile_remaining = {32'd0, rows_q} -
                                         {32'd0, row_tile_base_q};
                    if (row_tile_remaining > {32'd0, tile_rows_q})
                        row_tile_remaining = {32'd0, tile_rows_q};
                    row_slice_remaining = row_tile_remaining -
                                          {32'd0, row_slice_offset_q};
                    chosen_rows = (row_slice_remaining > 64'd256)
                                  ? 64'd256 : row_slice_remaining;

                    group_span = {32'd0, tile_cols_q} *
                                 {32'd0, issue_window_q};
                    group_end = {32'd0, col_group_base_q} + group_span;
                    if ((group_end > {32'd0, cols_q}) ||
                        (group_end < {32'd0, col_group_base_q}))
                        group_end = {32'd0, cols_q};
                    column_remaining = group_end - {32'd0, col_cursor_q};
                    column_capacity = 64'd256 / chosen_rows;
                    chosen_cols = (column_remaining > column_capacity)
                                  ? column_capacity : column_remaining;
                    chosen_active = chosen_rows * chosen_cols;

                    // These bounds follow from the admitted nonzero shape,
                    // but retain a local fail-closed guard so an internal
                    // arithmetic defect can never activate an invalid lane.
                    if ((chosen_rows == 0) || (chosen_cols == 0) ||
                        (chosen_active > 64'd256)) begin
                        busy <= 1'b0;
                        error_code <= ERR_SHAPE;
                        done <= 1'b1;
                        state <= S_IDLE;
                    end else begin
                        wave_row_base_q <= row_tile_base_q +
                                           row_slice_offset_q;
                        wave_col_base_q <= col_cursor_q;
                        wave_rows_q <= chosen_rows[8:0];
                        wave_cols_q <= chosen_cols[8:0];
                        wave_active_q <= chosen_active[8:0];
                        wave_last_q <=
                            ({32'd0, col_cursor_q} + chosen_cols ==
                             {32'd0, cols_q}) &&
                            ({32'd0, row_slice_offset_q} + chosen_rows ==
                             row_tile_remaining) &&
                            ({32'd0, row_tile_base_q} +
                             row_tile_remaining == {32'd0, rows_q});
                        state <= S_HOLD;
                    end
                end

                S_HOLD: begin
                    if (wave_ready) begin
                        wave_count <= wave_count + 64'd1;
                        logical_output_count <= logical_output_count +
                                                {55'd0, wave_active_q};
                        active_lane_slots <= active_lane_slots +
                                             {55'd0, wave_active_q};
                        masked_lane_slots <= masked_lane_slots +
                                             (64'd256 -
                                              {55'd0, wave_active_q});
                        row_folded_output_count <= row_folded_output_count +
                            ({55'd0, wave_active_q} -
                             {55'd0, wave_rows_q});
                        if (wave_last_q) begin
                            busy <= 1'b0;
                            done <= 1'b1;
                            state <= S_IDLE;
                        end else begin
                            group_span = {32'd0, tile_cols_q} *
                                         {32'd0, issue_window_q};
                            group_end = {32'd0, col_group_base_q} + group_span;
                            if ((group_end > {32'd0, cols_q}) ||
                                (group_end < {32'd0, col_group_base_q}))
                                group_end = {32'd0, cols_q};
                            row_tile_remaining = {32'd0, rows_q} -
                                                 {32'd0, row_tile_base_q};
                            if (row_tile_remaining > {32'd0, tile_rows_q})
                                row_tile_remaining = {32'd0, tile_rows_q};

                            if ({32'd0, col_cursor_q} +
                                {55'd0, wave_cols_q} < group_end) begin
                                col_cursor_q <= col_cursor_q +
                                                {23'd0, wave_cols_q};
                            end else if (group_end < {32'd0, cols_q}) begin
                                col_group_base_q <= group_end[31:0];
                                col_cursor_q <= group_end[31:0];
                            end else begin
                                col_group_base_q <= 32'd0;
                                col_cursor_q <= 32'd0;
                                if ({32'd0, row_slice_offset_q} +
                                    {55'd0, wave_rows_q} <
                                    row_tile_remaining) begin
                                    row_slice_offset_q <= row_slice_offset_q +
                                                          {23'd0,
                                                           wave_rows_q};
                                end else begin
                                    row_tile_base_q <= row_tile_base_q +
                                                       row_tile_remaining[31:0];
                                    row_slice_offset_q <= 32'd0;
                                end
                            end
                            state <= S_PREPARE;
                        end
                    end
                end

                default: begin
                    busy <= 1'b0;
                    error_code <= ERR_SHAPE;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
            endcase
        end
    end
    /* verilator lint_on BLKSEQ */
endmodule
