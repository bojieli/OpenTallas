// ot_ratio_cdc_fifo -- closable rational-ratio clock-domain crossing (successor of ot_chip_v41_ratio_fifo).
//
// Clocking contract (docs/ARCHITECTURE_ATLAS.html clock plan; results/physical_abi3/asap7/chip/v41_w18/
// clock_plan.json): one PLL per die, VCO 3.6 GHz, /3 -> 1.2 GHz streaming domain, /4 -> 0.9 GHz serial-chain
// domain.  The two clocks are therefore RELATED (frequency-locked, every edge on the 277.8 ps VCO grid), not
// asynchronous.  Because gcd(3,4) = 1, for ANY divider phase the set of fast->slow and slow->fast edge
// spacings is {0, 1, 2, 3, 4} VCO ticks: the tightest setup window is one tick (278 ps) and the hold window is
// the coincident edge.  STA with both clocks at phase 0 therefore times every divider phase.  No synchroniser,
// no Gray code and NO timing exception is used: every arc that crosses the domain boundary is a single
// flop -> flop wire with no logic, and STA times it at the 278 ps window (setup, SS, 60 ps) and at the
// coincident edge (hold, FF, 25 ps).  Crossings between dies (different PLLs) are NOT covered by this module.
//
// Why the predecessor failed: its reader selected mem[rp] through a DEPTH:1 mux straight from write-domain
// flops into r_d, so the 278 ps window carried clk->q + mux + setup (-75.59 ps at SS on 64 pins).  Here the
// read domain captures EVERY entry unconditionally into its own shadow register each read cycle (pure
// flop -> flop, the data analogue of the pointer crossing that closed at +32 ps); the read mux then works on
// read-domain flops only (a full read period).
//
// Coherence: an entry and the write pointer that publishes it are launched by the same write edge (entry first
// or same edge); any read edge strictly after that write edge captures both new values (setup met at 278 ps),
// a coincident read edge captures both old values (hold met).  So the shadow of an entry is valid at the very
// read edge whose pointer sample first shows it, and stays valid until the reader has retired it (the writer
// only rewrites a slot after the retiring read pointer has crossed back).
//
// Reset: wrst_n / rrst_n are SYNCHRONOUS to their own clock (per-domain reset synchronisers upstream), so the
// state/pointer flops that cross only ever change on a clock edge.  The FIFO is flushed as a whole.  Each side
// publishes its registered state (DOWN / WAIT / RUN, two flop bits that cross like the pointers):
//   * local reset -> DOWN: pointer cleared, no accept, no valid;
//   * DOWN -> WAIT after at least HOLD further own cycles AND after this side has seen the peer not in RUN
//     (a side whose own pointer is still live never lets the peer restart behind it);
//   * WAIT -> RUN when the peer is seen up (WAIT or RUN); pointers stay cleared until then;
//   * RUN  -> DOWN when the peer is seen DOWN (the peer's pointer was cleared at that same edge, and the
//     gating below already blocks valid/accept in the cycle the DOWN sample arrives).
// A side's DOWN lasts >= HOLD + 1 own cycles; (HOLD + 1) * T_own must exceed T_peer so the peer samples it
// (HOLD = 1 suffices for 3:4 in either direction; the default 2 keeps a cycle of margin and costs only reset
// recovery time, never data latency).  The bench's mutation runs show both the HOLD and the seen-not-RUN rule
// are necessary.  The reader never replays an old epoch's word, the writer never
// accepts while either side is in reset, words in flight at a reset are discarded by both sides, and every word
// accepted while both sides are live is delivered in order unless a later reset discards it.
//
// Latency (no backpressure, accept edge to consumer accept edge): one destination cycle plus the wait from the
// write edge to the next destination edge (1..4 VCO ticks): fast->slow 5..8 ticks = 1.25..2.00 slow cycles,
// slow->fast 4..6 ticks = 1.33..2.00 fast cycles.  tools/two_clock_crossing_model.py enumerates it and the
// dual-clock bench (rtl/test/two_clock) measures it.
module ot_ratio_cdc_fifo #(
    parameter int W     = 64,
    parameter int DEPTH = 4,            // entries, power of two
    parameter int HOLD  = 2             // extra DOWN cycles of each side; (HOLD + 1) * T_own must exceed T_peer
) (
    input  logic         wclk,
    input  logic         wrst_n,        // synchronous to wclk
    input  logic         w_v,
    output logic         w_rdy,
    input  logic [W-1:0] w_d,
    input  logic         rclk,
    input  logic         rrst_n,        // synchronous to rclk
    output logic         r_v,
    input  logic         r_rdy,
    output logic [W-1:0] r_d,
    output logic         w_live,        // write side in RUN with the reader seen up
    output logic         r_live         // read side in RUN with the writer seen up
);
    localparam int AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam int CW = $clog2(HOLD + 1);
    initial if (HOLD < 1 || DEPTH < 2 || (DEPTH & (DEPTH - 1)) != 0) $error("ot_ratio_cdc_fifo: HOLD >= 1, DEPTH a power of two >= 2");
    localparam logic [1:0] S_DOWN = 2'b00, S_WAIT = 2'b01, S_RUN = 2'b10;

    // ---------------- write domain ----------------
    logic [W-1:0]  mem [DEPTH];         // write-domain storage      (crosses: mem[i] -> sh[i])
    logic [AW:0]   wp;                  // write pointer             (crosses: wp -> wp_r)
    logic [1:0]    w_st;                // write-side state          (crosses: w_st -> w_st_r)
    logic [CW-1:0] w_cnt;
    logic          w_ok;                // reader seen not-RUN during this DOWN
    logic [AW:0]   rp_w;                // sampler of rp   (never reset: always a real sample)
    logic [1:0]    r_st_w;              // sampler of r_st
    logic          w_fire;
    logic [AW:0]   rp;
    logic [1:0]    r_st;

    always_ff @(posedge wclk) begin
        rp_w   <= rp;
        r_st_w <= r_st;
    end
    assign w_live = (w_st == S_RUN) && (r_st_w != S_DOWN);
    assign w_rdy  = wrst_n && w_live && ((wp - rp_w) != (AW+1)'(DEPTH));
    assign w_fire = w_v && w_rdy;
    always_ff @(posedge wclk) begin
        if (!wrst_n) begin
            w_st <= S_DOWN; w_cnt <= CW'(HOLD); w_ok <= 1'b0; wp <= '0;
        end else begin
            case (w_st)
                S_DOWN: begin
                    wp <= '0;
                    if (r_st_w != S_RUN) w_ok <= 1'b1;
                    if (w_cnt != '0) w_cnt <= w_cnt - 1'b1;
                    else if (w_ok || r_st_w != S_RUN) w_st <= S_WAIT;
                end
                S_WAIT: begin
                    wp <= '0;
                    if (r_st_w != S_DOWN) w_st <= S_RUN;
                end
                default: begin // S_RUN
                    if (r_st_w == S_DOWN) begin
                        w_st <= S_DOWN; w_cnt <= CW'(HOLD); w_ok <= 1'b1; wp <= '0;
                    end else if (w_fire) wp <= wp + 1'b1;
                end
            endcase
        end
    end
    always_ff @(posedge wclk) if (w_fire) mem[wp[AW-1:0]] <= w_d;

    // ---------------- read domain ----------------
    logic [W-1:0]  sh [DEPTH];          // read-domain shadow of every entry (flop -> flop, every cycle)
    logic [CW-1:0] r_cnt;
    logic          r_ok;
    logic [AW:0]   wp_r;                // sampler of wp
    logic [1:0]    w_st_r;              // sampler of w_st
    logic          r_take;

    always_ff @(posedge rclk) begin
        wp_r   <= wp;
        w_st_r <= w_st;
        for (int i = 0; i < DEPTH; i++) sh[i] <= mem[i];
    end
    assign r_live = (r_st == S_RUN) && (w_st_r != S_DOWN);
    assign r_v    = rrst_n && r_live && (wp_r != rp);
    assign r_d    = sh[rp[AW-1:0]];
    assign r_take = r_v && r_rdy;
    always_ff @(posedge rclk) begin
        if (!rrst_n) begin
            r_st <= S_DOWN; r_cnt <= CW'(HOLD); r_ok <= 1'b0; rp <= '0;
        end else begin
            case (r_st)
                S_DOWN: begin
                    rp <= '0;
                    if (w_st_r != S_RUN) r_ok <= 1'b1;
                    if (r_cnt != '0) r_cnt <= r_cnt - 1'b1;
                    else if (r_ok || w_st_r != S_RUN) r_st <= S_WAIT;
                end
                S_WAIT: begin
                    rp <= '0;
                    if (w_st_r != S_DOWN) r_st <= S_RUN;
                end
                default: begin // S_RUN
                    if (w_st_r == S_DOWN) begin
                        r_st <= S_DOWN; r_cnt <= CW'(HOLD); r_ok <= 1'b1; rp <= '0;
                    end else if (r_take) rp <= rp + 1'b1;
                end
            endcase
        end
    end
endmodule
