`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_link_rt: reliable package/die link layer (sequence numbers, CRC-32,
// go-back-N replay, ACK/NAK, cumulative credit return over the reverse
// channel).  A drop-in successor of rtl/rom/ot_rom_pkg_link.sv: the shared
// ports keep their names and meaning; the new outputs are status only.  Gap
// Z5/L1 of the 2026-10-03 ROM bridge review: the original returns credits
// instantly and its PHY/FEC is a loss-free delay line.  Default-off: the
// original stays the default in every existing bench.
//
// Structure (forward = data direction, reverse = ACK/NAK/credit direction):
//
//   in -> launch mux (new flit | replay[snd]) -> CRC -> TX_STAGES regs
//      -> ot_dsrom_link_chan (delay CHANNEL_CYCLES, deterministic bit flips)
//      -> RX_STAGES regs -> CRC/sequence check -> receive FIFO (CREDITS)
//      -> registered output stage -> out
//   receiver state -> reverse-frame register -> ot_dsrom_link_chan (same
//      delay) -> 1 reg -> CRC check -> ACK / NAK / credit update at sender
//
// Forward frame  = {seq[SEQW], last, data[W], crc32}, CRC over {seq,last,data}.
// Reverse frame  = {nak, ack[SEQW], freed[CW], crc32}, CRC over the first three.
// CRC-32 is rtl/link/ot_link_crc32.sv: IEEE 802.3 polynomial 0x04C11DB7,
// init 0xFFFFFFFF, MSB-first, no reflection, no final XOR (the CRC-32/MPEG-2
// parameterisation of the IEEE polynomial; Hamming distance is that of the
// polynomial, so every single- and double-bit error in these frame sizes is
// detected).
//
// Protocol invariants (argued here, checked by tb_dsrom_link_rt):
//  * ack = the receiver's expected sequence number (cumulative); freed = the
//    receiver's count of FIFO pops mod 2^CW (cumulative).  A lost reverse
//    frame therefore loses neither an ACK nor a credit: the next good frame
//    carries the totals.  Reverse frames are sent when either total changes,
//    on a NAK / duplicate request, and at least every KEEPALIVE cycles.
//  * Credits are taken only on FIRST transmission (when the flit enters the
//    replay buffer).  The receiver accepts only the in-order sequence number,
//    so each sequence number occupies one FIFO slot exactly once; a
//    retransmission either fills the slot its first copy failed to fill or
//    is dropped as a duplicate.  Hence FIFO occupancy <= CREDITS: accepted
//    <= first-sent <= CREDITS + freed_seen_by_sender <= CREDITS + popped.
//    A receive-FIFO overflow is impossible in a correct link and is a fault.
//  * freed <= accepted = ack in every reverse frame, so whenever the sender
//    regains a credit it has also seen the ACK of that flit: replay-buffer
//    occupancy <= credits outstanding <= CREDITS.  REPLAY = CREDITS (default)
//    never limits the rate below what the credits allow.
//  * Sequence window: occupancy <= REPLAY <= 2^(SEQW-1), so a received
//    sequence number is unambiguously expected, ahead (an earlier frame was
//    lost: drop + one NAK) or behind (a duplicate: drop + re-ACK).
//  * Go-back-N: a NAK(E) or ACK_TIMEOUT cycles without ACK progress while
//    flits are outstanding rewinds the transmit pointer to the oldest
//    unacknowledged entry.  NAKs are suppressed after the first until E is
//    accepted; a lost NAK is recovered by the timeout.  MAX_RETRY rewinds
//    without progress latch fault code 1.
//  * No silent drop: every overflow / unexplainable value latches `fault`.
//
// fault_code (first cause latched): 1 retry exhausted, 2 ACK beyond the
// transmitted window, 3 receive FIFO overflow, 4 replay buffer overflow,
// 5 credit return beyond the credits outstanding, 6 received sequence number
// outside the window.
//
// Build-time mutants (negative controls, never defined in a real build):
//   OT_DSROM_LINK_MUT_NOCRC      receiver ignores the forward CRC
//   OT_DSROM_LINK_MUT_NOREPLAY   NAK / timeout never rewind
//   OT_DSROM_LINK_MUT_FREECREDIT a send never consumes a credit
//
// NOT A PHY: ot_dsrom_link_chan (rtl/dsrom_sys/ot_dsrom_link_chan.sv; delay line + deterministic bit flips) is the
// only stand-in; everything else is synthesizable clocked logic.
// ---------------------------------------------------------------------------
module ot_dsrom_link_rt_clock #(
    parameter integer ENABLE_CLOCK_REPAIR = 0,
    parameter integer FLIT_BYTES     = 1800,
    parameter integer TX_STAGES      = 2,     // >= 1
    parameter integer CHANNEL_CYCLES = 60,    // one-way PHY+FEC+flight, both directions (maximum if DYNAMIC_DELAY)
    parameter integer RX_STAGES      = 2,     // >= 1
    parameter integer CREDITS        = 128,   // receiver buffer, in flits
    parameter integer DYNAMIC_DELAY  = 0,     // 1: channel_cycles (bounded) is the active one-way delay
    parameter integer SEQW           = 8,     // sequence number bits
    parameter integer REPLAY         = 0,     // replay buffer flits; 0 = CREDITS (see invariants)
    parameter integer ERR_PERIOD_FWD = 0,     // 0 = none; N = flip one bit of every Nth forward frame
    parameter integer ERR_PERIOD_REV = 0,     // same, reverse frames
    parameter integer ERR_OFFSET     = 0,     // phase of the first injected error
    parameter integer ACK_TIMEOUT    = 0,     // 0 = derived from the round trip
    parameter integer MAX_RETRY      = 8,     // rewinds without ACK progress before fault 1
    parameter integer LINK_CLASS     = 0,     // 0 in-package UCIe, 1 board light-FEC (informational)
    parameter integer KEEPALIVE      = 16     // maximum cycles between reverse frames
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [15:0]              channel_cycles, // used only with DYNAMIC_DELAY=1
    // sender side
    input  wire                     in_valid,
    output wire                     in_ready,
    input  wire [FLIT_BYTES*8-1:0]  in_data,
    input  wire                     in_last,
    // receiver side
    output wire                     out_valid,
    input  wire                     out_ready,
    output wire [FLIT_BYTES*8-1:0]  out_data,
    output wire                     out_last,
    output reg  [31:0]              credit_stalls,
    // reliability status
    output reg                      fault,
    output reg  [3:0]               fault_code,
    output reg  [31:0]              st_flits_tx,       // forward frames launched (first + retransmitted)
    output reg  [31:0]              st_flits_rx_ok,    // frames accepted in order into the receive FIFO
    output reg  [31:0]              st_crc_err,        // CRC failures, forward (receiver) + reverse (sender)
    output reg  [31:0]              st_naks,           // NAK frames emitted by the receiver
    output reg  [31:0]              st_replays,        // go-back-N rewinds (NAK or timeout)
    output reg  [31:0]              st_timeouts,       // ACK timeouts
    output reg  [31:0]              st_retx_flits,     // retransmitted frames
    output reg  [31:0]              st_max_replay_occ  // peak replay-buffer occupancy
);
    generate if (ENABLE_CLOCK_REPAIR) begin : g_repaired
        ot_dsrom_link_rt_clock_core #(.FLIT_BYTES(FLIT_BYTES), .TX_STAGES(TX_STAGES), .CHANNEL_CYCLES(CHANNEL_CYCLES), .RX_STAGES(RX_STAGES), .CREDITS(CREDITS), .DYNAMIC_DELAY(DYNAMIC_DELAY), .SEQW(SEQW), .REPLAY(REPLAY), .ERR_PERIOD_FWD(ERR_PERIOD_FWD), .ERR_PERIOD_REV(ERR_PERIOD_REV), .ERR_OFFSET(ERR_OFFSET), .ACK_TIMEOUT(ACK_TIMEOUT), .MAX_RETRY(MAX_RETRY), .LINK_CLASS(LINK_CLASS), .KEEPALIVE(KEEPALIVE)) u_link (.clk(clk),
            .rst_n(rst_n),
            .channel_cycles(channel_cycles),
            .in_valid(in_valid),
            .in_ready(in_ready),
            .in_data(in_data),
            .in_last(in_last),
            .out_valid(out_valid),
            .out_ready(out_ready),
            .out_data(out_data),
            .out_last(out_last),
            .credit_stalls(credit_stalls),
            .fault(fault),
            .fault_code(fault_code),
            .st_flits_tx(st_flits_tx),
            .st_flits_rx_ok(st_flits_rx_ok),
            .st_crc_err(st_crc_err),
            .st_naks(st_naks),
            .st_replays(st_replays),
            .st_timeouts(st_timeouts),
            .st_retx_flits(st_retx_flits),
            .st_max_replay_occ(st_max_replay_occ));
    end else begin : g_baseline
        ot_dsrom_link_rt #(.FLIT_BYTES(FLIT_BYTES), .TX_STAGES(TX_STAGES), .CHANNEL_CYCLES(CHANNEL_CYCLES), .RX_STAGES(RX_STAGES), .CREDITS(CREDITS), .DYNAMIC_DELAY(DYNAMIC_DELAY), .SEQW(SEQW), .REPLAY(REPLAY), .ERR_PERIOD_FWD(ERR_PERIOD_FWD), .ERR_PERIOD_REV(ERR_PERIOD_REV), .ERR_OFFSET(ERR_OFFSET), .ACK_TIMEOUT(ACK_TIMEOUT), .MAX_RETRY(MAX_RETRY), .LINK_CLASS(LINK_CLASS), .KEEPALIVE(KEEPALIVE)) u_link (.clk(clk),
            .rst_n(rst_n),
            .channel_cycles(channel_cycles),
            .in_valid(in_valid),
            .in_ready(in_ready),
            .in_data(in_data),
            .in_last(in_last),
            .out_valid(out_valid),
            .out_ready(out_ready),
            .out_data(out_data),
            .out_last(out_last),
            .credit_stalls(credit_stalls),
            .fault(fault),
            .fault_code(fault_code),
            .st_flits_tx(st_flits_tx),
            .st_flits_rx_ok(st_flits_rx_ok),
            .st_crc_err(st_crc_err),
            .st_naks(st_naks),
            .st_replays(st_replays),
            .st_timeouts(st_timeouts),
            .st_retx_flits(st_retx_flits),
            .st_max_replay_occ(st_max_replay_occ));
    end endgenerate
endmodule
