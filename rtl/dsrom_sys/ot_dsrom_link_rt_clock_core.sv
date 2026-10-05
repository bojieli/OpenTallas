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
module ot_dsrom_link_rt_clock_core #(
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
    localparam integer W    = FLIT_BYTES * 8;
    localparam integer RP   = (REPLAY == 0) ? CREDITS : REPLAY;
    localparam integer CW   = $clog2(CREDITS + 1);
    localparam integer IW   = (RP > 1) ? $clog2(RP) : 1;
    localparam integer FPW  = SEQW + 1 + W;         // forward payload
    localparam integer FFW  = FPW + 32;             // forward frame
    localparam integer RVW  = 1 + SEQW + CW;        // reverse payload
    localparam integer RFW  = RVW + 32;             // reverse frame
    localparam integer RTT  = 2 * CHANNEL_CYCLES + TX_STAGES + RX_STAGES + 7;
    localparam integer ATO  = (ACK_TIMEOUT == 0) ? (RTT + 2 * KEEPALIVE + 32) : ACK_TIMEOUT;
    localparam integer TW   = $clog2(ATO + 2);
    localparam integer RCW  = $clog2(MAX_RETRY + 2);
    localparam integer KW   = $clog2(KEEPALIVE + 1);
    localparam [SEQW-1:0] HALF = {1'b1, {(SEQW-1){1'b0}}};
    localparam [SEQW-1:0] RPS  = RP[SEQW-1:0];       // RP <= 2^(SEQW-1) < 2^SEQW
    localparam [31:0]     RP32 = RP;
    localparam integer    PW   = (CREDITS > 1) ? $clog2(CREDITS) : 1;   // FIFO pointer
    localparam [31:0]     PLAST32 = CREDITS - 1;
    localparam [31:0]     CRED32  = CREDITS;
    localparam [31:0]     ATO32   = ATO - 1;
    localparam [31:0]     MR32    = MAX_RETRY;
    localparam [PW-1:0]   PLAST  = PLAST32[PW-1:0];
    localparam [CW:0]     CRED_W = CRED32[CW:0];
    localparam [TW-1:0]   ATO_W  = ATO32[TW-1:0];
    localparam [RCW-1:0]  MR_W   = MR32[RCW-1:0];

    initial begin
        if (TX_STAGES < 1 || RX_STAGES < 1 || CHANNEL_CYCLES < 1)
            $fatal(1, "ot_dsrom_link_rt: TX_STAGES, RX_STAGES, CHANNEL_CYCLES must be >= 1");
        if (RP < 1 || RP > (1 << (SEQW - 1)))
            $fatal(1, "ot_dsrom_link_rt: REPLAY=%0d must be in [1, 2^(SEQW-1)=%0d]", RP, 1 << (SEQW - 1));
        if (KEEPALIVE < 1 || MAX_RETRY < 1)
            $fatal(1, "ot_dsrom_link_rt: KEEPALIVE and MAX_RETRY must be >= 1");
    end

    function automatic [IW-1:0] idx_add(input [IW-1:0] x, input [SEQW-1:0] d);
        reg [SEQW:0] s;
        begin
            s = x + {1'b0, d};   // x < RP, d <= RP
            if (s >= RP32) s = s - RP32;
            idx_add = s[IW-1:0];
        end
    endfunction

    // Parallel byte increments preserve same-edge modulo-2^32 diagnostics.
    // Carry tests use OLD counter bits, never a 32-bit event-gated ripple.
    function automatic [31:0] stat_add(input [31:0] x, input [1:0] delta);
        reg c8, c16, c24;
        begin
            c8 = ((delta == 1) && (&x[7:0])) || ((delta == 2) && (&x[7:1]));
            c16 = c8 && (&x[15:8]);
            c24 = c16 && (&x[23:16]);
            stat_add[7:0] = x[7:0] + delta;
            stat_add[15:8] = x[15:8] + c8;
            stat_add[23:16] = x[23:16] + c16;
            stat_add[31:24] = x[31:24] + c24;
        end
    endfunction

    // ======================================================================
    // Sender
    // ======================================================================
    reg  [SEQW-1:0] una, snd, nxt;          // oldest unacked, next to launch, next new
    reg  [IW-1:0]   una_i, snd_i, nxt_i;    // the same as replay-buffer indices
    reg  [CW-1:0]   credits;
    reg  [CW-1:0]   fr_seen;                // last cumulative freed count applied
    reg  [TW-1:0]   timer;
    reg  [RCW-1:0]  retry;
    reg  [W-1:0]    rb_data [0:RP-1];
    reg             rb_last [0:RP-1];

    wire [SEQW-1:0] occ = nxt - una;
    wire            replaying = (snd != nxt);
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    assign in_ready = (occ < RPS) && !replaying;
`else
    assign in_ready = (credits != 0) && (occ < RPS) && !replaying;
`endif
    wire            accept = in_valid && in_ready;
    wire            launch = replaying || accept;
    wire [W-1:0]    l_data = replaying ? rb_data[snd_i] : in_data;
    wire            l_last = replaying ? rb_last[snd_i] : in_last;
    wire [FPW-1:0]  l_pay  = {snd, l_last, l_data};
    // Accept/replay owns this immutable launch head before CRC. A later
    // rewind changes the NEXT head only; the in-flight sequence remains owned.
    reg h_v;
    reg [FPW-1:0] h_pay;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) h_v <= 1'b0;
        else begin h_v <= launch; h_pay <= l_pay; end
    wire [31:0] l_crc;
    ot_link_crc32 #(.W(FPW)) u_tx_crc (.d(h_pay), .crc(l_crc));

    // reverse-frame receive register and check
    wire            rch_v;
    wire [RFW-1:0]  rch_f;
    reg             rr_v;
    reg  [RFW-1:0]  rr_f;
    wire [31:0] rch_crc_calc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_before_reg (.d(rch_f[RFW-1:32]), .crc(rch_crc_calc));
    reg rr_crc_match;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rr_crc_match <= 1'b0;
        else rr_crc_match <= (rch_crc_calc == rch_f[31:0]);
    wire            rr_ok   = rr_v && rr_crc_match;
    wire            rr_bad  = rr_v && !rr_ok;
    wire            rr_nak  = rr_f[RFW-1];
    wire [SEQW-1:0] rr_ack  = rr_f[RFW-2 -: SEQW];
    wire [CW-1:0]   rr_fr   = rr_f[32 +: CW];
    wire [SEQW-1:0] d_ack   = rr_ack - una;
    wire [CW-1:0]   d_fr    = rr_fr - fr_seen;
    wire            ack_bad = rr_ok && (d_ack > occ);
    wire [CW:0]     cred_sum = {1'b0, credits} + {1'b0, d_fr};
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            fr_bad  = 1'b0;     // the mutant ignores returns; let the receive FIFO show the damage
`else
    wire            fr_bad  = rr_ok && (cred_sum > CRED_W);
`endif
    wire            ack_ok  = rr_ok && !ack_bad;
    wire            progress = ack_ok && (d_ack != 0);
    wire [SEQW-1:0] una_n   = ack_ok ? rr_ack : una;
    wire [IW-1:0]   una_i_n = ack_ok ? idx_add(una_i, d_ack) : una_i;
    wire            timeout = (occ != 0) && !progress && (timer == ATO_W);
