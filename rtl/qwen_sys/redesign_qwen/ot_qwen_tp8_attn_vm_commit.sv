`timescale 1ns/1ps
// Native-only integration candidate. A kernel result handshake is NOT a VM
// commit. Hold each registered word through write acceptance and matching
// receiver commit before accepting the next result. Throughput UNMEASURED.
module ot_qwen_tp8_attn_vm_commit #(
    parameter integer ATTN_BASE = 50672
) (
    input wire clk, input wire rst_n,
    input wire start, input wire [15:0] epoch, input wire [5:0] layer,
    input wire res_valid, output wire res_ready,
    input wire [4:0] res_beat, input wire [511:0] res_data,
    input wire [15:0] res_epoch, input wire [5:0] res_layer,
    output wire vm_valid, input wire vm_ready,
    output wire [23:0] vm_word_addr, output wire [511:0] vm_data,
    output wire [4:0] vm_beat, output wire [15:0] vm_epoch,
    output wire [5:0] vm_layer,
    input wire commit_valid, input wire [4:0] commit_beat,
    input wire [15:0] commit_epoch, input wire [5:0] commit_layer,
    output reg done, output reg fault,
    output reg [5:0] committed_words
);
    reg active, buffered, sent;
    reg [15:0] epoch_q; reg [5:0] layer_q;
    reg [4:0] beat_q; reg [511:0] data_q;
    wire result_matches = res_epoch == epoch_q && res_layer == layer_q &&
                          {1'b0,res_beat} == committed_words;
    assign res_ready = active && !buffered && result_matches && !fault;
    assign vm_valid = buffered && !sent && !fault;
    assign vm_word_addr = ATTN_BASE/16 + beat_q;
    assign vm_data = data_q;
    assign vm_beat = beat_q; assign vm_epoch = epoch_q; assign vm_layer = layer_q;
    wire issue = vm_valid && vm_ready;
    wire ack_matches = buffered && (sent || issue) &&
                       commit_beat == beat_q && commit_epoch == epoch_q && commit_layer == layer_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 0; buffered <= 0; sent <= 0; done <= 0; fault <= 0;
            committed_words <= 0; epoch_q <= 0; layer_q <= 0; beat_q <= 0; data_q <= 0;
        end else if (start) begin
            if (active || buffered) fault <= 1;
            else begin
                active <= 1; buffered <= 0; sent <= 0; done <= 0; fault <= 0;
                committed_words <= 0; epoch_q <= epoch; layer_q <= layer;
            end
        end else begin
            if (res_valid && active && !buffered && !result_matches) fault <= 1;
            if (res_valid && res_ready) begin buffered <= 1; sent <= 0; beat_q <= res_beat; data_q <= res_data; end
            if (issue) sent <= 1;
            if (commit_valid) begin
                if (!ack_matches) fault <= 1;
                else begin
                    buffered <= 0; sent <= 0; committed_words <= committed_words + 1;
                    if (committed_words == 31) begin done <= 1; active <= 0; end
                end
            end
        end
    end
endmodule
