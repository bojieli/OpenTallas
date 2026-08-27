`timescale 1ns/1ps
// Public stage-link endpoint.  Physical serialization/equalization is outside
// this wrapper; the logical packet contract is fully exercised by the TX/RX
// behavioral blocks.
module ot_stage_link_endpoint #(
    parameter integer FLIT_W = 256,
    parameter integer MAX_FLITS = 256,
    parameter integer SEQ_W = 8,
    parameter integer RETRY_MAX = 2,
    parameter integer ACK_TIMEOUT = 1024
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         tx_in_valid,
    output wire                         tx_in_ready,
    input  wire [FLIT_W-1:0]             tx_in_flit,
    input  wire                         tx_in_last,
    input  wire [SEQ_W-1:0]             tx_in_packet_seq,
    input  wire                         tx_remote_credit,
    output wire                         tx_link_valid,
    input  wire                         tx_link_ready,
    output wire [FLIT_W-1:0]             tx_link_flit,
    output wire [31:0]                  tx_link_flit_crc,
    output wire [31:0]                  tx_link_packet_crc,
    output wire                         tx_link_last,
    output wire [SEQ_W-1:0]             tx_link_packet_seq,
    input  wire                         tx_ack_valid,
    input  wire [SEQ_W-1:0]              tx_ack_seq,
    input  wire                         tx_ack_ok,
    input  wire                         rx_link_valid,
    output wire                         rx_link_ready,
    input  wire [FLIT_W-1:0]             rx_link_flit,
    input  wire [31:0]                  rx_link_flit_crc,
    input  wire [31:0]                  rx_link_packet_crc,
    input  wire                         rx_link_last,
    input  wire [SEQ_W-1:0]             rx_link_packet_seq,
    output wire                         rx_out_valid,
    input  wire                         rx_out_ready,
    output wire [FLIT_W-1:0]             rx_out_flit,
    output wire                         rx_out_last,
    output wire [SEQ_W-1:0]              rx_out_packet_seq,
    output wire                         rx_out_poison,
    output wire                         rx_ack_valid,
    output wire [SEQ_W-1:0]              rx_ack_seq,
    output wire                         rx_ack_ok,
    output wire                         tx_busy,
    output wire [1:0]                   tx_retry_count,
    output wire                         tx_timeout,
    output wire                         tx_error,
    output wire                         rx_protocol_error,
    output wire                         rx_duplicate_packet
);
    ot_stage_link_tx #(
        .FLIT_W(FLIT_W), .MAX_FLITS(MAX_FLITS), .SEQ_W(SEQ_W),
        .RETRY_MAX(RETRY_MAX), .ACK_TIMEOUT(ACK_TIMEOUT)
    ) tx (
        .clk(clk), .rst_n(rst_n), .in_valid(tx_in_valid), .in_ready(tx_in_ready),
        .in_flit(tx_in_flit), .in_last(tx_in_last), .in_packet_seq(tx_in_packet_seq),
        .remote_credit(tx_remote_credit), .credit_consumed(),
        .link_valid(tx_link_valid), .link_ready(tx_link_ready), .link_flit(tx_link_flit),
        .link_flit_crc(tx_link_flit_crc), .link_packet_crc(tx_link_packet_crc),
        .link_last(tx_link_last), .link_packet_seq(tx_link_packet_seq),
        .ack_valid(tx_ack_valid), .ack_seq(tx_ack_seq), .ack_ok(tx_ack_ok),
        .abort(1'b0), .busy(tx_busy), .retry_count(tx_retry_count),
        .timeout(tx_timeout), .error(tx_error)
    );

    ot_stage_link_rx #(
        .FLIT_W(FLIT_W), .MAX_FLITS(MAX_FLITS), .SEQ_W(SEQ_W)
    ) rx (
        .clk(clk), .rst_n(rst_n), .link_valid(rx_link_valid), .link_ready(rx_link_ready),
        .link_flit(rx_link_flit), .link_flit_crc(rx_link_flit_crc),
        .link_packet_crc(rx_link_packet_crc), .link_last(rx_link_last),
        .link_packet_seq(rx_link_packet_seq), .out_valid(rx_out_valid),
        .out_ready(rx_out_ready), .out_flit(rx_out_flit), .out_last(rx_out_last),
        .out_packet_seq(rx_out_packet_seq), .out_poison(rx_out_poison),
        .ack_valid(rx_ack_valid), .ack_seq(rx_ack_seq), .ack_ok(rx_ack_ok),
        .protocol_error(rx_protocol_error), .duplicate_packet(rx_duplicate_packet)
    );
endmodule