`ifdef OT_DSROM_LINK_MUT_NOREPLAY
    wire            rewind  = 1'b0;
`else
    wire            rewind  = (ack_ok && rr_nak) || timeout;
`endif
    wire [SEQW-1:0] snd_l   = launch ? snd + 1'b1 : snd;
    wire [IW-1:0]   snd_i_l = launch ? idx_add(snd_i, 1) : snd_i;
    wire [SEQW-1:0] snd_off = snd_l - una;  // launched-but-not-acked span
    wire            retry_exh = rewind && !progress && (retry >= MR_W);

    // TX pipe
    reg             tp_v [0:TX_STAGES-1];
    reg  [FFW-1:0]  tp_f [0:TX_STAGES-1];
    genvar gi;
    generate for (gi = 0; gi < TX_STAGES; gi = gi + 1) begin : g_tx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_n)
                if (!rst_n) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= h_v; tp_f[gi] <= {h_pay, l_crc}; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_n)
                if (!rst_n) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= tp_v[gi-1]; tp_f[gi] <= tp_f[gi-1]; end
        end
    end endgenerate

    // ======================================================================
    // Forward channel
    // ======================================================================
    wire            fch_v;
    wire [FFW-1:0]  fch_f;
    wire [31:0]     fwd_injected, rev_injected;
    ot_dsrom_link_chan #(.W(FFW), .MAXD(CHANNEL_CYCLES), .DYN(DYNAMIC_DELAY),
                         .ERR_PERIOD(ERR_PERIOD_FWD), .ERR_OFFSET(ERR_OFFSET), .ERR_STRIDE(37)) u_fwd (
        .clk(clk), .rst_n(rst_n), .delay(channel_cycles),
        .in_valid(tp_v[TX_STAGES-1]), .in_data(tp_f[TX_STAGES-1]),
        .out_valid(fch_v), .out_data(fch_f), .err_injected(fwd_injected));

    // ======================================================================
    // Receiver
    // ======================================================================
    reg             xp_v [0:RX_STAGES-1];
    reg  [FFW-1:0]  xp_f [0:RX_STAGES-1];
    generate for (gi = 0; gi < RX_STAGES; gi = gi + 1) begin : g_rx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_n)
                if (!rst_n) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= fch_v; xp_f[gi] <= fch_f; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_n)
                if (!rst_n) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= xp_v[gi-1]; xp_f[gi] <= xp_f[gi-1]; end
        end
    end endgenerate

    wire            c_v    = xp_v[RX_STAGES-1];
    wire [FFW-1:0]  c_f    = xp_f[RX_STAGES-1];
    wire [FFW-1:0] crc_frame_in;
    generate if (RX_STAGES == 1) begin : g_crc_input_one
        assign crc_frame_in = fch_f;
    end else begin : g_crc_input_many
        assign crc_frame_in = xp_f[RX_STAGES-2];
    end endgenerate
    wire [31:0] c_crc_calc;
    ot_link_crc32 #(.W(FPW)) u_rx_crc (.d(crc_frame_in[FFW-1:32]), .crc(c_crc_calc));
    reg c_crc_match;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c_crc_match <= 1'b0;
        else c_crc_match <= (c_crc_calc == crc_frame_in[31:0]);
`ifdef OT_DSROM_LINK_MUT_NOCRC
    wire            c_crc_ok = 1'b1;
