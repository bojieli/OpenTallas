`timescale 1ns/1ps
// Capacity-bounded session table.  A full 24-bit session ID and a generation
// tag are retained so late HBM/link responses cannot alias a recycled entry.
module ot_session_table #(
    parameter integer ENTRIES = 256,
    parameter integer SESSION_W = 24,
    parameter integer GENERATION_W = 8,
    parameter integer CONTEXT_W = 20,
    parameter integer POSITION_W = 20
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         req_valid,
    output wire                         req_ready,
    input  wire [2:0]                   req_op, // 0 configure,1 release,2 lookup,3 retire,4 abort
    input  wire [SESSION_W-1:0]         req_session_id,
    input  wire [7:0]                   req_image_slot,
    input  wire [CONTEXT_W-1:0]         req_context_minus_one,
    input  wire [POSITION_W-1:0]        req_position,
    input  wire [7:0]                   req_epoch_id,
    input  wire [15:0]                  req_transaction_id,
    input  wire                         req_force,
    output reg                          rsp_valid,
    output reg [7:0]                    rsp_status,
    output reg                          rsp_hit,
    output reg [GENERATION_W-1:0]       rsp_generation,
    output reg [POSITION_W-1:0]          rsp_expected_position,
    output reg                          rsp_poison,
    output wire [ENTRIES-1:0]           busy_bitmap,
    output reg                          integrity_error
);
    localparam [7:0] ST_SUCCESS = 8'h00;
    localparam [7:0] ST_BAD_FIELD = 8'h03;
    localparam [7:0] ST_BUSY = 8'h05;
    localparam [7:0] ST_EPOCH = 8'h07;
    localparam [7:0] ST_CAPACITY = 8'h09;
    localparam [7:0] ST_INTERNAL = 8'h0f;
    localparam integer INDEX_W = (ENTRIES <= 2) ? 1 : $clog2(ENTRIES);
    reg [ENTRIES-1:0] entry_valid;
    reg [ENTRIES-1:0] entry_busy;
    reg [ENTRIES-1:0] entry_poison;
    reg [SESSION_W-1:0] entry_session [0:ENTRIES-1];
    reg [7:0] entry_image [0:ENTRIES-1];
    reg [CONTEXT_W-1:0] entry_context [0:ENTRIES-1];
    reg [POSITION_W-1:0] entry_position [0:ENTRIES-1];
    reg [GENERATION_W-1:0] entry_generation [0:ENTRIES-1];
    reg [GENERATION_W-1:0] allocation_generation;
    reg [7:0] entry_epoch [0:ENTRIES-1];
    reg [15:0] entry_transaction [0:ENTRIES-1];
    integer scan_i;
    reg [INDEX_W-1:0] match_idx;
    reg [INDEX_W-1:0] free_idx;
    reg found_match;
    reg found_free;
    reg op_legal;

    assign req_ready = 1'b1;
    assign busy_bitmap = entry_valid & entry_busy;

    always @* begin
        found_match = 1'b0;
        found_free = 1'b0;
        match_idx = 0;
        free_idx = 0;
        for (scan_i = 0; scan_i < ENTRIES; scan_i = scan_i + 1) begin
            if (entry_valid[scan_i] && entry_session[scan_i] == req_session_id && !found_match) begin
                found_match = 1'b1;
                match_idx = scan_i[INDEX_W-1:0];
            end
            if (!entry_valid[scan_i] && !found_free) begin
                found_free = 1'b1;
                free_idx = scan_i[INDEX_W-1:0];
            end
        end
        op_legal = (req_op <= 3'd4);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rsp_valid <= 1'b0;
            rsp_status <= ST_SUCCESS;
            rsp_hit <= 1'b0;
            rsp_generation <= {GENERATION_W{1'b0}};
            rsp_expected_position <= {POSITION_W{1'b0}};
            rsp_poison <= 1'b0;
            integrity_error <= 1'b0;
            entry_valid <= {ENTRIES{1'b0}};
            entry_busy <= {ENTRIES{1'b0}};
            entry_poison <= {ENTRIES{1'b0}};
            allocation_generation <= {GENERATION_W{1'b0}};
        end else begin
            rsp_valid <= 1'b0;
            if (|(entry_busy & ~entry_valid))
                integrity_error <= 1'b1;
            if (req_valid && req_ready) begin
                rsp_valid <= 1'b1;
                rsp_status <= ST_SUCCESS;
                rsp_hit <= found_match;
                rsp_generation <= found_match ? entry_generation[match_idx] : {GENERATION_W{1'b0}};
                rsp_expected_position <= found_match ? entry_position[match_idx] : {POSITION_W{1'b0}};
                rsp_poison <= found_match ? entry_poison[match_idx] : 1'b0;
                if (!op_legal) begin
                    rsp_status <= ST_BAD_FIELD;
                    rsp_hit <= 1'b0;
                end else begin
                    case (req_op)
                        3'd0: begin // configure
                            if (found_match) begin
                                rsp_status <= ST_BUSY;
                            end else if (!found_free) begin
                                rsp_status <= ST_CAPACITY;
                            end else begin
                                entry_valid[free_idx] <= 1'b1;
                                entry_busy[free_idx] <= 1'b0;
                                entry_poison[free_idx] <= 1'b0;
                                entry_session[free_idx] <= req_session_id;
                                entry_image[free_idx] <= req_image_slot;
                                entry_context[free_idx] <= req_context_minus_one;
                                entry_position[free_idx] <= req_position;
                                entry_epoch[free_idx] <= req_epoch_id;
                                entry_transaction[free_idx] <= req_transaction_id;
                                if (&allocation_generation)
                                    allocation_generation <= {{(GENERATION_W-1){1'b0}},1'b1};
                                else
                                    allocation_generation <= allocation_generation + 1'b1;
                                entry_generation[free_idx] <= (&allocation_generation) ?
                                    {{(GENERATION_W-1){1'b0}},1'b1} :
                                    allocation_generation + 1'b1;
                                rsp_hit <= 1'b1;
                                rsp_generation <= (&allocation_generation) ?
                                    {{(GENERATION_W-1){1'b0}},1'b1} :
                                    allocation_generation + 1'b1;
                            end
                        end
                        3'd1: begin // release
                            if (!found_match)
                                rsp_status <= ST_BAD_FIELD;
                            else if (entry_busy[match_idx] && !req_force)
                                rsp_status <= ST_BUSY;
                            else begin
                                entry_valid[match_idx] <= 1'b0;
                                entry_busy[match_idx] <= 1'b0;
                                entry_poison[match_idx] <= 1'b0;
                                entry_generation[match_idx] <= entry_generation[match_idx] + 1'b1;
                                rsp_hit <= 1'b1;
                            end
                        end
                        3'd2: begin // lookup
                            if (!found_match)
                                rsp_status <= ST_BAD_FIELD;
                            else if (entry_image[match_idx] != req_image_slot ||
                                     entry_context[match_idx] != req_context_minus_one ||
                                     entry_position[match_idx] != req_position ||
                                     entry_epoch[match_idx] != req_epoch_id)
                                rsp_status <= ST_EPOCH;
                            else if (entry_busy[match_idx])
                                rsp_status <= ST_BUSY;
                            else begin
                                entry_busy[match_idx] <= 1'b1;
                                entry_transaction[match_idx] <= req_transaction_id;
                                rsp_hit <= 1'b1;
                            end
                        end
                        3'd3: begin // retire one ordered position
                            if (!found_match)
                                rsp_status <= ST_BAD_FIELD;
                            else if (entry_poison[match_idx])
                                rsp_status <= ST_INTERNAL;
                            else if (!entry_busy[match_idx] ||
                                     entry_transaction[match_idx] != req_transaction_id)
                                rsp_status <= ST_EPOCH;
                            else if (req_position != entry_position[match_idx] ||
                                     req_epoch_id != entry_epoch[match_idx])
                                rsp_status <= ST_EPOCH;
                            else begin
                                entry_position[match_idx] <= entry_position[match_idx] + 1'b1;
                                entry_busy[match_idx] <= 1'b0;
                                entry_epoch[match_idx] <= req_epoch_id;
                                entry_transaction[match_idx] <= req_transaction_id;
                                rsp_hit <= 1'b1;
                                rsp_expected_position <= entry_position[match_idx] + 1'b1;
                            end
                        end
                        3'd4: begin // abort/poison
                            if (!found_match)
                                rsp_status <= ST_BAD_FIELD;
                            else if (entry_busy[match_idx] &&
                                     entry_transaction[match_idx] != req_transaction_id &&
                                     !req_force)
                                rsp_status <= ST_EPOCH;
                            else begin
                                entry_poison[match_idx] <= 1'b1;
                                entry_busy[match_idx] <= 1'b0;
                                rsp_hit <= 1'b1;
                                rsp_poison <= 1'b1;
                            end
                        end
                        default: rsp_status <= ST_BAD_FIELD;
                    endcase
                end
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (ENTRIES < 2)
            $error("ot_session_table requires at least two entries");
    end
`endif
endmodule
