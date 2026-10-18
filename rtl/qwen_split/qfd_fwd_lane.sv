`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Q-DIE11-RLY (2026-10-18, coordinator decision HANDOFF 0ea item 1): FORWARDED-CLOCK HALF-CYCLE LANES + LANDINGS for the
// Qwen split compute die (contract /home/ubuntu/claude-takeover-20261007/lanes/LANDING-CONTRACT.md sections 2, 3, 6, 7).
// The die generator (tools/qwen_rom_fulldie_b3r2.py, OT_SPLIT_FWD_LANES=1) turns every relay chain of n >= 1 frames into
//   frame 0          hop-0 station (ot_qfd_lane_st FIRST=1): the hop-0 forward cell is an INVERTING clock gate on the
//                    SOURCE block's root (cko = ~ck, opened by the source's released reset en), so station 0 captures half
//                    a period after the source launches (t_data,min - t_cko,max >= 0 by construction: the gate inverts)
//   frames 1..n-2    half-cycle stations (ot_qfd_lane_st FIRST=0): capture on ckf (previous ck_o), ck_o = ~ckf through
//                    ONE kept inverter (S81-LAND2 hold fix (a), dsfd_dvrlyh_* form)
//   frame n-1        the LANDING (ot_qfd_land): its ring slots ARE the last capture (flop-first, written on the lane's
//                    forwarded clock), read on the RECEIVING block's root ck at slot (rc - K) mod D into o (flop-last),
//                    o -> the block input is one single-cycle hop on the block root (landing within one reach of the pin).
//                    n = 1: the landing carries the hop-0 gate itself (ot_qfd_land FIRST=1).
// No ready, no credit, no occupancy, no training (owner static-schedule rule 10-14): both pointers free-run.
//
// WRITE EPOCH (contract L3, in-band form): every station also carries the lane EPOCH bit e = the source's released reset.
//   It is a reset-repeater bit (asynchronous clear, release on the station's capture clock): at power-on the source
//   reset clears it along the whole lane at once, with every clock stopped; after the source releases (edge G) the
//   gate opens and the 1 walks one station per forwarded edge, so the landing's write counter wc leaves its clear on a
//   FIXED forwarded edge (G + n half-periods) whatever the lane delay dL.  The write epoch therefore depends on the
//   source reset only; the receiver's reset may release before OR after G (the Qwen reset trees are equal-depth per
//   domain with different depths, rst_field 404 vs rst_seq 22 cycles): no reset-ordering constraint.
// READ EPOCH: rc counts ck edges from the release of rs (receiving block's regional reset, released on ck).
// K (strap k2..k0, tied by the die from the instance's OWN tie_hi / tie_lo, never a netlist literal): K = (E + G - R0)
//   mod 2D, 0 meaning 2D (both counters are AW+1 = 3 bits wide; ot_s81_land requires 1 <= K <= 7 and G >= R0).
// FAULT (assertion only, L6): every slot stores its write epoch and a written flag (cleared with the lane epoch); after
//   warm-up a WRITTEN read slot whose epoch is not rc - K sets the sticky fault.  Slots never written read as 0 bubbles.
// Differences to ot_s81_land (rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv): write side cleared by the in-band lane epoch
//   instead of the block reset (no G >= R0 calendar condition), per-slot written flag (no false fault while the source
//   is still in reset), K mod 2D.  Bench: tools/qwen_split/bench_fwd_lane.sh (pass + 4 mutants).
// ---------------------------------------------------------------------------------------------------------------------

// one kept inverter cell (the ck -> ck_o forward of a half-cycle station; flattened, yosys would fold it into a wire)
(* keep_hierarchy *)
module ot_qfd_ckinv (input wire a, output wire y);
    assign y = ~a;
endmodule

// hop-0 forward cell: INVERTING integrated clock gate on the source root.  cko = ~ck while en (latched while ~ck is low,
// i.e. while ck is high) is 1.  en is the source's released reset (synchronous to ck): it rises after source edge G, the
// latch takes it while ck is high, and the first cko rising edge is ck's falling edge G + T/2.
module ot_qfd_fwd0 (input wire ck, input wire en, output wire cko);
    wire ckn;
    ot_qfd_ckinv u_inv (.a(ck), .y(ckn));
`ifdef OT_QFD_LANE_MUT_NOINV
    ot_hdc_cg u_cg (.clk(ck), .en(en), .gclk(cko));            // bench mutant: non-inverting hop-0 (full-cycle hop 0)
`else
    ot_hdc_cg u_cg (.clk(ckn), .en(en), .gclk(cko));
`endif
endmodule

