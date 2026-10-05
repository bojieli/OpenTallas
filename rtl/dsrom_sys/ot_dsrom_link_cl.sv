`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_link_cl: the CLOSED S81 stage-hop link endpoint (lever hop_closed of
// the 2026-10-04 DS-ROM recovery).  Successor of ot_dsrom_link_ct and
// ot_dsrom_link_rt (both pinned, byte-identical), which fail the 1.2 GHz
// pre-layout SS screen (-500.4 / -417.3 ps).  Same link protocol: forward frame
// {seq, last, data, crc32}, reverse frame {nak, ack, freed, crc32}, CRC-32 of
// rtl/link/ot_link_crc32.sv, cumulative ACK and credit return, go-back-N
// replay on NAK / ACK timeout, in-order acceptance, sequence-window and
// overflow faults, the PHY lane-rate pacer of ot_dsrom_link_ct.
//
// What changes, and the cycles it costs (forward path, per leg):
//  (a) CREDITS is a power of two and the replay / receive indices are the low
//      log2(CREDITS) bits of the sequence numbers: no modular index adder on
//      the ACK -> replay-pointer path.                                   0 cyc
//  (b) Reverse frames: CRC check registered (stage A), ACK/credit processing
//      on the registered fields (stage B).  ACK/credit return +1 cycle (not on
//      the forward path while credits cover the round trip).
//  (c) TX: stage 0 registers the launch mux (new flit | replay data), stage 1
//      the CRC-32 of stage 0 (was: mux + CRC in one cycle).               0 cyc
//  (d) RX: 3 stages; the CRC-32 tree of stage 0 is registered into stage 1,
//      its compare into stage 2.                                         +1 cyc
//  (e) Storage = registered-read 1R1W arrays (rtl ot_dsrom_link_mem: MEM=0
//      flops, MEM=1 ASAP7 ot_sram_1r1w_256x256 macros at depth 256), written
//      from registers (sender: TX stage 0; receiver: a write register),
//      read through an extra register (SRAM SS clk->q 511 ps leaves no room
//      for logic).  Receive path: write register +1, 2-cycle read +1, a
//      4-entry output skid buffer (out_valid from the skid).             +2 cyc
//      Replays read the replay array with one read outstanding (a replay
//      launches every 3rd cycle at most; error recovery only).
//  (f) Status counters: registered increment, 16 + 16-bit halves with a
//      registered carry (a status read may lag by <= 2 cycles).  Fault
//      causes are registered before the first-cause latch (+1 cycle).
//  (h) IN_NEG=1: in_data / in_last are captured on the FALLING clock edge
//      (mid-cycle, after the producer's rising-edge launch has settled) and
//      used by the rising-edge logic: the value at the next rising edge is
//      the same as a direct capture (0 cycles), while the port-to-register
//      hold check becomes a half-cycle check, so the ~770 data inputs need no
//      hold-buffer chains against the block's propagated clock latency under
//      the in-context I/O constraints (input min 30 ps).  The controls
//      (in_valid, out_ready) stay rising-edge.                           0 cyc
//  (i) Registered port outputs: in_ready is a register loaded with the
//      readiness of the NEXT state (identical behaviour), and out_valid /
//      out_data / out_last leave from an output register fed from the skid
//      or, bypassing it, straight from the read register (no added cycle),
//      so no port output carries logic behind the propagated clock.     0 cyc
//  (g) The ACK-window, receive-overflow and credit-return checks stay as
//      faults but no longer gate the state update (a correct link never
//      raises them; the fault latches either way).  ACK processing uses no
//      subtract-compare chain: occ_a = nxt - ack, progress = (ack != una),
//      an ACK overtaking snd is the window test on (ack - snd), which needs
//      SEQW >= log2(CREDITS) + 2.  The receiver's in-order test is
//      precomputed a stage early against exp_seq and exp_seq + 1.
//
// fault_code: 1 retry exhausted, 2 ACK beyond the window, 3 receive buffer
// overflow, 4 replay buffer overflow, 5 credit return beyond the credits
// outstanding, 6 received sequence number outside the window.
// Mutants (negative controls): OT_DSROM_LINK_MUT_NOCRC, _NOREPLAY, _FREECREDIT.
// NOT A PHY: ot_dsrom_link_chan is the delay-line stand-in, as in link_rt.
// ---------------------------------------------------------------------------
module ot_dsrom_link_cl #(
    parameter integer FLIT_BYTES     = 96,
    parameter integer CHANNEL_CYCLES = 60,
    parameter integer CREDITS        = 256,   // power of two; replay buffer = CREDITS
    parameter integer DYNAMIC_DELAY  = 0,
    parameter integer SEQW           = 10,    // >= log2(CREDITS) + 2
    parameter integer ERR_PERIOD_FWD = 0,
    parameter integer ERR_PERIOD_REV = 0,
    parameter integer ERR_OFFSET     = 0,
    parameter integer ACK_TIMEOUT    = 0,
    parameter integer MAX_RETRY      = 8,
    parameter integer LINK_CLASS     = 0,
    parameter integer KEEPALIVE      = 16,
    parameter integer PHY_NUM        = 0,
    parameter integer PHY_DEN        = 1,
    parameter integer MEM            = 0,     // 0 flop arrays, 1 SRAM macros (CREDITS 256)
    parameter integer IN_NEG         = 1      // 1: in_data / in_last captured on the falling edge, see (h)
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
    output reg                      fault,
    output reg  [3:0]               fault_code,
    output wire [31:0]              st_flits_tx,
    output wire [31:0]              st_flits_rx_ok,
    output wire [31:0]              st_crc_err,
    output wire [31:0]              st_naks,
    output wire [31:0]              st_replays,
    output wire [31:0]              st_timeouts,
    output wire [31:0]              st_retx_flits,
    output reg  [31:0]              st_max_replay_occ
);
    localparam integer W    = FLIT_BYTES * 8;
    localparam integer IW   = $clog2(CREDITS);
    localparam integer CW   = $clog2(CREDITS + 1);
    localparam integer FPW  = SEQW + 1 + W;
    localparam integer FFW  = FPW + 32;
    localparam integer RVW  = 1 + SEQW + CW;
    localparam integer RFW  = RVW + 32;
    localparam integer ATO  = (ACK_TIMEOUT == 0) ? (2 * CHANNEL_CYCLES + 2 * KEEPALIVE + 64) : ACK_TIMEOUT;
    localparam integer TW   = $clog2(ATO + 2);
    localparam integer RCW  = $clog2(MAX_RETRY + 2);
    localparam integer KW   = $clog2(KEEPALIVE + 1);
    localparam integer SK   = 4;                        // receive output skid entries
    localparam [SEQW-1:0] HALF = {1'b1, {(SEQW-1){1'b0}}};
    localparam [31:0]     CRED32 = CREDITS;
    localparam [SEQW-1:0] RPS  = CRED32[SEQW-1:0];
    localparam [CW-1:0]   CRED_C = CRED32[CW-1:0];
    localparam [31:0]     ATO32 = ATO - 1;
    localparam [TW-1:0]   ATO_W = ATO32[TW-1:0];
    localparam [31:0]     MR32 = MAX_RETRY;
    localparam [RCW-1:0]  MR_W = MR32[RCW-1:0];

`ifndef SYNTHESIS
    initial begin
        if ((1 << IW) != CREDITS || CREDITS < 2)
            $fatal(1, "ot_dsrom_link_cl: CREDITS=%0d must be a power of two >= 2", CREDITS);
        if (SEQW < IW + 2)
            $fatal(1, "ot_dsrom_link_cl: SEQW must be >= log2(CREDITS) + 2");
        if (CHANNEL_CYCLES < 1 || KEEPALIVE < 1 || MAX_RETRY < 1)
            $fatal(1, "ot_dsrom_link_cl: CHANNEL_CYCLES, KEEPALIVE, MAX_RETRY must be >= 1");
        if (PHY_NUM < 0 || PHY_DEN < 1 || PHY_NUM > FLIT_BYTES * PHY_DEN)
            $fatal(1, "ot_dsrom_link_cl: PHY_NUM out of range");
    end
