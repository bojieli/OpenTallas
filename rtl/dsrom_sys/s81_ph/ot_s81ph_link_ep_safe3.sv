// S81-COLL bank64 safe3 fork (LEAD-S81 10-19) of ot_s81ph_link_ep_safe2 (which stays byte-identical); OLDREAD 1 only.
// Changes, all cycle-identical at every port (lane miter against the legacy P1 lane):
//  * replay buffer and receive FIFO on ot_sram_oldread_b64 (2 x 9 ot_sram_1r1w2c_256x64_m1 each; 2.56 pins/um faces);
//  * a_rep (1,106 loads: b_pay replay/in select) -> kept same-edge copies per ARS-bit slice, fed by two kept copies of
//    rep_r (same D);
//  * S2 reverse-frame stage: s2 data registers load every cycle (all consumers are qualified by the S2 valid), so
//    p_take drives no wide enable; ack_ok / rr_ok are kept REGISTERED copies per consumer group (same edge as s2v,
//    D = p_take && !bad, the original s2v && !s2bad); una has a kept copy for the S2 subtracts;
//  * ready/replay next state: (sndnx == nxt) evaluated as parallel compares selected by rewind / skip (same function,
//    shorter cone than the 16-level snd -> sub -> compare -> mux -> compare -> ready_r path);
//  * reset: RN same-depth reset leaves (rst_v), <= ~32 reset pins each, instead of one 191-load leaf;
//  * out_ready: ORN copies (caller registered flags), groups split across them.
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
module ot_s81ph_link_ep_safe3 #(
    parameter integer FLIT_BYTES     = 69,
    parameter integer TX_STAGES      = 2,     // >= 2
    parameter integer CHANNEL_CYCLES = 60,    // used only to derive the ACK timeout (as ct)
    parameter integer CHANNEL_CYCLES_B = CHANNEL_CYCLES,   // CLAUDE S81-PH coll v2: second timeout basis, chosen by the static pin ch_b (one lane tile master serves UCIe and board lanes)
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
    // RXPIPE (ds-1010 2026-10-10, opt-in; RX_STAGES >= 3): the receive sequence classification is precomputed one stage
    // early against the NEXT expected sequence (exp_seq + this cycle's accept, both arms in parallel, selected at the
    // flop), so c_acc = registered in-order flag && !full: the 10-bit seq subtract / compare no longer sits in front of
    // fill / tail / exp_seq / the landing SRAM write in one cycle (coll lane lcrpe TT -560 exp_seq -> fill).  0 cycles.
    // TOREG (ds-1010 2026-10-10, opt-in): the ACK timeout limit (static ch_b select) is registered and the timer keeps a
    // registered at-limit flag, so timeout = occ && !progress && at_lim (coll lane lcrpg TT -470 = ch_b_q -> limit mux ->
    // timer == limit compare -> retry / rewind across the tile).  0 cycles.
    // MWR (ds-1010/coll-tu 2026-10-11, opt-in): the replay buffer and the receive FIFO use ot_s81ph_mem1r1w WREG = 1
    // (registered write ports beside the macros, read-after-write forwarded inside the wrapper; caller-visible timing
    // unchanged), and the replay forward word rb_fwd_d loads every cycle (it is read only when rb_fwd, i.e. right after an
    // accept, so its accept load enable was redundant): accept no longer drives 553-bit enables or macro pins directly
    // (lane lcrpi: hold stuck -68 at u_rb w_addr_in = nxt_i, a setup-critical register).  0 cycles.
    parameter integer MWR            = `ifdef OT_S81PH_EP_MWR 1 `else 0 `endif,
    parameter integer OLDREAD = 0,
    parameter integer MEM_NS = (FLIT_BYTES*8+1+7)/8,
    parameter integer MEM_NA = (MEM_NS+3)/4,
    parameter integer TOREG          = `ifdef OT_S81PH_EP_TOREG 1 `else 0 `endif,
    parameter integer RXPIPE         = `ifdef OT_S81PH_EP_RXPIPE 1 `else 0 `endif,
    // DNR (S81-SAFE-FIX/COLL 2026-10-19, opt-in, default 0 = same netlist): the frame DATA registers (TX pipe tp_f /
    // tp_lo / tp_hi, RX pipe xp_f, RX CRC partials p_lo / p_hi / p_got, reverse frames rr_f / rg_f) load every cycle in
    // reset-free processes.  Written inside the async-reset processes without a reset value, yosys kept them "hold during
    // reset" = one rst_n-gated enable per bit: the lane's reset synchroniser drove 6,837 loads (5,700 NAND2 / OA21 data
    // enables + the async clears; dscoll_lane_w_ltr gate textbook.high_fanout).  Every consumer is qualified by its
    // reset valid (tp_v / xp_v / rr_v / rg_v), so the transfer function after reset is unchanged.  0 cycles.
    parameter integer DNR            = 0,
    parameter integer PIPE           = 0,     // CLAUDE S81-PH coll lane v3: 1 = sender pipelined (see the PIPE notes below)
                                              // CLAUDE s81-blocks 2026-10-07: 2 = PIPE 1 + (a) the freed-count difference
                                              // d_fr registered in S2 (fr_seen only changes in S2-apply cycles, as una for
                                              // s2dack), (b) rdy_r / rep_r / credits / snd / snd_i computed for accept = 0
                                              // and 1 in parallel and selected by accept at the flop (lane e -489 / w -408)
    // derived frame widths (ports)
    parameter integer FFW_P = SEQW + 1 + FLIT_BYTES * 8 + 32,
    parameter integer RFW_P = 1 + SEQW + $clog2(CREDITS + 1) + 32,
    parameter integer ARS = 24,               // a_rep copy slice
    parameter integer RN = 12,                // reset leaves
    parameter integer ORN = 3                 // out_ready copies
) (
    input  wire                     clk,
    input  wire [RN-1:0]            rst_v,
    input wire [2*(MEM_NS+MEM_NA)-1:0] mem_rst_n,
    input  wire                     ch_b,      // static: 1 = ACK timeout from CHANNEL_CYCLES_B
    input  wire                     in_valid,
    output wire                     in_ready,
    input  wire [FLIT_BYTES*8-1:0]  in_data,
    input  wire                     in_last,
    output wire                     out_valid,
    input  wire [ORN-1:0]           out_ready_v,
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
    wire rst_n = rst_v[0];                       // only for non-synthesis checks below
    wire out_ready = out_ready_v[0];
    localparam integer W    = FLIT_BYTES * 8;
    localparam integer RP   = (REPLAY == 0) ? CREDITS : REPLAY;
    localparam integer CW   = $clog2(CREDITS + 1);
    localparam integer IW   = (RP > 1) ? $clog2(RP) : 1;
    localparam integer FPW  = SEQW + 1 + W;
    localparam integer FFW  = FPW + 32;
    localparam integer RVW  = 1 + SEQW + CW;
    localparam integer RFW  = RVW + 32;
    localparam integer RTT  = 2 * CHANNEL_CYCLES + TX_STAGES + 2 * PIPE + RX_STAGES + 6;
    localparam integer RTTB = 2 * CHANNEL_CYCLES_B + TX_STAGES + 2 * PIPE + RX_STAGES + 6;
    localparam integer ATO  = (ACK_TIMEOUT == 0) ? (RTT + 2 * KEEPALIVE + 32) : ACK_TIMEOUT;
    localparam integer ATOB = (ACK_TIMEOUT == 0) ? (RTTB + 2 * KEEPALIVE + 32) : ACK_TIMEOUT;
    localparam integer TW   = $clog2(((ATOB > ATO) ? ATOB : ATO) + 2);
    localparam integer RCW  = $clog2(MAX_RETRY + 2);
    localparam integer KW   = $clog2(KEEPALIVE + 1);
    localparam [SEQW-1:0] HALF = {1'b1, {(SEQW-1){1'b0}}};
    localparam [SEQW-1:0] RPS  = RP[SEQW-1:0];
    localparam integer    PW   = (CREDITS > 1) ? $clog2(CREDITS) : 1;
    localparam [31:0]     PLAST32 = CREDITS - 1;
    localparam [31:0]     CRED32  = CREDITS;
    localparam [31:0]     ATO32   = ATO - 1;
    localparam [31:0]     ATOB32  = ATOB - 1;
    localparam [31:0]     MR32    = MAX_RETRY;
    localparam [PW-1:0]   PLAST  = PLAST32[PW-1:0];
    localparam [CW:0]     CRED_W = CRED32[CW:0];
    localparam [TW-1:0]   ATO_WA = ATO32[TW-1:0];
    localparam [TW-1:0]   ATO_WB = ATOB32[TW-1:0];
    reg ch_b_q;                                // static pin, registered
    always @(posedge clk) ch_b_q <= ch_b;
    wire [TW-1:0]         ATO_W  = ch_b_q ? ATO_WB : ATO_WA;
    reg  [TW-1:0]         ato_q;                 // TOREG: registered limit (static after reset)
    always @(posedge clk) ato_q <= ATO_W;
    reg                   at_lim;                // TOREG: timer == limit, registered with the timer
    wire [TW-1:0]         ATO_S  = TOREG ? ato_q : ATO_W;
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

`ifndef SYNTHESIS
    initial if(OLDREAD!=0 && (PIPE!=2 || MWR!=1 || SRAM!=1 || IW!=9 || PW!=9))
      $fatal(1,"COLL safe oldread requires current512-row PIPE2/MWR1 SRAM contract");
