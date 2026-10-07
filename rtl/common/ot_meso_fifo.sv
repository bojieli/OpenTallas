// ot_meso_fifo -- same-frequency (mesochronous) clock-region crossing for the ROM-die clocking option C
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
//     after the peer was seen not RUN; in ALIGN, once the peer has been seen out of DOWN for SETTLE cycles,
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
module ot_meso_fifo #(
    parameter int W        = 512,
    parameter int DEPTH    = 4,      // ring slots, power of two
    parameter int OFFSET   = 2,      // placement lag window centre, periods (window OFFSET -+ 0.5)
    parameter int GUARD_LO = 0,      // low guard trips at lag < (GUARD_LO + 0.5) T
    parameter int GUARD_HI = 4,      // high guard trips at lag > (GUARD_HI - 0.5) T; <= DEPTH
    parameter int CREDITS  = 8,      // receive buffer entries = writer credits
    parameter int HOLD     = 8,      // DOWN lasts >= HOLD + 1 own cycles (peer must see it)
    parameter int SETTLE   = 8,      // cycles the peer ring is seen running before placement (>= DEPTH)
    parameter bit ENABLE   = 0,
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
`ifndef SYNTHESIS   // yosys derives the module once per chparam: an intermediate parameter set (GUARD_LO 1 with the
                    // default OFFSET 2) would trip the check; simulation still checks the final set
    initial begin
        if (OBYP && !(NOBP && RDREG)) $error("ot_meso_fifo: OBYP needs NOBP and RDREG");
        if (RSPLIT && !RDREG) $error("ot_meso_fifo: RSPLIT needs RDREG");
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $error("ot_meso_fifo: DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_LO + 2 > OFFSET || GUARD_HI < OFFSET + 2 || GUARD_HI > DEPTH)
            $error("ot_meso_fifo: need GUARD_LO+2 <= OFFSET, OFFSET+2 <= GUARD_HI <= DEPTH");
        if (SETTLE < DEPTH || HOLD < 6 || CREDITS < 1) $error("ot_meso_fifo: SETTLE >= DEPTH, HOLD >= 6, CREDITS >= 1");
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

        ot_meso_ring #(.W(W), .DEPTH(DEPTH), .OFFSET(OFFSET), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI)) u_data (
            .tclk(wclk), .t_v(w_send), .t_d(w_d_i),
            .rclk(rclk), .r_align(r_align), .r_on(r_on),
            .r_d(d_rd), .r_v(d_rv), .r_lap_ok(d_lap_ok), .r_glo_ok(d_glo), .r_ghi_ok(d_ghi)
`ifdef OT_MESO_DEBUG
           ,.dbg_tc(dbg_wc), .dbg_rp(dbg_rp)
