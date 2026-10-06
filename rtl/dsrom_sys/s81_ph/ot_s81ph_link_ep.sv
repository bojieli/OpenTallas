`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81ph_link_ep (CLAUDE S81-PH collective, 2026-10-06): one die's END of a reliable link pair, derived from
// ot_dsrom_link_ct (rtl/dsrom_sys/ot_dsrom_link_ct.sv, unchanged).  Protocol, frame formats, invariants, fault codes
// and the three build-time mutants are ct's.  What changes:
//
//  (E) EXTERNAL CHANNEL.  ct holds sender, receiver and BOTH channel models of one direction.  Here the two
//      ot_dsrom_link_chan instances are replaced by ports, so the instance is the sender of this die's OUTBOUND
//      link plus the receiver of its INBOUND link:  f_tx (forward frames out) / f_rx (the peer's forward frames in),
//      r_tx (this receiver's reverse frames out) / r_rx (the peer receiver's reverse frames in).  Two ep instances
//      cross-wired through channels == two ct instances (one per direction), cycle for cycle
//      (tb_s81ph_link_ep: lockstep against ct).
//  (M) SRAM = 1: replay buffer and receive FIFO in ot_s81ph_mem1r1w (512x128 macros).  ct's replay read is
//      already a registered read (address = next cycle's index, same-cycle write forwarded); the receive FIFO's
//      registered output becomes the macro read register (read enable = drain, address = head).
//  (T) MARGIN-FIRST timing, no behaviour change: forward CRC generated over two cycles (TX_STAGES >= 2: partial
//      CRCs of the two payload halves registered in TX stage 0, XORed into stage 1 -- the CRC is affine in the
//      data); forward CRC check over two cycles (RX_STAGES >= 3); reverse-frame CRC check computed on the input
//      and registered beside the frame; pacer compare precomputed; replay index add as a wrap add (RP a power
//      of two).  The status counters stay (die tops leave them unloaded, synthesis removes them).
// ---------------------------------------------------------------------------
module ot_s81ph_link_ep #(
    parameter integer FLIT_BYTES     = 69,
    parameter integer TX_STAGES      = 2,     // >= 2
    parameter integer CHANNEL_CYCLES = 60,    // used only to derive the ACK timeout (as ct)
    parameter integer RX_STAGES      = 3,     // >= 3
    parameter integer CREDITS        = 512,
    parameter integer SEQW           = 10,
    parameter integer REPLAY         = 0,
    parameter integer ACK_TIMEOUT    = 0,
    parameter integer MAX_RETRY      = 8,
    parameter integer KEEPALIVE      = 16,
    parameter integer PHY_NUM        = 0,
    parameter integer PHY_DEN        = 1,
    parameter integer SRAM           = 0,
    // derived frame widths (ports)
    parameter integer FFW_P = SEQW + 1 + FLIT_BYTES * 8 + 32,
    parameter integer RFW_P = 1 + SEQW + $clog2(CREDITS + 1) + 32
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     in_valid,
    output wire                     in_ready,
    input  wire [FLIT_BYTES*8-1:0]  in_data,
    input  wire                     in_last,
    output wire                     out_valid,
    input  wire                     out_ready,
    output wire [FLIT_BYTES*8-1:0]  out_data,
    output wire                     out_last,
    // external channels
    output wire                     f_tx_v,
    output wire [FFW_P-1:0]         f_tx,
    input  wire                     f_rx_v,
    input  wire [FFW_P-1:0]         f_rx,
    output wire                     r_tx_v,
    output wire [RFW_P-1:0]         r_tx,
    input  wire                     r_rx_v,
    input  wire [RFW_P-1:0]         r_rx,
    output reg  [31:0]              credit_stalls,
    output reg                      fault,
    output reg  [3:0]               fault_code,
    output reg  [31:0]              st_flits_tx,
    output reg  [31:0]              st_flits_rx_ok,
    output reg  [31:0]              st_crc_err,
    output reg  [31:0]              st_naks,
    output reg  [31:0]              st_replays,
    output reg  [31:0]              st_timeouts,
    output reg  [31:0]              st_retx_flits,
    output reg  [31:0]              st_max_replay_occ
);
    localparam integer W    = FLIT_BYTES * 8;
    localparam integer RP   = (REPLAY == 0) ? CREDITS : REPLAY;
    localparam integer CW   = $clog2(CREDITS + 1);
    localparam integer IW   = (RP > 1) ? $clog2(RP) : 1;
    localparam integer FPW  = SEQW + 1 + W;
    localparam integer FFW  = FPW + 32;
    localparam integer RVW  = 1 + SEQW + CW;
    localparam integer RFW  = RVW + 32;
    localparam integer RTT  = 2 * CHANNEL_CYCLES + TX_STAGES + RX_STAGES + 6;
    localparam integer ATO  = (ACK_TIMEOUT == 0) ? (RTT + 2 * KEEPALIVE + 32) : ACK_TIMEOUT;
    localparam integer TW   = $clog2(ATO + 2);
    localparam integer RCW  = $clog2(MAX_RETRY + 2);
    localparam integer KW   = $clog2(KEEPALIVE + 1);
    localparam [SEQW-1:0] HALF = {1'b1, {(SEQW-1){1'b0}}};
    localparam [SEQW-1:0] RPS  = RP[SEQW-1:0];
    localparam integer    PW   = (CREDITS > 1) ? $clog2(CREDITS) : 1;
    localparam [31:0]     PLAST32 = CREDITS - 1;
    localparam [31:0]     CRED32  = CREDITS;
    localparam [31:0]     ATO32   = ATO - 1;
    localparam [31:0]     MR32    = MAX_RETRY;
    localparam [PW-1:0]   PLAST  = PLAST32[PW-1:0];
    localparam [CW:0]     CRED_W = CRED32[CW:0];
    localparam [TW-1:0]   ATO_W  = ATO32[TW-1:0];
    localparam [RCW-1:0]  MR_W   = MR32[RCW-1:0];
    localparam integer    HB   = FPW / 2;           // CRC split point

`ifndef SYNTHESIS
    initial begin
        if (TX_STAGES < 2 || RX_STAGES < 3) $fatal(1, "ot_s81ph_link_ep: TX_STAGES >= 2 and RX_STAGES >= 3");
        if (RP < 1 || RP > (1 << (SEQW - 1)) || (1 << IW) != RP) $fatal(1, "ot_s81ph_link_ep: REPLAY must be a power of two <= 2^(SEQW-1)");
        if ((1 << PW) != CREDITS) $fatal(1, "ot_s81ph_link_ep: CREDITS must be a power of two");
        if (FFW != FFW_P || RFW != RFW_P) $fatal(1, "ot_s81ph_link_ep: frame width parameters");
        if (PHY_NUM < 0 || PHY_DEN < 1 || PHY_NUM > FLIT_BYTES * PHY_DEN) $fatal(1, "ot_s81ph_link_ep: PHY_NUM");
    end
