`timescale 1ns/1ps
// Opt-in integration seam for the split ME controller. This block provides
// routing and status ownership only; providers must implement every ISA effect.
// Default preserves the historical ROM path. Native admission requires a real
// service and its exact program contract: separate QK/PV for the original
// image, or the explicitly lowered fused request for the candidate image.
// The integrating wrapper must bind native_contract_ready to that image's
// verified capability, never merely to the presence of any attention kernel.
module ot_qwen_tp8_me_provider_dispatch #(
    parameter integer NATIVE_ATTENTION = 0
) (
    input wire clk, input wire rst_n,
    input wire ctrl_go, input wire ctrl_wsrc,
    input wire native_contract_ready,
    input wire rom_ready, input wire rom_idle,
    input wire [15:0] rom_progress, input wire rom_fault,
    input wire attn_ready, input wire attn_idle,
    input wire [15:0] attn_progress, input wire attn_fault,
    output wire rom_go, output wire attn_go,
    output wire ctrl_ready, output wire ctrl_idle,
    output wire [15:0] ctrl_progress, output wire ctrl_fault,
    output wire descriptor_native, output wire accepted_provider_native,
    output reg dispatch_fault
);
    // NEXT can change before the previous provider drains. Progress/faults
    // belong to the last ACCEPTED operation, never to NEXT's WSRC selector.
    reg accepted_native;
    wire request_native = (NATIVE_ATTENTION != 0) && ctrl_wsrc;
    // The local clock predictor needs both identities. Descriptor identifies
    // NEXT's wake request; accepted identity owns in-flight status. Transport
    // both through the same stations/epochs as the matching command/return.
    assign descriptor_native = request_native;
    assign accepted_provider_native = accepted_native;
    wire all_idle = rom_idle && ((NATIVE_ATTENTION == 0) || attn_idle);
    assign ctrl_ready = (NATIVE_ATTENTION == 0) ? rom_ready :
                        (all_idle && (request_native ?
                         (native_contract_ready && attn_ready) : rom_ready));
    assign rom_go = ctrl_go && ctrl_ready && !request_native;
    assign attn_go = ctrl_go && ctrl_ready && request_native;
    assign ctrl_idle = all_idle;
    assign ctrl_progress = accepted_native ? attn_progress : rom_progress;
    assign ctrl_fault = dispatch_fault || (accepted_native ? attn_fault : rom_fault);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin accepted_native <= 1'b0; dispatch_fault <= 1'b0; end
        else begin
            if (ctrl_go && ctrl_ready) accepted_native <= request_native;
            if (ctrl_go && !ctrl_ready) dispatch_fault <= 1'b1;
        end
    end
endmodule
