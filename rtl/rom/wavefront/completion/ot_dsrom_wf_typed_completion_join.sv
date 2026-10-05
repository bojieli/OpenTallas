`timescale 1ns/1ps
// Additive typed terminal successor. Raw native payload is never fabricated;
// only token_result_valid permits interpreting it as a token/HEAD result.
// One finite retained result from the selected native terminal END. Whole-plan
// coverage and visibility are REQUIRED source-owned, identity-matched inputs.
// This block creates neither a stage schedule nor a receipt/credit ledger.
module ot_dsrom_wf_typed_completion_join #(
    parameter integer ENABLE=0, IDW=47, PAW=14, NW=21
)(
    input wire clk, rst_n,
    // 0 TOKEN_RESULT: fresh argmax required; 1 STAGE_HANDOFF: no token validity.
    input wire request_v, request_binding_valid, request_kind,
    output wire request_ready,
    input wire [IDW-1:0] request_identity,
    input wire [PAW-1:0] request_terminal_entry, request_producer_pc, request_end_pc,
    input wire native_active, native_producer_take, native_end_take, native_done, native_am_any,
    input wire [IDW-1:0] native_identity,
    input wire [PAW-1:0] native_entry, native_pc,
    input wire [NW-1:0] native_next_token,
    input wire [31:0] native_next_value,
    input wire coverage_valid, coverage_wholeplan_complete,
    input wire [IDW-1:0] coverage_identity,
    input wire visibility_valid, visibility_fault,
    input wire [IDW-1:0] visibility_identity,
    // [0] continuation, [1] KV, [2] index, [3] remote, [4] all copies.
    input wire [4:0] visibility,
    input wire c8_write_quiet, c8_quarantine, c8_fault,
    input wire capture_live, capture_drained, capture_fault,
    input wire collective_busy, collective_fault, native_fault,
    input wire stage_accepted,
    output wire stage_done,
    output wire [NW-1:0] stage_next_token,
    output wire [31:0] stage_next_value,
    output wire terminal_kind, token_result_valid, stage_handoff_done,
    output wire pending, fault
);
    generate if (ENABLE) begin : g_join
        reg active=0, fresh=0, end_pending=0, held=0, poison=0;
        reg kind=0;
        reg [IDW-1:0] identity=0;
        reg [PAW-1:0] entry=0, producer_pc=0, end_pc=0;
        reg [NW-1:0] token=0;
        reg [31:0] value=0;
        wire bad = c8_quarantine || c8_fault || capture_fault ||
                   collective_fault || native_fault || visibility_fault;
        wire scope = native_active && native_identity == identity && native_entry == entry;
        // END updates native done/data on its own edge. In the following cycle
        // this bypass permits the ORIGINAL acceptance edge, without a +1 stage.
        wire capture_now = active && end_pending && scope && native_done && !held;
        wire coverage_ok = (coverage_valid === 1'b1) &&
                           (coverage_wholeplan_complete === 1'b1) && coverage_identity == identity;
        wire visibility_ok = (visibility_valid === 1'b1) &&
                             (visibility === 5'b11111) && visibility_identity == identity;
        wire health_ok = (c8_write_quiet === 1'b1) &&
                         (capture_live === 1'b0) && (capture_drained === 1'b1) &&
                         (collective_busy === 1'b0) && (bad === 1'b0);
        assign stage_done = rst_n && active && !poison && health_ok &&
                            coverage_ok && visibility_ok && (held || capture_now);
        assign stage_next_token = held ? token : capture_now ? native_next_token : {NW{1'b0}};
        assign stage_next_value = held ? value : capture_now ? native_next_value : 32'b0;
        assign terminal_kind = kind;
        assign token_result_valid = stage_done && !kind;
        assign stage_handoff_done = stage_done && kind;
        wire accept = stage_done && stage_accepted;
        assign request_ready = rst_n && !poison && (bad === 1'b0) &&
                               (request_binding_valid === 1'b1) &&
                               ((request_kind === 1'b1) ||
                                ((request_kind === 1'b0) && request_producer_pc < request_end_pc)) &&
                               request_terminal_entry <= request_end_pc && (!active || accept);
        wire take = request_v && request_ready;
        assign pending = active;
        assign fault = poison;
        always @(posedge clk) begin
            // Warm reset never erases an accepted request/result or its debt.
            if (!rst_n) begin
                if (active) poison <= 1'b1;
            end else if (!poison) begin
                if (bad || (stage_accepted && !stage_done)) poison <= 1'b1;
                if (active && scope && native_producer_take)
                    fresh <= native_pc == producer_pc;
                if (active && scope && native_end_take) begin
                    if (native_pc != end_pc || (!kind && (!fresh || !native_am_any)) || held || end_pending)
                        poison <= 1'b1;
                    else end_pending <= 1'b1;
                end
                if (capture_now) begin
                    token <= native_next_token; value <= native_next_value;
                    held <= 1'b1; end_pending <= 1'b0;
                end
                // Retire the old accepted result before retaining a simultaneous
                // new request. Metadata/result belonging to the old edge wins
                // at the output; new metadata becomes visible after that edge.
                if (accept) begin
                    active <= 1'b0; fresh <= 1'b0; end_pending <= 1'b0; held <= 1'b0;
                end
                if (take) begin
                    active <= 1'b1; fresh <= 1'b0; end_pending <= 1'b0; held <= 1'b0;
                    kind <= request_kind;
                    identity <= request_identity; entry <= request_terminal_entry;
                    producer_pc <= request_producer_pc; end_pc <= request_end_pc;
                end
            end
        end
    end else begin : g_disabled
        assign request_ready=0; assign stage_done=0;
        assign stage_next_token=0; assign stage_next_value=0;
        assign terminal_kind=0; assign token_result_valid=0; assign stage_handoff_done=0;
        assign pending=0; assign fault=0;
    end endgenerate
endmodule