`endif

    // RP is a power of two: (x + d) mod RP for x < RP, d <= RP is the IW-bit wrap add (ct: 32-bit add and compare)
    function automatic [IW-1:0] idx_add(input [IW-1:0] x, input [SEQW-1:0] d);
        idx_add = x + d[IW-1:0];
    endfunction

    // ======================================================================== sender
    reg  [SEQW-1:0] una, snd, nxt;
    reg  [IW-1:0]   una_i, snd_i, nxt_i;
    reg  [CW-1:0]   credits;
    reg  [CW-1:0]   fr_seen;
    reg  [TW-1:0]   timer;
    reg  [RCW-1:0]  retry;

    localparam integer PCOST = FLIT_BYTES * PHY_DEN;
    localparam integer PAW   = $clog2(2 * PCOST + PHY_NUM + 1);
    localparam [PAW-1:0] PCOST_W = PCOST[PAW-1:0];
    localparam [PAW-1:0] PNUM_W  = PHY_NUM[PAW-1:0];
    localparam [PAW-1:0] PTH2    = 2 * PCOST - PHY_NUM;        // pace - PCOST + PNUM >= PCOST
    reg  [PAW-1:0]  pace;
    reg             pace_ok_r;
    wire            pace_ok = (PHY_NUM == 0) || pace_ok_r;

    wire [SEQW-1:0] occ = nxt - una;
    wire            replaying = (snd != nxt);
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    assign in_ready = (occ < RPS) && !replaying && pace_ok;
`else
    assign in_ready = (credits != 0) && (occ < RPS) && !replaying && pace_ok;
