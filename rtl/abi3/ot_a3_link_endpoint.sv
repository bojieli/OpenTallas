`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One complete ABI 3.0 inter-chip endpoint for a single directed hop: the
// sending half with its bounded credit window, CRC32C and bounded replay, and
// the receiving half with its integrity check, sequence check and credit
// return.  This is the block the physical flow implements, so that the
// endpoint the analytical model charges a traversal to has a routed area and a
// post-route arrival time rather than only a cycle count.
//
// The wire is NOT inside this module.  A hop's physical delay is a property of
// the interconnect between two of these, and nothing in this repository has
// measured it.
// ---------------------------------------------------------------------------
module ot_a3_link_endpoint #(
    parameter integer FLIT_W      = 64,
    parameter integer CREDITS     = 8,
    parameter integer RETRY_MAX   = 3,
    parameter integer ACK_TIMEOUT = 512
) (
    input  wire                  clk,
    input  wire                  rst_n,

    // service side of the sending half
    input  wire                  tx_in_valid,
    output wire                  tx_in_ready,
    input  wire [FLIT_W-1:0]     tx_in_flit,

    // outgoing wire
    output wire                  tx_w_valid,
    output wire [FLIT_W-1:0]     tx_w_flit,
    output wire [7:0]            tx_w_seq,
    output wire [31:0]           tx_w_crc,

    // return path arriving from the far end
    input  wire                  tx_r_ack,
    input  wire [7:0]            tx_r_ack_seq,
    input  wire [1:0]            tx_r_credit,
    input  wire                  tx_r_nak,
    input  wire [7:0]            tx_r_nak_seq,

    // incoming wire
    input  wire                  rx_w_valid,
    input  wire [FLIT_W-1:0]     rx_w_flit,
    input  wire [7:0]            rx_w_seq,
    input  wire [31:0]           rx_w_crc,

    // return path leaving for the far end
    output wire                  rx_r_ack,
    output wire [7:0]            rx_r_ack_seq,
    output wire [1:0]            rx_r_credit,
    output wire                  rx_r_nak,
    output wire [7:0]            rx_r_nak_seq,

    // service side of the receiving half
    output wire                  rx_out_valid,
    output wire [FLIT_W-1:0]     rx_out_flit,
    input  wire                  rx_out_ready,

    input  wire                  inject_crc_error,

    output wire [31:0]           flits_transmitted,
    output wire [31:0]           replayed_flits,
    output wire [31:0]           retry_events,
    output wire [31:0]           credit_stall_cycles,
    output wire [31:0]           crc_errors,
    output wire [31:0]           sequence_errors,
    output wire [31:0]           flits_delivered,
    output wire                  timeout,
    output wire                  error
);
    wire tx_error;
    wire tx_ack_seq_error;
    wire tx_credit_overflow;
    wire rx_overrun;

    assign error = tx_error | tx_ack_seq_error | tx_credit_overflow | rx_overrun;

    ot_a3_link_tx_channel #(
        .FLIT_W(FLIT_W), .CREDITS(CREDITS), .RETRY_MAX(RETRY_MAX),
        .ACK_TIMEOUT(ACK_TIMEOUT)
    ) u_tx (
        .clk(clk), .rst_n(rst_n),
        .in_valid(tx_in_valid), .in_ready(tx_in_ready), .in_flit(tx_in_flit),
        .w_valid(tx_w_valid), .w_flit(tx_w_flit), .w_seq(tx_w_seq),
        .w_crc(tx_w_crc),
        .r_ack(tx_r_ack), .r_ack_seq(tx_r_ack_seq), .r_credit(tx_r_credit),
        .r_nak(tx_r_nak), .r_nak_seq(tx_r_nak_seq),
        .inject_crc_error(inject_crc_error),
        .flits_accepted(),
        .flits_transmitted(flits_transmitted),
        .replayed_flits(replayed_flits),
        .retry_events(retry_events),
        .credit_stall_cycles(credit_stall_cycles),
        .retry_count(), .timeout(timeout),
        .error(tx_error), .ack_sequence_error(tx_ack_seq_error),
        .credit_overflow_error(tx_credit_overflow)
    );

    ot_a3_link_rx_channel #(
        .FLIT_W(FLIT_W), .CREDITS(CREDITS)
    ) u_rx (
        .clk(clk), .rst_n(rst_n),
        .w_valid(rx_w_valid), .w_flit(rx_w_flit), .w_seq(rx_w_seq),
        .w_crc(rx_w_crc),
        .r_ack(rx_r_ack), .r_ack_seq(rx_r_ack_seq), .r_credit(rx_r_credit),
        .r_nak(rx_r_nak), .r_nak_seq(rx_r_nak_seq),
        .out_valid(rx_out_valid), .out_flit(rx_out_flit),
        .out_ready(rx_out_ready),
        .crc_errors(crc_errors), .sequence_errors(sequence_errors),
        .flits_delivered(flits_delivered),
        .overrun_error(rx_overrun), .dropping()
    );
endmodule
