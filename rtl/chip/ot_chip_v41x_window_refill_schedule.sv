`timescale 1ns/1ps
// Functional barrier between packed WINDOW HBM refill and attention row issue.
// A job starts only after all of its WINDOW rows have passed the prefetch
// validity barrier. This deliberately makes no sustained-bandwidth claim.
module ot_chip_v41x_window_refill_schedule #(
    parameter integer POS_W = 21,
    parameter integer USER_W = 10,
    parameter integer MAX_CONTEXT = 1048576
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start_v,
    output wire                  start_ready,
    input  wire [USER_W-1:0]     start_user,
    input  wire [POS_W-1:0]      start_first,
    input  wire [7:0]            start_count,
    output wire                  prefetch_v,
    input  wire                  prefetch_ready,
    output wire [USER_W-1:0]     prefetch_user,
    output wire [POS_W-1:0]      prefetch_row,
    input  wire                  prefetch_ok,
    input  wire                  prefetch_fault,
    output wire                  issue_v,
    input  wire                  issue_ready,
    output wire [USER_W-1:0]     issue_user,
    output wire [POS_W-1:0]      issue_first,
    output wire [7:0]            issue_count,
    input  wire                  issue_done,
    input  wire                  issue_fault,
    output wire                  busy,
    output reg                   done,
    output reg                   fault,
    output reg  [31:0]           refill_cycles,
    output reg  [7:0]            rows_refilled
);
    localparam [2:0] IDLE=0, SEND=1, WAIT=2, ISSUE=3, RUN=4, FAILED=5;
    reg [2:0] state;
    reg [USER_W-1:0] user_id;
    reg [POS_W-1:0] first;
    reg [7:0] count, row_idx;
    wire [POS_W:0] end_pos = {1'b0,start_first} + (POS_W+1)'(start_count);
    assign start_ready = state == IDLE;
    assign prefetch_v = state == SEND && prefetch_ready;
    assign prefetch_user = user_id;
    assign prefetch_row = first + POS_W'(row_idx);
    assign issue_v = state == ISSUE;
    assign issue_user = user_id;
    assign issue_first = first;
    assign issue_count = count;
    assign busy = state != IDLE;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; user_id <= 0; first <= 0; count <= 0;
            row_idx <= 0; rows_refilled <= 0; refill_cycles <= 0;
            done <= 0; fault <= 0;
        end else begin
            done <= 0;
            if (state == SEND || state == WAIT) refill_cycles <= refill_cycles + 1;
            if (state != IDLE && (prefetch_fault || issue_fault)) begin
                fault <= 1; state <= FAILED;
            end else case (state)
                IDLE: if (start_v) begin
                    user_id <= start_user; first <= start_first;
                    count <= start_count; row_idx <= 0;
                    rows_refilled <= 0; refill_cycles <= 0; fault <= 0;
                    if (start_count > 8'd128 || end_pos > (POS_W+1)'(MAX_CONTEXT)) begin
                        fault <= 1; state <= FAILED;
                    end else state <= start_count == 0 ? ISSUE : SEND;
                end
                SEND: if (prefetch_ready) state <= WAIT;
                WAIT: if (prefetch_ok) begin
                    rows_refilled <= rows_refilled + 1'b1;
                    if (row_idx + 1'b1 == count) state <= ISSUE;
                    else begin row_idx <= row_idx + 1'b1; state <= SEND; end
                end
                ISSUE: if (issue_ready) state <= RUN;
                RUN: if (issue_done) begin done <= 1; state <= IDLE; end
                FAILED: state <= FAILED;
                default: begin fault <= 1; state <= FAILED; end
            endcase
        end
    end
endmodule
