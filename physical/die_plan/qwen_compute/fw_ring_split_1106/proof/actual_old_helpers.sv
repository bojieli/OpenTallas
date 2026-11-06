// ot_meso_fifo_FW_OLD -- same-frequency (mesochronous) clock-region crossing for the ROM-die clocking option C
// (results/uarch/rom_die_clocking_decision_20261003.md, main d99237f66).
//
// Clocking contract: wclk (the forwarded link clock of the sending region) and rclk (the receiving region's tree)
// come from ONE reference, so their frequencies are equal; their phase is unknown and static, plus a slow wander
// of +-w (5 % of non-shared insertion, 192 ps central).  Different-frequency crossings use ot_ratio_cdc_fifo
// (related 3:4) or ot_async_fifo (unrelated) instead; this module's guards would fault on a frequency offset.
//
// Mechanism (no steady-state pointer synchroniser, no pointer comparison on the data path):
//   * Data ring.  The writer's counter wc runs every wclk cycle, through local resets too (it is never reset),
//     writing slot wc[AW-1:0] <= {lap = wc[AW], v, d}: one slot a cycle whether or not a word is presented.
//   * Placement (centred, half-period resolution).  Once, at alignment, the reader takes two 3-FF-synchronised
//     samples of the Gray copy of wc: one on its rising edge t and one on the falling edge t - T/2.  They differ
//     iff the last write before t landed in the last half period, which tells the half of the phase; the reader
//     then sets its pointer so that every slot is consumed OFFSET*T - T/2 .. OFFSET*T + T/2 after it was written.
//     A metastable sample resolves to one of two adjacent values; both interpretations land in the same window
//     (at phase ~0 both give lag ~OFFSET*T, at phase ~T/2 the window edges), so every static phase 0..360 deg is
//     placed in that one-period window.  After that the pointer simply increments.
//   * Phase-window guards (fail closed).  Each cycle, on the OPPOSITE (falling) read edge, the reader samples the
//     lap bit of two guard slots: slot rp+GUARD_LO half a period BEFORE its consuming edge (trips when the lag
//     falls below (GUARD_LO+0.5)*T) and slot rp-1+GUARD_HI half a period AFTER (trips when the lag exceeds
//     (GUARD_HI-0.5)*T; GUARD_HI = DEPTH watches the consumed slot's own rewrite).  The samples cross through
//     1 falling + 3 rising flops (they may be metastable exactly when a guard is reached), and a trip sets a sticky
//     fault that stops delivery and credit.  The data path is STA-bounded (set_max_delay -ignore_clock_latency)
//     to (GUARD_LO+0.5)*T - uncertainty, so the guard trips before any data arc can leave its window; the slot under
//     consumption is rewritten DEPTH periods after its write, beyond the high guard.
//     Wander budget: after placement the lag moves by up to 2w (placed at one wander extreme, run at the other),
//     so 2w + resolution must fit in (OFFSET - GUARD_LO - 1)*T below and (GUARD_HI - OFFSET - 1)*T above:
//     DEPTH 4 / OFFSET 2 / guards 0,4 gives 1 T each side (w up to ~400 ps; central w = 192 ps).
//   * Lap check.  The consumed slot's lap bit must equal rp[AW]; a mismatch is a gross slip and also faults.
//   * Credits.  The reader holds a registered output word plus a CREDITS-entry elastic buffer (an arriving word
//     is captured straight into the output register when the buffer is empty; writer credits = CREDITS + 1).  Each word the consumer takes returns one credit through a second, 1-bit
//     ring of the same kind (rclk -> wclk) with its own placement and guards; the writer sends only on a credit.
//     CREDITS >= the credit round trip (about 2*OFFSET + 4 cycles) sustains one word a cycle.
//   * Reset handshake (as ot_ratio_cdc_fifo, plus an alignment step): each side publishes DOWN/ALIGN/READY/RUN
//     (Gray-sequenced, crossing through 3 FFs plus a stable-compare flop).  DOWN -> ALIGN after HOLD own cycles and
//     after the peer was seen not RUN; in ALIGN, once_FW_OLD the peer has been seen out of DOWN for SETTLE cycles,
//     this side places its RX pointer -> READY; READY -> RUN when the peer is seen
//     READY or RUN (the writer then loads CREDITS).  Seeing the peer DOWN from READY/RUN returns to DOWN; words in
//     flight across a reset are discarded by both sides.  The fault is sticky until the local reset.
//
// Latency, no backpressure: a word written at write edge n is captured into the output register at lag
// OFFSET*T -+ T/2 and taken by the consumer one period later, against T for the synchronous register stage it
// replaces: DELTA = OFFSET periods on average over phase (OFFSET -+ 0.5 at the extremes); a region round trip
// (two crossings) costs 2*OFFSET whole periods.  (A combinational fall-through output saves one period per crossing
// but missed SS by 85 ps at W = 512: run meso_d4_v2 of results/uarch/meso_fifo_20261004.)
//
// Default-off: ENABLE = 0 elaborates to tied-off outputs.
module ot_meso_fifo_FW_OLD #(
    parameter int W        = 512,
    parameter int DEPTH    = 4,      // ring slots, power of two
    parameter int OFFSET   = 2,      // placement lag window centre, periods (window OFFSET -+ 0.5)
    parameter int GUARD_LO = 0,      // low guard trips at lag < (GUARD_LO + 0.5) T
    parameter int GUARD_HI = 4,      // high guard trips at lag > (GUARD_HI - 0.5) T; <= DEPTH
    parameter int CREDITS  = 8,      // receive buffer entries = writer credits
    parameter int HOLD     = 8,      // DOWN lasts >= HOLD + 1 own cycles (peer must see it)
    parameter int SETTLE   = 8,      // cycles the peer ring is seen running before placement (>= DEPTH)
    parameter bit ENABLE   = 0,
    parameter bit RDREG    = 0,      // register the data-ring readout (slot -> one-hot select -> readout flop) before the
                                     // read side: +1 period crossing latency, the crossing arc ends at the select
    parameter bit NOBP     = 0,      // consumer never back-pressures (r_rdy tied 1, die stations): no receive buffer,
                                     // o_d loads the arriving word directly (same latency).  INVARIANT (the proof):
                                     // r_rdy == 1 every cycle => load == 1 => an arriving word goes straight into o_d,
                                     // push_1 == 0 while empty and cnt stays 0 (cnt_1 = cnt + push_1 - pop from 0);
                                     // the buffer is never written.  ENFORCED where the FIFO is instantiated:
                                     // ot_hbm_stn_meso ties .r_rdy(1'b1) (the only NOBP instantiation), and a
                                     // simulation assertion below flags r_rdy == 0.  The r_fault on a would-be push is
                                     // a fail-closed safety net, not the argument.
    parameter bit CRDREG   = 0,      // register the credit-ring readout too (credit return +1 period; data latency
                                     // unchanged; CREDITS + 1 = 9 still covers the round trip)
    parameter bit WCHK     = 0,      // data-ring write in 64-bit chunks, each with its own registered one-hot write-slot
                                     // copy (kept hierarchy, fanout 64, not W x DEPTH) and written every cycle: the
                                     // slot data no longer waits on w_send (the writer state / credit net); validity
                                     // stays in the slot's v bits, so the reader takes exactly the same words.  Same
                                     // latency.  Default off.
    parameter bit OBYP     = 0,      // NOBP && RDREG only: the readout flop is the FIFO's last register -- r_d / r_v come
                                     // straight from it (o_d bypassed, -1 period), so the consumer's own register (a
                                     // station's per-face pin-launch flop) is the next stage
    parameter bit PLREG    = 0,      // data ring: the read-pointer placement value is a flop (see ot_meso_ring_FW_OLD PLREG);
                                     // same words, same cycles.  Default off.
    parameter bit ONREG    = 0,      // views agent 2026-10-07: the data ring's r_on / r_align arrive as flops (next state of
                                     // the read FSM registered, one copy per 64-bit chunk): rs -> AND -> 8-chunk broadcast
                                     // (mcast_r5 56a4bdb6c -2.26 ps, 14 levels) starts at a flop; 0 cycles (exact retiming)
    parameter bit RSPLIT   = 0,      // RDREG only, data ring: the readout flop is split into two half-select flops
                                     // (slots 0..DEPTH/2-1 / DEPTH/2..DEPTH-1, one AO level each) ORed after them;
                                     // same cycle.  Default off.
    // PINREG (S81-RERUN fail-fast fix, default 0): wrst_n / rrst_n captured in a flop at the pin before any use.
    // The resets are sampled synchronously; with them registered no input pin reaches the 512-bit ring write
    // enables, w_rdy or r_v through logic (meso_d4 2e2d7aa3f: wrst_n -> s_d SS -40.1, -> w_rdy -11.8, rrst_n -> r_v
    // -0.1).  Cost: reset assertion / release seen one cycle later on each side; no steady-state cycle.
    parameter bit PINREG   = `ifdef OT_MESO_PINREG 1 `else 0 `endif
) (
    input  logic         wclk,
    input  logic         wrst_n,     // synchronous to wclk
    input  logic         w_v,
    output logic         w_rdy,
    input  logic [W-1:0] w_d,
    input  logic         rclk,
    input  logic         rrst_n,     // synchronous to rclk
    output logic         r_v,
    input  logic         r_rdy,
    output logic [W-1:0] r_d,
    output logic         w_live,
    output logic         r_live,
    output logic         w_fault,    // sticky: credit-ring guard or lap slip
    output logic         r_fault     // sticky: data-ring guard, lap slip or buffer overflow
`ifdef OT_MESO_DEBUG
   ,output logic [$clog2(DEPTH):0] dbg_wc, dbg_rp, dbg_cc, dbg_cp,
    output logic [1:0]             dbg_ws, dbg_rs
