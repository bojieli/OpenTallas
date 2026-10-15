`timescale 1ns/1ps
// Functional candidate. Events are actual credited endpoint request pulses,
// not offered HC packets or inferred transport completion. Identity is POR-only.
module ot_qwen_tp8_token_cohort (
    input wire clk, input wire por_n, input wire warm_ready,
    input wire begin_valid, output wire begin_ready,
    input wire [58:0] begin_tag, input wire [1:0] begin_generation,
    input wire [7:0] request_valid,
    input wire [471:0] request_tag, input wire [15:0] request_generation,
    output reg [7:0] request_credit,
    output wire dispatch_valid, input wire dispatch_ready,
    output reg [58:0] cohort_tag, output reg [1:0] cohort_generation,
    output reg [7:0] accepted_ranks, output reg active,
    output reg dispatched, output reg identity_fault,
    // A held terminal is consumed once. Caller binds this to the actual
    // matching allocator terminal snapshot and genuine system drain proof.
    input wire terminal_valid, input wire [58:0] terminal_tag,
    input wire [1:0] terminal_generation, input wire terminal_done,
    input wire terminal_fault, input wire kv_drained, input wire vm_drained,
    input wire collective_drained, input wire host_drained,
    output reg terminal_accepted,
    // Fault recovery additionally requires genuine coherent link reset.
    input wire recovery_valid, input wire links_drained,
    input wire link_reset_seen, input wire retraining_done
);
    reg terminal_consumed;
    integer rank;
    wire begin_identity_ok = begin_tag[42:37] == 6'd0 &&
        begin_tag[5:0] == 6'd0 && begin_tag[36:19] < 18'd151936;
    wire [58:0] expected_terminal = {cohort_tag[58:43],6'd37,cohort_tag[36:0]};
    wire drains = kv_drained && vm_drained && collective_drained && host_drained;
    wire terminal_matches = active && terminal_tag == expected_terminal &&
        terminal_generation == cohort_generation && (terminal_done || terminal_fault) &&
        (terminal_fault || dispatched);
    wire invalid_terminal = terminal_valid && !terminal_consumed && !terminal_matches;
    wire invalid_begin = begin_valid && !begin_identity_ok;
    wire invalid_request = |request_valid && (!active || !warm_ready);
    assign begin_ready = por_n && warm_ready && !active && !identity_fault &&
        !terminal_valid && !terminal_consumed && !(|request_valid) && begin_identity_ok;
    // Combinational blocking of a new invalid event prevents dispatch on the
    // same edge on which a late duplicate/stale participant is diagnosed.
    reg participant_fault;
    always @* begin
        participant_fault = invalid_request;
        for (integer r = 0; r < 8; r = r + 1)
            if (request_valid[r] && (accepted_ranks[r] ||
                request_tag[59*r +: 59] != cohort_tag ||
                request_generation[2*r +: 2] != cohort_generation))
                participant_fault = 1;
    end
    assign dispatch_valid = active && (&accepted_ranks) && !dispatched &&
        warm_ready && !identity_fault && !participant_fault && !invalid_terminal && !invalid_begin;
    always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            active <= 0; dispatched <= 0; identity_fault <= 0;
            cohort_tag <= 0; cohort_generation <= 0; accepted_ranks <= 0;
            request_credit <= 0; terminal_accepted <= 0; terminal_consumed <= 0;
        end else begin
            request_credit <= 0; terminal_accepted <= 0;
            if (!terminal_valid) terminal_consumed <= 0;
            if (invalid_begin) identity_fault <= 1;
            if (begin_valid && begin_ready) begin
                active <= 1; dispatched <= 0; accepted_ranks <= 0;
                cohort_tag <= begin_tag; cohort_generation <= begin_generation;
            end
            if (participant_fault || invalid_terminal) identity_fault <= 1;
            if (active && warm_ready && !identity_fault && !participant_fault && !invalid_terminal)
                for (rank = 0; rank < 8; rank = rank + 1)
                    if (request_valid[rank]) begin
                        accepted_ranks[rank] <= 1;
                        request_credit[rank] <= 1;
                    end
            if (dispatch_valid && dispatch_ready) dispatched <= 1;
            if (terminal_valid && !terminal_consumed && terminal_matches && drains) begin
                active <= 0; accepted_ranks <= 0; dispatched <= 0;
                terminal_accepted <= 1; terminal_consumed <= 1;
            end
            if (recovery_valid) begin
                if (!active && !begin_valid && !terminal_valid && !terminal_consumed && !(|request_valid) &&
                    drains && links_drained && link_reset_seen && retraining_done)
                    identity_fault <= 0;
                else identity_fault <= 1;
            end
        end
    end
endmodule