`endif
        );
        ot_meso_ring #(.W(1), .DEPTH(DEPTH), .OFFSET(OFFSET), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI), .RDREG(CRDREG)) u_cred (
            .tclk(rclk), .t_v(c_pulse), .t_d(1'b1),
            .rclk(wclk), .r_align(w_align), .r_on(w_on),
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
        // between them, in a separately kept 2:1 select (ABC cannot fold c_hit back into the arithmetic)
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
        ot_meso_sel #(.N(BW)) u_wsel (.s(c_hit), .a(wcr_n1), .b(wcr_n0), .y(wcr_d));
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
                // guards are armed once the placed pointer's first guard samples have crossed (1 fall + 3 rise)
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
        assign r_v      = rrst_i && !r_flt && o_v;
        assign r_d      = o_d;
        assign r_take   = r_v && r_rdy;
        wire   load     = !o_v || r_rdy;
`ifndef SYNTHESIS
        if (NOBP) begin : g_nobp_check
            always @(posedge rclk) if (rrst_n && !r_rdy) $error("ot_meso_fifo NOBP: r_rdy low (no-backpressure invariant broken)");
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
        ot_meso_sel #(.N(RN)) u_rsel (.s(d_hit), .a(rn1), .b(rn0), .y(rnd));
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
// once from a synchronised Gray sample, with opposite-edge lap guards.
module ot_meso_ring #(
    parameter int W        = 1,
    parameter int DEPTH    = 4,
    parameter int OFFSET   = 2,
    parameter int GUARD_LO = 0,
    parameter int GUARD_HI = 4,
    parameter bit RDREG    = 0,      // readout flops: r_d / r_v / r_lap_ok captured at the consuming rclk edge (r_v,
                                     // r_lap_ok masked by r_on of that cycle), presented one period later
    parameter bit WCHK     = 0,      // chunked write (see ot_meso_fifo WCHK): ot_meso_wch per 64 bits
    parameter bit PLREG    = 0,      // placement value from a flop: rp_place = f(g3, n3) and g3 / n3 are plain copies of
                                     // g2 / n2 one edge later, so a flop loaded with f(g2, n2) holds exactly rp_place at
                                     // every edge (pure retiming, same cycles).  The pointer-decode logic (Gray ->
                                     // binary, add, late compare) then sits before that flop and the broadcast to the
                                     // DEPTH-slot selects of every 64-bit chunk starts at a register (mcast_r6 Q1:
                                     // g3 -> 4 levels -> 400 um of buffers -> dsel di, SS -95 ps).  The synchroniser
                                     // (async_reg g1 g2 / n0 n1 n2) is unchanged.
    parameter bit RSPLIT   = 0       // RDREG: two half-select readout flops per bit, ORed after them (ot_meso_dsel SPLIT)
) (
    input  logic         tclk,
    input  logic         t_v,
    input  logic [W-1:0] t_d,
    input  logic         rclk,
    input  logic         r_align,    // place the read pointer this cycle
    input  logic         r_on,       // pointer placed: advance every cycle
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
    always_ff @(posedge tclk) begin
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
            ot_meso_wch #(.W(WCW), .DEPTH(DEPTH)) u_wch (.clk(tclk), .nxt(nxt), .d(t_d[c*WCW +: WCW]), .sd(sd_c));
            for (genvar i = 0; i < DEPTH; i++) begin : sl
                assign s_d[i][c*WCW +: WCW] = sd_c[i*WCW +: WCW];
            end
        end
    end else begin : g_wone
        always_ff @(posedge tclk) if (t_v) s_d[tc[AW-1:0]] <= t_d;
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
        // retiming proof in every bench: the flop equals the combinational placement at every edge once g/n are
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
        ot_meso_dsel #(.W(WCH), .DEPTH(DEPTH), .REG(RDREG), .SPLIT(RSPLIT)) u_dsel (.clk(rclk), .align(r_align), .on(r_on),
                                                      .place(rp_place[AW-1:0]), .sd(sd_c), .y(r_d[c*WCH +: WCH]));
    end
    logic r_v_c, r_lap_c;
    ot_meso_ohor #(.N(NS)) u_v   (.sel(oh), .x(pos_v),   .y(r_v_c));
    ot_meso_ohor #(.N(NS)) u_lap (.sel(oh), .x(pos_lap), .y(r_lap_c));
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
// (ot_meso_sel) after a two-level AND-OR (ot_meso_ohor) and cannot be folded back into next-state arithmetic.
(* keep_hierarchy *)
module ot_meso_sel #(parameter int N = 1) (
    input  logic         s,
    input  logic [N-1:0] a,
    input  logic [N-1:0] b,
    output logic [N-1:0] y
);
    assign y = s ? a : b;
endmodule

(* keep_hierarchy *)
module ot_meso_ohor #(parameter int N = 2) (
    input  logic [N-1:0] sel,
    input  logic [N-1:0] x,
    output logic         y
);
    assign y = |(sel & x);
endmodule

// One chunk of the data-ring read: its own one-hot copy of the slot index (placed and advanced with rp), then a
// one-hot AND-OR of the DEPTH slots.  Kept hierarchy keeps the replicated index registers from being merged.
(* keep_hierarchy *)
module ot_meso_dsel #(parameter int W = 64, parameter int DEPTH = 4, parameter bit REG = 0, parameter bit SPLIT = 0) (
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
    always_comb begin
        y_c = '0;
        for (int i = 0; i < DEPTH; i++) y_c = y_c | (sd[i*W +: W] & {W{di[i]}});
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
module ot_meso_wch #(parameter int W = 64, parameter int DEPTH = 4) (
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