`else
    wire            c_crc_ok = c_crc_match;
`endif
    wire [SEQW-1:0] c_seq  = c_f[FFW-1 -: SEQW];
    wire            c_last = c_f[32 + W];
    wire [W-1:0]    c_data = c_f[32 +: W];

    reg  [SEQW-1:0] exp_seq;
    reg             nak_sent, nak_req, dup_req;
    reg  [CW-1:0]   freed;
    reg  [CW-1:0]   fill;
    reg  [PW-1:0]   head, tail;
    reg  [W-1:0]    fifo_data [0:CREDITS-1];
    reg             fifo_last [0:CREDITS-1];
    reg             out_valid_r, out_last_r;
    reg  [W-1:0]    out_data_r;
    assign out_valid = out_valid_r;
    assign out_data  = out_data_r;
    assign out_last  = out_last_r;

    wire [SEQW-1:0] c_diff   = c_seq - exp_seq;
    wire [SEQW-1:0] c_back   = exp_seq - c_seq;
    wire            c_good   = c_v && c_crc_ok;
    wire            c_crcerr = c_v && !c_crc_ok;
    wire            c_inord  = c_good && (c_diff == 0);
    wire            c_full   = (fill == CREDITS[CW-1:0]);
    wire            c_acc    = c_inord && !c_full;
    wire            c_ovf    = c_inord && c_full;
    wire            c_ahead  = c_good && (c_diff != 0) && (c_diff < HALF);
    wire            c_behind = c_good && (c_diff >= HALF);
    wire            c_unexpl = (c_ahead && (c_diff >= RPS)) || (c_behind && (c_back > RPS));
    wire            c_nak    = (c_crcerr || c_ahead) && !nak_sent;
    wire            drain    = (fill != 0) && (!out_valid_r || out_ready);

    // reverse frame generation
    reg  [SEQW-1:0] tx_ack;
    reg  [CW-1:0]   tx_fr;
    reg  [KW-1:0]   ka;
    wire            rg_need = nak_req || dup_req || (exp_seq != tx_ack) || (freed != tx_fr) || (ka == 0);
    wire [RVW-1:0]  rg_pay  = {nak_req, exp_seq, freed};
    wire [31:0]     rg_crc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_gen (.d(rg_pay), .crc(rg_crc));
    reg             rg_v;
    reg  [RFW-1:0]  rg_f;

    // ======================================================================
    // Reverse channel
    // ======================================================================
    ot_dsrom_link_chan #(.W(RFW), .MAXD(CHANNEL_CYCLES), .DYN(DYNAMIC_DELAY),
                         .ERR_PERIOD(ERR_PERIOD_REV), .ERR_OFFSET(ERR_OFFSET), .ERR_STRIDE(11)) u_rev (
        .clk(clk), .rst_n(rst_n), .delay(channel_cycles),
        .in_valid(rg_v), .in_data(rg_f),
        .out_valid(rch_v), .out_data(rch_f), .err_injected(rev_injected));

    // ======================================================================
    // State
    // ======================================================================
    reg  [3:0] fault_n;
    always @* begin
        fault_n = 4'd0;
        if      (retry_exh)                  fault_n = 4'd1;
        else if (ack_bad)                    fault_n = 4'd2;
        else if (c_ovf)                      fault_n = 4'd3;
        else if (accept && (occ >= RPS))     fault_n = 4'd4;
        else if (fr_bad)                     fault_n = 4'd5;
        else if (c_unexpl)                   fault_n = 4'd6;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            una <= 0; snd <= 0; nxt <= 0; una_i <= 0; snd_i <= 0; nxt_i <= 0;
            credits <= CREDITS[CW-1:0]; fr_seen <= 0; timer <= 0; retry <= 0;
            rr_v <= 1'b0; rr_f <= 0;
            exp_seq <= 0; nak_sent <= 1'b0; nak_req <= 1'b0; dup_req <= 1'b0;
            freed <= 0; fill <= 0; head <= 0; tail <= 0;
            out_valid_r <= 1'b0; out_last_r <= 1'b0; out_data_r <= 0;
            tx_ack <= 0; tx_fr <= 0; ka <= KEEPALIVE[KW-1:0] - 1'b1;
            rg_v <= 1'b0; rg_f <= 0;
            fault <= 1'b0; fault_code <= 4'd0; credit_stalls <= 0;
            st_flits_tx <= 0; st_flits_rx_ok <= 0; st_crc_err <= 0; st_naks <= 0;
            st_replays <= 0; st_timeouts <= 0; st_retx_flits <= 0; st_max_replay_occ <= 0;
        end else begin
            // ---------------- sender ----------------
            if (accept) begin
                rb_data[nxt_i] <= in_data;
                rb_last[nxt_i] <= in_last;
                nxt   <= nxt + 1'b1;
                nxt_i <= idx_add(nxt_i, 1);
            end
            una <= una_n; una_i <= una_i_n;
            if (rewind) begin
                snd <= una_n; snd_i <= una_i_n;
            end else if (ack_ok && (d_ack > snd_off)) begin
                // an ACK overtook a rewound pointer: those flits already arrived
                snd <= rr_ack; snd_i <= una_i_n;
            end else begin
                snd <= snd_l; snd_i <= snd_i_l;
            end
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
            credits <= credits;
