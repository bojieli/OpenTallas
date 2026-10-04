`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_link_sel -- selects the package/die link implementation of the
// DeepSeek-V4.1 ROM system top.  LINK_RT = 0 (default) is the pinned
// ot_rom_pkg_link (lossless delay line, immediate credit return), so every
// existing configuration is unchanged; LINK_RT = 1 is ot_dsrom_link_rt
// (sequence numbers, CRC-32, go-back-N replay with ACK/NAK, credits returned
// over the reverse channel).  LINK_CLASS records which physical class the
// instance stands for (0 in-package UCIe, 1 board light-FEC); the latency is
// CHANNEL_CYCLES either way.
// ---------------------------------------------------------------------------
module ot_dsrom_link_sel #(
    parameter integer LINK_RT        = 0,
    parameter integer LINK_CLASS     = 0,
    parameter integer FLIT_BYTES     = 64,
    parameter integer TX_STAGES      = 2,
    parameter integer CHANNEL_CYCLES = 60,
    parameter integer RX_STAGES      = 2,
    parameter integer CREDITS        = 32,
    parameter integer DYNAMIC_DELAY  = 0,
    parameter integer ERR_PERIOD_FWD = 0,
    parameter integer ERR_PERIOD_REV = 0,
    parameter integer ERR_OFFSET     = 0,
    parameter integer SEQW           = 8
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [15:0]              channel_cycles,
    input  wire                     in_valid,
    output wire                     in_ready,
    input  wire [FLIT_BYTES*8-1:0]  in_data,
    input  wire                     in_last,
    output wire                     out_valid,
    input  wire                     out_ready,
    output wire [FLIT_BYTES*8-1:0]  out_data,
    output wire                     out_last,
    output wire [31:0]              credit_stalls,
    output wire                     fault,
    output wire [3:0]               fault_code,
    output wire [32*8-1:0]          stats          // tx, rx_ok, crc_err, naks, replays, timeouts, retx, max_replay_occ
);
    generate if (LINK_RT) begin : g_rt
        wire [31:0] s_tx, s_rx, s_crc, s_nak, s_rep, s_to, s_retx, s_occ;
        ot_dsrom_link_rt #(.FLIT_BYTES(FLIT_BYTES), .TX_STAGES(TX_STAGES), .CHANNEL_CYCLES(CHANNEL_CYCLES),
                           .RX_STAGES(RX_STAGES), .CREDITS(CREDITS), .DYNAMIC_DELAY(DYNAMIC_DELAY),
                           .ERR_PERIOD_FWD(ERR_PERIOD_FWD), .ERR_PERIOD_REV(ERR_PERIOD_REV),
                           .ERR_OFFSET(ERR_OFFSET), .LINK_CLASS(LINK_CLASS), .SEQW(SEQW)) u (
            .clk(clk), .rst_n(rst_n), .channel_cycles(channel_cycles),
            .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
            .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
            .credit_stalls(credit_stalls), .fault(fault), .fault_code(fault_code),
            .st_flits_tx(s_tx), .st_flits_rx_ok(s_rx), .st_crc_err(s_crc), .st_naks(s_nak),
            .st_replays(s_rep), .st_timeouts(s_to), .st_retx_flits(s_retx), .st_max_replay_occ(s_occ));
        assign stats = {s_occ, s_retx, s_to, s_rep, s_nak, s_crc, s_rx, s_tx};
    end else begin : g_pinned
        ot_rom_pkg_link #(.FLIT_BYTES(FLIT_BYTES), .TX_STAGES(TX_STAGES), .CHANNEL_CYCLES(CHANNEL_CYCLES),
                          .RX_STAGES(RX_STAGES), .CREDITS(CREDITS), .DYNAMIC_DELAY(DYNAMIC_DELAY)) u (
            .clk(clk), .rst_n(rst_n), .channel_cycles(channel_cycles),
            .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
            .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
            .credit_stalls(credit_stalls));
        assign fault = 1'b0;
        assign fault_code = 4'd0;
        assign stats = '0;
    end endgenerate
endmodule
