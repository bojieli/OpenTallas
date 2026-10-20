`timescale 1ns/1ps
// Functional candidate: sole shared epoch allocator. Only POR resets identity.
// warm_ready suppresses admission during soft reset; it does not reset state.
module ot_qwen_tp8_token_epoch_allocator #(
    parameter [15:0] INITIAL_EPOCH = 16'd0
) (
    input wire clk, input wire por_n, input wire warm_ready,
    input wire request_valid, output wire request_ready,
    input wire [17:0] request_token, input wire [17:0] request_position,
    input wire [1:0] request_generation,
    output wire grant_valid, input wire grant_ready,
    output reg [15:0] grant_epoch, output reg [17:0] grant_token,
    output reg [17:0] grant_position, output reg [1:0] grant_generation,
    output wire [58:0] grant_tag,
    // Actual allocation witness remains visible during warm-reset/abort while
    // delivery-valid is suppressed. Tuple pins above retain the accepted data.
    output wire allocated_valid, output wire allocated_delivered,
    input wire terminal_valid, input wire [58:0] terminal_tag,
    input wire [1:0] terminal_generation,
    input wire terminal_done, input wire terminal_fault, input wire terminal_kv_drained,
    input wire terminal_vm_drained, input wire terminal_collective_drained,
    input wire terminal_host_drained,
    // Assert only from actual drained links reset and retraining completion.
    input wire wrap_fence_valid, input wire wrap_links_drained,
    input wire wrap_link_reset_seen, input wire wrap_retraining_done,
    output reg busy, output reg wrap_locked, output reg identity_fault,
    output reg terminal_accepted
);
    reg [15:0] next_epoch;
    reg grant_delivered, grant_pending, terminal_consumed;
    wire [58:0] expected_terminal = {grant_epoch,6'd37,grant_token,grant_position[12:0],6'd0};
    assign grant_tag = {grant_epoch,6'd0,grant_token,grant_position[12:0],6'd0};
    assign allocated_valid = busy || grant_pending;
    assign allocated_delivered = busy && grant_delivered;
    wire terminal_identity_ok = busy && (grant_delivered || terminal_fault) &&
         terminal_tag == expected_terminal && terminal_generation == grant_generation &&
         (terminal_done || terminal_fault);
    wire invalid_terminal = terminal_valid && !terminal_consumed && !terminal_identity_ok;
    wire invalid_request = request_valid && (request_position >= 18'd8192 || request_token >= 18'd151936);
    assign grant_valid = grant_pending && !identity_fault && !invalid_terminal && warm_ready;
    assign request_ready = por_n && warm_ready && !identity_fault && !terminal_valid && !terminal_consumed &&
                           !busy && !grant_pending && !wrap_locked &&
                           request_position < 18'd8192 && request_token < 18'd151936;
    wire drains = terminal_kv_drained && terminal_vm_drained &&
                  terminal_collective_drained && terminal_host_drained;
    always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            next_epoch <= INITIAL_EPOCH; grant_pending <= 0; grant_epoch <= 0;
            grant_token <= 0; grant_position <= 0; grant_generation <= 0;
            busy <= 0; wrap_locked <= 0; identity_fault <= 0;
            grant_delivered <= 0; terminal_consumed <= 0; terminal_accepted <= 0;
        end else begin
            terminal_accepted <= 0;
            if (!terminal_valid) terminal_consumed <= 0;
            if (invalid_request)
                identity_fault <= 1;
            if (request_valid && request_ready) begin
                grant_epoch <= next_epoch; grant_token <= request_token;
                grant_position <= request_position; grant_generation <= request_generation;
                grant_pending <= 1; busy <= 1; grant_delivered <= 0;
                if (next_epoch == 16'hffff) wrap_locked <= 1;
                else next_epoch <= next_epoch + 1'b1;
            end
            if (grant_valid && grant_ready && warm_ready) begin
                grant_pending <= 0; grant_delivered <= 1;
            end
            if (terminal_valid && !terminal_consumed) begin
                if (!terminal_identity_ok)
                    identity_fault <= 1;
                else if (drains) begin busy <= 0; grant_pending <= 0; terminal_consumed <= 1; terminal_accepted <= 1; end
            end
            if (wrap_fence_valid) begin
                if (!terminal_valid && !terminal_consumed && !invalid_request &&
                    !busy && !grant_pending && (wrap_locked || identity_fault) && drains && wrap_links_drained &&
                    wrap_link_reset_seen && wrap_retraining_done) begin
                    if (wrap_locked) begin next_epoch <= 0; wrap_locked <= 0; end
                    identity_fault <= 0;
                end else identity_fault <= 1;
            end
        end
    end
endmodule
