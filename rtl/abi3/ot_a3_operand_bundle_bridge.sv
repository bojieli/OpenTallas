`timescale 1ns/1ps
// Baseline variable-latency bundle adapter. One outstanding fetch prevents
// reordering; complete bundles reserve all planes before lane issue. The output
// is delayed one edge AFTER issue to match the lane's registered SRAM request.
// Reset/clear requires the upstream service to flush outstanding responses.
// This conservative one-entry bridge establishes timing/ownership correctness;
// it does not claim one bundle/cycle or replace the planned deeper prefetch queue.
module ot_a3_operand_bundle_bridge #(
    parameter integer ADDRESS_BITS = 128,
    parameter integer DATA_BITS = 192
) (
    input wire clk, rst_n, clear,
    input wire lane_request,
    input wire [ADDRESS_BITS-1:0] lane_address,
    input wire lane_issue,
    output wire lane_credit,
    output reg [DATA_BITS-1:0] lane_data,
    output wire service_valid,
    input wire service_ready,
    output wire [ADDRESS_BITS-1:0] service_address,
    input wire response_valid,
    output wire response_ready,
    input wire [DATA_BITS-1:0] response_data
);
    localparam [1:0] IDLE=0, SEND=1, WAITING=2, HELD=3;
    reg [1:0] state;
    reg [ADDRESS_BITS-1:0] address_q;
    reg [DATA_BITS-1:0] bundle_q, deliver_q;
    reg deliver_pending;
    assign service_valid = rst_n && !clear && state == SEND;
    assign service_address = address_q;
    assign response_ready = rst_n && !clear && state == WAITING;
    assign lane_credit = rst_n && !clear && state == HELD;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; address_q <= 0; bundle_q <= 0;
            deliver_q <= 0; deliver_pending <= 0; lane_data <= 0;
        end else if (clear) begin
            state <= IDLE; deliver_pending <= 0; lane_data <= 0;
        end else begin
            deliver_pending <= 0;
            if (deliver_pending) lane_data <= deliver_q;
            case(state)
                IDLE: if(lane_request) begin
                    address_q <= lane_address;
                    state <= SEND;
                end
                SEND: if(service_ready) state <= WAITING;
                WAITING: if(response_valid) begin
                    bundle_q <= response_data;
                    state <= HELD;
                end
                HELD: if(lane_issue) begin
                    deliver_q <= bundle_q;
                    deliver_pending <= 1;
                    state <= IDLE;
                end
            endcase
        end
    end
endmodule
