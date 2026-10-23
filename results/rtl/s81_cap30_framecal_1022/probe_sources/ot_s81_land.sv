`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-LAND (2026-10-17, coordinator decision HANDOFF 0dm): the LANDING of a forwarded-clock die lane into a block.
// Contract: /home/ubuntu/claude-takeover-20261007/lanes/LANDING-CONTRACT.md (summary in results/arch/s81_dv_1016/landing/audit.json).
//
// The lane arrives on its own forwarded clock ck_f (the last relay station's ck_o, ~+115 ps per hop behind the source
// root); the block runs on its regional root ck.  Same frequency, unknown-but-FIXED phase dL = L(ck_f) - L(ck), which
// may exceed a period on a long lane and moves with corner / temperature.  The landing:
//   1. CAPTURE on ck_f: every ck_f edge writes the lane word into ring slot wc mod D (the slots ARE the capture flops:
//      flop-first, one hop like a relay stage; no pin register in front).  Bubbles are written too.
//   2. HANDOFF on ck: every ck edge after warm-up reads slot (rc - K) mod D into the registered output o (flop-last).
// No ready, no occupancy, no credit, no training: both pointers free-run from their epochs.
//
// Epochs (static calendar, compile-time):
//   * write epoch: wc counts ck_f edges from the FIRST one.  The lane's forwarded clock is started by the source: the
//     hop-0 forward cell is a clock gate opened at source edge G by the source's released reset (die netlist), so ck_f
//     edge 0 at the landing is source edge G whatever dL is.  wc is cleared asynchronously by rs while ck_f is
//     stopped (calendar: the block's reset releases at or before G), so no edge can race the release.
//   * read epoch:  rc counts ck edges from the release of rs (the block's regional synchronous reset, released on ck at
//     the region's calendar edge R0).
//   => o after ck edge m = the word written at ck_f edge m - R0 - K + G (K = strap k).  With E = K + R0 - G the compile-time latency
//      from the last relay station to o is E + 1 edges, INDEPENDENT of dL, provided
//          (E - D) * T + t_hold  <  dL  <  E * T - t_cq - t_setup                                     (window)
//      i.e. a D x T wide window (D = 4: ~3.0 ns at 833 ps).  The die STA checks it as the bank -> o path with
//      set_multicycle_path -setup E -hold (D - 1) at TT and FF with ONE E per lane.
// Fault (assertion only, never changes the calendar): every slot stores its write epoch wc; after warm-up the read slot's
// epoch must equal rc - K.  A slipped calendar (gate opened on the wrong edge, window violated, clock glitch) sets fault.
// Area: D x W slot flops + W output flops + 2 x (AW+1) pointer + D x (AW+1) epoch flops.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_land #(
    parameter integer W  = 276,
    parameter integer D  = 4,       // ring depth (power of two, >= 2): window width in periods
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer KW = AW + 1   // LANDFIX-SQ (10-18): strap width.  KW = AW + 1 (default) = the original tiles
                                    // (1 <= K <= 2D-1).  A long lane (E > 2D-1, e.g. the 24-mm S81 host plane, E 28)
                                    // takes KW > AW + 1: the slot / epoch arithmetic stays mod 2D (2^KW is a multiple
                                    // of 2D), only the warm-up count uses the full K, so K = E + G - R0 needs no
                                    // reset-calendar offset between the source gate G and the receiver release R0.
) (
    input  wire [KW-1:0] k,         // read offset K: identity STRAP (die tie, compile-time per lane from the die STA dL
                                    // at TT and FF; 1 <= K <= 2^KW-1); case-analysed in the tile and die STA
    input  wire         ck_f,       // lane forwarded clock (last station ck_o)
    input  wire [W-1:0] i,          // lane data (last station o)
    input  wire         ck,         // block root clock
    input  wire         rs,         // block regional reset, active low (asynchronous assert, release synchronous on ck)
    output reg  [W-1:0] o,
    output reg          fault
);
    reg [W-1:0]  bank [0:D-1];
    reg [AW:0]   epo  [0:D-1];
    reg [AW:0]   wc;
    reg [KW-1:0] rc;                // read counter: low AW+1 bits = the read epoch; full width = the warm-up count
    reg          warm;
    // ------------------------------------------------------------------ write side (ck_f)
    always @(posedge ck_f or negedge rs)
        if (!rs) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    genvar s;
    generate for (s = 0; s < D; s = s + 1) begin : g_slot
        always @(posedge ck_f)
            if (wc[AW-1:0] == s) begin bank[s] <= i; epo[s] <= wc; end   // no rs term: rs is a ck-domain net
    end endgenerate
    // ------------------------------------------------------------------ read side (ck)
`ifdef OT_S81_LAND_MUT_SEL
    wire [KW-1:0] expw = rc - k + 1'b1;        // bench mutant: read slot one late
`else
    wire [KW-1:0] expw = rc - k;
`endif
    wire [AW:0] exp_ = expw[AW:0];
    always @(posedge ck or negedge rs)
        if (!rs) begin rc <= {KW{1'b0}}; warm <= 1'b0; fault <= 1'b0; end
        else begin
            rc <= rc + 1'b1;
            if (rc == k - 1'b1) warm <= 1'b1;
            if (warm && epo[exp_[AW-1:0]] != exp_) fault <= 1'b1;
        end
`ifdef OT_S81_LAND_MUT_NAIVE
    // bench mutant: bounded-skew retime register only (no ring): o samples the lane directly on ck
    always @(posedge ck) o <= warm ? i : {W{1'b0}};
`else
    always @(posedge ck) o <= warm ? bank[exp_[AW-1:0]] : {W{1'b0}};
`endif
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "ot_s81_land: D must be a power of two >= 2");
    initial if (KW < AW + 1) $fatal(1, "ot_s81_land: KW must be >= AW + 1");
    always @(posedge ck) if (warm && (k == 0)) $fatal(1, "ot_s81_land: strap k must be >= 1");
`endif
endmodule
`default_nettype wire