`endif
    // RP is a power of two: (x + d) mod RP for x < RP, d <= RP is the IW-bit wrap add (ct: 32-bit add and compare)
    function automatic [IW-1:0] idx_add(input [IW-1:0] x, input [SEQW-1:0] d);
        idx_add = x + d[IW-1:0];
    endfunction

    // ======================================================================== sender
    reg  [SEQW-1:0] una, snd, nxt;
    // safe3: kept copy of snd for the ready / skip compares, in its own kept hierarchy (ot_s81ph_kff10,
    // SYNTH_KEEP_MODULES): a same-D (* keep *) reg was merged back into snd by Yosys (mapped census 10-19: 33 loads)
    wire [SEQW-1:0] snd_c;
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
    // PIPE (coll lane v3, s81ph-dsfd_coll_lane_w-34b3e75dd SS -971: nxt -> occ / ack compare -> una_i add ->
    // replay read address -> SRAM -> CRC -> tp, 30 levels, one cycle):
    //  (1) in_ready and replaying are REGISTERS computed from the next-state values (same function, one flop)
    //  (2) the replay read address is the snd_i register (read data one cycle later), payload registered (stage A
    //      launch, stage B payload), CRC from registers: +2 TX cycles (RTT / ACK timeout include them)
    //  (3) reverse frames: pin register -> pending slot P (newest frame wins; NAK sticky until taken) -> stage S2
    //      (ack / credit differences against una / fr_seen, which only change when S2 applies) -> applied: one
    //      reverse frame applied every other cycle at most; ACKs and freed counts are cumulative, so merging is exact
    //      for the protocol (go-back-N recovers any NAK merged into a newer ACK)
    //  (4) index registers are seq[IW-1:0] (RP a power of two): una_i_n = ack[IW-1:0], no add
    reg             rdy_r, rep_r;
    wire            replaying = PIPE ? rep_r : (snd != nxt);
    // safe3: in_ready is a kept copy of rdy_r (the caller's pop), and accept is evaluated per consumer group from
    // kept rdy_r copies (a: snd / snd_i / rdy / rep, b: nxt / credits, c: launch / pace / faults) -- same edge, same D.
    (* keep = "true" *) reg [3:0] rdy_k;
    assign in_ready = rdy_k[3];
    wire            accept_a = in_valid && rdy_k[0], accept_b = in_valid && rdy_k[1], accept_c = in_valid && rdy_k[2];
    wire            accept = accept_c;
    wire            launch = (replaying && pace_ok) || accept_c;
    // replay storage: registered read of next cycle's index, same-cycle write forwarded
    wire [W:0]      rb_q;
    reg             rb_fwd;
    reg  [W:0]      rb_fwd_d;
    wire [W-1:0]    rd_data = rb_fwd ? rb_fwd_d[W-1:0] : rb_q[W-1:0];
    wire            rd_last = rb_fwd ? rb_fwd_d[W] : rb_q[W];
    wire [W-1:0]    l_data = replaying ? rd_data : in_data;
    wire            l_last = replaying ? rd_last : in_last;
    wire [FPW-1:0]  l_pay  = {snd, l_last, l_data};
    // PIPE TX stages A (launch, replay select, in word) / B (payload from the registered replay read)
    reg             a_v, b_v; reg [SEQW-1:0] a_snd; reg [W:0] a_in; reg [FPW-1:0] b_pay;
    always @(posedge clk or negedge rst_v[0]) if (!rst_v[0]) begin a_v <= 1'b0; b_v <= 1'b0; end else begin a_v <= launch; b_v <= a_v; end
    always @(posedge clk) begin
        a_snd <= snd; a_in <= {in_last, in_data};
        b_pay[FPW-1 -: SEQW] <= a_snd;
    end
    // a_rep: kept copies, one per ARS payload bits, from two kept copies of rep_r (same D as rep_r)
    localparam integer NAR = (W + 1 + ARS - 1) / ARS;
    (* keep = "true" *) reg [1:0] rep_ra;
    generate for (genvar ar = 0; ar < NAR; ar = ar + 1) begin : g_arep
        localparam integer LO = ar * ARS, HI = ((ar + 1) * ARS > W + 1) ? W + 1 : (ar + 1) * ARS;
        (* keep = "true" *) reg a_rep_c, a_in_c;   // one-hot {replay, in} select copies: one AND-OR term per bit each
        always @(posedge clk) begin
            a_rep_c <= rep_ra[(2 * ar) / NAR];
            a_in_c  <= !rep_ra[(2 * ar) / NAR];
            b_pay[HI-1:LO] <= ({(HI-LO){a_rep_c}} & rb_q[HI-1:LO]) | ({(HI-LO){a_in_c}} & a_in[HI-1:LO]);
        end
    end endgenerate
    wire [FPW-1:0]  t_pay    = PIPE ? b_pay : l_pay;
    wire            t_launch = PIPE ? b_v : launch;
    // (T) two-cycle forward CRC: partial CRCs of the halves (the CRC is affine: crc(a ^ b) = crc(a) ^ crc(b) ^ crc(0))
    wire [31:0]     l_crc_lo, l_crc_hi, crc_zero;
    ot_link_crc32 #(.W(FPW)) u_tx_crc_lo (.d({{(FPW-HB){1'b0}}, t_pay[HB-1:0]}), .crc(l_crc_lo));
    ot_link_crc32 #(.W(FPW)) u_tx_crc_hi (.d({t_pay[FPW-1:HB], {HB{1'b0}}}), .crc(l_crc_hi));
    ot_link_crc32 #(.W(FPW)) u_crc_zero (.d({FPW{1'b0}}), .crc(crc_zero));

    // reverse-frame receive register; (T) its CRC check is computed on the input and registered beside it
    reg             rr_v;
    (* keep = "true" *) reg [1:0] rrv_k, rrc_k;    // safe3: kept copies of rr_v / rr_crc_ok for the pending-slot enables
    reg  [RFW-1:0]  rr_f;
    reg             rr_crc_ok;
    wire [31:0]     r_rx_crc;
    ot_link_crc32 #(.W(RVW)) u_rv_crc_chk (.d(r_rx[RFW-1:32]), .crc(r_rx_crc));
    wire            rr_ok0  = rr_v && rr_crc_ok;
    wire            rr_bad  = rr_v && !rr_crc_ok;
    reg  [RFW-1:0]  rrn_f;                       // DNR: reset-free reverse frame (qualified by rr_v)
    always @(posedge clk) rrn_f <= r_rx;
    wire [RFW-1:0]  rr_fs   = (DNR != 0) ? rrn_f : rr_f;
    wire            rr_nak0 = rr_fs[RFW-1];
    wire [SEQW-1:0] rr_ack0 = rr_fs[RFW-2 -: SEQW];
    wire [CW-1:0]   rr_fr0  = rr_fs[32 +: CW];
    // PIPE: pending slot P and decode stage S2
    reg             pv, s2v, pnak, s2nak, s2bad; reg [SEQW-1:0] pack, s2ack, s2dack; reg [CW-1:0] pfr, s2fr, s2dfr;
    wire            p_take = pv && !s2v;
    // kept registered copies, same edge as s2v: ok_u = ack_ok for una / una_i; ok_c = ack_ok for control; ok_f = rr_ok
    // for the freed-credit path.  una_s = kept copy of una for the S2 subtracts.
    // ok_u / ok_v / ok_c: same-edge copies of (p_take && !p_bad), each in its own kept hierarchy (ot_s81ph_kff1):
    // the (* keep *) regs were partially merged by Yosys (mapped census 10-19: ok_u 37 loads)
    wire ok_u, ok_v, ok_c; (* keep = "true" *) reg ok_f;
    (* keep = "true" *) reg [SEQW-1:0] una_s;
    wire [SEQW-1:0] p_dack = pack - una_s;
    wire            p_bad  = p_dack > (nxt - una_s);
    wire ok_d = p_take && !p_bad;
    ot_s81ph_kff1 u_k_oku (.clk(clk), .rst_n(rst_v[0]), .d(ok_d), .q(ok_u));
    ot_s81ph_kff1 u_k_okv (.clk(clk), .rst_n(rst_v[0]), .d(ok_d), .q(ok_v));
    ot_s81ph_kff1 u_k_okc (.clk(clk), .rst_n(rst_v[0]), .d(ok_d), .q(ok_c));
    always @(posedge clk or negedge rst_v[0])
        if (!rst_v[0]) begin pv <= 1'b0; s2v <= 1'b0; pnak <= 1'b0; ok_f <= 1'b0; una_s <= 0; end
        else begin
            s2v <= p_take; ok_f <= p_take;
            una_s <= una_n;
            if (rr_ok0) begin pv <= 1'b1; pnak <= rr_nak0 | (pv && !p_take && pnak); end
            else if (p_take) begin pv <= 1'b0; pnak <= 1'b0; end
        end
    // S2 data: loaded every cycle (read only in S2-valid cycles, which follow a p_take edge)
    always @(posedge clk) begin
        if (rrv_k[0] && rrc_k[0]) pack <= rr_ack0;
        if (rrv_k[1] && rrc_k[1]) pfr <= rr_fr0;
        s2ack <= pack; s2fr <= pfr; s2nak <= pnak; s2dack <= p_dack; s2bad <= p_bad; s2dfr <= pfr - fr_seen;
    end
    wire            rr_ok   = PIPE ? s2v : rr_ok0;
    wire            rr_nak  = PIPE ? s2nak : rr_nak0;
    wire [SEQW-1:0] rr_ack  = PIPE ? s2ack : rr_ack0;
    wire [CW-1:0]   rr_fr   = PIPE ? s2fr : rr_fr0;
    wire [SEQW-1:0] d_ack   = PIPE ? s2dack : (rr_ack - una);
    wire [CW-1:0]   d_fr    = (PIPE >= 2) ? s2dfr : (rr_fr - fr_seen);
    wire            ack_bad = rr_ok && (PIPE ? s2bad : (d_ack > occ));   // fault code only (ok_* carry the control)
    wire [CW:0]     cred_sum = {1'b0, credits} + {1'b0, d_fr};
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            fr_bad  = 1'b0;
`else
    wire            fr_bad  = ok_f && (cred_sum > CRED_W);