`endif
    wire            accept = in_valid && in_ready;
    wire            launch = (replaying && pace_ok) || accept;
    // replay storage: registered read of next cycle's index, same-cycle write forwarded
    wire [W:0]      rb_q;
    reg             rb_fwd;
    reg  [W:0]      rb_fwd_d;
    wire [W-1:0]    rd_data = rb_fwd ? rb_fwd_d[W-1:0] : rb_q[W-1:0];
    wire            rd_last = rb_fwd ? rb_fwd_d[W] : rb_q[W];
    wire [W-1:0]    l_data = replaying ? rd_data : in_data;
    wire            l_last = replaying ? rd_last : in_last;
    wire [FPW-1:0]  l_pay  = {snd, l_last, l_data};
    // (T) two-cycle forward CRC: partial CRCs of the halves (the CRC is affine: crc(a ^ b) = crc(a) ^ crc(b) ^ crc(0))
    wire [31:0]     l_crc_lo, l_crc_hi, crc_zero;
    ot_link_crc32 #(.W(FPW)) u_tx_crc_lo (.d({{(FPW-HB){1'b0}}, l_pay[HB-1:0]}), .crc(l_crc_lo));
    ot_link_crc32 #(.W(FPW)) u_tx_crc_hi (.d({l_pay[FPW-1:HB], {HB{1'b0}}}), .crc(l_crc_hi));
    ot_link_crc32 #(.W(FPW)) u_crc_zero (.d({FPW{1'b0}}), .crc(crc_zero));

    // reverse-frame receive register; (T) its CRC check is computed on the input and registered beside it
    reg             rr_v;
    reg  [RFW-1:0]  rr_f;
    reg             rr_crc_ok;
    wire [31:0]     r_rx_crc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_chk (.d(r_rx[RFW-1:32]), .crc(r_rx_crc));
    wire            rr_ok   = rr_v && rr_crc_ok;
    wire            rr_bad  = rr_v && !rr_crc_ok;
    wire            rr_nak  = rr_f[RFW-1];
    wire [SEQW-1:0] rr_ack  = rr_f[RFW-2 -: SEQW];
    wire [CW-1:0]   rr_fr   = rr_f[32 +: CW];
    wire [SEQW-1:0] d_ack   = rr_ack - una;
    wire [CW-1:0]   d_fr    = rr_fr - fr_seen;
    wire            ack_bad = rr_ok && (d_ack > occ);
    wire [CW:0]     cred_sum = {1'b0, credits} + {1'b0, d_fr};
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            fr_bad  = 1'b0;
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
    wire [SEQW-1:0] snd_off = snd_l - una;
    wire            retry_exh = rewind && !progress && (retry >= MR_W);
    wire            ack_skip  = ack_ok && (d_ack > snd_off);
    wire [IW-1:0]   snd_i_nx  = (rewind || ack_skip) ? una_i_n : snd_i_l;

    ot_s81ph_mem1r1w #(.W(W + 1), .DEPTH(RP), .SRAM(SRAM)) u_rb (.clk(clk),
        .we(accept), .wa(nxt_i), .wd({in_last, in_data}), .re(1'b1), .ra(snd_i_nx), .q(rb_q));

    // TX pipe: stage 0 = {payload, partial CRCs}; stage 1 = {payload, CRC}; stages 2.. copies
    reg             tp_v [0:TX_STAGES-1];
    reg  [FFW-1:0]  tp_f [0:TX_STAGES-1];
    reg  [31:0]     tp_lo, tp_hi;
    genvar gi;
    generate for (gi = 0; gi < TX_STAGES; gi = gi + 1) begin : g_tx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_n)
                if (!rst_n) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= launch; tp_f[gi] <= {l_pay, 32'd0}; tp_lo <= l_crc_lo; tp_hi <= l_crc_hi; end
        end else if (gi == 1) begin : g_crc
            always @(posedge clk or negedge rst_n)
                if (!rst_n) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= tp_v[gi-1]; tp_f[gi] <= {tp_f[gi-1][FFW-1:32], tp_lo ^ tp_hi
`ifndef OT_S81PH_EP_MUT_NOZERO
                    ^ crc_zero