// half-cycle lane station: one register stage of the W data bits + the epoch bit, captured on cap, ck_o = ~cap.
//   FIRST = 1: cap = ot_qfd_fwd0(ck = source root, en); the epoch input is en itself.
//   FIRST = 0: cap = ckf (previous station ck_o); the epoch input is ea.
module ot_qfd_lane_st #(parameter integer W = 16, parameter integer FIRST = 0) (
    input  wire         ck,          // FIRST: source block root;  else: the lane's forwarded clock
    input  wire         en,          // FIRST: source released reset (gate enable + epoch);  else: lane epoch in (ea)
    input  wire [W-1:0] a,
    output reg  [W-1:0] b,
    output reg          eb,          // lane epoch out
    output wire         ck_o
);
    wire cap;
    generate if (FIRST != 0) begin : g_hop0
        ot_qfd_fwd0 u_fwd0 (.ck(ck), .en(en), .cko(cap));
    end else begin : g_st
        assign cap = ck;
    end endgenerate
    always @(posedge cap) b <= a;                                // data: no reset (flushed by the producer, as qfd_rly_*)
    always @(posedge cap or negedge en)                          // epoch: async clear, release on the capture clock
        if (!en) eb <= 1'b0; else eb <= 1'b1;
`ifdef OT_QFD_LANE_MUT_FULL
    wire ckn, ckp;                                               // bench mutant: non-inverting forward (full-cycle hops)
    ot_qfd_ckinv u_ck0 (.a(cap), .y(ckn));
    ot_qfd_ckinv u_ck1 (.a(ckn), .y(ckp));
    assign ck_o = ckp;
`else
    ot_qfd_ckinv u_ck0 (.a(cap), .y(ck_o));
`endif
endmodule

// landing (contract L1-L7, in-band write epoch): ring of D slots written on the lane clock, read on the block root.
module ot_qfd_land #(
    parameter integer W     = 16,
    parameter integer D     = 4,                       // ring depth, power of two >= 2 (window D x T)
    parameter integer FIRST = 0,                       // 1: n = 1 lane, the landing carries the hop-0 gate (ck_s, en)
    parameter integer AW    = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire         ckf,      // FIRST 0: lane forwarded clock (last station ck_o); FIRST 1: source block root
    input  wire         ea,       // FIRST 0: lane epoch (last station eb); FIRST 1: source released reset
    input  wire [W-1:0] i,
    input  wire         ck,       // receiving block root
    input  wire         rs,       // receiving block regional reset, active low (async assert, release on ck)
    input  wire [AW:0]  k,        // K strap (identity strap from the instance's own tie cells)
    output reg  [W-1:0] o,
    output reg          fault
);
    wire wck, we;                 // ring write clock / write-side epoch
    generate if (FIRST != 0) begin : g_hop0
        ot_qfd_fwd0 u_fwd0 (.ck(ckf), .en(ea), .cko(wck));
        assign we = ea;           // en rises after source edge G, half a period before the first gated edge
    end else begin : g_lane
        assign wck = ckf;
        assign we = ea;
    end endgenerate
    reg [W-1:0] bank [0:D-1];
    reg [AW:0]  epo  [0:D-1];
    wire [D-1:0] vld;
    reg [AW:0]  wc, rc;
    reg         warm;
    // ------------------------------------------------------------------ write side (wck), cleared by the lane epoch
    always @(posedge wck or negedge we)
        if (!we) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    genvar s;
    generate for (s = 0; s < D; s = s + 1) begin : g_slot
        always @(posedge wck) if (wc[AW-1:0] == s) begin bank[s] <= i; epo[s] <= wc; end
        reg v;                                                     // slot written since the lane epoch began
        always @(posedge wck or negedge we)
            if (!we) v <= 1'b0;
`ifdef OT_QFD_LAND_MUT_VLD
            else v <= 1'b1;                                        // bench mutant: every slot valid at once
`else
            else if (wc[AW-1:0] == s) v <= 1'b1;
`endif
        assign vld[s] = v;
    end endgenerate
    // ------------------------------------------------------------------ read side (ck)
`ifdef OT_QFD_LAND_MUT_SEL
    wire [AW:0] exp_ = rc - k + 1'b1;                              // bench mutant: read slot one late
`else
    wire [AW:0] exp_ = rc - k;
`endif
    wire [AW-1:0] rs_ = exp_[AW-1:0];
    always @(posedge ck or negedge rs)
        if (!rs) begin rc <= {(AW + 1){1'b0}}; warm <= 1'b0; fault <= 1'b0; end
        else begin
            rc <= rc + 1'b1;
            if (rc == k - 1'b1) warm <= 1'b1;
            if (warm && vld[rs_] && epo[rs_] != exp_) fault <= 1'b1;
        end
`ifdef OT_QFD_LAND_MUT_NAIVE
    always @(posedge ck) o <= warm ? i : {W{1'b0}};                // bench mutant: retime register only, no ring
`else
    always @(posedge ck) o <= (warm && vld[rs_]) ? bank[rs_] : {W{1'b0}};
`endif
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "ot_qfd_land: D must be a power of two >= 2");
`endif
endmodule
`default_nettype wire
