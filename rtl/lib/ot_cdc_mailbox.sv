`timescale 1ns/1ps
// One-outstanding, closed-loop four-phase CDC mailbox.  Request and response
// payloads remain stable while their associated levels traverse two-flop
// synchronizers.  Online levels distinguish reset state from protocol state.
//
// If the destination resets with a request outstanding, the request is replayed
// after the online rendezvous.  Therefore the destination operation must share
// dst_rst_n (as the stage schedule controller does) or be explicitly idempotent.
module ot_cdc_mailbox #(
    parameter integer WIDTH = 32,
    parameter integer RESPONSE_W = 1
) (
    input  wire                         src_clk,
    input  wire                         src_rst_n,
    input  wire                         src_valid,
    output wire                         src_ready,
    input  wire [WIDTH-1:0]             src_data,
    output reg                          src_done,
    output reg [RESPONSE_W-1:0]         src_response,

    input  wire                         dst_clk,
    input  wire                         dst_rst_n,
    output wire                         dst_valid,
    input  wire                         dst_ready,
    output wire [WIDTH-1:0]             dst_data,
    input  wire [RESPONSE_W-1:0]        dst_response
);
    // Source-domain request state.
    reg [WIDTH-1:0] payload_hold;
    reg request_level;
    reg source_waiting;
    reg source_online;
    (* async_reg = "true" *) reg ack_sync1, ack_sync2;
    (* async_reg = "true" *) reg dst_online_sync1, dst_online_sync2;

    // Destination-domain request/response state.
    reg [WIDTH-1:0] payload_capture;
    reg [RESPONSE_W-1:0] response_hold;
    reg acknowledge_level;
    reg destination_valid;
    reg destination_online;
    (* async_reg = "true" *) reg request_sync1, request_sync2;
    (* async_reg = "true" *) reg src_online_sync1, src_online_sync2;

    assign src_ready = source_online && dst_online_sync2 &&
                       !source_waiting && !request_level && !ack_sync2;
    assign dst_valid = destination_valid && src_online_sync2 && request_sync2;
    assign dst_data = payload_capture;

    always @(posedge src_clk or negedge src_rst_n) begin
        if (!src_rst_n) begin
            payload_hold <= {WIDTH{1'b0}};
            request_level <= 1'b0;
            source_waiting <= 1'b0;
            source_online <= 1'b0;
            ack_sync1 <= 1'b0;
            ack_sync2 <= 1'b0;
            dst_online_sync1 <= 1'b0;
            dst_online_sync2 <= 1'b0;
            src_done <= 1'b0;
            src_response <= {RESPONSE_W{1'b0}};
        end else begin
            source_online <= 1'b1;
            ack_sync1 <= acknowledge_level;
            ack_sync2 <= ack_sync1;
            dst_online_sync1 <= destination_online;
            dst_online_sync2 <= dst_online_sync1;
            src_done <= 1'b0;

            if (src_valid && src_ready) begin
                payload_hold <= src_data;
                request_level <= 1'b1;
                source_waiting <= 1'b1;
            end

            if (source_waiting && ack_sync2) begin
                src_response <= response_hold;
                src_done <= 1'b1;
                request_level <= 1'b0;
                source_waiting <= 1'b0;
            end
        end
    end

    always @(posedge dst_clk or negedge dst_rst_n) begin
        if (!dst_rst_n) begin
            payload_capture <= {WIDTH{1'b0}};
            response_hold <= {RESPONSE_W{1'b0}};
            acknowledge_level <= 1'b0;
            destination_valid <= 1'b0;
            destination_online <= 1'b0;
            request_sync1 <= 1'b0;
            request_sync2 <= 1'b0;
            src_online_sync1 <= 1'b0;
            src_online_sync2 <= 1'b0;
        end else begin
            destination_online <= 1'b1;
            request_sync1 <= request_level;
            request_sync2 <= request_sync1;
            src_online_sync1 <= source_online;
            src_online_sync2 <= src_online_sync1;

            if (!src_online_sync2 || !request_sync2) begin
                // Source reset/cancellation or the return-to-zero phase.
                destination_valid <= 1'b0;
                acknowledge_level <= 1'b0;
            end else if (!acknowledge_level) begin
                if (!destination_valid) begin
                    // The source payload has been stable for at least the two
                    // request synchronizer stages before this capture.
                    payload_capture <= payload_hold;
                    destination_valid <= 1'b1;
                end else if (dst_ready) begin
                    response_hold <= dst_response;
                    destination_valid <= 1'b0;
                    acknowledge_level <= 1'b1;
                end
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (WIDTH < 1 || RESPONSE_W < 1)
            $error("ot_cdc_mailbox requires positive widths");
    end
`endif
endmodule