`endif
    wire            ack_ok  = ok_c;                                 // = rr_ok && !ack_bad (registered copy)
    wire            progress = ack_ok && (d_ack != 0);
    wire [SEQW-1:0] una_n   = ok_u ? rr_ack : una;
    wire [IW-1:0]   una_i_n = ok_u ? rr_ack[IW-1:0] : una_i;     // = una_i + d_ack (indices are seq mod RP)
`ifdef OT_S81PH_EP_TOREG_MUT
    wire            timeout = (occ != 0) && !progress && (TOREG ? 1'b0 : (timer == ATO_W));  // mutant: the registered timeout never fires
`else
    wire            timeout = (occ != 0) && !progress && (TOREG ? at_lim : (timer == ATO_W));
`endif
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

    generate if(OLDREAD!=0) begin:g_rb_safe
        wire [MEM_NA*IW-1:0] wa_copy,ra_copy;
        wire [MEM_NA-1:0] wr_group;
        for(genvar mg=0;mg<MEM_NA;mg=mg+1) begin:g_address
            (* keep="true" *) reg [IW-1:0] wp_r,rp_r;
            (* keep="true" *) reg ready_r;
            wire wr=in_valid && ready_r;
            assign wr_group[mg]=wr;
            assign wa_copy[IW*mg+:IW]=wp_r;
            assign ra_copy[IW*mg+:IW]=rp_r;
            always @(posedge clk or negedge mem_rst_n[MEM_NS+mg])
              if(!mem_rst_n[MEM_NS+mg]) begin wp_r<=0;rp_r<=0;ready_r<=1;end
              else begin
                wp_r<=wp_r+IW'(wr);
                rp_r<=wr?sndinx_1k:sndinx_0k;
                ready_r<=wr?rdy_1k:rdy_0k;
              end
`ifndef SYNTHESIS
            always @(posedge clk) if(rst_n && mem_rst_n[MEM_NS+mg])
              if({wp_r,rp_r,ready_r,wr,rdy_k} !== {nxt_i,snd_i,rdy_r,accept,{4{rdy_r}}})
                $fatal(1,"COLL replay group state differs group%0d",mg);
`endif
        end
        ot_sram_oldread_b64 #(.W(W+1),.AW(IW),.SB(8),.GA(4),.GROUP_IO(1),
`ifdef OT_S81PH_OLDREAD_MUT
          .MUT(1)
`elsif OT_S81PH_B64_COLLIDE_MUT
          .MUT(2)
`else
          .MUT(0)
`endif
        ) u_m(.clk(clk),.rst_n(mem_rst_n[0+:MEM_NS]),.we(accept),.we_group(wr_group),
          .wa(wa_copy),.wd({in_last,in_data}),.re(1'b1),.re_group({MEM_NA{1'b1}}),.ra(ra_copy),.q(rb_q));
    end else begin:g_rb_legacy
    ot_s81ph_mem1r1w #(.W(W + 1), .DEPTH(RP), .SRAM(SRAM), .WREG(MWR)) u_rb (.clk(clk), .rst_n(rst_n),
        .we(accept), .wa(nxt_i), .wd({in_last, in_data}), .re(1'b1), .ra(PIPE ? snd_i : snd_i_nx), .q(rb_q));
    end endgenerate


    // TX pipe: stage 0 = {payload, partial CRCs}; stage 1 = {payload, CRC}; stages 2.. copies
    reg             tp_v [0:TX_STAGES-1];
    reg  [FFW-1:0]  tp_f [0:TX_STAGES-1];
    reg  [31:0]     tp_lo, tp_hi;
    genvar gi;
    generate for (gi = 0; gi < TX_STAGES; gi = gi + 1) begin : g_tx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= t_launch; tp_f[gi] <= {t_pay, 32'd0}; tp_lo <= l_crc_lo; tp_hi <= l_crc_hi; end
        end else if (gi == 1) begin : g_crc
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= tp_v[gi-1]; tp_f[gi] <= {tp_f[gi-1][FFW-1:32], tp_lo ^ tp_hi
`ifndef OT_S81PH_EP_MUT_NOZERO
                    ^ crc_zero
`endif
                    }; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) tp_v[gi] <= 1'b0;
                else begin tp_v[gi] <= tp_v[gi-1]; tp_f[gi] <= tp_f[gi-1]; end
        end
    end endgenerate
    assign f_tx_v = tp_v[TX_STAGES-1];
    reg  [FFW-1:0]  tpn_f [0:TX_STAGES-1];       // DNR: reset-free frame data
    reg  [31:0]     tpn_lo, tpn_hi;
    generate if (DNR != 0) begin : g_tx_dnr
        for (gi = 0; gi < TX_STAGES; gi = gi + 1) begin : g_s
            if (gi == 0) begin : g_first
                always @(posedge clk) begin tpn_f[gi] <= {t_pay, 32'd0}; tpn_lo <= l_crc_lo; tpn_hi <= l_crc_hi; end
            end else if (gi == 1) begin : g_crc
                always @(posedge clk) tpn_f[gi] <= {tpn_f[gi-1][FFW-1:32], tpn_lo ^ tpn_hi
`ifndef OT_S81PH_EP_MUT_NOZERO
                    ^ crc_zero
`endif
                    };
            end else begin : g_rest
                always @(posedge clk) tpn_f[gi] <= tpn_f[gi-1];
            end
        end
    end endgenerate
    assign f_tx   = (DNR != 0) ? tpn_f[TX_STAGES-1] : tp_f[TX_STAGES-1];

    // ======================================================================== receiver
    reg             xp_v [0:RX_STAGES-1];
    reg  [FFW-1:0]  xp_f [0:RX_STAGES-1];
    generate for (gi = 0; gi < RX_STAGES; gi = gi + 1) begin : g_rx
        if (gi == 0) begin : g_first
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= f_rx_v; xp_f[gi] <= f_rx; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_v[1])
                if (!rst_v[1]) xp_v[gi] <= 1'b0;
                else begin xp_v[gi] <= xp_v[gi-1]; xp_f[gi] <= xp_f[gi-1]; end
        end
    end endgenerate

    wire            c_v    = xp_v[RX_STAGES-1];
    reg  [FFW-1:0]  xpn_f [0:RX_STAGES-1];       // DNR: reset-free frame data
    generate if (DNR != 0) begin : g_rx_dnr
        for (gi = 0; gi < RX_STAGES; gi = gi + 1) begin : g_s
            if (gi == 0) begin : g_first
                always @(posedge clk) xpn_f[gi] <= f_rx;
            end else begin : g_rest
                always @(posedge clk) xpn_f[gi] <= xpn_f[gi-1];
            end
        end
    end endgenerate
    wire [FFW-1:0]  c_f    = (DNR != 0) ? xpn_f[RX_STAGES-1] : xp_f[RX_STAGES-1];
    // (T) CRC of RX stage RX_STAGES-3 in two halves, registered beside stage RX_STAGES-2, compared into the flag
    // registered beside the last stage (ct: one cycle, stage RX_STAGES-2)
    wire [FFW-1:0]  q_f    = (DNR != 0) ? xpn_f[RX_STAGES-3] : xp_f[RX_STAGES-3];
    wire [31:0]     q_lo, q_hi;
    ot_link_crc32 #(.W(FPW)) u_rx_crc_lo (.d({{(FPW-HB){1'b0}}, q_f[32 +: HB]}), .crc(q_lo));
    ot_link_crc32 #(.W(FPW)) u_rx_crc_hi (.d({q_f[FFW-1:32+HB], {HB{1'b0}}}), .crc(q_hi));
    reg  [31:0]     p_lo, p_hi, p_got;
    reg             c_crc_ok_r;
    wire [31:0]     p_lo_s, p_hi_s, p_got_s;
    always @(posedge clk or negedge rst_v[1])
        if (!rst_v[1]) begin c_crc_ok_r <= 1'b0; p_lo <= 0; p_hi <= 0; p_got <= 0; end
        else begin
            p_lo <= q_lo; p_hi <= q_hi; p_got <= q_f[31:0];
            c_crc_ok_r <= ((p_lo_s ^ p_hi_s ^ crc_zero) == p_got_s);
        end
    reg  [31:0]     pn_lo, pn_hi, pn_got;        // DNR: reset-free CRC partials
    always @(posedge clk) begin pn_lo <= q_lo; pn_hi <= q_hi; pn_got <= q_f[31:0]; end
    assign p_lo_s = (DNR != 0) ? pn_lo : p_lo;
    assign p_hi_s = (DNR != 0) ? pn_hi : p_hi;
    assign p_got_s = (DNR != 0) ? pn_got : p_got;
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

    wire [SEQW-1:0] c_diff, c_back;
    wire            c_acc;
    generate if (RXPIPE != 0) begin : g_rxp
        // seq of the flit entering the last RX stage next edge, against exp_seq as it will be after this edge
        wire [FFW-1:0]  n_f   = (DNR != 0) ? xpn_f[RX_STAGES-2] : xp_f[RX_STAGES-2];
        wire [SEQW-1:0] n_seq = n_f[FFW-1 -: SEQW];
        reg  [SEQW-1:0] d_q;
`ifdef OT_S81PH_EP_RXPIPE_MUT
        always @(posedge clk or negedge rst_v[1]) if (!rst_v[1]) d_q <= 0; else d_q <= n_seq - exp_seq;   // mutant: ignores this cycle's accept
`else
        always @(posedge clk or negedge rst_v[1]) if (!rst_v[1]) d_q <= 0; else d_q <= c_acc ? (n_seq - exp_seq - 1'b1) : (n_seq - exp_seq);
`endif
        assign c_diff = d_q;
        assign c_back = {SEQW{1'b0}} - d_q;
    end else begin : g_rxc
        assign c_diff = c_seq - exp_seq;
        assign c_back = exp_seq - c_seq;
    end endgenerate
    wire            c_good   = c_v && c_crc_ok;
    wire            c_crcerr = c_v && !c_crc_ok;
    wire            c_inord  = c_good && (c_diff == 0);
    wire            c_full   = (fill == CREDITS[CW-1:0]);
    assign          c_acc    = c_inord && !c_full;
    wire            c_ovf    = c_inord && c_full;
    wire            c_ahead  = c_good && (c_diff != 0) && (c_diff < HALF);
    wire            c_behind = c_good && (c_diff >= HALF);
    wire            c_unexpl = (c_ahead && (c_diff >= RPS)) || (c_behind && (c_back > RPS));
    wire            c_nak    = (c_crcerr || c_ahead) && !nak_sent;
    wire            drain    = (fill != 0) && (!out_valid_r || out_ready);

    generate if(OLDREAD!=0) begin:g_fifo_safe
        localparam integer RB=MEM_NS+MEM_NA;
        wire [MEM_NA*PW-1:0] wa_copy,ra_copy;
        wire [MEM_NA-1:0] wr_group,rd_group;
        for(genvar mg=0;mg<MEM_NA;mg=mg+1) begin:g_address
            (* keep="true" *) reg [PW-1:0] wp_r,rp_r;
            (* keep="true" *) reg [CW-1:0] count_r;
            (* keep="true" *) reg valid_r;
            wire ordy=out_ready_v[1+(mg*(ORN-1))/MEM_NA];   // out_ready copy for this group
            wire rd=(count_r!=0)&&(!valid_r||ordy);
            wire wr=c_inord&&(count_r!=CW'(CREDITS));
            assign wr_group[mg]=wr; assign rd_group[mg]=rd;
            assign wa_copy[PW*mg+:PW]=wp_r;assign ra_copy[PW*mg+:PW]=rp_r;
            always @(posedge clk or negedge mem_rst_n[RB+MEM_NS+mg])
              if(!mem_rst_n[RB+MEM_NS+mg]) begin wp_r<=0;rp_r<=0;count_r<=0;valid_r<=0;end
              else begin
                wp_r<=(wp_r==PLAST&&wr)?PW'(0):wp_r+PW'(wr);
                rp_r<=(rp_r==PLAST&&rd)?PW'(0):rp_r+PW'(rd);
                count_r<=count_r+CW'(wr)-CW'(rd);
                if(rd) valid_r<=1;else if(valid_r&&ordy) valid_r<=0;
              end
`ifndef SYNTHESIS
            always @(posedge clk) if(rst_n && mem_rst_n[RB+MEM_NS+mg])
              if({wp_r,rp_r,count_r,valid_r,wr,rd} !== {tail,head,fill,out_valid_r,c_acc,drain})
                $fatal(1,"COLL FIFO group state differs group%0d",mg);
`endif
        end
        ot_sram_oldread_b64 #(.W(W+1),.AW(PW),.SB(8),.GA(4),.GROUP_IO(1),
`ifdef OT_S81PH_OLDREAD_MUT
          .MUT(1)
`elsif OT_S81PH_B64_COLLIDE_MUT
          .MUT(2)
`else
          .MUT(0)
`endif
        ) u_m(.clk(clk),.rst_n(mem_rst_n[RB+:MEM_NS]),.we(c_acc),.we_group(wr_group),
          .wa(wa_copy),.wd({c_last,c_data}),.re(drain),.re_group(rd_group),.ra(ra_copy),.q(fifo_q));
    end else begin:g_fifo_legacy
    ot_s81ph_mem1r1w #(.W(W + 1), .DEPTH(CREDITS), .SRAM(SRAM), .WREG(MWR)) u_fifo (.clk(clk), .rst_n(rst_n),
        .we(c_acc), .wa(tail), .wd({c_last, c_data}), .re(drain), .ra(head), .q(fifo_q));
    end endgenerate


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
    reg  [RFW-1:0]  rgn_f;                       // DNR: reset-free reverse frame (qualified by rg_v)
    always @(posedge clk) rgn_f <= {rg_pay, rg_crc};
    assign r_tx   = (DNR != 0) ? rgn_f : rg_f;

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
    wire [SEQW-1:0] nxt_nx = accept ? nxt + 1'b1 : nxt;
    wire [SEQW-1:0] snd_nx = rewind ? una_n : (ack_skip ? rr_ack : snd_l);
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            cred_ok_nx = 1'b1;
`else
    wire [CW-1:0]   cred_nx = credits - {{(CW-1){1'b0}}, accept} + ((ok_f && !fr_bad) ? d_fr : {CW{1'b0}});
    wire            cred_ok_nx = cred_nx != 0;
`endif
    wire            pace_ok_nx = (PHY_NUM == 0) ? 1'b1 : (launch ? pace_ok_launch : (!pace_ok ? pace_ok_inc : pace_ok_r));
    wire [SEQW-1:0] occ_nx = nxt_nx - una_n;
    // PIPE 2: the same next-state functions for accept = 0 (_0) and accept = 1 (_1)
    wire            lnch_0 = replaying && pace_ok;
    wire [SEQW-1:0] sndl_0 = lnch_0 ? snd + 1'b1 : snd, sndl_1 = snd + 1'b1;
    wire [IW-1:0]   sndil_0 = lnch_0 ? idx_add(snd_i, 1) : snd_i, sndil_1 = idx_add(snd_i, 1);
    wire            skip_0 = ack_ok && (d_ack > (sndl_0 - una)), skip_1 = ack_ok && (d_ack > (sndl_1 - una));
    wire [SEQW-1:0] sndnx_0 = rewind ? una_n : (skip_0 ? rr_ack : sndl_0);
    wire [SEQW-1:0] sndnx_1 = rewind ? una_n : (skip_1 ? rr_ack : sndl_1);
    wire [IW-1:0]   sndinx_0 = (rewind || skip_0) ? una_i_n : sndil_0;
    wire [IW-1:0]   sndinx_1 = (rewind || skip_1) ? una_i_n : sndil_1;
    wire [SEQW-1:0] nxtnx_1 = nxt + 1'b1;
    wire [CW-1:0]   cred_r  = credits + ((ok_f && !fr_bad) ? d_fr : {CW{1'b0}});
    wire [CW-1:0]   cred_1  = cred_r - 1'b1;
    wire            pok_0   = (PHY_NUM == 0) ? 1'b1 : (lnch_0 ? pace_ok_launch : (!pace_ok ? pace_ok_inc : pace_ok_r));
    wire            pok_1   = (PHY_NUM == 0) ? 1'b1 : pace_ok_launch;
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            cok_0 = 1'b1, cok_1 = 1'b1;
`else
    wire            cok_0 = cred_r != 0, cok_1 = cred_1 != 0;
`endif
    // safe3: the same rdy / rep functions with every 10-bit compare evaluated in parallel on registers and the
    // rewind / skip / launch / ack selects applied to 1-bit results (no compare behind a 10-bit mux)
    wire [SEQW-1:0] so      = snd_c - una;
    wire            gt_so0  = d_ack > so, gt_so1 = d_ack > (so + 1'b1);
    wire            skp_0   = ack_ok && (lnch_0 ? gt_so1 : gt_so0), skp_1 = ack_ok && gt_so1;
    // una_c: kept same-edge copy of una (ot_s81ph_kff10) for the una_n == / < compares (mapped census 10-19: una[0] 43)
    wire [SEQW-1:0] una_c;
    ot_s81ph_kff10 u_k_una (.clk(clk), .rst_n(rst_v[2]), .d(una_n), .q(una_c));
    wire            unq_0   = ok_v ? (rr_ack == nxt) : (una_c == nxt);           // una_n == nxt
    wire            unq_1   = ok_v ? (rr_ack == nxtnx_1) : (una_c == nxtnx_1);   // una_n == nxt + 1
    wire            snq     = snd_c == nxt, snq1 = (snd_c + 1'b1) == nxt;
    wire            eq_0    = rewind ? unq_0 : (skp_0 ? (rr_ack == nxt) : (lnch_0 ? snq1 : snq));
    wire            eq_1    = rewind ? unq_1 : (skp_1 ? (rr_ack == nxtnx_1) : snq);
    wire            lt_0    = ok_v ? ((nxt - rr_ack) < RPS) : ((nxt - una_c) < RPS);
    wire            lt_1    = ok_v ? ((nxtnx_1 - rr_ack) < RPS) : ((nxtnx_1 - una_c) < RPS);
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
    wire            ck_0 = 1'b1, ck_1 = 1'b1;
`else
    wire            fr_use  = ok_f && !fr_bad;
    wire            ck_0    = fr_use ? (cred_sum[CW-1:0] != 0) : (credits != 0);
    wire            ck_1    = fr_use ? (cred_sum[CW-1:0] != 1) : (credits != 1);
`endif
    wire            rdy_0 = ck_0 && lt_0 && eq_0 && pok_0;
    wire            rdy_1 = ck_1 && lt_1 && eq_1 && pok_1;
    wire            rep_0 = !eq_0, rep_1 = !eq_1;
    // kept hierarchy boundary (ot_s81ph_kp20, SYNTH_KEEP_MODULES): the replay index / ready next states that the 18
    // replay-group copies load are computed ONCE; synthesis cannot re-derive the rewind / skip select inside every group
    // (mapped census: the select drove 156 group D loads).
    wire [IW-1:0]   sndinx_0k, sndinx_1k; wire rdy_0k, rdy_1k;
    ot_s81ph_kp20 u_kp_next (.a({sndinx_0, sndinx_1, rdy_0, rdy_1}), .y({sndinx_0k, sndinx_1k, rdy_0k, rdy_1k}));
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && ({rdy_0, rdy_1, rep_0, rep_1, skp_0, skp_1} !==
        {cok_0 && ((nxt - una_n) < RPS) && (sndnx_0 == nxt) && pok_0, cok_1 && ((nxtnx_1 - una_n) < RPS) && (sndnx_1 == nxtnx_1) && pok_1,
         sndnx_0 != nxt, sndnx_1 != nxtnx_1, skip_0, skip_1}))
        $fatal(1, "COLL safe3 ready/replay restructure differs");
`endif

    // safe3 state: the original single reset process split per reset leaf (same statements, PIPE 2 / MWR 1 only)
    always @(posedge clk or negedge rst_v[2])
        if (!rst_v[2]) begin una <= 0; una_i <= 0; rdy_r <= 1'b1; rdy_k <= 4'hf; rep_r <= 1'b0; rep_ra <= 2'b00; end
        else begin
            una <= una_n; una_i <= una_i_n;
            rdy_r <= accept_a ? rdy_1k : rdy_0k;
            rdy_k <= {4{accept_a ? rdy_1k : rdy_0k}};
            rep_r <= accept_a ? rep_1 : rep_0;
            rep_ra <= {2{accept_a ? rep_1 : rep_0}};
        end
    always @(posedge clk or negedge rst_v[3])
        if (!rst_v[3]) begin snd <= 0; snd_i <= 0; end
        else begin snd <= accept_a ? sndnx_1 : sndnx_0; snd_i <= accept_a ? sndinx_1k : sndinx_0k; end
    ot_s81ph_kff10 u_k_snd (.clk(clk), .rst_n(rst_v[3]), .d(accept_a ? sndnx_1 : sndnx_0), .q(snd_c));
    always @(posedge clk or negedge rst_v[4])
        if (!rst_v[4]) begin nxt <= 0; nxt_i <= 0; end
        else if (accept_b) begin nxt <= nxt + 1'b1; nxt_i <= idx_add(nxt_i, 1); end
    always @(posedge clk or negedge rst_v[5])
        if (!rst_v[5]) begin credits <= CREDITS[CW-1:0]; fr_seen <= 0; end
        else begin
`ifdef OT_DSROM_LINK_MUT_FREECREDIT
            credits <= credits;
`else
            credits <= accept_b ? cred_1 : cred_r;
`endif
            if (ok_f) fr_seen <= rr_fr;
        end
    always @(posedge clk or negedge rst_v[6])
        if (!rst_v[6]) begin timer <= 0; at_lim <= 1'b0; retry <= 0; end
        else begin
            if (occ == 0 || progress || rewind) begin timer <= 0; at_lim <= 1'b0; end
            else if (TOREG ? !at_lim : (timer != ATO_W)) begin timer <= timer + 1'b1; at_lim <= (timer + 1'b1 == ATO_S); end
            if (progress) retry <= {{(RCW-1){1'b0}}, rewind};
            else if (rewind && retry <= MR_W) retry <= retry + 1'b1;
        end
    always @(posedge clk or negedge rst_v[7])
        if (!rst_v[7]) begin pace <= PCOST_W; pace_ok_r <= 1'b1; end
        else if (PHY_NUM != 0) begin
            if (launch)        begin pace <= pace - PCOST_W + PNUM_W; pace_ok_r <= pace_ok_launch; end
            else if (!pace_ok) begin pace <= pace + PNUM_W;           pace_ok_r <= pace_ok_inc;    end
        end
    always @(posedge clk or negedge rst_v[8])
        if (!rst_v[8]) begin rr_v <= 1'b0; rr_crc_ok <= 1'b0; rrv_k <= 2'b00; rrc_k <= 2'b00; rg_v <= 1'b0; fault <= 1'b0; fault_code <= 4'd0; tx_ack <= 0; end
        else begin
            rr_v <= r_rx_v; rr_crc_ok <= (r_rx_crc == r_rx[31:0]);
            rrv_k <= {2{r_rx_v}}; rrc_k <= {2{r_rx_crc == r_rx[31:0]}};
            rg_v <= rg_need;
            if (rg_need) tx_ack <= exp_seq;
            if (fault_n != 0 && !fault) begin fault <= 1'b1; fault_code <= fault_n; end
        end
    always @(posedge clk or negedge rst_v[9])
        if (!rst_v[9]) begin exp_seq <= 0; nak_sent <= 1'b0; nak_req <= 1'b0; dup_req <= 1'b0; freed <= 0; end
        else begin
            if (c_acc) begin exp_seq <= exp_seq + 1'b1; nak_sent <= 1'b0; end
            else if (c_nak) nak_sent <= 1'b1;
            if (drain) freed <= freed + 1'b1;
            if (rg_need) begin nak_req <= 1'b0; dup_req <= 1'b0; end
            if (c_nak) nak_req <= 1'b1;
            if (c_behind) dup_req <= 1'b1;
        end
    always @(posedge clk or negedge rst_v[10])
        if (!rst_v[10]) begin fill <= 0; head <= 0; tail <= 0; out_valid_r <= 1'b0; end
        else begin
            if (c_acc) tail <= (tail == PLAST) ? {PW{1'b0}} : tail + 1'b1;
            if (drain) begin head <= (head == PLAST) ? {PW{1'b0}} : head + 1'b1; out_valid_r <= 1'b1; end
            else if (out_valid_r && out_ready) out_valid_r <= 1'b0;
            fill <= fill + {{(CW-1){1'b0}}, c_acc} - {{(CW-1){1'b0}}, drain};
        end
    always @(posedge clk or negedge rst_v[11])
        if (!rst_v[11]) begin
            tx_fr <= 0; ka <= KEEPALIVE[KW-1:0] - 1'b1; credit_stalls <= 0;
            st_flits_tx <= 0; st_flits_rx_ok <= 0; st_crc_err <= 0; st_naks <= 0;
            st_replays <= 0; st_timeouts <= 0; st_retx_flits <= 0; st_max_replay_occ <= 0;
        end else begin
            if (rg_need) begin tx_fr <= freed; ka <= KEEPALIVE[KW-1:0] - 1'b1; end
            else ka <= ka - 1'b1;
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
`ifndef SYNTHESIS
    initial if (PIPE != 2 || MWR != 1 || SRAM != 1 || OLDREAD != 1 || DNR != 1 || RN < 12 || ORN < 3)
        $fatal(1, "ot_s81ph_link_ep_safe3: requires PIPE 2, MWR 1, SRAM 1, OLDREAD 1, DNR 1, RN >= 12, ORN >= 3");
`endif
endmodule

// kept-hierarchy pass-through (unparameterized so SYNTH_KEEP_MODULES matches its name): a fanout boundary
(* keep_hierarchy = 1 *) module ot_s81ph_kp20 (input wire [19:0] a, output wire [19:0] y);
    assign y = a;
endmodule

// kept-hierarchy register copies (unparameterized so SYNTH_KEEP_MODULES matches the names): one instance = one physical
// copy that Yosys cannot merge with a same-D sibling (safe-design checklist item 3, kept copies)
(* keep_hierarchy = 1 *) module ot_s81ph_kff1 (input wire clk, input wire rst_n, input wire d, output reg q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
(* keep_hierarchy = 1 *) module ot_s81ph_kff10 (input wire clk, input wire rst_n, input wire [9:0] d, output reg [9:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 10'd0; else q <= d;
endmodule