`else
            credits <= credits - {{(CW-1){1'b0}}, accept} + ((rr_ok && !fr_bad) ? d_fr : {CW{1'b0}});
`endif
            if (rr_ok) fr_seen <= rr_fr;
            if (occ == 0 || progress || rewind) timer <= 0;
            else if (timer != ATO_W) timer <= timer + 1'b1;
            if (progress) retry <= {{(RCW-1){1'b0}}, rewind};
            else if (rewind && retry <= MR_W) retry <= retry + 1'b1;
            rr_v <= rch_v; rr_f <= rch_f;

            // ---------------- receiver ----------------
            if (c_acc) begin
                fifo_data[tail] <= c_data;
                fifo_last[tail] <= c_last;
                tail <= (tail == PLAST) ? {PW{1'b0}} : tail + 1'b1;
                exp_seq <= exp_seq + 1'b1;
                nak_sent <= 1'b0;
            end else if (c_nak) begin
                nak_sent <= 1'b1;
            end
            if (drain) begin
                head <= (head == PLAST) ? {PW{1'b0}} : head + 1'b1;
                out_data_r  <= fifo_data[head];
                out_last_r  <= fifo_last[head];
                out_valid_r <= 1'b1;
                freed <= freed + 1'b1;
            end else if (out_valid_r && out_ready) begin
                out_valid_r <= 1'b0;
            end
            fill <= fill + {{(CW-1){1'b0}}, c_acc} - {{(CW-1){1'b0}}, drain};

            // ---------------- reverse frame ----------------
            rg_v <= rg_need;
            rg_f <= {rg_pay, rg_crc};
            if (rg_need) begin
                tx_ack <= exp_seq; tx_fr <= freed; ka <= KEEPALIVE[KW-1:0] - 1'b1;
                nak_req <= 1'b0; dup_req <= 1'b0;
            end else begin
                ka <= ka - 1'b1;
            end
            if (c_nak) nak_req <= 1'b1;
            if (c_behind) dup_req <= 1'b1;

            // ---------------- status ----------------
            if (fault_n != 0 && !fault) begin fault <= 1'b1; fault_code <= fault_n; end
            if (in_valid && !in_ready) credit_stalls <= stat_add(credit_stalls, 2'd1);
            if (launch) st_flits_tx <= stat_add(st_flits_tx, 2'd1);
            if (launch && replaying) st_retx_flits <= stat_add(st_retx_flits, 2'd1);
            if (c_acc) st_flits_rx_ok <= stat_add(st_flits_rx_ok, 2'd1);
            st_crc_err <= stat_add(st_crc_err, {1'b0,c_crcerr}+{1'b0,rr_bad});
            if (rg_need && nak_req) st_naks <= stat_add(st_naks, 2'd1);
            if (rewind) st_replays <= stat_add(st_replays, 2'd1);
            if (timeout) st_timeouts <= stat_add(st_timeouts, 2'd1);
            if ({{(32-SEQW){1'b0}}, occ} > st_max_replay_occ) st_max_replay_occ <= {{(32-SEQW){1'b0}}, occ};
        end
    end

    // LINK_CLASS and the injection counters are informational only.
    wire unused_ok = &{1'b0, LINK_CLASS[0], fwd_injected, rev_injected};
endmodule
