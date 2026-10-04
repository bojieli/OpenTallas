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
//   * Placement.  Once, at alignment, the reader takes a 3-FF-synchronised sample of the Gray copy of wc and sets
//     its read pointer so that slot k is consumed at the read edge OFFSET..OFFSET+1 periods after it was written:
//     rp <= sample + SYNC + 1 - OFFSET.  A metastable sample resolves to one of two adjacent values, and each of
//     them yields a lag inside [OFFSET*T, (OFFSET+1)*T] for its own phase interpretation, so every static phase
//     0..360 deg is placed with lag in that one-period window.  After that the pointer simply increments.
//   * Phase-window guards (fail closed).  Each cycle, on the OPPOSITE (falling) read edge, the reader samples the
//     lap bit of two guard slots: slot rp+GUARD_LO half a period BEFORE its consuming edge (trips when the lag
//     falls below (GUARD_LO+0.5)*T) and slot rp-1+GUARD_HI half a period AFTER (trips when the lag exceeds
//     (GUARD_HI-0.5)*T).  The samples cross through 1 falling + 3 rising flops (they may be metastable exactly
//     when a guard is reached), and a trip sets a sticky fault that stops delivery and credit.  The data path is
//     STA-bounded (set_max_delay -ignore_clock_latency) to (GUARD_LO+0.5)*T - uncertainty, so the guard trips
//     before any data arc can leave its window; the slot under consumption is rewritten DEPTH periods later.
//     Static window: OFFSET*T-w .. (OFFSET+1)*T+w must lie inside the guards: w < 0.5 T at DEPTH 4 (central).
//   * Lap check.  The consumed slot's lap bit must equal rp[AW]; a mismatch is a gross slip and also faults.
//   * Credits.  The reader holds a CREDITS-entry elastic buffer (fall-through: an arriving word goes straight to
//     r_d when the buffer is empty).  Each word the consumer takes returns one credit through a second, 1-bit
//     ring of the same kind (rclk -> wclk) with its own placement and guards; the writer sends only on a credit.
//     CREDITS >= the credit round trip (about 6 cycles at OFFSET 1) sustains one word a cycle.
//   * Reset handshake (as ot_ratio_cdc_fifo, plus an alignment step): each side publishes DOWN/ALIGN/READY/RUN
//     (Gray-sequenced, crossing through 3 FFs plus a stable-compare flop).  DOWN -> ALIGN after HOLD own cycles and
//     after the peer was seen not RUN; in ALIGN, once the peer has been seen out of DOWN for SETTLE cycles,
//     this side places its RX pointer -> READY; READY -> RUN when the peer is seen
//     READY or RUN (the writer then loads CREDITS).  Seeing the peer DOWN from READY/RUN returns to DOWN; words in
//     flight across a reset are discarded by both sides.  The fault is sticky until the local reset.
//
// Latency, no backpressure: a word written at write edge n is presented on r_d from the read edge at lag
// OFFSET*T - T .. OFFSET*T and is taken by a consumer register at lag OFFSET*T .. (OFFSET+1)*T, against T for the
// synchronous register stage it replaces: DELTA = OFFSET*T + phase, i.e. at most OFFSET cycles (1 at DEPTH 4).
// The dual-clock bench rtl/test/meso/tb_meso_fifo.cpp measures it.
//
// Default-off: ENABLE = 0 elaborates to tied-off outputs.
module ot_meso_fifo #(
    parameter int W        = 512,
    parameter int DEPTH    = 4,      // ring slots, power of two
    parameter int OFFSET   = 1,      // placement lag in periods
    parameter int GUARD_LO = 0,      // low guard trips at lag < (GUARD_LO + 0.5) T
    parameter int GUARD_HI = 3,      // high guard trips at lag > (GUARD_HI - 0.5) T
    parameter int CREDITS  = 8,      // receive buffer entries = writer credits
    parameter int HOLD     = 8,      // DOWN lasts >= HOLD + 1 own cycles (peer must see it)
    parameter int SETTLE   = 8,      // cycles the peer ring is seen running before placement (>= DEPTH)
    parameter bit ENABLE   = 0
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
    initial begin
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $error("ot_meso_fifo: DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_LO + 1 > OFFSET || GUARD_HI < OFFSET + 2 || GUARD_HI > DEPTH - 1)
            $error("ot_meso_fifo: need GUARD_LO+1 <= OFFSET, OFFSET+2 <= GUARD_HI <= DEPTH-1");
        if (SETTLE < DEPTH || HOLD < 6 || CREDITS < 1) $error("ot_meso_fifo: SETTLE >= DEPTH, HOLD >= 6, CREDITS >= 1");
    end

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
        localparam int BW = $clog2(CREDITS + 1);
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
            .tclk(wclk), .t_v(w_send), .t_d(w_d),
            .rclk(rclk), .r_align(r_align), .r_on(r_on),
            .r_d(d_rd), .r_v(d_rv), .r_lap_ok(d_lap_ok), .r_glo_ok(d_glo), .r_ghi_ok(d_ghi)
`ifdef OT_MESO_DEBUG
           ,.dbg_tc(dbg_wc), .dbg_rp(dbg_rp)
`endif
        );
        ot_meso_ring #(.W(1), .DEPTH(DEPTH), .OFFSET(OFFSET), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI)) u_cred (
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
        assign w_rdy    = wrst_n && (ws == S_RUN) && !w_flt && (w_cred != '0);
        assign w_send   = w_v && w_rdy;
        assign w_fault  = w_flt;
        assign w_align  = (ws == S_ALIGN) && (w_set == SW'(SETTLE));
        wire   c_in     = w_on && c_rv && c_lap_ok;    // a returned credit
        always_ff @(posedge wclk) begin
            if (!wrst_n) begin
                ws <= S_DOWN; w_cnt <= HW'(HOLD); w_ok <= 1'b0; w_set <= '0; w_cred <= '0; w_flt <= 1'b0; w_arm <= '0;
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
                            ws <= S_DOWN; w_cnt <= HW'(HOLD); w_ok <= 1'b1; w_cred <= '0;
                        end else if (ws == S_READY) begin
                            if (rs_w == S_READY || rs_w == S_RUN) begin ws <= S_RUN; w_cred <= BW'(CREDITS); end
                        end else begin
                            w_cred <= w_cred - BW'(w_send) + BW'(c_in);
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
        wire   d_in     = r_on && !r_flt && d_rv && d_lap_ok;   // a word arrives (crosses: d_rv, d_lap_ok)
        wire   empty    = (cnt == '0);
        assign r_v      = rrst_n && !r_flt && (!empty || d_in);
        assign r_d      = empty ? d_rd : buf_d[hd];
        assign r_take   = r_v && r_rdy;
        wire   push     = d_in && !(empty && r_rdy);
`ifdef OT_MESO_MUTANT_EARLY_CREDIT
        assign c_pulse  = d_in;              // MUTANT: credit on arrival instead of consumption
`else
        assign c_pulse  = r_take;            // one credit per word the consumer takes
`endif
        wire   pop      = !empty && r_rdy;
        // written every cycle unless full (read-domain condition only; no crossing signal in the enable); tl
        // advances only on push, so a non-push cycle just rewrites the free slot
        always_ff @(posedge rclk) if (cnt != BW'(CREDITS)) buf_d[tl] <= d_rd;
        always_ff @(posedge rclk) begin
            if (!rrst_n) begin
                rs <= S_DOWN; r_cnt <= HW'(HOLD); r_ok <= 1'b0; r_set <= '0; r_flt <= 1'b0; r_arm <= '0;
                hd <= '0; tl <= '0; cnt <= '0;
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
                if (!r_on) begin
                    hd <= '0; tl <= '0; cnt <= '0;
                end else begin
                    if (push) tl <= (tl == IW'(CREDITS - 1)) ? '0 : tl + 1'b1;
                    if (pop)  hd <= (hd == IW'(CREDITS - 1)) ? '0 : hd + 1'b1;
                    cnt <= cnt + BW'(push) - BW'(pop);
                end
                if (!r_on) r_arm <= '0; else if (r_arm != 3'd5) r_arm <= r_arm + 1'b1;
                if (r_on && ((r_arm == 3'd5 && (!d_glo || !d_ghi)) || !d_lap_ok ||
                             (push && cnt == BW'(CREDITS) && !pop))) r_flt <= 1'b1;
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
    parameter int OFFSET   = 1,
    parameter int GUARD_LO = 0,
    parameter int GUARD_HI = 3
) (
    input  logic         tclk,
    input  logic         t_v,
    input  logic [W-1:0] t_d,
    input  logic         rclk,
    input  logic         r_align,    // place the read pointer this cycle
    input  logic         r_on,       // pointer placed: advance every cycle
    output logic [W-1:0] r_d,
    output logic         r_v,
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
    logic [DEPTH-1:0] s_v, s_lap;
    // Free-running, never reset: a local reset of either side must not stop or restart the ring under a placed
    // reader (that would be a slot slip, which the lap check rightly treats as a fault).  Power-up value is arbitrary.
    always_ff @(posedge tclk) begin
        s_v[tc[AW-1:0]]   <= t_v;
        s_lap[tc[AW-1:0]] <= tc[AW];
        tg <= tc ^ (tc >> 1);                    // Gray of the index written at this edge
        tc <= tc + 1'b1;
    end
    always_ff @(posedge tclk) if (t_v) s_d[tc[AW-1:0]] <= t_d;

    // ---------------- receive (rclk) ----------------
    (* async_reg = "true" *) logic [PW-1:0] g1, g2, g3;
    always_ff @(posedge rclk) begin g1 <= tg; g2 <= g1; g3 <= g2; end
    logic [PW-1:0] gb;
    always_comb begin
        gb[PW-1] = g3[PW-1];
        for (int i = PW - 2; i >= 0; i--) gb[i] = gb[i+1] ^ g3[i];
    end
    logic [PW-1:0] rp;
`ifdef OT_MESO_MUTANT_OFFSET
    localparam int PLACE = SYNC + 1 - OFFSET + 1;   // MUTANT: one period early (lag 0..T)
`else
    localparam int PLACE = SYNC + 1 - OFFSET;
`endif
    always_ff @(posedge rclk) begin
        if (r_align) rp <= gb + PW'(PLACE);
        else if (r_on) rp <= rp + 1'b1;
    end
    wire [AW-1:0] ri = rp[AW-1:0];
    assign r_d      = s_d[ri];
    assign r_v      = s_v[ri];
    assign r_lap_ok = (s_lap[ri] == rp[PW-1]);

    // guards on the falling read edge, then 3 rising flops
    wire [PW-1:0] q_lo = rp + PW'(GUARD_LO);            // consumed at the next rising edge + GUARD_LO
    wire [PW-1:0] q_hi = rp - 1'b1 + PW'(GUARD_HI);      // rp-1 was consumed at the last rising edge
    (* async_reg = "true" *) logic glo0, ghi0;
    (* async_reg = "true" *) logic glo1, glo2, ghi1, ghi2;
    logic glo3, ghi3;
    always_ff @(negedge rclk) begin
        glo0 <= (s_lap[q_lo[AW-1:0]] == q_lo[PW-1]);   // written in this lap
        ghi0 <= (s_lap[q_hi[AW-1:0]] != q_hi[PW-1]);   // not yet written in this lap
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