`endif

    // ======================================================================
    // Sender
    // ======================================================================
    localparam integer PCOST = FLIT_BYTES * PHY_DEN;
    localparam integer PAW   = $clog2(PCOST + PHY_NUM + 1);
    localparam [PAW-1:0] PCOST_W = PCOST[PAW-1:0];
    localparam [PAW-1:0] PNUM_W  = PHY_NUM[PAW-1:0];
    reg  [PAW-1:0]  pace;
    wire            pace_ok = (PHY_NUM == 0) || (pace >= PCOST_W);

    reg  [SEQW-1:0] una, snd, nxt;
    reg  [IW:0]     occ;                     // nxt - una, <= CREDITS
    reg  [CW-1:0]   credits, fr_seen;
    reg  [TW-1:0]   timer;
    reg  [RCW-1:0]  retry;

    // reverse frames: channel -> rr (reg) -> stage A (CRC checked, reg) -> stage B (processing)
    wire            rch_v;
    wire [RFW-1:0]  rch_f;
    reg             rr_v;
    reg  [RFW-1:0]  rr_f;
    wire [31:0]     rr_crc_calc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_chk (.d(rr_f[RFW-1:32]), .crc(rr_crc_calc));
    reg             ra_ok, ra_bad, ra_nak;
    reg  [SEQW-1:0] ra_ack;
    reg  [CW-1:0]   ra_fr;

    wire [SEQW-1:0] d_ack    = ra_ack - una;                       // fault check only
    wire [SEQW-1:0] occ_s    = {{(SEQW-IW-1){1'b0}}, occ};
    wire            ack_bad  = ra_ok && (d_ack > occ_s);
    wire            ack_ok   = ra_ok;
    wire            progress = ra_ok && (ra_ack != una);
    wire [CW-1:0]   d_fr     = ra_fr - fr_seen;
    wire [CW:0]     cred_sum = {1'b0, credits} + {1'b0, d_fr};
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            fr_bad   = 1'b0;
`else
    wire            fr_bad   = ra_ok && (cred_sum > {1'b0, CRED_C});
`endif
    wire            timeout  = (occ != 0) && !progress && (timer == ATO_W);
`ifdef OT_DSROM_LINK_MUT_NOREPLAY
    wire            rewind   = 1'b0;
`else
    wire            rewind   = (ack_ok && ra_nak) || timeout;
`endif
    wire            replaying = (snd != nxt);
    reg             rdy_r;                   // = (credits != 0) && !occ[IW] && !replaying && pace_ok, registered
    assign in_ready = rdy_r;
    wire            accept = in_valid && rdy_r;
    reg  [W-1:0]    in_data_n;
    reg             in_last_n;
    always @(negedge clk) begin in_data_n <= in_data; in_last_n <= in_last; end
    wire [W-1:0]    in_d = (IN_NEG != 0) ? in_data_n : in_data;
    wire            in_l = (IN_NEG != 0) ? in_last_n : in_last;

    // replay read: one read outstanding, 2-cycle registered read
    reg             rd_v1, rd_v2;
    reg  [SEQW-1:0] rd_s1, rd_s2;
    wire [W:0]      rb_q;                    // {last, data} of the read issued 2 cycles earlier
    wire            rd_hit = rd_v2 && (rd_s2 == snd);
    wire            rp_go  = replaying && pace_ok && rd_hit;
    wire            launch = accept || rp_go;
    // ACK overtaking a rewound pointer, decided on snd - una (not snd_l - una): when an ACK lands exactly one
    // past snd in a launch cycle both choices give snd + 1 = ra_ack, so the result equals link_rt's, and the
    // late `launch` only selects the final mux.
    wire [SEQW-1:0] d_sk   = ra_ack - snd;                         // > 0 and inside the half window: ACK past snd
    wire            ack_skip = ack_ok && (d_sk != 0) && !d_sk[SEQW-1];
    wire [SEQW-1:0] nmack  = nxt - ra_ack;
    wire [IW:0]     occ_a  = ack_ok ? nmack[IW:0] : occ;           // = occ - (ack - una), since occ = nxt - una
    // next-state values (the always block assigns these) and the readiness they imply
    wire [IW:0]     occ_n  = accept ? occ_a + 1'b1 : occ_a;
    wire [SEQW-1:0] nxt_n  = accept ? nxt + 1'b1 : nxt;
    wire [SEQW-1:0] snd_n  = rewind ? una_n : ack_skip ? ra_ack : launch ? snd + 1'b1 : snd;
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire [CW-1:0]   credits_n = credits;
`else
    wire [CW-1:0]   credits_n = credits - {{(CW-1){1'b0}}, accept} + (ra_ok ? d_fr : {CW{1'b0}});
`endif
    wire [PAW-1:0]  pace_n = (PHY_NUM == 0) ? pace : launch ? pace - PCOST_W + PNUM_W : !pace_ok ? pace + PNUM_W : pace;
    wire            pace_ok_n = (PHY_NUM == 0) || (pace_n >= PCOST_W);
    // replaying next cycle (snd_n != nxt_n) without comparing the muxed pointers: after a rewind or an ACK
    // overtake snd_n = una_n, so it replays iff occ_n != 0 (occ_n = occ - dk + accept); otherwise only an ongoing
    // replay continues, and it ends when the last outstanding flit relaunches
    wire            last_rp = (snd + 1'b1 == nxt);
    wire            rpl_n  = (rewind || ack_skip) ? (accept || (occ_a != 0)) : (replaying && !(rp_go && last_rp));
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            rdy_n  = !occ_n[IW] && !rpl_n && pace_ok_n;
`else
    wire            rdy_n  = (credits_n != 0) && !occ_n[IW] && !rpl_n && pace_ok_n;
`endif
    wire [SEQW-1:0] una_n  = ack_ok ? ra_ack : una;
    wire            retry_exh = rewind && !progress && (retry >= MR_W);

    // TX stage 0 (launch mux registered) and stage 1 (CRC)
    reg             t0_v, t0_first, t0_last;
    reg  [SEQW-1:0] t0_seq;
    reg  [W-1:0]    t0_data;
    wire [FPW-1:0]  t0_pay = {t0_seq, t0_last, t0_data};
    wire [31:0]     t0_crc;
    ot_link_crc32 #(.W(FPW)) u_tx_crc (.d(t0_pay), .crc(t0_crc));
    reg             t1_v;
    reg  [FFW-1:0]  t1_f;

    // replay storage: written from TX stage 0 on a first transmission
    wire            rb_we   = t0_v && t0_first;
    wire [IW-1:0]   rb_wa   = t0_seq[IW-1:0];
    wire            rd_issue = replaying && !rd_v1 && !rd_hit && !(rb_we && (rb_wa == snd[IW-1:0]));
    ot_dsrom_link_mem #(.W(W + 1), .D(CREDITS), .MEM(MEM)) u_rb (
        .clk(clk), .r_ce(rd_issue), .r_addr(snd[IW-1:0]), .q_en(rd_v1), .q(rb_q),
        .w_ce(rb_we), .w_addr(rb_wa), .w_d({t0_last, t0_data}));

    // ======================================================================
    // Forward channel
    // ======================================================================
    wire            fch_v;
    wire [FFW-1:0]  fch_f;
    wire [31:0]     fwd_injected, rev_injected;
    ot_dsrom_link_chan #(.W(FFW), .MAXD(CHANNEL_CYCLES), .DYN(DYNAMIC_DELAY),
                         .ERR_PERIOD(ERR_PERIOD_FWD), .ERR_OFFSET(ERR_OFFSET), .ERR_STRIDE(37)) u_fwd (
        .clk(clk), .rst_n(rst_n), .delay(channel_cycles),
        .in_valid(t1_v), .in_data(t1_f),
        .out_valid(fch_v), .out_data(fch_f), .err_injected(fwd_injected));

    // ======================================================================
    // Receiver: x0 (reg) -> x1 (+ CRC of x0) -> x2 (+ compare) = c
    // ======================================================================
    reg             x0_v, x1_v, x2_v;
    reg  [FFW-1:0]  x0_f, x1_f, x2_f;
    wire [31:0]     x0_crc;
    ot_link_crc32 #(.W(FPW)) u_rx_crc (.d(x0_f[FFW-1:32]), .crc(x0_crc));
    reg  [31:0]     x1_crc;
    reg             x2_ok, x2_eq;
`ifdef OT_DSROM_LINK_MUT_NOCRC
    wire            c_crc_ok = 1'b1;
`else
    wire            c_crc_ok = x2_ok;
`endif
    wire            c_v    = x2_v;
    wire [SEQW-1:0] c_seq  = x2_f[FFW-1 -: SEQW];
    wire            c_last = x2_f[32 + W];
    wire [W-1:0]    c_data = x2_f[32 +: W];

    reg  [SEQW-1:0] exp_seq;
    reg             nak_sent, nak_req, dup_req;
    reg  [CW-1:0]   freed;
    reg  [CW-1:0]   fill;                    // accepted, not yet read out of the array
    reg  [CW-1:0]   cm;                      // written into the array, not yet read
    reg  [IW-1:0]   head;
    wire [SEQW-1:0] c_diff   = c_seq - exp_seq;
    wire [SEQW-1:0] c_back   = exp_seq - c_seq;
    wire            c_good   = c_v && c_crc_ok;
    wire            c_crcerr = c_v && !c_crc_ok;
    wire            c_inord  = c_good && x2_eq;                   // == (c_diff == 0), precomputed
    wire            c_full   = (fill == CRED_C);
    wire            c_acc    = c_inord && !c_full;
    wire            c_ovf    = c_inord && c_full;
    wire            c_ahead  = c_good && (c_diff != 0) && (c_diff < HALF);
    wire            c_behind = c_good && (c_diff >= HALF);
    wire            c_unexpl = (c_ahead && (c_diff >= RPS)) || (c_behind && (c_back > RPS));
    wire            c_nak    = (c_crcerr || c_ahead) && !nak_sent;

    // receive write register -> array -> 2-cycle read -> skid -> out
    reg             wq_v;
    reg  [IW-1:0]   wq_a;
    reg  [W:0]      wq_d;
    reg             r_v1, r_v2;
    reg  [2:0]      sk_cnt;
    reg  [1:0]      sk_hd, sk_tl;
    reg  [W:0]      sk_d [0:SK-1];
    wire [W:0]      fq;
    wire [3:0]      sk_room = {1'b0, sk_cnt} + {3'b0, r_v1} + {3'b0, r_v2};
    wire            r_issue = (cm != 0) && (sk_room < SK);
    reg             ov;
    reg  [W:0]      od;
    wire            o_take  = !ov || out_ready;
    wire            sk_pop  = o_take && (sk_cnt != 0);
    wire            fq_byp  = o_take && (sk_cnt == 0) && r_v2;   // the fresh read goes straight to the output
    assign out_valid = ov;
    assign out_data  = od[W-1:0];
    assign out_last  = od[W];
    ot_dsrom_link_mem #(.W(W + 1), .D(CREDITS), .MEM(MEM)) u_fifo (
        .clk(clk), .r_ce(r_issue), .r_addr(head), .q_en(r_v1), .q(fq),
        .w_ce(wq_v), .w_addr(wq_a), .w_d(wq_d));
    reg  [IW-1:0]   tail;

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
    ot_dsrom_link_chan #(.W(RFW), .MAXD(CHANNEL_CYCLES), .DYN(DYNAMIC_DELAY),
                         .ERR_PERIOD(ERR_PERIOD_REV), .ERR_OFFSET(ERR_OFFSET), .ERR_STRIDE(11)) u_rev (
        .clk(clk), .rst_n(rst_n), .delay(channel_cycles),
        .in_valid(rg_v), .in_data(rg_f),
        .out_valid(rch_v), .out_data(rch_f), .err_injected(rev_injected));

    // ======================================================================
    // State
    // ======================================================================
    reg [5:0] fc_r;                           // registered fault causes, priority on the next cycle
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pace <= PCOST_W; rdy_r <= 1'b1;
            una <= 0; snd <= 0; nxt <= 0; occ <= 0;
            credits <= CRED_C; fr_seen <= 0; timer <= 0; retry <= 0;
            rr_v <= 1'b0; rr_f <= 0;
            ra_ok <= 1'b0; ra_bad <= 1'b0; ra_nak <= 1'b0; ra_ack <= 0; ra_fr <= 0;
            rd_v1 <= 1'b0; rd_v2 <= 1'b0; rd_s1 <= 0; rd_s2 <= 0;
            t0_v <= 1'b0; t0_first <= 1'b0; t0_last <= 1'b0; t0_seq <= 0;
            t1_v <= 1'b0;
            x0_v <= 1'b0; x1_v <= 1'b0; x2_v <= 1'b0; x2_ok <= 1'b0; x2_eq <= 1'b0;
            exp_seq <= 0; nak_sent <= 1'b0; nak_req <= 1'b0; dup_req <= 1'b0;
            freed <= 0; fill <= 0; cm <= 0; head <= 0; tail <= 0;
            wq_v <= 1'b0; r_v1 <= 1'b0; r_v2 <= 1'b0; sk_cnt <= 0; sk_hd <= 0; sk_tl <= 0; ov <= 1'b0;
            tx_ack <= 0; tx_fr <= 0; ka <= KEEPALIVE[KW-1:0] - 1'b1;
            rg_v <= 1'b0; rg_f <= 0;
            fc_r <= 0; fault <= 1'b0; fault_code <= 4'd0; st_max_replay_occ <= 0;
        end else begin
            // ---------------- sender ----------------
            pace <= pace_n;
            rdy_r <= rdy_n;
            rr_v <= rch_v; rr_f <= rch_f;
            ra_ok  <= rr_v && (rr_crc_calc == rr_f[31:0]);
            ra_bad <= rr_v && (rr_crc_calc != rr_f[31:0]);
            ra_nak <= rr_f[RFW-1];
            ra_ack <= rr_f[RFW-2 -: SEQW];
            ra_fr  <= rr_f[32 +: CW];
            nxt <= nxt_n;
            una <= una_n;
            occ <= occ_n;
            snd <= snd_n;                     // rewind > ACK overtaking a rewound pointer > launch
            credits <= credits_n;
            if (ra_ok) fr_seen <= ra_fr;
            if (occ == 0 || progress || rewind) timer <= 0;
            else if (timer != ATO_W) timer <= timer + 1'b1;
            if (progress) retry <= {{(RCW-1){1'b0}}, rewind};
            else if (rewind && retry <= MR_W) retry <= retry + 1'b1;
            // replay read pipeline
            rd_v1 <= rd_issue; rd_s1 <= snd;
            if (rd_v1) begin rd_v2 <= 1'b1; rd_s2 <= rd_s1; end
            else if (rp_go || (rd_v2 && rd_s2 != snd)) rd_v2 <= 1'b0;
            // TX pipe
            t0_v <= launch; t0_first <= accept; t0_seq <= snd;
            t0_data <= rp_go ? rb_q[W-1:0] : in_d;
            t0_last <= rp_go ? rb_q[W] : in_l;
            t1_v <= t0_v; t1_f <= {t0_pay, t0_crc};

            // ---------------- receiver ----------------
            x0_v <= fch_v; x0_f <= fch_f;
            x1_v <= x0_v;  x1_f <= x0_f; x1_crc <= x0_crc;
            x2_v <= x1_v;  x2_f <= x1_f; x2_ok <= (x1_crc == x1_f[31:0]);
            x2_eq <= c_acc ? (x1_f[FFW-1 -: SEQW] == exp_seq + 1'b1) : (x1_f[FFW-1 -: SEQW] == exp_seq);
            if (c_acc) begin
                exp_seq <= exp_seq + 1'b1;
                nak_sent <= 1'b0;
                tail <= tail + 1'b1;
            end else if (c_nak) begin
                nak_sent <= 1'b1;
            end
            wq_v <= c_acc; wq_a <= tail; wq_d <= {c_last, c_data};
            fill <= fill + {{(CW-1){1'b0}}, c_acc} - {{(CW-1){1'b0}}, r_issue};
            cm   <= cm + {{(CW-1){1'b0}}, wq_v} - {{(CW-1){1'b0}}, r_issue};
            if (r_issue) begin head <= head + 1'b1; freed <= freed + 1'b1; end
            r_v1 <= r_issue; r_v2 <= r_v1;
            if (r_v2 && !fq_byp) begin sk_d[sk_tl] <= fq; sk_tl <= sk_tl + 1'b1; end
            if (sk_pop) sk_hd <= sk_hd + 1'b1;
            sk_cnt <= sk_cnt + {2'b0, r_v2 && !fq_byp} - {2'b0, sk_pop};
            if (sk_pop)      begin od <= sk_d[sk_hd]; ov <= 1'b1; end
            else if (fq_byp) begin od <= fq;          ov <= 1'b1; end
            else if (o_take) ov <= 1'b0;

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

            // ---------------- faults (registered causes, first cause latched) ----------------
            fc_r <= {c_unexpl, fr_bad, accept && occ[IW], c_ovf, ack_bad, retry_exh};
            if (fc_r != 0 && !fault) begin
                fault <= 1'b1;
                fault_code <= fc_r[0] ? 4'd1 : fc_r[1] ? 4'd2 : fc_r[2] ? 4'd3 :
                              fc_r[3] ? 4'd4 : fc_r[4] ? 4'd5 : 4'd6;
            end
            if ({{(31-IW){1'b0}}, occ} > st_max_replay_occ) st_max_replay_occ <= {{(31-IW){1'b0}}, occ};
        end
    end

`ifndef SYNTHESIS
    // the registered readiness must equal the direct one every cycle (checked in every bench run)
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire rdy_direct = !occ[IW] && !replaying && pace_ok;
`else
    wire rdy_direct = (credits != 0) && !occ[IW] && !replaying && pace_ok;
`endif
    always @(posedge clk) if (rst_n && (rdy_r !== rdy_direct))
        $fatal(1, "ot_dsrom_link_cl: registered in_ready %b != direct %b at %0t", rdy_r, rdy_direct, $time);
    // the arithmetic-free ACK forms equal link_rt's on every in-window ACK, and the precomputed in-order test
    // equals the direct compare
    wire [SEQW-1:0] snd_off_ref = snd - una;
    always @(posedge clk) if (rst_n && ra_ok && !ack_bad) begin
        if (ack_skip !== (d_ack > snd_off_ref))
            $fatal(1, "ot_dsrom_link_cl: ack_skip mismatch at %0t", $time);
        if (occ_a !== occ - d_ack[IW:0])
            $fatal(1, "ot_dsrom_link_cl: occ_a mismatch at %0t", $time);
    end
    always @(posedge clk) if (rst_n && x2_v && (x2_eq !== (c_diff == 0)))
        $fatal(1, "ot_dsrom_link_cl: in-order precompute mismatch at %0t", $time);
`endif

    // status counters (registered increments, split carry)
    ot_dsrom_link_ctr u_c_cs  (.clk(clk), .rst_n(rst_n), .inc({1'b0, in_valid && !in_ready}), .count(credit_stalls));
    ot_dsrom_link_ctr u_c_tx  (.clk(clk), .rst_n(rst_n), .inc({1'b0, launch}),  .count(st_flits_tx));
    ot_dsrom_link_ctr u_c_rtx (.clk(clk), .rst_n(rst_n), .inc({1'b0, rp_go}),   .count(st_retx_flits));
    ot_dsrom_link_ctr u_c_rx  (.clk(clk), .rst_n(rst_n), .inc({1'b0, c_acc}),   .count(st_flits_rx_ok));
    ot_dsrom_link_ctr u_c_crc (.clk(clk), .rst_n(rst_n), .inc({c_crcerr && ra_bad, c_crcerr ^ ra_bad}), .count(st_crc_err));
    ot_dsrom_link_ctr u_c_nak (.clk(clk), .rst_n(rst_n), .inc({1'b0, rg_need && nak_req}), .count(st_naks));
    ot_dsrom_link_ctr u_c_rep (.clk(clk), .rst_n(rst_n), .inc({1'b0, rewind}),  .count(st_replays));
    ot_dsrom_link_ctr u_c_to  (.clk(clk), .rst_n(rst_n), .inc({1'b0, timeout}), .count(st_timeouts));

    wire unused_ok = &{1'b0, LINK_CLASS[0], fwd_injected, rev_injected};
endmodule

// 32-bit status counter: the increment (0..3) is registered, the low 16 bits add it, their carry is registered
// into the high 16 bits on the next cycle.  The value read may lag the event by up to 2 cycles.
module ot_dsrom_link_ctr (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [1:0]  inc,
    output wire [31:0] count
);
    reg [1:0]  inc_r;
    reg [15:0] lo, hi;
    reg        cy;
    wire [16:0] lo_n = {1'b0, lo} + {15'd0, inc_r};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin inc_r <= 0; lo <= 0; hi <= 0; cy <= 1'b0; end
        else begin
            inc_r <= inc;
            lo <= lo_n[15:0];
            cy <= lo_n[16];
            if (cy) hi <= hi + 1'b1;
        end
    assign count = {hi, lo};
endmodule

// 1R1W storage with a registered read and a second (enable-held) output register:
// r_ce at cycle t -> q valid from cycle t+2 when q_en is high at cycle t+1.  Read-before-write.
// MEM=0: flop array.  MEM=1: ASAP7 ot_sram_1r1w_256x256_m2_r2c2 macros (D = 256), the bits beyond the macro
// tiles in a flop column.
module ot_dsrom_link_mem #(
    parameter integer W   = 8,
    parameter integer D   = 16,
    parameter integer MEM = 0
) (
    input  wire                 clk,
    input  wire                 r_ce,
    input  wire [$clog2(D)-1:0] r_addr,
    input  wire                 q_en,
    output reg  [W-1:0]         q,
    input  wire                 w_ce,
    input  wire [$clog2(D)-1:0] w_addr,
    input  wire [W-1:0]         w_d
);
    localparam integer AW = $clog2(D);
    wire [W-1:0] q1;
    generate if (MEM == 1) begin : g_sram
        localparam integer NT = W / 256;                  // full macro tiles
        localparam integer RB = W - NT * 256;             // remainder bits in flops
        genvar t;
        for (t = 0; t < NT; t = t + 1) begin : g_t
            ot_sram_1r1w_256x256_m2_r2c2 u_m (
                .clk(clk), .r_ce_in(r_ce), .r_addr_in(r_addr[7:0]), .rd_out(q1[t*256 +: 256]),
                .w_ce_in(w_ce), .w_addr_in(w_addr[7:0]), .wd_in(w_d[t*256 +: 256]), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
        if (RB > 0) begin : g_rem
            reg [RB-1:0] arr [0:D-1];
            reg [RB-1:0] q1r;
            always @(posedge clk) begin
                if (r_ce) q1r <= arr[r_addr];
                if (w_ce) arr[w_addr] <= w_d[W-1 -: RB];
            end
            assign q1[W-1 -: RB] = q1r;
        end
    end else begin : g_flop
        reg [W-1:0] arr [0:D-1];
        reg [W-1:0] q1r;
        always @(posedge clk) begin
            if (r_ce) q1r <= arr[r_addr];
            if (w_ce) arr[w_addr] <= w_d;
        end
        assign q1 = q1r;
    end endgenerate
    always @(posedge clk) if (q_en) q <= q1;
endmodule
