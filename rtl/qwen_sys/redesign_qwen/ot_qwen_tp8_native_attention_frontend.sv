`timescale 1ns/1ps
// External actual-kernel ABI frontend. The harness must bind every kernel port
// to the source-pinned compiled production attention service, never golden data.
// Default-off candidate integration. Requires the actual fused service and a
// source-bound lowered payload program. All clocks here are one functional
// bench clock; routed domain/CDC qualification is a separate requirement.
module ot_qwen_tp8_native_attention_frontend (
    input wire clk, input wire rst_n,
    input wire request_valid, output wire request_ready,
    input wire fused_program_capability,
    input wire [15:0] request_epoch, input wire [5:0] request_layer,
    input wire [17:0] request_position,
    input wire [3:0] kv_landing_committed, input wire q_reader_idle,
    output wire q_reader_start,
    input wire q_valid, output wire q_ready,
    input wire [4:0] q_beat, input wire [511:0] q_data,
    input wire [15:0] q_epoch, input wire [5:0] q_layer,
    input wire [15:0] active_epoch, input wire [5:0] active_layer,
    output wire vm_valid, input wire vm_ready,
    output wire [23:0] vm_word_addr, output wire [511:0] vm_data,
    output wire [4:0] vm_beat, output wire [15:0] vm_epoch,
    output wire [5:0] vm_layer,
    input wire commit_valid, input wire [4:0] commit_beat,
    input wire [15:0] commit_epoch, input wire [5:0] commit_layer,
    output wire idle, output reg completed, output wire fault,
    output wire [5:0] committed_words,
    output wire kernel_request_valid,
    output wire [15:0] kernel_request_epoch, output wire [5:0] kernel_request_layer,
    output wire [17:0] kernel_request_position, output wire kernel_capability,
    output wire kernel_q_valid, output wire [4:0] kernel_q_beat, output wire [511:0] kernel_q_data,
    input wire service_ready, service_busy, service_fault, service_done, service_q_ready,
    input wire result_valid, output wire result_ready,
    input wire [4:0] result_beat, input wire [511:0] result_data,
    input wire [15:0] result_epoch, input wire [5:0] result_layer
);
    reg active, kernel_done_seen, local_fault;
    wire bridge_done, bridge_fault;
    wire q_matches = q_epoch == active_epoch && q_layer == active_layer;
    assign fault = local_fault || service_fault || bridge_fault;
    assign idle = !active && !service_busy && !fault;
    assign request_ready = idle && service_ready && fused_program_capability &&
                           (&kv_landing_committed) && q_reader_idle;
    wire accept = request_valid && request_ready;
    assign q_reader_start = accept;
    assign q_ready = active && q_matches && service_q_ready && !fault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin active <= 0; kernel_done_seen <= 0; local_fault <= 0; completed <= 0; end
        else begin
            completed <= 0;
            if (request_valid && !fused_program_capability) local_fault <= 1;
            if (q_valid && active && !q_matches) local_fault <= 1;
            if (accept) begin active <= 1; kernel_done_seen <= 0; end
            if (service_done) kernel_done_seen <= 1;
            if (active && bridge_done && kernel_done_seen && !fault) begin
                active <= 0; completed <= 1;
            end
        end
    end
    assign kernel_request_valid = accept;
    assign kernel_request_epoch = request_epoch;
    assign kernel_request_layer = request_layer;
    assign kernel_request_position = request_position;
    assign kernel_capability = fused_program_capability;
    assign kernel_q_valid = q_valid && q_ready;
    assign kernel_q_beat = q_beat;
    assign kernel_q_data = q_data;
    ot_qwen_tp8_attn_vm_commit commit_bridge (
        .clk(clk), .rst_n(rst_n), .start(accept), .epoch(request_epoch), .layer(request_layer),
        .res_valid(result_valid), .res_ready(result_ready), .res_beat(result_beat), .res_data(result_data),
        .res_epoch(result_epoch), .res_layer(result_layer),
        .vm_valid(vm_valid), .vm_ready(vm_ready), .vm_word_addr(vm_word_addr), .vm_data(vm_data),
        .vm_beat(vm_beat), .vm_epoch(vm_epoch), .vm_layer(vm_layer),
        .commit_valid(commit_valid), .commit_beat(commit_beat), .commit_epoch(commit_epoch),
        .commit_layer(commit_layer), .done(bridge_done), .fault(bridge_fault), .committed_words(committed_words));
endmodule
