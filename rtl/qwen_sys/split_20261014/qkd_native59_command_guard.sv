`timescale 1ns/1ps
// Actual fused PC11 descriptor + authoritative HOST token/context receiver.
// This boundary contains no allocator, inferred epoch, ready stall or helper ACK.
// Every descriptor bit is checked against the actual source-pinned fused image.
// Context producers, provider binding, physical pins and compiled slots remain
// mandatory at die integration. This block is not a substitute for native59.
module qkd_native59_command_guard #(
    // Packed qfd_tt_ctlm_s command order, not the ROM instruction encoding.
    parameter [379:0] COMMAND = {24'd0,1'b0,1'b0,1'b1,1'b1,
        24'd1,24'd1,24'd3167,1'b0,24'd0,4'd0,3'd0,
        24'd0,24'd0,24'd1,24'd13696,24'd0,24'd0,24'd0,24'd0,
        1'b1,18'd128,18'd1,18'd512,1'b1},
    parameter integer MUT = 0
) (
    input wire ck, rst_n,
    input wire command_valid,
    input wire [379:0] command,
    input wire [58:0] command_tag,
    input wire fused_program_capability,
    // Actual HOST allocator/cohort certificate and typed TT stage, never a
    // token counter created at this endpoint. Epoch is shared by all 36 layers.
    input wire authority_valid,
    input wire [15:0] authority_epoch,
    input wire [17:0] authority_token, authority_position,
    input wire [5:0] authority_stage,
    output reg accepted,
    output reg [379:0] accepted_command,
    output reg [58:0] accepted_tag,
    output wire [23:0] native_xbase, native_obase,
    output wire [17:0] native_nout, native_k, native_position,
    output wire [15:0] native_epoch,
    output wire [5:0] native_layer,
    output reg fault,
    output reg [2:0] fault_cause
);
    reg valid_q, capability_q, authority_q;
    reg [379:0] command_q;
    reg [58:0] tag_q;
    reg [15:0] authority_epoch_q;
    reg [17:0] authority_token_q, authority_position_q;
    reg [5:0] authority_stage_q;
    always @(posedge ck) begin
        command_q <= command; tag_q <= command_tag;
        capability_q <= fused_program_capability; authority_q <= authority_valid;
        authority_epoch_q <= authority_epoch; authority_token_q <= authority_token;
        authority_position_q <= authority_position; authority_stage_q <= authority_stage;
    end
    wire descriptor_ok = MUT == 1 || command_q == COMMAND;
    wire identity_ok = MUT == 2 ||
        (authority_q && authority_token_q < 18'd151936 && authority_position_q < 18'd8192 &&
         authority_stage_q >= 6'd1 && authority_stage_q <= 6'd36 &&
         tag_q == {authority_epoch_q, authority_stage_q, authority_token_q, authority_position_q[12:0], 6'd0});
    wire image_ok = capability_q || MUT == 3;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            valid_q <= 0; accepted <= 0; accepted_command <= 0; accepted_tag <= 0;
            fault <= 0; fault_cause <= 0;
        end else begin
            valid_q <= command_valid;
            accepted <= 0;
            if (valid_q && !fault) begin
                if (!descriptor_ok || !identity_ok || !image_ok) begin
                    fault <= 1;
                    fault_cause <= {!image_ok, !identity_ok, !descriptor_ok};
                end else begin
                    accepted <= 1;
                    accepted_command <= command_q;
                    accepted_tag <= tag_q;
                end
            end
        end
    end
    assign native_xbase = accepted_command[175:152];
    assign native_obase = accepted_command[303:280];
    assign native_nout = accepted_command[18:1];
    assign native_k = accepted_command[54:37];
    assign native_position = {5'd0,accepted_tag[18:6]};
    assign native_epoch = accepted_tag[58:43];
    assign native_layer = accepted_tag[42:37] - 6'd1;
endmodule