`endif
                    }; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_n)
                if (!rst_n) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= tp_v[gi-1]; tp_f[gi] <= tp_f[gi-1]; end
        end
    end endgenerate
    assign f_tx_v = tp_v[TX_STAGES-1];
    assign f_tx   = tp_f[TX_STAGES-1];

    // ======================================================================== receiver
    reg             xp_v [0:RX_STAGES-1];
    reg  [FFW-1:0]  xp_f [0:RX_STAGES-1];
    generate for (gi = 0; gi < RX_STAGES; gi = gi + 1) begin : g_rx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_n)
                if (!rst_n) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= f_rx_v; xp_f[gi] <= f_rx; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_n)
                if (!rst_n) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= xp_v[gi-1]; xp_f[gi] <= xp_f[gi-1]; end
        end
    end endgenerate

    wire            c_v    = xp_v[RX_STAGES-1];
    wire [FFW-1:0]  c_f    = xp_f[RX_STAGES-1];
    // (T) CRC of RX stage RX_STAGES-3 in two halves, registered beside stage RX_STAGES-2, compared into the flag
    // registered beside the last stage (ct: one cycle, stage RX_STAGES-2)
    wire [FFW-1:0]  q_f    = xp_f[RX_STAGES-3];
    wire [31:0]     q_lo, q_hi;
    ot_link_crc32 #(.W(FPW)) u_rx_crc_lo (.d({{(FPW-HB){1'b0}}, q_f[32 +: HB]}), .crc(q_lo));
    ot_link_crc32 #(.W(FPW)) u_rx_crc_hi (.d({q_f[FFW-1:32+HB], {HB{1'b0}}}), .crc(q_hi));
    reg  [31:0]     p_lo, p_hi, p_got;
    reg             c_crc_ok_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin c_crc_ok_r <= 1'b0; p_lo <= 0; p_hi <= 0; p_got <= 0; end
        else begin
            p_lo <= q_lo; p_hi <= q_hi; p_got <= q_f[31:0];
            c_crc_ok_r <= ((p_lo ^ p_hi ^ crc_zero) == p_got);
        end
`ifdef OT_DSROM_LINK_MUT_NOCRC
    wire            c_crc_ok = 1'b1;
