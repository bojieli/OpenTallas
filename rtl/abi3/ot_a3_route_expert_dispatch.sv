`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROUTE.EXPERT_DISPATCH -- one token row per selected expert slot.
//
// ``input_view_0`` is [groups, slots] U32 expert IDs, ``input_view_1`` the token
// rows [groups, width], and ``output_view_0`` the dispatch buffer
// [groups * slots, width] in (group, slot) order: output row ``g*slots + s``
// carries a copy of token row ``g``.  ``output_view_1``, when bound, records the
// expert each dispatched row was routed to, in the same order.
//
// ``aux_id_0`` is the expert count and is MANDATORY: the reference refuses an
// operator that cannot state the bound, because an engine that cannot state it
// cannot prove an ID is inside it.  Every ID is checked; one outside the bound
// is a fault after being counted, never a clamp and never a wrap.
//
// THE CHECK RUNS BEFORE ANY WRITE.  The reference reads every ID, counts the
// rejects and raises before it writes a single row, so a refused dispatch leaves
// the buffer untouched.  Checking IDs as the walk consumed them would be one
// state fewer and would leave a partially written buffer behind a fault, which
// is the difference between a refusal and a corruption.  The scan is
// groups*slots cycles, once, against a walk of groups*slots*width.
//
// FULLY PIPELINED.  One output element per cycle through the walk: the token
// read is registered, the write is registered behind it, and the (group, slot,
// column) walk is three counters that roll over. No multiplier and no divider --
// the output row index is not divided to recover its group, and the source row
// base advances by ``width`` when the group does.
// ---------------------------------------------------------------------------
module ot_a3_route_expert_dispatch #(
    parameter integer MAX_SLOTS = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [31:0] cfg_groups,
    input  wire [31:0] cfg_slots,       //: 1..MAX_SLOTS
    input  wire [31:0] cfg_width,
    input  wire [31:0] cfg_experts,     //: aux_id_0, the bound every ID is checked against
    input  wire [31:0] cfg_id_base,
    input  wire [31:0] cfg_token_base,
    input  wire [31:0] cfg_out_base,
    input  wire        cfg_has_expert_out,
    input  wire [31:0] cfg_expert_out_base,

    output reg         id_rd_en,
    output reg  [31:0] id_rd_addr,
    input  wire [31:0] id_rd_data,
    output reg         tok_rd_en,
    output reg  [31:0] tok_rd_addr,
    input  wire [31:0] tok_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         eout_we,
    output reg  [31:0] eout_addr,
    output reg  [31:0] eout_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] out_count,
    output reg  [31:0] rejected_ids
);
    // Re-declared rather than wildcard-imported: Icarus 11 turns a
    // wildcard-imported name used only in a port connection into an implicit
    // net, and the pinned Yosys 0.68 frontend rejects ``import`` outright.
    localparam [7:0] ERR_NONE        = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SHAPE       = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_SCAN   = 3'd1;
    localparam [2:0] S_SCAND  = 3'd2;   //: the scan's last read is in flight
    localparam [2:0] S_WALK   = 3'd3;
    localparam [2:0] S_DRAIN  = 3'd4;
    localparam [2:0] S_DONE   = 3'd5;

    reg [2:0]  state;
    //: The scan's cursor over every (group, slot) pair.
    reg [31:0] scan_index;
    reg [31:0] scan_total;
    reg [1:0]  scan_tail;
    //: The walk: which group, which slot of it, which column.
    reg [31:0] grp;
    reg [31:0] slot;
    reg [31:0] col;
    //: ``out_row`` is the output ROW index -- what output_view_1 is addressed by
    //: -- while ``out_elem`` is the linear element cursor the row-major output
    //: view is addressed by.  Using the row index as an element address writes
    //: every row on top of the first ``width`` elements, which is the shape of
    //: mistake a [rows, width] output invites.
    reg [31:0] out_row;
    reg [31:0] out_elem;
    //: Source row base, advanced by cfg_width when the group advances, so the
    //: address is never ``grp * width``.
    reg [31:0] row_base;
    reg [31:0] drain;

    //: Stage A issues the read; the registered address means the memory answers
    //: two cycles later, so the write metadata travels two stages.
    reg        a_valid, b_valid;
    reg [31:0] a_out_addr, b_out_addr;
    //: The expert id of the row being emitted, held for output_view_1.
    reg        a_first, b_first;
    reg [31:0] a_expert_addr, b_expert_addr;

    wire cfg_bad = (cfg_groups == 32'd0) || (cfg_slots == 32'd0) ||
                   (cfg_width == 32'd0) || (cfg_experts == 32'd0) ||
                   (cfg_slots > MAX_SLOTS[31:0]);

    //: The scanned id, valid two cycles after its address was driven.
    reg       scan_v1, scan_v2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scan_v1 <= 1'b0; scan_v2 <= 1'b0;
        end else begin
            scan_v1 <= id_rd_en;
            scan_v2 <= scan_v1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            scan_index <= 32'd0;
            scan_total <= 32'd0;
            scan_tail <= 2'd0;
            grp <= 32'd0; slot <= 32'd0; col <= 32'd0;
            out_row <= 32'd0; out_elem <= 32'd0; row_base <= 32'd0; drain <= 32'd0;
            id_rd_en <= 1'b0; id_rd_addr <= 32'd0;
            tok_rd_en <= 1'b0; tok_rd_addr <= 32'd0;
            out_we <= 1'b0; out_addr <= 32'd0; out_data <= 32'd0;
            eout_we <= 1'b0; eout_addr <= 32'd0; eout_data <= 32'd0;
            a_valid <= 1'b0; b_valid <= 1'b0;
            a_out_addr <= 32'd0; b_out_addr <= 32'd0;
            a_first <= 1'b0; b_first <= 1'b0;
            a_expert_addr <= 32'd0; b_expert_addr <= 32'd0;
            busy <= 1'b0; done <= 1'b0;
            error_code <= ERR_NONE;
            out_count <= 32'd0;
            rejected_ids <= 32'd0;
        end else begin
            id_rd_en <= 1'b0;
            tok_rd_en <= 1'b0;
            out_we <= 1'b0;
            eout_we <= 1'b0;
            done <= 1'b0;

            // -- the write stage, two behind the read ----------------------
            if (b_valid) begin
                out_we <= 1'b1;
                out_addr <= b_out_addr;
                out_data <= tok_rd_data;
                out_count <= out_count + 32'd1;
                if (b_first && cfg_has_expert_out) begin
                    eout_we <= 1'b1;
                    eout_addr <= b_expert_addr;
                    eout_data <= id_rd_data;
                end
            end
            b_valid <= a_valid;
            b_out_addr <= a_out_addr;
            b_first <= a_first;
            b_expert_addr <= a_expert_addr;
            a_valid <= 1'b0;
            a_first <= 1'b0;

            // -- every ID checked, and counted, before any row is written ---
            if (scan_v2 && (state == S_SCAN || state == S_SCAND)) begin
                if (id_rd_data >= cfg_experts)
                    rejected_ids <= rejected_ids + 32'd1;
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        scan_index <= 32'd0;
                        grp <= 32'd0; slot <= 32'd0; col <= 32'd0;
                        out_row <= 32'd0; out_elem <= 32'd0; row_base <= 32'd0;
                        out_count <= 32'd0; rejected_ids <= 32'd0;
                        drain <= 32'd0; scan_tail <= 2'd0;
                        scan_total <= cfg_groups * cfg_slots;
                        if (cfg_bad) begin
                            error_code <= ERR_SHAPE;
                            busy <= 1'b0; done <= 1'b1;
                            state <= S_DONE;
                        end else begin
                            error_code <= ERR_NONE;
                            busy <= 1'b1;
                            state <= S_SCAN;
                        end
                    end
                end
                S_SCAN: begin
                    id_rd_en <= 1'b1;
                    id_rd_addr <= cfg_id_base + scan_index;
                    if (scan_index + 32'd1 >= scan_total) begin
                        scan_tail <= 2'd0;
                        state <= S_SCAND;
                    end else begin
                        scan_index <= scan_index + 32'd1;
                    end
                end
                S_SCAND: begin
                    //: Two cycles for the last registered id read to land and be
                    //: counted, then the verdict.
                    if (scan_tail >= 2'd2) begin
                        if (rejected_ids != 32'd0) begin
                            error_code <= ERR_INDEX_RANGE;
                            busy <= 1'b0; done <= 1'b1;
                            state <= S_DONE;
                        end else begin
                            state <= S_WALK;
                        end
                    end else begin
                        scan_tail <= scan_tail + 2'd1;
                    end
                end
                S_WALK: begin
                    tok_rd_en <= 1'b1;
                    tok_rd_addr <= cfg_token_base + row_base + col;
                    //: The id of THIS output row, re-read alongside its first
                    //: column so output_view_1 needs no second pass.
                    id_rd_en <= 1'b1;
                    id_rd_addr <= cfg_id_base + out_row;
                    a_valid <= 1'b1;
                    a_out_addr <= cfg_out_base + out_elem;
                    a_first <= (col == 32'd0);
                    a_expert_addr <= cfg_expert_out_base + out_row;
                    out_elem <= out_elem + 32'd1;
                    if (col + 32'd1 >= cfg_width) begin
                        col <= 32'd0;
                        if (slot + 32'd1 >= cfg_slots) begin
                            slot <= 32'd0;
                            row_base <= row_base + cfg_width;
                            if (grp + 32'd1 >= cfg_groups) begin
                                drain <= 32'd0;
                                state <= S_DRAIN;
                            end else begin
                                grp <= grp + 32'd1;
                            end
                        end else begin
                            slot <= slot + 32'd1;
                        end
                        out_row <= out_row + 32'd1;
                    end else begin
                        col <= col + 32'd1;
                    end
                end
                S_DRAIN: begin
                    busy <= 1'b1;
                    if (drain >= 32'd2)
                        state <= S_DONE;
                    else
                        drain <= drain + 32'd1;
                end
                S_DONE: begin
                    busy <= 1'b0; done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