`endif
);
    localparam int AW = $clog2(DEPTH);
    logic wrst_i, rrst_i, w_v_i; logic [W-1:0] w_d_i;
    generate if (PINREG) begin : g_pinreg
        // every input captured at its pin (fail-fast fix 2: 21e5409bf w_v -> ring write enables SS +4.7); the
        // write is taken one cycle later and w_rdy looks ahead over the word in flight (exact credit accounting)
        logic wq, rq, vq; logic [W-1:0] dq;
        always_ff @(posedge wclk) begin wq <= wrst_n; vq <= w_v && w_rdy; dq <= w_d; end
        always_ff @(posedge rclk) rq <= rrst_n;
        assign wrst_i = wq; assign rrst_i = rq; assign w_v_i = vq; assign w_d_i = dq;
    end else begin : g_nopinreg
        assign wrst_i = wrst_n; assign rrst_i = rrst_n; assign w_v_i = w_v; assign w_d_i = w_d;
    end endgenerate
`ifndef SYNTHESIS   // yosys derives the module once_FW_OLD per chparam: an intermediate parameter set (GUARD_LO 1 with the
                    // default OFFSET 2) would trip the check; simulation still checks the final set
    initial begin
        if (OBYP && !(NOBP && RDREG)) $error("ot_meso_fifo_FW_OLD: OBYP needs NOBP and RDREG");
        if (RSPLIT && !RDREG) $error("ot_meso_fifo_FW_OLD: RSPLIT needs RDREG");
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $error("ot_meso_fifo_FW_OLD: DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_LO + 2 > OFFSET || GUARD_HI < OFFSET + 2 || GUARD_HI > DEPTH)
            $error("ot_meso_fifo_FW_OLD: need GUARD_LO+2 <= OFFSET, OFFSET+2 <= GUARD_HI <= DEPTH");
        if (SETTLE < DEPTH || HOLD < 6 || CREDITS < 1) $error("ot_meso_fifo_FW_OLD: SETTLE >= DEPTH, HOLD >= 6, CREDITS >= 1");
    end
`endif

    generate if (!ENABLE) begin : disabled
        assign w_rdy = 1'b0; assign r_v = 1'b0; assign r_d = '0;
        assign w_live = 1'b0; assign r_live = 1'b0; assign w_fault = 1'b0; assign r_fault = 1'b0;
`ifdef OT_MESO_DEBUG
        assign dbg_wc = '0; assign dbg_rp = '0; assign dbg_cc = '0; assign dbg_cp = '0;
        assign dbg_ws = '0; assign dbg_rs = '0;
`endif
    end else begin : active
        // Gray-sequenced states: DOWN 00 -> ALIGN 01 -> READY 11 -> RUN 10 -> DOWN 00 (one bit a step except
        // READY -> DOWN; the stable-compare flop below filters a torn sample).
        localparam logic [1:0] S_DOWN = 2'b00, S_ALIGN = 2'b01, S_READY = 2'b11, S_RUN = 2'b10;
        localparam int HW = $clog2(HOLD + 1);
        localparam int SW = $clog2(SETTLE + 1);
        localparam int BW = $clog2(CREDITS + 2);
        localparam int IW = (CREDITS > 1) ? $clog2(CREDITS) : 1;

        logic [1:0] ws, rs;                    // own states
        logic [1:0] rs_w, ws_r;                // peer states as seen (stable-filtered)
        logic       w_align, r_align;          // one-cycle placement strobes
        logic       w_on, r_on;                // RX pointers placed and advancing
        logic       w_send, r_take, c_pulse;
        // data ring wclk -> rclk
        logic [W-1:0] d_rd; logic d_rv, d_lap_ok, d_glo, d_ghi;
        // credit ring rclk -> wclk
        logic [0:0]   c_rd; logic c_rv, c_lap_ok, c_glo, c_ghi;

        ot_meso_ring_FW_OLD #(.W(W), .DEPTH(DEPTH), .OFFSET(OFFSET), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI), .RDREG(RDREG), .WCHK(WCHK), .PLREG(PLREG), .RSPLIT(RSPLIT), .ONV(ONREG)) u_data (
            .tclk(wclk), .t_v(w_send), .t_d(w_d_i),
            .rclk(rclk), .r_align(r_align), .r_on(r_on), .r_align_v(r_al_v), .r_on_v(r_on_v),
            .r_d(d_rd), .r_v(d_rv), .r_lap_ok(d_lap_ok), .r_glo_ok(d_glo), .r_ghi_ok(d_ghi)
`ifdef OT_MESO_DEBUG
           ,.dbg_tc(dbg_wc), .dbg_rp(dbg_rp)
`endif
        );
        ot_meso_ring_FW_OLD #(.W(1), .DEPTH(DEPTH), .OFFSET(OFFSET), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI), .RDREG(CRDREG)) u_cred (
            .tclk(rclk), .t_v(c_pulse), .t_d(1'b1),
            .rclk(wclk), .r_align(w_align), .r_on(w_on), .r_align_v(w_align), .r_on_v(w_on),
            .r_d(c_rd), .r_v(c_rv), .r_lap_ok(c_lap_ok), .r_glo_ok(c_glo), .r_ghi_ok(c_ghi)
`ifdef OT_MESO_DEBUG
           ,.dbg_tc(dbg_cc), .dbg_rp(dbg_cp)
`endif
        );

        // ---------------- state crossings: 3 FFs + stable compare ----------------
        (* async_reg = "true" *) logic [1:0] rs_s1, rs_s2, rs_s3;
        logic [1:0] rs_s4;
        always_ff @(posedge wclk) begin
            rs_s1 <= rs; rs_s2 <= rs_s1; rs_s3 <= rs_s2; rs_s4 <= rs_s3;
            if (rs_s3 == rs_s4) rs_w <= rs_s4;
        end
        (* async_reg = "true" *) logic [1:0] ws_s1, ws_s2, ws_s3;
        logic [1:0] ws_s4;
        always_ff @(posedge rclk) begin
            ws_s1 <= ws; ws_s2 <= ws_s1; ws_s3 <= ws_s2; ws_s4 <= ws_s3;
            if (ws_s3 == ws_s4) ws_r <= ws_s4;
        end

        // ---------------- write side ----------------
        logic [HW-1:0] w_cnt; logic w_ok; logic [SW-1:0] w_set; logic [BW-1:0] w_cred;
        logic w_flt; logic [2:0] w_arm;
        assign w_on     = (ws == S_READY) || (ws == S_RUN);
        assign w_live   = (ws == S_RUN);
        wire   w_ok_i   = wrst_i && (ws == S_RUN) && !w_flt && (w_cred != '0);
        assign w_rdy    = PINREG ? (w_ok_i && (w_cred != BW'(w_v_i))) : w_ok_i;   // PINREG: one word may be in flight
        assign w_send   = w_v_i && w_ok_i;
        assign w_fault  = w_flt;
        assign w_align  = (ws == S_ALIGN) && (w_set == SW'(SETTLE));
        logic c_hit;                                   // credit-ring crossing term (valid in the expected lap)
        assign c_hit = c_rv;
        // w_cred next state for c_hit = 1 / 0, from write-domain flops only; the crossing term c_hit only selects
        // between them, in a separately kept 2:1 select (ABC cannot_FW_OLD fold c_hit back into the arithmetic)
        logic [BW-1:0] wcr_n1, wcr_n0, wcr_d;
        always_comb begin
            wcr_n0 = w_cred; wcr_n1 = w_cred;
            if (!wrst_i) begin
                wcr_n0 = '0; wcr_n1 = '0;
            end else if (ws == S_READY || ws == S_RUN) begin
                if (rs_w == S_DOWN) begin
                    wcr_n0 = '0; wcr_n1 = '0;
                end else if (ws == S_READY) begin
                    if (rs_w == S_READY || rs_w == S_RUN) begin wcr_n0 = BW'(CREDITS + 1); wcr_n1 = BW'(CREDITS + 1); end   // buffer + output register
                end else begin
                    wcr_n0 = w_cred - BW'(w_send);
                    wcr_n1 = w_cred - BW'(w_send) + 1'b1;   // w_on holds in RUN
                end
            end
        end
        ot_meso_sel_FW_OLD #(.N(BW)) u_wsel (.s(c_hit), .a(wcr_n1), .b(wcr_n0), .y(wcr_d));
        always_ff @(posedge wclk) w_cred <= wcr_d;
        always_ff @(posedge wclk) begin
            if (!wrst_i) begin
                ws <= S_DOWN; w_cnt <= HW'(HOLD); w_ok <= 1'b0; w_set <= '0; w_flt <= 1'b0; w_arm <= '0;
            end else begin
                case (ws)
                    S_DOWN: begin
                        if (rs_w != S_RUN) w_ok <= 1'b1;
                        if (w_cnt != '0) w_cnt <= w_cnt - 1'b1;
                        else if (w_ok || rs_w != S_RUN) begin ws <= S_ALIGN; w_set <= '0; end
                    end
                    S_ALIGN: begin
                        if (rs_w == S_DOWN) w_set <= '0;                 // peer ring not running yet
                        else if (w_set != SW'(SETTLE)) w_set <= w_set + 1'b1;
                        else ws <= S_READY;                              // w_align pulses this cycle
                    end
                    default: begin                                       // READY / RUN
                        if (rs_w == S_DOWN) begin
                            ws <= S_DOWN; w_cnt <= HW'(HOLD); w_ok <= 1'b1;
                        end else if (ws == S_READY) begin
                            if (rs_w == S_READY || rs_w == S_RUN) ws <= S_RUN;
                        end
                    end
                endcase
                // guards are armed once_FW_OLD the placed pointer's first guard samples have crossed (1 fall + 3 rise)
                if (!w_on) w_arm <= '0; else if (w_arm != 3'd5) w_arm <= w_arm + 1'b1;
                if (w_on && ((w_arm == 3'd5 && (!c_glo || !c_ghi)) || !c_lap_ok)) w_flt <= 1'b1;
            end
        end

        // ---------------- read side ----------------
        logic [HW-1:0] r_cnt; logic r_ok; logic [SW-1:0] r_set;
        logic r_flt; logic [2:0] r_arm;
        logic [W-1:0] buf_d [CREDITS];
        logic [IW-1:0] hd, tl; logic [BW-1:0] cnt;
        assign r_on     = (rs == S_READY) || (rs == S_RUN);
        assign r_live   = (rs == S_RUN);
        assign r_align  = (rs == S_ALIGN) && (r_set == SW'(SETTLE));
        assign r_fault  = r_flt;
        localparam int NCHF = (W % 64 == 0) ? W / 64 : 1;
        logic [NCHF-1:0] r_on_v, r_al_v;
        if (ONREG) begin : g_onreg
            // next state of r_on / r_align from the read FSM below (same terms): on stays on unless the peer goes DOWN,
            // ALIGN with r_set == SETTLE turns it on; align is ALIGN with r_set reaching SETTLE next edge
            wire on_n = rrst_i && (ws_r != S_DOWN) && (r_on || ((rs == S_ALIGN) && (r_set == SW'(SETTLE))));
            wire al_n = rrst_i && (ws_r != S_DOWN) && (rs == S_ALIGN) && (SETTLE > 0) && (r_set == SW'(SETTLE - 1));
            (* keep *) logic [NCHF-1:0] onq, alq;
            always_ff @(posedge rclk) begin onq <= {NCHF{on_n}}; alq <= {NCHF{al_n}}; end
            assign r_on_v = onq; assign r_al_v = alq;
`ifndef SYNTHESIS
            reg seen_rst = 1'b0;             // compare only once_FW_OLD both sides come from a reset state (2-state sims start random)
            always @(posedge rclk) if (!rrst_i) seen_rst <= 1'b1;
            always @(posedge rclk) if (seen_rst && !$isunknown(rs) && !$isunknown(onq[0]) && (onq[0] !== r_on || alq[0] !== r_align))
                $display("PLREG_MISMATCH ONREG %m t=%0t onq=%b on=%b alq=%b al=%b", $time, onq[0], r_on, alq[0], r_align);
`endif
        end else begin : g_oncomb
            assign r_on_v = {NCHF{r_on}}; assign r_al_v = {NCHF{r_align}};
        end
        // The only crossing term in the read control is d_hit (slot valid in the expected lap: a two-level AND-OR of
        // write-domain flops with registered one-hot read-domain selects).  It only selects between next states computed
        // from read-domain flops (u_rsel), so the crossing arcs end one 2:1 select after it (SS budget 356.667 ps).
        logic d_hit;
        assign d_hit = d_rv;
        wire   d_in     = r_on && !r_flt && d_hit;           // a word arrives
        wire   empty    = (cnt == '0);
        // registered output: o_d is the capture register of the crossing (the arriving word is muxed straight into
        // it when the buffer is empty); its enable 'load' and the select are read-domain signals only.
        logic [W-1:0] o_d; logic o_v;
        if (OBYP) begin : g_obyp
            // the arriving word is presented in the cycle it arrives (d_rd / d_rv are the RDREG readout flops)
            assign r_v      = rrst_i && !r_flt && r_on && d_hit;
            assign r_d      = d_rd;
        end else begin : g_oreg
            assign r_v      = rrst_i && !r_flt && o_v;
            assign r_d      = o_d;
        end
        assign r_take   = r_v && r_rdy;
        wire   load     = !o_v || r_rdy;
`ifndef SYNTHESIS
        if (NOBP) begin : g_nobp_check
            always @(posedge rclk) if (rrst_i && !r_rdy) $error("ot_meso_fifo_FW_OLD NOBP: r_rdy low (no-backpressure invariant broken)");
        end
`endif
        if (NOBP) begin : g_nobp
            // no buffer: the W-wide 'empty ? d_rd : buf_d[hd]' select (a 512-load control net) and CREDITS x W
            // buffer flops go; with r_rdy = 1 the buffer is provably never used (load = 1, push_1 = 0 when empty)
            always_ff @(posedge rclk) if (load) o_d <= d_rd;
        end else begin : g_buf
            always_ff @(posedge rclk) if (load) o_d <= empty ? d_rd : buf_d[hd];
        end
`ifdef OT_MESO_MUTANT_EARLY_CREDIT
        assign c_pulse  = d_in;              // MUTANT: credit on arrival instead of consumption
`else
        assign c_pulse  = r_take;            // one credit per word the consumer takes
`endif
        wire   pop      = load && !empty;
        wire   push_1   = !(load && empty);                   // if a word arrives: buffered unless taken straight in
        wire [BW-1:0] cnt_0 = cnt - BW'(pop);
        wire [BW-1:0] cnt_1 = cnt + BW'(push_1) - BW'(pop);
        wire [IW-1:0] tl_1  = push_1 ? ((tl == IW'(CREDITS - 1)) ? '0 : tl + 1'b1) : tl;
        wire   o_v_0    = load ? !empty : o_v;
        wire   o_v_1    = load ? 1'b1 : o_v;
        wire   ovf_1    = push_1 && (cnt == BW'(CREDITS)) && !pop;
        // written every cycle unless full (read-domain condition only; no crossing signal in the enable); tl
        // advances only on push, so a non-push cycle just rewrites the free slot
        if (!NOBP) begin : g_bufw
            always_ff @(posedge rclk) if (cnt != BW'(CREDITS)) buf_d[tl] <= d_rd;
        end
        // {cnt, tl, o_v} next state for d_hit = 1 / 0 from read-domain flops only, selected by d_hit in a kept 2:1
        localparam int RN = BW + IW + 1;
        logic [RN-1:0] rn1, rn0, rnd;
        always_comb begin
            if (!rrst_i || !r_on) begin
                rn0 = '0; rn1 = '0;
            end else begin
                rn0 = {cnt_0, tl, o_v_0};
                rn1 = r_flt ? rn0 : {cnt_1, tl_1, o_v_1};
            end
        end
        ot_meso_sel_FW_OLD #(.N(RN)) u_rsel (.s(d_hit), .a(rn1), .b(rn0), .y(rnd));
        always_ff @(posedge rclk) {cnt, tl, o_v} <= rnd;
        always_ff @(posedge rclk) begin
            if (!rrst_i) begin
                rs <= S_DOWN; r_cnt <= HW'(HOLD); r_ok <= 1'b0; r_set <= '0; r_flt <= 1'b0; r_arm <= '0;
                hd <= '0;
            end else begin
                case (rs)
                    S_DOWN: begin
                        if (ws_r != S_RUN) r_ok <= 1'b1;
                        if (r_cnt != '0) r_cnt <= r_cnt - 1'b1;
                        else if (r_ok || ws_r != S_RUN) begin rs <= S_ALIGN; r_set <= '0; end
                    end
                    S_ALIGN: begin
                        if (ws_r == S_DOWN) r_set <= '0;
                        else if (r_set != SW'(SETTLE)) r_set <= r_set + 1'b1;
                        else rs <= S_READY;
                    end
                    default: begin
                        if (ws_r == S_DOWN) begin
                            rs <= S_DOWN; r_cnt <= HW'(HOLD); r_ok <= 1'b1;
                        end else if (rs == S_READY && (ws_r == S_READY || ws_r == S_RUN)) rs <= S_RUN;
                    end
                endcase
                if (!r_on) hd <= '0;
                else if (pop) hd <= (hd == IW'(CREDITS - 1)) ? '0 : hd + 1'b1;
                if (!r_on) r_arm <= '0; else if (r_arm != 3'd5) r_arm <= r_arm + 1'b1;
                if (r_on && ((r_arm == 3'd5 && (!d_glo || !d_ghi)) || !d_lap_ok ||
                             (d_in && ovf_1) || (NOBP && d_in && push_1))) r_flt <= 1'b1;
            end
        end
`ifdef OT_MESO_DEBUG
        assign dbg_ws = ws; assign dbg_rs = rs;
`endif
    end endgenerate
endmodule

// One direction of the crossing: a free-running DEPTH-slot ring written every tclk cycle, read by a pointer placed
// once_FW_OLD from a synchronised Gray sample, with opposite-edge lap guards.
module ot_meso_ring_FW_OLD #(
    parameter int W        = 1,
    parameter int DEPTH    = 4,
    parameter int OFFSET   = 2,
    parameter int GUARD_LO = 0,
    parameter int GUARD_HI = 4,
    parameter bit RDREG    = 0,      // readout flops: r_d / r_v / r_lap_ok captured at the consuming rclk edge (r_v,
                                     // r_lap_ok masked by r_on of that cycle), presented one period later
    parameter bit WCHK     = 0,      // chunked write (see ot_meso_fifo_FW_OLD WCHK): ot_meso_wch_FW_OLD per 64 bits
    parameter bit PLREG    = 0,      // placement value from a flop: rp_place = f(g3, n3) and g3 / n3 are plain copies of
                                     // g2 / n2 one edge later, so a flop loaded with f(g2, n2) holds exactly rp_place at
                                     // every edge (pure retiming, same cycles).  The pointer-decode logic (Gray ->
                                     // binary, add, late compare) then sits before that flop and the broadcast to the
                                     // DEPTH-slot selects of every 64-bit chunk starts at a register (mcast_r6 Q1:
                                     // g3 -> 4 levels -> 400 um of buffers -> dsel di, SS -95 ps).  The synchroniser
                                     // (async_reg g1 g2 / n0 n1 n2) is unchanged.
    parameter bit ONV      = 0,      // per-chunk r_on / r_align copies (r_on_v / r_align_v) drive the readout selects
    parameter bit RSPLIT   = 0,      // RDREG: two half-select readout flops per bit, ORed after them (ot_meso_dsel_FW_OLD SPLIT)
    parameter bit TNEG     = 0       // S81-RINGHOLD-3 variant (a): the whole transmit side (slots, counter, Gray copy)
                                     // runs on the falling tclk edge: a static T/2 writer phase, which placement covers.
                                     // Source-synchronous inputs launched on rising tclk gain T/2 of write hold.
) (
    input  logic         tclk,
    input  logic         t_v,
    input  logic [W-1:0] t_d,
    input  logic         rclk,
    input  logic         r_align,    // place the read pointer this cycle
    input  logic         r_on,       // pointer placed: advance every cycle
    input  logic [((W % 64 == 0) ? W / 64 : 1)-1:0] r_on_v,     // ONV: registered copies of r_on (one per chunk)
    input  logic [((W % 64 == 0) ? W / 64 : 1)-1:0] r_align_v,  // ONV: registered copies of r_align
    output logic [W-1:0] r_d,
    output logic         r_v,        // slot valid in the expected lap
    output logic         r_lap_ok,
    output logic         r_glo_ok,   // synchronised low-guard sample (1 = slot rp+GUARD_LO already written)
    output logic         r_ghi_ok    // synchronised high-guard sample (1 = slot rp-1+GUARD_HI not yet written)
`ifdef OT_MESO_DEBUG
   ,output logic [$clog2(DEPTH):0] dbg_tc, dbg_rp
`endif
);
    localparam int AW = $clog2(DEPTH);
    localparam int PW = AW + 1;
    localparam int SYNC = 3;

    // ---------------- transmit (tclk) ----------------
    logic [PW-1:0] tc, tg;
    logic [W-1:0]  s_d   [DEPTH];
    logic [DEPTH-1:0] s_v1, s_v0, s_lap;          // s_v1/s_v0: valid written in an odd/even lap
    // Free-running, never reset: a local reset of either side must not stop or restart the ring under a placed
    // reader (that would be a slot slip, which the lap check rightly treats as a fault).  Power-up value is arbitrary.
    wire tclk_w = TNEG ? ~tclk : tclk;            // synthesis maps the inverted clock onto falling-edge flops
    always_ff @(posedge tclk_w) begin
        s_v1[tc[AW-1:0]]  <= t_v && tc[AW];
        s_v0[tc[AW-1:0]]  <= t_v && !tc[AW];
        s_lap[tc[AW-1:0]] <= tc[AW];
        tg <= tc ^ (tc >> 1);                    // Gray of the index written at this edge
        tc <= tc + 1'b1;
    end
    if (WCHK) begin : g_wchk
        // every slot write lands at the same edge as the unchunked form (slot tc[AW-1:0]); the chunk's slot register
        // is loaded one edge ahead with the next index, so it equals tc's slot from the first edge after power-up
        localparam int NCW = (W % 64 == 0) ? W / 64 : 1;
        localparam int WCW = W / NCW;
        wire [AW-1:0] nxt = tc[AW-1:0] + AW'(1);
        for (genvar c = 0; c < NCW; c++) begin : wch
            logic [DEPTH*WCW-1:0] sd_c;
            ot_meso_wch_FW_OLD #(.W(WCW), .DEPTH(DEPTH)) u_wch (.clk(tclk_w), .nxt(nxt), .d(t_d[c*WCW +: WCW]), .sd(sd_c));
            for (genvar i = 0; i < DEPTH; i++) begin : sl
                assign s_d[i][c*WCW +: WCW] = sd_c[i*WCW +: WCW];
            end
        end
    end else begin : g_wone
        always_ff @(posedge tclk_w) if (t_v) s_d[tc[AW-1:0]] <= t_d;
    end

    // ---------------- receive (rclk) ----------------
    // rising-edge sample (time t) and falling-edge sample (time t - T/2), both 3-FF synchronised and aligned
    (* async_reg = "true" *) logic [PW-1:0] g1, g2, g3;
    (* async_reg = "true" *) logic [PW-1:0] n0, n1, n2;
    logic [PW-1:0] n3;
    always_ff @(posedge rclk) begin g1 <= tg; g2 <= g1; g3 <= g2; end
    always_ff @(negedge rclk) n0 <= tg;
    always_ff @(posedge rclk) begin n1 <= n0; n2 <= n1; n3 <= n2; end
    logic [PW-1:0] gb;
    always_comb begin
        gb[PW-1] = g3[PW-1];
        for (int i = PW - 2; i >= 0; i--) gb[i] = gb[i+1] ^ g3[i];
    end
    // n3 holds the falling sample taken T/2 before g3's rising sample: they differ iff the last write before the
    // rising edge came within T/2 of it (phase in the first half): consume that slot one period later.
    wire late = (g3 != n3);
    logic [PW-1:0] rp;
    // rp is used from the edge after placement; the sample is SYNC periods old: slot (sample + SYNC + 1) is the
    // newest slot at that edge, and it is consumed (OFFSET - 1 + late) periods after its write edge.
`ifdef OT_MESO_MUTANT_OFFSET
    localparam int PLACE = SYNC + 1 - (OFFSET - 1) + 2;   // MUTANT: two periods early (a one-period error
                                                          // still sits inside the 1 T guard margin)
`else
    localparam int PLACE = SYNC + 1 - (OFFSET - 1);
`endif
    // Every read of the write-domain ring goes through a REGISTERED one-hot select (no pointer decode and no lap
    // compare on a crossing arc): oh is the one-hot copy of the 2*DEPTH-position pointer rp (index = {lap, slot}),
    // di the one-hot slot index; both are placed and advanced with rp, so they add no latency.  A crossing arc is
    // then slot flop -> AND -> OR tree -> the reader's next-state select.
    localparam int NS = 2 * DEPTH;
    wire [PW-1:0] rp_place_c = gb + PW'(PLACE) - PW'(late);
    wire [PW-1:0] rp_place;
    if (PLREG) begin : g_plreg
        logic [PW-1:0] gb2;
        always_comb begin
            gb2[PW-1] = g2[PW-1];
            for (int i = PW - 2; i >= 0; i--) gb2[i] = gb2[i+1] ^ g2[i];
        end
        logic [PW-1:0] pl_q;
`ifdef OT_MESO_MUTANT_PLREG
        always_ff @(posedge rclk) pl_q <= rp_place_c;        // MUTANT: one edge late (the un-retimed value registered)
`else
        always_ff @(posedge rclk) pl_q <= gb2 + PW'(PLACE) - PW'(g2 != n2);
`endif
        assign rp_place = pl_q;
`ifndef SYNTHESIS
        // retiming proof in every bench: the flop equals the combinational placement at every edge once_FW_OLD g/n are
        // defined (x-initial: both sides hold the same arbitrary power-up words after 4 edges)
        int pl_n = 0;
        always @(posedge rclk) begin
            if (pl_n < 4) pl_n <= pl_n + 1;
            else if (pl_q !== rp_place_c) $display("PLREG_MISMATCH %m t=%0t q=%0d c=%0d", $time, pl_q, rp_place_c);
        end
`endif
    end else begin : g_plcomb
        assign rp_place = rp_place_c;
    end
    logic [NS-1:0] oh;
    always_ff @(posedge rclk) begin
        if (r_align) begin
            rp <= rp_place;
            oh <= NS'(1) << rp_place;
        end else if (r_on) begin
            rp <= rp + 1'b1;
            oh <= {oh[NS-2:0], oh[NS-1]};
        end
    end
    // position j = {lap, slot}: valid in the expected lap, and lap bit as expected
    wire [NS-1:0] pos_v   = {s_v1, s_v0};
    wire [NS-1:0] pos_lap = {s_lap, ~s_lap};
    // one-hot rotations: rot(oh, k)[j] = oh[j - k]  (the position k ahead of rp)
    function automatic logic [NS-1:0] rot(input logic [NS-1:0] x, input int k);
        for (int j = 0; j < NS; j++) rot[j] = x[(j - k + 2 * NS) % NS];
    endfunction
    // data word: NCH chunks, each with its own one-hot slot-index register (fanout 64, not W)
    localparam int NCH = (W % 64 == 0) ? W / 64 : 1;
    localparam int WCH = W / NCH;
    for (genvar c = 0; c < NCH; c++) begin : dch
        logic [DEPTH*WCH-1:0] sd_c;
        for (genvar i = 0; i < DEPTH; i++) begin : sl
            assign sd_c[i*WCH +: WCH] = s_d[i][c*WCH +: WCH];
        end
        ot_meso_dsel_FW_OLD #(.W(WCH), .DEPTH(DEPTH), .REG(RDREG), .SPLIT(RSPLIT)) u_dsel (.clk(rclk), .align(ONV ? r_align_v[c] : r_align), .on(ONV ? r_on_v[c] : r_on),
                                                      .place(rp_place[AW-1:0]), .sd(sd_c), .y(r_d[c*WCH +: WCH]));
    end
    logic r_v_c, r_lap_c;
    ot_meso_ohor_FW_OLD #(.N(NS)) u_v   (.sel(oh), .x(pos_v),   .y(r_v_c));
    ot_meso_ohor_FW_OLD #(.N(NS)) u_lap (.sel(oh), .x(pos_lap), .y(r_lap_c));
    if (RDREG) begin : g_rdreg
        // captured at the same rclk edge the unregistered reader would consume them (same crossing window); a
        // pointer not yet placed in that cycle presents no word and no lap fault
        logic r_v_q, r_lap_q;
        always_ff @(posedge rclk) begin
            r_v_q   <= r_v_c && r_on;
            r_lap_q <= r_lap_c || !r_on;
        end
        assign r_v = r_v_q; assign r_lap_ok = r_lap_q;
    end else begin : g_comb
        assign r_v = r_v_c; assign r_lap_ok = r_lap_c;
    end

    // guards on the falling read edge, then 3 rising flops
    wire [NS-1:0] oh_lo = rot(oh, GUARD_LO);            // rp + GUARD_LO: consumed at the next rising edge + GUARD_LO
    wire [NS-1:0] oh_hi = rot(oh, GUARD_HI - 1);        // rp - 1 + GUARD_HI (rp-1 was consumed at the last rising edge)
    (* async_reg = "true" *) logic glo0, ghi0;
    (* async_reg = "true" *) logic glo1, glo2, ghi1, ghi2;
    logic glo3, ghi3;
    always_ff @(negedge rclk) begin
        glo0 <= |(oh_lo & pos_lap);                    // written in this lap
        ghi0 <= ~|(oh_hi & pos_lap);                   // not yet written in this lap
    end
    always_ff @(posedge rclk) begin
        glo1 <= glo0; glo2 <= glo1; glo3 <= glo2;
        ghi1 <= ghi0; ghi2 <= ghi1; ghi3 <= ghi2;
    end
`ifdef OT_MESO_MUTANT_NO_GUARD
    assign r_glo_ok = 1'b1;
    assign r_ghi_ok = 1'b1;
`else
    assign r_glo_ok = glo3;
    assign r_ghi_ok = ghi3;
`endif
`ifdef OT_MESO_DEBUG
    assign dbg_tc = tc; assign dbg_rp = rp;
`endif
endmodule

// Kept-hierarchy leaves of the crossing arcs: ABC optimises each alone, so the crossing term arrives at one 2:1 select
// (ot_meso_sel_FW_OLD) after a two-level AND-OR (ot_meso_ohor_FW_OLD) and cannot_FW_OLD be folded back into next-state arithmetic.
(* keep_hierarchy *)
module ot_meso_sel_FW_OLD #(parameter int N = 1) (
    input  logic         s,
    input  logic [N-1:0] a,
    input  logic [N-1:0] b,
    output logic [N-1:0] y
);
    assign y = s ? a : b;
endmodule

(* keep_hierarchy *)
module ot_meso_ohor_FW_OLD #(parameter int N = 2) (
    input  logic [N-1:0] sel,
    input  logic [N-1:0] x,
    output logic         y
);
    assign y = |(sel & x);
endmodule

// One chunk of the data-ring read: its own one-hot copy of the slot index (placed and advanced with rp), then a
// one-hot AND-OR of the DEPTH slots.  Kept hierarchy keeps the replicated index registers from being merged.
(* keep_hierarchy *)
module ot_meso_dsel_FW_OLD #(parameter int W = 64, parameter int DEPTH = 4, parameter bit REG = 0, parameter bit SPLIT = 0,
                      // DSREP-1 (DIE-HEAD-58 TURNB): SREP kept copies of the one-hot select di, copy s drives bits
                      // [s*W/SREP, (s+1)*W/SREP); same align/on/place, so every copy equals di.  1 = identical logic.
                      parameter int SREP = 1) (
    input  logic                    clk,
    input  logic                    align,
    input  logic                    on,
    input  logic [$clog2(DEPTH)-1:0] place,
    input  logic [DEPTH*W-1:0]      sd,
    output logic [W-1:0]            y
);
    logic [DEPTH-1:0] di;
    always_ff @(posedge clk) begin
        if (align) di <= DEPTH'(1) << place;
        else if (on) di <= {di[DEPTH-2:0], di[DEPTH-1]};
    end
    logic [W-1:0] y_c;
    if (SREP > 1) begin : g_srep
        localparam int SW = W / SREP;
        if (SW * SREP != W) begin : g_bad $error("ot_meso_dsel_FW_OLD: W %% SREP != 0"); end
        wire [DEPTH-1:0] dr [SREP];
        for (genvar r = 0; r < SREP; r++) begin : sr
            (* keep = "true" *) ot_meso_dsel_sel_FW_OLD #(.DEPTH(DEPTH)) u_sel (.clk(clk), .align(align), .on(on), .place(place),
                                                                   .di(dr[r]));
        end
        always_comb begin
            y_c = '0;
            for (int i = 0; i < DEPTH; i++)
                for (int b = 0; b < W; b++)
                    y_c[b] = y_c[b] | (sd[i*W + b] & dr[b / SW][i]);
        end
    end else begin : g_s1
        always_comb begin
            y_c = '0;
            for (int i = 0; i < DEPTH; i++) y_c = y_c | (sd[i*W +: W] & {W{di[i]}});
        end
    end
    if (REG && SPLIT) begin : g_split
        // SPLIT: the crossing arc is slot -> one AO22 level -> a half-select flop (mcast_r6 Q1: m -> AO22 -> AO221 ->
        // y_q -63.9 ps against the 356.667 ps crossing bound); the two halves are ORed in rclk after the flops, the
        // same edge the single readout flop would present (one-hot di: at most one half is non-zero)
        logic [W-1:0] ya_c, yb_c, ya_q, yb_q;
        always_comb begin
            ya_c = '0; yb_c = '0;
            for (int i = 0; i < DEPTH / 2; i++) ya_c = ya_c | (sd[i*W +: W] & {W{di[i]}});
            for (int i = DEPTH / 2; i < DEPTH; i++) yb_c = yb_c | (sd[i*W +: W] & {W{di[i]}});
        end
        always_ff @(posedge clk) begin ya_q <= ya_c; yb_q <= yb_c; end
`ifdef OT_MESO_MUTANT_RSPLIT
        assign y = ya_q;                                    // MUTANT: upper half-select dropped
`else
        assign y = ya_q | yb_q;
`endif
    end else if (REG) begin : g_reg
        // the crossing's capture flop sits next to the select (RDREG): the arc is slot -> AND-OR -> this flop
        logic [W-1:0] y_q;
        always_ff @(posedge clk) y_q <= y_c;
        assign y = y_q;
    end else begin : g_comb
        assign y = y_c;
    end
endmodule

// One chunk of the data-ring write (WCHK): its own one-hot copy of the write slot, loaded with the next index one edge
// ahead, and the chunk's DEPTH slots written every cycle.  Kept hierarchy keeps the replicated slot registers apart.
(* keep_hierarchy *)
module ot_meso_wch_FW_OLD #(parameter int W = 64, parameter int DEPTH = 4) (
    input  logic                     clk,
    input  logic [$clog2(DEPTH)-1:0] nxt,
    input  logic [W-1:0]             d,
    output logic [DEPTH*W-1:0]       sd
);
    logic [DEPTH-1:0] we;
    logic [W-1:0] m [DEPTH];
    always_ff @(posedge clk) we <= DEPTH'(1) << nxt;
    for (genvar i = 0; i < DEPTH; i++) begin : sl
        always_ff @(posedge clk) if (we[i]) m[i] <= d;
        assign sd[i*W +: W] = m[i];
    end
endmodule

// DSREP-1 select copy of ot_meso_dsel_FW_OLD (same state machine as its di register); kept so the copies are not merged.
(* keep_hierarchy, keep *)
module ot_meso_dsel_sel_FW_OLD #(parameter int DEPTH = 4) (
    input  logic                     clk,
    input  logic                     align,
    input  logic                     on,
    input  logic [$clog2(DEPTH)-1:0] place,
    (* keep *) output logic [DEPTH-1:0] di
);
    always_ff @(posedge clk) begin
        if (align) di <= DEPTH'(1) << place;
        else if (on) di <= {di[DEPTH-2:0], di[DEPTH-1]};
    end
endmodule

// Opt-in die-plan clock-region landing. The entire bus, including its epoch
// bit, is one continuously sampled word: no valid decoding or backpressure.
// fclk is forwarded from the transmitting partition beside the data bus.
// clk is the receiving partition's local clock from the same frequency source.
// The receiver's original boundary flop remains AFTER q. OFFSET=2/RDREG=1
// prices three extra cycles in the zero-phase reference; phase placement and
// its guard window still require the region-specific physical timing gate.
// rst_n is the timed receiver wavefront reset, not an asynchronous reset.
(* keep_hierarchy *)
module ot_dp_clk_landing_FW_OLD #(
    parameter integer W = 1,
    parameter integer SETTLE = 16,
    parameter bit     WNEG = 0     // S81-RINGHOLD-3 variant (a), opt-in: ring write on the falling fclk edge
) (
    input wire fclk,
    input wire clk,
    input wire rst_n,
    input wire [W-1:0] d,
    output wire [W-1:0] q,
    output reg ready,
    output wire fault
);
    // Keep the existing ring's selectors in 64-bit chunks even for a bus
    // carrying an extra epoch bit. Padding is internal unused capacity only.
    localparam integer RW = ((W + 63) / 64) * 64;
    localparam integer NC = RW / 64;
    localparam integer CW = $clog2(SETTLE + 1);
    reg [CW-1:0] count;
    reg on;
    wire align = rst_n && !on && (count == CW'(SETTLE));
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [RW-1:0] ring_d = {{(RW-W){1'b0}}, d};
    wire [RW-1:0] ring_q;
    assign q = ring_q[W-1:0];
    reg [2:0] arm;
    reg fault_state;
    wire trip = arm[2] && (!rv || !lap_ok || !glo_ok || !ghi_ok);
    wire fault_next = fault_state || trip;
    // A private output flop drives ONLY the observed fault pin. The sticky
    // state also controls readiness, so exporting that state directly would
    // violate the dedicated registered-pin rule.
    ot_dp_landing_fault_port_FW_OLD u_fault_port (.clk(clk), .rst_n(rst_n), .d(fault_next), .q(fault));
    // The ring write pointer is deliberately free-running across local resets.
    // SETTLE lets Gray/half-edge samples fill before placing the read pointer.
    always @(posedge clk) begin
        if (!rst_n) begin
            count <= 0;
            on <= 0;
            ready <= 0;
            fault_state <= 0;
            arm <= 0;
        end else begin
            if (!on) begin
                if (count != CW'(SETTLE)) count <= count + 1'b1;
                else on <= 1;
            end
            arm <= {arm[1:0], on};
            ready <= arm[2] && !fault_state;
            fault_state <= fault_next;
        end
    end
    ot_meso_ring_FW_OLD #(.W(RW), .DEPTH(4), .OFFSET(2), .GUARD_LO(0),
                   .GUARD_HI(4), .RDREG(1), .TNEG(WNEG)) u_ring (
        .tclk(fclk), .t_v(1'b1), .t_d(ring_d), .rclk(clk),
        .r_align(align), .r_on(on), .r_align_v({NC{align}}), .r_on_v({NC{on}}),
        .r_d(ring_q), .r_v(rv), .r_lap_ok(lap_ok),
        .r_glo_ok(glo_ok), .r_ghi_ok(ghi_ok)
    );
`ifndef SYNTHESIS
    initial begin
        if (W < 1) $fatal(1, "clock landing requires a nonempty bundle");
        if (SETTLE < 8) $fatal(1, "clock landing SETTLE must cover synchronizer fill");
    end
`endif
endmodule

(* keep_hierarchy, keep *)
module ot_dp_landing_fault_port_FW_OLD (
    input wire clk, rst_n, d,
    output reg q
);
    always @(posedge clk) if (!rst_n) q <= 0; else q <= d;
endmodule

// Active-input-only reverse wavefront reduction. Source faults are sticky;
// their registered OR remains sticky until the raw wavefront reset. No child
// pin is synthesized for an absent branch.
(* keep_hierarchy, keep *)
module ot_dp_landing_collect_FW_OLD #(parameter integer N=1) (
    input wire clk, rst_n,
    input wire [N-1:0] ready_i, fault_i,
    output reg ready_o, fault_o
);
    always @(posedge clk) begin
        if (!rst_n) begin ready_o <= 0; fault_o <= 0; end
        else begin ready_o <= &ready_i; fault_o <= |fault_i; end
    end
endmodule

// Face capture flop of one same-region (non-seam) status input pin (DIE-S81-29, COORD DIE-S81-28-PARK (2)): the
// partition pin loads ONLY this flop's D, with no reset term (an AND2 before D would break the face rule), and the
// reduction above reads q. The sender's dedicated output register runs on the same region clock. +1 status cycle
// (boot only, priced in the collector boot budget), 0 data cycles. The collector stage after it is synchronously reset.
(* keep_hierarchy, keep *)
module ot_dp_landing_face_FW_OLD (
    input wire clk, d,
    output reg q
);
    always @(posedge clk) q <= d;
endmodule

// COUNT-ALIGNED landed (mesochronous) crossing.  MESO-COUNT-1 study (OWNER-approved 10-27), opt-in, default-off:
// opt-in: instantiated only by the count_aligned form of tools/die_plan/clock_landings.py (MESO-INTEG-1, table
// "count_aligned" from count_align_bind.py).  ot_dp_clk_landing_FW_OLD / ot_meso_ring_FW_OLD are unchanged and stay the default.
//
// Why.  ot_meso_ring_FW_OLD places its read pointer at start-up from the MEASURED PHASE (half-period resolution), so the
// whole-cycle latency of a crossing is a function of (phase mod T).  Two chips whose phases differ by exactly T
// measure the same thing but need pointers one apart, so NO phase-measured placement can give a chip-invariant
// latency once_FW_OLD a crossing's derated phase spread reaches T (HEAD 950 ps, KV 1091 ps > 833 ps).
//
// Mechanism.  Both sides count cycles from a chip-invariant COUNT ORIGIN (their start/reset release at a design-time
// known cycle a_x, a_y; see results/meso_count_1027/README.md for how the origin is delivered).
//   * Writer (fclk = the sender's forwarded clock): tc is reset by t_rst_n, the sender's start forwarded beside the
//     bus (source-synchronous with fclk).  Sender word n is written into slot n mod DEPTH with lap bit n[AW] and a
//     written-since-start bit; slot n is rewritten by word n + DEPTH.
//   * Reader (clk): rp is reset by rst_n to -K (mod 2*DEPTH) and increments every cycle, so at receiver count m it
//     consumes the slot of sender word m - K.  NO phase sample, NO Gray synchroniser, NO placement decision.
//   * The lag of every word is then L = (K + a_y - a_x) T + d, d = the static receiver-minus-sender clock phase
//     (+ drift).  The word is captured correctly iff (GUARD_LO + 0.5) T <= L <= (GUARD_HI - 0.5) T: the same
//     opposite-edge lap guards as ot_meso_ring_FW_OLD (copied, unchanged) watch exactly that window, fail closed (sticky).
//   * Latency is K + RDREG receiver cycles after the sender cycle, for EVERY static phase in the window: chip-to-chip
//     whole-cycle variation is absorbed by the ring depth, window width (GUARD_HI - GUARD_LO - 1) T (3 T at the
//     default DEPTH 4 / guards 0,4), instead of the old one-period placement window.
//
// Ready-timeout (MESO-RECONCILE-1, COORD 21:55): a lag below the window never consumes a valid word, so the guards
// never arm and the crossing stayed !ready with no fault (fail-closed but silent).  TIMEOUT receiver cycles after rst_n
// release without arming raise the sticky fault on the same fault port.  GUARD_HI defaults to DEPTH.
// Ports as ot_dp_clk_landing_FW_OLD plus t_rst_n.  Receiver count c = rclk edges since rst_n release (c = 0 at the first edge
// that samples rst_n high).  Right after edge c, q holds sender word c - K (captured at that edge, RDREG); the
// receiver's own boundary flop takes it at c + 1: crossing latency K + 1 counts, for every lag in the window.
// Start-up: a region's count origin (its rst_n release) comes from ot_dp_landing_origin_FW_OLD on ONE tree crossing per
// region (start wavefront over a spanning tree of these rings); every other crossing's K is set at bind time.
// Model, conditions on K / DEPTH / guards and loop consistency: results/meso_count_1027/README.md.
// OT_MESO_CA_FV (formal only): fv_recent / fv_now / fv_any make the reads of a slot written within the STA bound
// (recent) or at the sampling instant (now) arbitrary, i.e. metastable / unbounded data, so the proof covers them.
(* keep_hierarchy *)
module ot_dp_clk_landing_ca_FW_OLD #(
    parameter integer W        = 1,
    parameter integer DEPTH    = 4,   // power of two >= 4
    parameter integer K        = 2,   // read offset in counts (binder: K' - (a_y - a_x)); any integer
    parameter integer GUARD_LO = 0,
    parameter integer GUARD_HI = DEPTH, // <= DEPTH; MESO-RECONCILE-1: default DEPTH (4 was wrong at DEPTH 8)
    parameter integer ARM      = 2 * DEPTH + 4, // receiver cycles after the first valid word before guards are trusted
    // MESO-RECONCILE-1 ready-timeout: fault if the crossing is not armed TIMEOUT receiver cycles after rst_n release
    // (0 = off).  In the window the first valid word (sender count 0) is consumed at receiver count max(K, 0), seen one
    // count later, armed ARM counts after that: armed by count max(K,0) + ARM + 2.  The default adds 2*DEPTH + 6 counts
    // of slack, so it never fires in the window (proven, fv_ca2 A_ALL); a lag below the window (no valid word is ever
    // consumed: never ready, previously no fault) now raises fault (fv_ca2 A_TMO).
    parameter integer TIMEOUT  = (K > 0 ? K : 0) + ARM + 2 * DEPTH + 8,
    parameter bit CONTROL_STATUS_COPY = 0, // optional private status bank; same cycles
    parameter bit WFALL = 0 // DIE-HEAD-48 ring-write hold: writer on the falling edge of fclk (see wclk)
) (
    input  wire         fclk,
    input  wire         t_rst_n,     // sender start, forwarded with fclk (synchronous to fclk)
    input  wire         clk,
    input  wire         rst_n,       // receiver start (count origin), synchronous to clk
    input  wire [W-1:0] d,
    output wire [W-1:0] q,
    output reg          ready,
    output wire         fault
`ifdef OT_MESO_CA_FV
   ,input  wire [DEPTH-1:0] fv_recent, fv_now,
    input  wire [W+3:0]     fv_any
`endif
);
    localparam integer RW = ((W + 63) / 64) * 64;
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(ARM + 1);
    localparam integer TCW = $clog2(TIMEOUT + 2);
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [RW-1:0] ring_q;
    assign q = ring_q[W-1:0];
    // WFALL = 1: the whole writer (slots, count, tags) runs on the opposite fclk edge, so a word launched on the sender's
    // rising edge is held T/2 by structure (FLOW-16 05:48).  Default 0 = no inverter, identical logic.
    wire wclk = WFALL ? ~fclk : fclk;
    reg seen;                       // first valid word consumed
    reg [CW-1:0] arm_cnt;
    wire armed = seen && (arm_cnt == CW'(ARM));
    reg fault_state;
    reg [TCW-1:0] tmo_cnt;          // receiver cycles since rst_n release while not armed (saturates at TIMEOUT)
`ifdef OT_MESO_CA_MUTANT_NO_TIMEOUT
    wire tmo = 1'b0;                // MUTANT: ready-timeout disabled
`else
    wire tmo = (TIMEOUT > 0) && !armed && (tmo_cnt == TCW'(TIMEOUT));
`endif
    wire trip = (armed && (!rv || !lap_ok || !glo_ok || !ghi_ok)) || tmo;
    wire fault_next = fault_state || trip;
    ot_dp_landing_fault_port_FW_OLD u_fault_port (.clk(clk), .rst_n(rst_n), .d(fault_next), .q(fault));
    always @(posedge clk) begin
        if (!rst_n) begin
            seen <= 0; arm_cnt <= 0; ready <= 0; fault_state <= 0; tmo_cnt <= 0;
        end else begin
            if (!armed && tmo_cnt != TCW'(TIMEOUT)) tmo_cnt <= tmo_cnt + 1'b1;
            if (rv) seen <= 1;
            if (seen && arm_cnt != CW'(ARM)) arm_cnt <= arm_cnt + 1'b1;
            ready <= armed && !fault_next;
            fault_state <= fault_next;
        end
    end
    localparam integer KTW = AW + 1 + 3;      // ring count width (LAPX = 3)
    localparam integer KNT = 1 << KTW;
    localparam integer KM  = ((K % KNT) + KNT) % KNT;
    ot_meso_ring_ca_FW_OLD #(.W(RW), .DEPTH(DEPTH), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI),
                      .CONTROL_STATUS_COPY(CONTROL_STATUS_COPY)) u_ring (
        .tclk(wclk), .wen_clk(1'b0), .t_rst_n(t_rst_n), .t_d({{(RW-W){1'b0}}, d}), .rclk(clk), .r_rst_n(rst_n), .k_s(KTW'(KM)),
        .r_d(ring_q), .r_v(rv), .r_lap_ok(lap_ok), .r_glo_ok(glo_ok), .r_ghi_ok(ghi_ok)
`ifdef OT_MESO_CA_FV
       ,.fv_recent(fv_recent), .fv_now(fv_now), .fv_any(fv_any)
`endif
    );
`ifndef SYNTHESIS
    initial begin
        if (W < 1) $fatal(1, "count-aligned landing requires a nonempty bundle");
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $fatal(1, "DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_HI > DEPTH || GUARD_HI < GUARD_LO + 2) $fatal(1, "need 0 <= GUARD_LO, GUARD_LO+2 <= GUARD_HI <= DEPTH");
        if (TIMEOUT != 0 && TIMEOUT < (K > 0 ? K : 0) + ARM + 3) $fatal(1, "TIMEOUT below max(K,0) + ARM + 3 would fire in the window");
    end
`endif
endmodule

// MESO-STRAP-1 (OWNER 12.15a COUNT STRAPS, METHODOLOGY 1.8 conditions): ot_dp_clk_landing_ca_FW_OLD with K as the strap input
// strap_k instead of a parameter, so all copies of a partition type share one hardened design; DEPTH stays a parameter
// (the type's largest).  strap_k = K mod 2^KW, KW = log2(DEPTH) + 4 (D4 6 bits, D8 7 bits); every value is legal.  Quasi-
// static: no pin register, read only by the reader-pointer reset load, kit SDC set_false_path -from the strap port, TIEHI/
// TIELO per bit at the parent.  Same logic as ot_dp_clk_landing_ca_FW_OLD (LEC per used K: tools/die_plan/strap_lec.py); proof
// with strap_k free-but-constant over all 2^KW values: rtl/test/meso/formal_ca/fv_ca2.sv FV_STRAP.
(* keep_hierarchy *)
module ot_dp_clk_landing_cas_FW_OLD #(
    parameter integer W        = 1,
    parameter integer DEPTH    = 4,   // power of two >= 4
    parameter integer GUARD_LO = 0,
    parameter integer GUARD_HI = DEPTH, // <= DEPTH; MESO-RECONCILE-1: default DEPTH (4 was wrong at DEPTH 8)
    parameter integer ARM      = 2 * DEPTH + 4, // receiver cycles after the first valid word before guards are trusted
    // MESO-RECONCILE-1 ready-timeout: fault if the crossing is not armed TIMEOUT receiver cycles after rst_n release
    // (0 = off).  In the window the first valid word (sender count 0) is consumed at receiver count max(K, 0), seen one
    // count later, armed ARM counts after that: armed by count max(K,0) + ARM + 2.  The default adds 2*DEPTH + 6 counts
    // of slack, so it never fires in the window (proven, fv_ca2 A_ALL); a lag below the window (no valid word is ever
    // consumed: never ready, previously no fault) now raises fault (fv_ca2 A_TMO).
    // strap form: K is any value of strap_k, so the timeout covers the largest, 2^KW - 1 (D4 91, D8 171 cycles)
    parameter integer TIMEOUT  = (1 << ($clog2(DEPTH) + 4)) - 1 + ARM + 2 * DEPTH + 8,
    parameter bit CONTROL_STATUS_COPY = 0, // appended to preserve positional parameters
    parameter bit WFALL = 0, // as ot_dp_clk_landing_ca_FW_OLD
    // WREG-1 (DIE-HEAD-58 TURNB, 11-03): 1 = the writer START t_rst_n is registered at the receiver face (one wclk edge,
    // == landing_writer_start W=1: K_new = K_old + 1 at bind, count_align_bind.strap_ties) and every (slot, 64-bit chunk)
    // write enable is its own register (fanout <= 64 per enable flop) instead of t_rst_n & slot-decode broadcast to W x
    // DEPTH data flops.  Default 0 = identical logic.
    parameter bit WREG = 0,
    // DSREP-1: copies of each read-select one-hot register per 64-bit chunk (ot_meso_dsel_FW_OLD SREP); 1 = identical logic
    parameter integer DSREP = 1,
    // FREG-1 (DIE-HEAD-58 ruling 11-03, hd_turn_a t_i): 1 = the bundle d AND the writer start t_rst_n are registered on
    // the RISING fclk at the receiver face (full-period capture of the source-synchronous input), and the (WFALL) writer
    // reads the registered copies over a local T/2 path.  Data and start move one fclk cycle together and the strap ties
    // K + 1 (count_align_bind.strap_ties) to keep the ring window: q is the same word stream ONE clk cycle later (one
    // added data cycle, results/dh58_turnb_1103/wreg_equiv TB_FREG).
    // Default 0 = identical logic.
    parameter bit FREG = 0
) (
    input  wire         fclk,
    input  wire         t_rst_n,     // sender start, forwarded with fclk (synchronous to fclk)
    input  wire         clk,
    input  wire         rst_n,       // receiver start (count origin), synchronous to clk
    input  wire [$clog2(DEPTH)+3:0] strap_k,  // K mod 2^(log2(DEPTH)+4), quasi-static strap (tied at the parent)
    input  wire [W-1:0] d,
    output wire [W-1:0] q,
    output reg          ready,
    output wire         fault
`ifdef OT_MESO_CA_FV
   ,input  wire [DEPTH-1:0] fv_recent, fv_now,
    input  wire [W+3:0]     fv_any
`endif
);
    localparam integer RW = ((W + 63) / 64) * 64;
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(ARM + 1);
    localparam integer TCW = $clog2(TIMEOUT + 2);
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [RW-1:0] ring_q;
    assign q = ring_q[W-1:0];
    // WFALL = 1: the whole writer (slots, count, tags) runs on the opposite fclk edge, so a word launched on the sender's
    // rising edge is held T/2 by structure (FLOW-16 05:48).  Default 0 = no inverter, identical logic.
    wire wclk = WFALL ? ~fclk : fclk;
    wire [W-1:0] d_w;
    wire t_rst_w;
    generate if (FREG) begin : g_freg
        wire t_rst_f;
        ot_meso_face_ff_FW_OLD #(.W(W + 1)) u_face (.clk(fclk), .d({t_rst_n, d}), .q({t_rst_f, d_w}));
`ifdef OT_MESO_CA_MUTANT_FREG
        assign t_rst_w = t_rst_n;   // MUTANT: data registered at the face, writer start not (one-cycle misalignment)
`else
        assign t_rst_w = t_rst_f;
`endif
    end else begin : g_nofreg
        assign d_w = d;
        assign t_rst_w = t_rst_n;
    end endgenerate
    reg seen;                       // first valid word consumed
    reg [CW-1:0] arm_cnt;
    wire armed = seen && (arm_cnt == CW'(ARM));
    reg fault_state;
    reg [TCW-1:0] tmo_cnt;          // receiver cycles since rst_n release while not armed (saturates at TIMEOUT)
`ifdef OT_MESO_CA_MUTANT_NO_TIMEOUT
    wire tmo = 1'b0;                // MUTANT: ready-timeout disabled
`else
    wire tmo = (TIMEOUT > 0) && !armed && (tmo_cnt == TCW'(TIMEOUT));
`endif
    wire trip = (armed && (!rv || !lap_ok || !glo_ok || !ghi_ok)) || tmo;
    wire fault_next = fault_state || trip;
    ot_dp_landing_fault_port_FW_OLD u_fault_port (.clk(clk), .rst_n(rst_n), .d(fault_next), .q(fault));
    always @(posedge clk) begin
        if (!rst_n) begin
            seen <= 0; arm_cnt <= 0; ready <= 0; fault_state <= 0; tmo_cnt <= 0;
        end else begin
            if (!armed && tmo_cnt != TCW'(TIMEOUT)) tmo_cnt <= tmo_cnt + 1'b1;
            if (rv) seen <= 1;
            if (seen && arm_cnt != CW'(ARM)) arm_cnt <= arm_cnt + 1'b1;
            ready <= armed && !fault_next;
            fault_state <= fault_next;
        end
    end
    ot_meso_ring_ca_FW_OLD #(.W(RW), .DEPTH(DEPTH), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI),
                      .CONTROL_STATUS_COPY(CONTROL_STATUS_COPY), .WREG(WREG), .WEN_NEG(WFALL), .DSREP(DSREP)) u_ring (
        .tclk(wclk), .wen_clk(WFALL ? fclk : wclk), .t_rst_n(t_rst_w), .t_d({{(RW-W){1'b0}}, d_w}), .rclk(clk), .r_rst_n(rst_n), .k_s(strap_k),
        .r_d(ring_q), .r_v(rv), .r_lap_ok(lap_ok), .r_glo_ok(glo_ok), .r_ghi_ok(ghi_ok)
`ifdef OT_MESO_CA_FV
       ,.fv_recent(fv_recent), .fv_now(fv_now), .fv_any(fv_any)
`endif
    );
`ifndef SYNTHESIS
    initial begin
        if (W < 1) $fatal(1, "count-aligned landing requires a nonempty bundle");
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $fatal(1, "DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_HI > DEPTH || GUARD_HI < GUARD_LO + 2) $fatal(1, "need 0 <= GUARD_LO, GUARD_LO+2 <= GUARD_HI <= DEPTH");
        if (TIMEOUT != 0 && TIMEOUT < (1 << ($clog2(DEPTH) + 4)) - 1 + ARM + 3) $fatal(1, "strap TIMEOUT below 2^KW - 1 + ARM + 3 would fire in the window");
    end
`endif
endmodule

// One direction: DEPTH-slot ring, writer slot = sender count, reader slot = receiver count - K.
// MESO-STRAP-1 (OWNER 12.15a): the read offset is the INPUT k_s (K mod 2^TW, TW = log2(DEPTH)+1+LAPX), so one hardened
// type serves every K: ot_dp_clk_landing_ca_FW_OLD drives it with the constant K (identical logic after constant propagation),
// ot_dp_clk_landing_cas_FW_OLD with its strap_k pin.  k_s is quasi-static (tied at the parent, sampled only by the reset load of
// rp/oh/dsel), never registered; every value is legal (the ring only uses K mod 2^TW).
module ot_meso_ring_ca_FW_OLD #(
    parameter int W        = 64,
    parameter int DEPTH    = 4,
    parameter int GUARD_LO = 0,
    parameter int GUARD_HI = 4,
    parameter int LAPX     = 3,     // extra lap-tag bits per slot: a consumed word from the wrong lap is caught for
                                    // origin errors up to 2^(AW+1+LAPX) counts (the 1-bit lap aliases every 2*DEPTH)
    parameter bit CONTROL_STATUS_COPY = 0,
    parameter bit WREG = 0,         // WREG-1: registered writer start + registered per-(slot, chunk) write enables
    parameter bit WEN_NEG = 0,      // WREG with WFALL: write-enable flops on the falling edge of wen_clk (raw fclk)
    parameter int DSREP = 1         // DSREP-1: read-select register copies per chunk (ot_meso_dsel_FW_OLD SREP)
) (
    input  logic         tclk,
    input  logic         wen_clk,    // WREG write-enable clock: tclk, or the raw fclk with WEN_NEG; unused when !WREG
    input  logic         t_rst_n,
    input  logic [W-1:0] t_d,
    input  logic         rclk,
    input  logic         r_rst_n,
    input  logic [$clog2(DEPTH)+LAPX:0] k_s,   // read offset K mod 2^TW (constant / strap)
    output logic [W-1:0] r_d,        // RDREG: word captured at the consuming edge, presented one period later
    output logic         r_v,        // consumed slot written since the sender start, in the expected lap
    output logic         r_lap_ok,
    output logic         r_glo_ok,
    output logic         r_ghi_ok
`ifdef OT_MESO_CA_FV
   ,input  logic [DEPTH-1:0] fv_recent, fv_now,
    input  logic [W+3:0]     fv_any
`endif
);
    localparam int AW = $clog2(DEPTH);
    localparam int PW = AW + 1;
    localparam int NS = 2 * DEPTH;
    localparam int TW = PW + LAPX;                       // count bits kept: {ext tag, lap, slot}
    localparam int NT = 1 << TW;
    // reader reset value: count of sender word (0 - K) modulo 2^TW
`ifdef OT_MESO_CA_MUTANT_K
    wire [TW-1:0] RP0T = TW'(0) - k_s + TW'(1);   // MUTANT: one count late
`else
    wire [TW-1:0] RP0T = TW'(0) - k_s;
`endif
    wire [PW-1:0] RP0 = RP0T[PW-1:0];

    // ---------------- transmit (tclk): slot = sender count ----------------
    logic [TW-1:0] tc;
    // The CA crossing is the declared flop ring, including widths above the RAM guard.
    (* mem2reg *) logic [W-1:0]  s_d   [DEPTH];
    logic [DEPTH-1:0] s_w, s_lap;
    // WREG-1: t_go = the writer start every slot/count/tag flop uses.  WREG 0: t_go = t_rst_n (identical logic).
    // WREG 1: t_go = t_rst_n one wclk edge late (fs_q), and wen[i, c] = t_go && tc[slot] == i is precomputed one edge
    // early from the port (fs_q ? tc + 1 : 0 is tc at the next edge), one kept flop per (slot, 64-bit chunk).
    // Exactly the WREG 0 ring fed by t_rst_n through one flop (proof: results/dh58_turnb_1103/wreg_equiv).
    localparam int WNC = (W % 64 == 0) ? W / 64 : 1;
    localparam int WWC = W / WNC;
    wire t_go;
    wire [DEPTH*WNC-1:0] wen;
    if (WREG) begin : g_wreg
        logic fs_q;
        always_ff @(posedge tclk) fs_q <= t_rst_n;
        wire [AW-1:0] slot_nx = fs_q ? tc[AW-1:0] + 1'b1 : '0;
        for (genvar i = 0; i < DEPTH; i++) begin : sl
            for (genvar c = 0; c < WNC; c++) begin : ch
                (* keep = "true" *) ot_meso_wen_ff_FW_OLD #(.NEG(WEN_NEG)) u_wen (.clk(wen_clk), .d(t_rst_n && (slot_nx == AW'(i))),
                                                         .q(wen[i * WNC + c]));
            end
        end
        assign t_go = fs_q;
    end else begin : g_wreg_off
        assign t_go = t_rst_n;
        assign wen = '0;
    end
    always_ff @(posedge tclk) begin
`ifdef OT_MESO_CA_MUTANT_FREERUN
        tc <= tc + 1'b1;                                // MUTANT: old free-running writer (no count origin)
        if (!CONTROL_STATUS_COPY) begin
            if (!t_go) s_w <= '0; else s_w[tc[AW-1:0]] <= 1'b1;
        end
`else
        if (!t_go) begin tc <= '0; if (!CONTROL_STATUS_COPY) s_w <= '0; end
        else begin tc <= tc + 1'b1; if (!CONTROL_STATUS_COPY) s_w[tc[AW-1:0]] <= 1'b1; end
`endif
        if (t_go) begin
            if (!CONTROL_STATUS_COPY) s_lap[tc[AW-1:0]] <= tc[AW];
            if (!WREG) s_d[tc[AW-1:0]] <= t_d;
        end
        if (WREG)
            for (int i = 0; i < DEPTH; i++)
                for (int c = 0; c < WNC; c++)
`ifdef OT_MESO_CA_MUTANT_WREG
                    if (wen[i * WNC + c] && !(i == 0 && c == 0)) s_d[i][c * WWC +: WWC] <= t_d[c * WWC +: WWC]; // MUTANT
`else
                    if (wen[i * WNC + c]) s_d[i][c * WWC +: WWC] <= t_d[c * WWC +: WWC];
`endif
    end

    // Private valid/lap status drivers separate their control decode from the
    // falling-edge guard bank. Same D/clock/reset as the original slot flags;
    // no extra crossing or data cycle. Off by default pending physical proof.
    wire [DEPTH-1:0] ctl_w, ctl_lap;
    if (CONTROL_STATUS_COPY) begin : g_control_status_copy
        // Both native banks expose directly kept register outputs. A kept
        // alias through a frontend connection is insufficient for the canonical
        // hook's one-cell driver selection; it allowed the lap banks to merge.
        ot_meso_ca_status_copy_FW_OLD #(.DEPTH(DEPTH)) u_guard_status (
            .tclk(tclk), .t_rst_n(t_go), .slot(tc[AW-1:0]),
            .lap(tc[AW]), .written(s_w), .lap_q(s_lap)
        );
        ot_meso_ca_status_copy_FW_OLD #(.DEPTH(DEPTH)) u_status (
            .tclk(tclk), .t_rst_n(t_go), .slot(tc[AW-1:0]),
            .lap(tc[AW]), .written(ctl_w), .lap_q(ctl_lap)
        );
    end else begin : g_control_status_original
        assign ctl_w = s_w;
        assign ctl_lap = s_lap;
    end

    // ---------------- receive (rclk): rp = receiver count - K ----------------
    logic [TW-1:0] rp;
    logic [NS-1:0] oh;
    always_ff @(posedge rclk) begin
        if (!r_rst_n) begin rp <= RP0T; oh <= NS'(1) << RP0; end
        else begin rp <= rp + 1'b1; oh <= {oh[NS-2:0], oh[NS-1]}; end
    end
    wire [NS-1:0] pos_v   = {ctl_w & ctl_lap, ctl_w & ~ctl_lap};
    wire [NS-1:0] pos_lap = {ctl_lap, ~ctl_lap} | {~ctl_w, ~ctl_w};   // not yet written since start: no lap verdict
    function automatic logic [NS-1:0] rot(input logic [NS-1:0] x, input int k);
        for (int j = 0; j < NS; j++) rot[j] = x[(j - k + 2 * NS) % NS];
    endfunction
    // data: per-64-bit chunk registered one-hot select (ot_meso_dsel_FW_OLD, REG=1), placed at reset, rotating every cycle
    localparam int NCH = (W % 64 == 0) ? W / 64 : 1;
    localparam int WCH = W / NCH;
    logic [W-1:0] rd_q;
    for (genvar c = 0; c < NCH; c++) begin : dch
        logic [DEPTH*WCH-1:0] sd_c;
        for (genvar i = 0; i < DEPTH; i++) begin : sl
            assign sd_c[i*WCH +: WCH] = s_d[i][c*WCH +: WCH];
        end
        ot_meso_dsel_FW_OLD #(.W(WCH), .DEPTH(DEPTH), .REG(1), .SPLIT(0), .SREP(DSREP)) u_dsel (.clk(rclk), .align(!r_rst_n), .on(r_rst_n),
            .place(RP0[AW-1:0]), .sd(sd_c), .y(rd_q[c*WCH +: WCH]));
    end
    logic r_v_c, r_lap_c, r_lap1_c;
    ot_meso_ohor_FW_OLD #(.N(NS)) u_v   (.sel(oh), .x(pos_v),   .y(r_v_c));
    ot_meso_ohor_FW_OLD #(.N(NS)) u_lap (.sel(oh), .x(pos_lap), .y(r_lap1_c));
    if (LAPX > 0) begin : g_tag
        // extended lap tag of every slot (written with the word); the consumed slot's tag must equal rp's upper bits
        (* mem2reg *) logic [LAPX-1:0] s_tag [DEPTH];
        always_ff @(posedge tclk) if (t_go) s_tag[tc[AW-1:0]] <= tc[TW-1:PW];
        logic [LAPX-1:0] tag_c; logic w_c;
        always_comb begin
            tag_c = '0; w_c = 1'b0;
            for (int i = 0; i < DEPTH; i++) if (oh[i] || oh[i + DEPTH]) begin tag_c = tag_c | s_tag[i]; w_c = w_c | ctl_w[i]; end
        end
`ifdef OT_MESO_CA_MUTANT_NO_TAG
        assign r_lap_c = r_lap1_c;                                       // MUTANT: extended tag ignored
`else
        assign r_lap_c = r_lap1_c && (!w_c || tag_c == rp[TW-1:PW]);
`endif
    end else begin : g_notag
        assign r_lap_c = r_lap1_c;
    end
    logic r_v_q, r_lap_q;
`ifdef OT_MESO_CA_FV
    // the slot consumed at this edge; if it was written within the STA bound the captured word/flags are arbitrary
    logic [AW-1:0] fv_rs; always_comb begin fv_rs = '0; for (int j = 0; j < NS; j++) if (oh[j]) fv_rs = AW'(j % DEPTH); end
    wire fv_dx = fv_recent[fv_rs];
    logic fv_dx_q; logic [W-1:0] fv_any_q;
    always_ff @(posedge rclk) begin
        r_v_q   <= (fv_dx ? fv_any[0] : r_v_c) && r_rst_n;
        r_lap_q <= (fv_dx ? fv_any[1] : r_lap_c) || !r_rst_n;
    end
    assign r_d = fv_dx_q ? fv_any_q : rd_q;
    always_ff @(posedge rclk) begin fv_dx_q <= fv_dx; fv_any_q <= W'(fv_any >> 4); end
`else
    always_ff @(posedge rclk) begin
        r_v_q   <= r_v_c && r_rst_n;
        r_lap_q <= r_lap_c || !r_rst_n;
    end
    assign r_d = rd_q;
`endif
    assign r_v = r_v_q; assign r_lap_ok = r_lap_q;

    // guards (as ot_meso_ring_FW_OLD): falling read edge, then 3 rising flops
    wire [NS-1:0] oh_lo = rot(oh, GUARD_LO);
    wire [NS-1:0] oh_hi = rot(oh, GUARD_HI - 1);
    wire glo_c = |(oh_lo & {s_lap, ~s_lap} & {s_w, s_w});   // written since start, in this lap
    wire ghi_c = ~|(oh_hi & {s_lap, ~s_lap} & {s_w, s_w});  // not yet written in this lap
    (* async_reg = "true" *) logic glo0, ghi0;
    (* async_reg = "true" *) logic glo1, glo2, ghi1, ghi2;
    logic glo3, ghi3;
`ifdef OT_MESO_CA_FV
    logic [AW-1:0] fv_lo_s, fv_hi_s;
    always_comb begin
        fv_lo_s = '0; fv_hi_s = '0;
        for (int j = 0; j < NS; j++) begin if (oh_lo[j]) fv_lo_s = AW'(j % DEPTH); if (oh_hi[j]) fv_hi_s = AW'(j % DEPTH); end
    end
    always_ff @(negedge rclk) begin
        glo0 <= fv_now[fv_lo_s] ? fv_any[2] : glo_c;
        ghi0 <= fv_now[fv_hi_s] ? fv_any[3] : ghi_c;
    end
`else
    always_ff @(negedge rclk) begin
        glo0 <= glo_c;
        ghi0 <= ghi_c;
    end
`endif
    always_ff @(posedge rclk) begin
        glo1 <= glo0; glo2 <= glo1; glo3 <= glo2;
        ghi1 <= ghi0; ghi2 <= ghi1; ghi3 <= ghi2;
    end
`ifdef OT_MESO_CA_MUTANT_NO_GUARD
    assign r_glo_ok = 1'b1;
    assign r_ghi_ok = 1'b1;
`else
    assign r_glo_ok = glo3;
    assign r_ghi_ok = ghi3;
`endif
endmodule

// Count origin of a region from its parent's start, forwarded beside a tree crossing (start wavefront).
// p_start: the parent's start flop, forwarded with fclk (as t_rst_n of the ring); it rises once_FW_OLD and stays high.
// The child's start = 3 synchroniser flops (the first optionally on the falling edge, EDGE_FALL, chosen at bind time
// so the sampling boundary lies away from the crossing's derated phase interval) + PAD plain flops.  Whole cycles
// added: PAD + 3 + j, j in {0, 1} set by the static phase; j is chip-invariant when the derated phase interval avoids
// the sampling boundary, otherwise both values occur across chips and the binder widens the lag window of every
// crossing whose tree path includes this edge by one period (tools/die_plan/count_align_plan.py).  The tree crossing
// itself always lands in its window: its lag lies in [c, c + T) by construction.  Cleared only by the raw reset.
(* keep_hierarchy *)
module ot_dp_landing_origin_FW_OLD #(
    parameter integer PAD = 0,
    parameter bit EDGE_FALL = 0
) (
    input  wire clk,
    input  wire rst_raw_n,   // raw region reset (power-on / die reset), synchronous to clk
    input  wire p_start,     // parent's forwarded start (asynchronous to clk, monotonic 0 -> 1)
    output wire start        // region count origin: the ring readers' rst_n and the region's own start
);
    (* async_reg = "true" *) reg s0, s1;
    reg s2;
    wire s_in;
    if (EDGE_FALL) begin : g_fall
        (* async_reg = "true" *) reg sf;
        always @(negedge clk) sf <= p_start;
        assign s_in = sf;
    end else begin : g_rise
        assign s_in = p_start;
    end
    always @(posedge clk) begin
        if (!rst_raw_n) begin s0 <= 0; s1 <= 0; s2 <= 0; end
        else begin s0 <= s_in; s1 <= s0; s2 <= s1; end
    end
    if (PAD > 0) begin : g_pad
        reg [PAD-1:0] pd;
        always @(posedge clk) if (!rst_raw_n) pd <= 0; else pd <= PAD'({pd, s2});
        assign start = pd[PAD-1];
    end else begin : g_nopad
        assign start = s2;
    end
endmodule

// MESO-STRAP-1 (OWNER 12.15a): ot_dp_landing_origin_FW_OLD with PAD and EDGE_FALL as strap inputs instead of parameters, so the
// copies of a partition type that differ only in their start-tree edge share one hardened design.  strap_pad selects the
// tap of a PADMAX = 2^PADW - 1 flop chain (every value legal), strap_efall the falling-edge first synchroniser.  Both are
// quasi-static (tied TIEHI/TIELO at the parent, no pin register, set_false_path -from in the kit SDC); for a tied value the
// logic equals ot_dp_landing_origin_FW_OLD #(.PAD(strap_pad), .EDGE_FALL(strap_efall)) plus unobservable flops (LEC per used
// value: tools/die_plan/strap_lec.py).  The static select muxes sit before the first synchroniser flop (p_start is
// asynchronous; a constant select never glitches) and after the chain (start, timed like the parameter form's last flop).
(* keep_hierarchy *)
module ot_dp_landing_origin_s_FW_OLD #(
    parameter integer PADW = 1,
    // Optional retained DATA-state copies for the forwarded START face flops.
    // Their D/clock/reset match the existing stages; latency and sampling stay exact.
    parameter integer FWD_COPY = 0
) (
    input  wire            clk,
    input  wire            rst_raw_n,
    input  wire            p_start,
    input  wire            strap_efall,
    input  wire [PADW-1:0] strap_pad,
    output wire            start,
    // DIE-HEAD-10 FSTART out: D-side of start (start_d(t) == start(t+1) while rst_raw_n is high).  The wrapper's
    // dedicated face flop per forwarded start pin (d = start_d, same clk / raw reset) equals start every cycle:
    // 0 added cycles, proven by results/die_head_1028/die_head_10_fstart/fv_start_o.sh; internal loads keep start
    output wire            start_d
);
    localparam integer PADMAX = (1 << PADW) - 1;
    (* async_reg = "true" *) reg s0, s1, sf;
    reg s2;
    always @(negedge clk) sf <= p_start;
    wire s_in = strap_efall ? sf : p_start;
    always @(posedge clk) begin
        if (!rst_raw_n) begin s0 <= 0; s1 <= 0; s2 <= 0; end
        else begin s0 <= s_in; s1 <= s0; s2 <= s1; end
    end
    reg [PADMAX-1:0] pd;
    always @(posedge clk) if (!rst_raw_n) pd <= 0; else pd <= PADMAX'({pd, s2});
    wire [PADMAX:0] taps = {pd, s2};
    assign start = taps[strap_pad];
    // one tap earlier: taps_e[j] is the D-side of taps[j] (taps_e[0] = s1 -> s2, taps_e[j] = taps[j-1])
    wire [PADMAX:0] taps_e = {taps[PADMAX-1:0], s1};
`ifdef OT_ORIGIN_MUTANT_LATE
    assign start_d = taps[strap_pad];     // MUTANT (fv only): one cycle late
`else
    generate if (FWD_COPY != 0) begin : g_export
        wire [PADMAX-1:0] export_q;
        for (genvar k = 0; k < PADMAX; k = k + 1) begin : g_copy
            wire d;
            if (k == 0) assign d = s1;
            else if (k == 1) assign d = s2;
            else assign d = pd[k-2];
`ifdef OT_ORIGIN_EXPORT_MUTANT_LATE
            wire copy_d;
            if (k == 0) assign copy_d = s2; else assign copy_d = d;
`else
            wire copy_d = d;
`endif
            (* keep = "true" *) ot_dp_origin_export_ff_FW_OLD u_copy (
                .clk(clk), .rst_raw_n(rst_raw_n), .d(copy_d), .q(export_q[k]));
        end
        wire [PADMAX:0] export_taps = {export_q, s1};
        assign start_d = export_taps[strap_pad];
    end else begin : g_shared_export
        assign start_d = taps_e[strap_pad];
    end endgenerate
`endif
`ifndef SYNTHESIS
    initial if (PADW < 1 || PADW > 4) $fatal(1, "origin strap PADW must be 1..4");
`endif
endmodule

// Hierarchy retains the distinct physical export copy when its data equation
// equals an internal origin stage. This is a data register, never a clock pad.
(* keep_hierarchy = "yes" *)
module ot_dp_origin_export_ff_FW_OLD (
    input wire clk,
    input wire rst_raw_n,
    input wire d,
    output reg q
);
    always @(posedge clk) if (!rst_raw_n) q <= 1'b0; else q <= d;
endmodule

// Root region count origin (MESO-INTEG-1): the start tree's root has no parent start; its origin is a plain counter
// SETTLE cycles after its raw reset release, so it is chip-invariant.  SETTLE must cover the die's raw-reset wavefront
// release spread (every child origin's rst_raw_n must be high before the start wave reaches it); the binder takes it
// from the bind table (root_settle_cycles).  Cleared only by the raw reset; start rises once_FW_OLD and stays high.
(* keep_hierarchy *)
module ot_dp_landing_root_FW_OLD #(
    parameter integer SETTLE = 64
) (
    input  wire clk,
    input  wire rst_raw_n,
    output reg  start,
    // DIE-HEAD-10 FSTART out: D-side of start (start_d(t) == start(t+1) while rst_raw_n is high), see origin_s
    output wire start_d
);
    localparam integer CW = $clog2(SETTLE + 1);
    reg [CW-1:0] n;
`ifdef OT_ROOT_MUTANT_EARLY
    assign start_d = (n == CW'(SETTLE - 1));   // MUTANT (fv only): one cycle early
`else
    assign start_d = (n == CW'(SETTLE));
`endif
    always @(posedge clk) begin
        if (!rst_raw_n) begin n <= 0; start <= 0; end
        else begin
            if (n != CW'(SETTLE)) n <= n + 1'b1;
            start <= (n == CW'(SETTLE));
        end
    end
`ifndef SYNTHESIS
    initial if (SETTLE < 1) $fatal(1, "root SETTLE must be >= 1");
`endif
endmodule

// Intra-region start relay stage (DIE-KV-3/CAORIGIN, COORD 21:14 ASK 3): a region holding several landed partitions
// has ONE origin (ot_dp_landing_root_FW_OLD / ot_dp_landing_origin_FW_OLD) in its origin partition; every other landed partition of
// the region takes the origin's start through two of these flops on the region clock (tx in the origin partition ->
// cland_rstart pin -> rx in the relay partition).  It is a plain registered same-clock control path, timed by the die
// STA as an intra-region related pair (not a landed crossing).  count_align_bind.py gives the relay partition the
// count origin N_origin + 2 and shifts the K of its crossings by the same 2 counts.  Cleared by the partition's raw
// reset (synchronous, like ot_dp_landing_root_FW_OLD); the raw reset must release before the start wave arrives (root SETTLE).
(* keep_hierarchy *)
module ot_dp_landing_relay_FW_OLD (
    input  wire clk,
    input  wire rst_raw_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk) begin
        if (!rst_raw_n) q <= 1'b0;
        else q <= d;
    end
endmodule

// FREG-1 receiver face register of ot_dp_clk_landing_cas_FW_OLD (rising fclk): kept so synthesis does not retime or merge it
// into the ring and the face-flop placement keeps it at the input pins.
(* keep_hierarchy, keep *)
module ot_meso_face_ff_FW_OLD #(parameter integer W = 1) (
    input wire clk,
    input wire [W-1:0] d,
    (* keep *) output reg [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

// WREG-1 write-enable register of one (slot, 64-bit chunk) of ot_meso_ring_ca_FW_OLD: kept so the per-chunk copies (same D)
// are not merged back into one W x DEPTH broadcast.
// NEG = 1 (DIE-QC-70, WFALL ring): the flop captures on the falling edge of clk, the raw fclk.  A kept module cannot_FW_OLD
// absorb the wclk inverter as the slot flops do, so posedge ~fclk here left one inverter per ring on the clock path
// and the write enables on another clock net than the slots they enable.
(* keep_hierarchy, keep *)
module ot_meso_wen_ff_FW_OLD #(parameter bit NEG = 0) (
    input wire clk, d,
    (* keep *) output reg q
);
    generate if (NEG) begin : g_neg
        always @(negedge clk) q <= d;
    end else begin : g_pos
        always @(posedge clk) q <= d;
    end endgenerate
endmodule

// Dedicated same-state slot status bank. The canonical keep-register hook
// preserves these drivers and the explicitly kept original guard bank.
(* keep_hierarchy, keep *)
module ot_meso_ca_status_copy_FW_OLD #(parameter int DEPTH=4) (
    input logic tclk, t_rst_n,
    input logic [$clog2(DEPTH)-1:0] slot,
    input logic lap,
    (* keep *) output logic [DEPTH-1:0] written,
    (* keep *) output logic [DEPTH-1:0] lap_q
);
    always_ff @(posedge tclk) begin
        if (!t_rst_n) written <= '0;
        else written[slot] <= 1'b1;
        if (t_rst_n) lap_q[slot] <= lap;
`ifdef OT_MESO_CA_MUTANT_STATUS_COPY
        written[0] <= 1'b0; // control: omit one slot's written status
`endif
    end
endmodule

// HEAD raw-reset output: preserve the original wavefront state and provide a
// dedicated same-cycle output register. The pin copy samples the SAME D and
// clock; adding a flop after q would add an unpriced reset-release cycle.
(* keep_hierarchy, keep *)
module ot_dp_head_raw_export_pair_FW_OLD (
    input wire clk, d,
    (* keep *) output reg q,
    (* keep *) output reg export_q
);
    always @(posedge clk) begin
        q <= d;
`ifdef OT_HEAD_RAW_EXPORT_MUTANT_LATE
        export_q <= q;
`else
        export_q <= d;
`endif
    end
endmodule