`else
    wire            c_crc_ok = c_crc_ok_r;
`endif
    wire [SEQW-1:0] c_seq  = c_f[FFW-1 -: SEQW];
    wire            c_last = c_f[32 + W];
    wire [W-1:0]    c_data = c_f[32 +: W];

    reg  [SEQW-1:0] exp_seq;
    reg             nak_sent, nak_req, dup_req;
    reg  [CW-1:0]   freed;
    reg  [CW-1:0]   fill;
    reg  [PW-1:0]   head, tail;
    reg             out_valid_r;
    wire [W:0]      fifo_q;
    assign out_valid = out_valid_r;
    assign out_data  = fifo_q[W-1:0];
    assign out_last  = fifo_q[W];

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

    ot_s81ph_mem1r1w #(.W(W + 1), .DEPTH(CREDITS), .SRAM(SRAM)) u_fifo (.clk(clk),
        .we(c_acc), .wa(tail), .wd({c_last, c_data}), .re(drain), .ra(head), .q(fifo_q));

    reg  [SEQW-1:0] tx_ack;
    reg  [CW-1:0]   tx_fr;
    reg  [KW-1:0]   ka;
    wire            rg_need = nak_req || dup_req || (exp_seq != tx_ack) || (freed != tx_fr) || (ka == 0);
    wire [RVW-1:0]  rg_pay  = {nak_req, exp_seq, freed};
    wire [31:0]     rg_crc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_gen (.d(rg_pay), .crc(rg_crc));
    reg             rg_v;
    reg  [RFW-1:0]  rg_f;
    assign r_tx_v = rg_v;
    assign r_tx   = rg_f;

    // ======================================================================== state
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
    wire pace_ok_launch = (pace >= PTH2);
    wire pace_ok_inc    = ({1'b0, pace} + {1'b0, PNUM_W}) >= {1'b0, PCOST_W};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            una <= 0; snd <= 0; nxt <= 0; una_i <= 0; snd_i <= 0; nxt_i <= 0;
            credits <= CREDITS[CW-1:0]; fr_seen <= 0; timer <= 0; retry <= 0;
            pace <= PCOST_W; pace_ok_r <= 1'b1; rb_fwd <= 1'b0; rb_fwd_d <= 0;
            rr_v <= 1'b0; rr_f <= 0; rr_crc_ok <= 1'b0;
            exp_seq <= 0; nak_sent <= 1'b0; nak_req <= 1'b0; dup_req <= 1'b0;
            freed <= 0; fill <= 0; head <= 0; tail <= 0;
            out_valid_r <= 1'b0;
            tx_ack <= 0; tx_fr <= 0; ka <= KEEPALIVE[KW-1:0] - 1'b1;
            rg_v <= 1'b0; rg_f <= 0;
            fault <= 1'b0; fault_code <= 4'd0; credit_stalls <= 0;
            st_flits_tx <= 0; st_flits_rx_ok <= 0; st_crc_err <= 0; st_naks <= 0;
            st_replays <= 0; st_timeouts <= 0; st_retx_flits <= 0; st_max_replay_occ <= 0;
        end else begin
            if (PHY_NUM != 0) begin
                if (launch)        begin pace <= pace - PCOST_W + PNUM_W; pace_ok_r <= pace_ok_launch; end
                else if (!pace_ok) begin pace <= pace + PNUM_W;           pace_ok_r <= pace_ok_inc;    end
            end
            rb_fwd <= accept && (nxt_i == snd_i_nx);
            if (accept) rb_fwd_d <= {in_last, in_data};
            if (accept) begin
                nxt   <= nxt + 1'b1;
                nxt_i <= idx_add(nxt_i, 1);
            end
            una <= una_n; una_i <= una_i_n;
            if (rewind) begin
                snd <= una_n; snd_i <= una_i_n;
            end else if (ack_skip) begin
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
            rr_v <= r_rx_v; rr_f <= r_rx; rr_crc_ok <= (r_rx_crc == r_rx[31:0]);

            if (c_acc) begin
                tail <= (tail == PLAST) ? {PW{1'b0}} : tail + 1'b1;
                exp_seq <= exp_seq + 1'b1;
                nak_sent <= 1'b0;
            end else if (c_nak) begin
                nak_sent <= 1'b1;
            end
            if (drain) begin
                head <= (head == PLAST) ? {PW{1'b0}} : head + 1'b1;
                out_valid_r <= 1'b1;
                freed <= freed + 1'b1;
            end else if (out_valid_r && out_ready) begin
                out_valid_r <= 1'b0;
            end
            fill <= fill + {{(CW-1){1'b0}}, c_acc} - {{(CW-1){1'b0}}, drain};

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

            if (fault_n != 0 && !fault) begin fault <= 1'b1; fault_code <= fault_n; end
            if (in_valid && !in_ready) credit_stalls <= credit_stalls + 1;
            if (launch) st_flits_tx <= st_flits_tx + 1;
            if (launch && replaying) st_retx_flits <= st_retx_flits + 1;
            if (c_acc) st_flits_rx_ok <= st_flits_rx_ok + 1;
            st_crc_err <= st_crc_err + {31'd0, c_crcerr} + {31'd0, rr_bad};
            if (rg_need && nak_req) st_naks <= st_naks + 1;
            if (rewind) st_replays <= st_replays + 1;
            if (timeout) st_timeouts <= st_timeouts + 1;
            if ({{(32-SEQW){1'b0}}, occ} > st_max_replay_occ) st_max_replay_occ <= {{(32-SEQW){1'b0}}, occ};
        end
    end
endmodule
