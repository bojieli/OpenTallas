`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Q-DIE11-RLY (2026-10-18, coordinator decision HANDOFF 0ea item 1): FORWARDED-CLOCK HALF-CYCLE LANES + LANDINGS for the
// Qwen split compute die (contract /home/ubuntu/claude-takeover-20261007/lanes/LANDING-CONTRACT.md sections 2, 3, 6, 7).
// The die generator (tools/qwen_rom_fulldie_b3r2.py, OT_SPLIT_FWD_LANES=1) turns every relay chain of n >= 1 frames into
//   frame 0          hop-0 station (ot_qfd_lane_st FIRST=1): the hop-0 forward cell is a clock gate on the SOURCE
//                    block's root (cko = ck, opened by the source's released reset en): station 0 captures one period
//                    after the source launches (an ordinary root -> root hop); its ck_o = ~cko starts the half-cycle hops
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

// hop-0 forward cell: integrated clock gate on the source root, cko = ck while en is 1.  en is the source's released reset
// (synchronous to ck): it rises after source edge G, and the first cko rising edge is source edge G + 1.
// Q-DIE11 10-18 (kit fix, coordinator): hop 0 captures on the RISING source-root edge (a full-cycle root -> root hop, one
// ordinary tile IO budget, as the S81 dsfd_dvrlyh kits); the station's ck_o = ~cko (one kept inverter) makes every later
// hop half-cycle.  The first form captured hop 0 on the FALLING edge (~ck gate): its tile could not be budgeted (no
// rise -> rise clock latency: link_budget 'no measured clock' crash; half-period input window).  Cost: + T/2 per lane.
module ot_qfd_fwd0 (input wire ck, input wire en, output wire cko);
`ifdef OT_QFD_LANE_MUT_HOP0INV
    wire ckn;                                                  // bench mutant: the first form (inverting hop-0 gate)
    ot_qfd_ckinv u_inv (.a(ck), .y(ckn));
    ot_hdc_cg u_cg (.clk(ckn), .en(en), .gclk(cko));
`else
    ot_hdc_cg u_cg (.clk(ck), .en(en), .gclk(cko));
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

// QK-LAND600B 10-18 (variant B, coordinator): REGISTERED ONE-HOT WRITE SELECT, one copy per ~WSELB data bits.
// The original ring decodes wc[AW-1:0] == s for every slot and fans that decode out to all W enables of the slot (600 b:
// wc -> ~500 ps buffer tree -> bank/D, -72.6 ps @770 placed).  Variant B holds onehot(wc[1:0]) in registers that load
// onehot of wc's NEXT state (wc + 1) on the same wck edge as wc, and are cleared to onehot(0) with wc by the lane epoch:
// so ws == onehot(wc[1:0]) on every cycle (same write slot on the same edge; landing latency unchanged).  One copy per
// WSELB bits (600 b: 4 copies x 4 slots = 16 flops); each copy is its own NON-parameterised keep_hierarchy module
// (ot_qfd_wsel4: synthesis cannot merge the copies back, and SYNTH_KEEP_MODULES matches its post-synthesis name).
// Slot 0's bit is stored inverted (async CLEAR only, the same cell class as wc).
(* keep_hierarchy *)
module ot_qfd_wsel4 (
    input  wire       wck,
    input  wire       we,         // lane epoch, active low clear
    input  wire [1:0] wn,         // wc[1:0] + 1 (the counter's next state while we = 1)
    output wire [3:0] ws          // onehot(wc[1:0])
);
    (* keep *) reg [3:0] q;       // q[0] = ~ws[0]; q[3:1] = ws[3:1]
    always @(posedge wck or negedge we)
        if (!we) q <= 4'b0000;
        else     q <= {wn == 2'd3, wn == 2'd2, wn == 2'd1, wn != 2'd0};
    assign ws = {q[3:1], ~q[0]};
endmodule

// landing (contract L1-L7, in-band write epoch): ring of D slots written on the lane clock, read on the block root.
module ot_qfd_land #(
    parameter integer W     = 16,
    parameter integer D     = 4,                       // ring depth, power of two >= 2 (window D x T)
    parameter integer FIRST = 0,                       // 1: n = 1 lane, the landing carries the hop-0 gate (ck_s, en)
    parameter integer AW    = (D <= 2) ? 1 : $clog2(D),
`ifdef OT_QFD_LAND_WSEL_REG
    parameter integer WSEL  = 1,                       // QK-LAND600B: 1 = registered one-hot write select copies (D 4)
`else
    parameter integer WSEL  = 0,                       // 0 = combinational wc decode (the original landing)
`endif
    parameter integer WSELB = 150                      // data bits per write-select copy (WSEL 1)
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
    reg [W-1:0] bank [0:D-1];     // WSEL 0 ring data
    wire [D*W-1:0] rd;            // WSEL 1 ring data, slot s at [s*W +: W] (per-slot registers, no array)
    reg [AW:0]  epo  [0:D-1];
    wire [D-1:0] vld;
    reg [AW:0]  wc, rc;
    reg         warm;
    // ------------------------------------------------------------------ write side (wck), cleared by the lane epoch
    always @(posedge wck or negedge we)
        if (!we) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    genvar s;
    localparam integer NC = (W + WSELB - 1) / WSELB;               // write-select copies (WSEL 1)
    wire [D-1:0] wsl;                                              // slot select of the epoch / valid bookkeeping
    generate if (WSEL != 0) begin : g_wsel
        wire [D*NC-1:0] wsc;                                       // copy c, slot s at [c*D + s]
        wire [AW:0] wnx = wc + 1'b1;
        genvar c;
        for (c = 0; c < NC; c = c + 1) begin : g_cp
`ifdef OT_QFD_LAND_MUT_WSEL
            // bench mutant: the copies load the CURRENT count (select one slot late), as a copy registered from wc
            ot_qfd_wsel4 u_ws (.wck(wck), .we(we), .wn(wc[1:0]), .ws(wsc[c*D +: D]));
`else
            ot_qfd_wsel4 u_ws (.wck(wck), .we(we), .wn(wnx[1:0]), .ws(wsc[c*D +: D]));
`endif
        end
        for (s = 0; s < D; s = s + 1) begin : g_slotb
            for (c = 0; c < NC; c = c + 1) begin : g_ch
                localparam integer LO = c * WSELB;
                localparam integer N  = (W - LO < WSELB) ? (W - LO) : WSELB;
                reg [N-1:0] bk;
                always @(posedge wck) if (wsc[c*D + s]) bk <= i[LO +: N];
                assign rd[s*W + LO +: N] = bk;
            end
            assign wsl[s] = wsc[s];                                // copy 0 also selects the epoch / valid flags
        end
`ifndef SYNTHESIS
        initial if (D != 4) $fatal(1, "ot_qfd_land: WSEL 1 needs D = 4 (ot_qfd_wsel4)");
`endif
    end else begin : g_wdec
        for (s = 0; s < D; s = s + 1) begin : g_slotd
            assign wsl[s] = (wc[AW-1:0] == s);
            always @(posedge wck) if (wsl[s]) bank[s] <= i;
        end
    end endgenerate
    generate for (s = 0; s < D; s = s + 1) begin : g_slot
        always @(posedge wck) if (wsl[s]) epo[s] <= wc;
        reg v;                                                     // slot written since the lane epoch began
        always @(posedge wck or negedge we)
            if (!we) v <= 1'b0;
`ifdef OT_QFD_LAND_MUT_VLD
            else v <= 1'b1;                                        // bench mutant: every slot valid at once
`else
            else if (wsl[s]) v <= 1'b1;
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
    always @(posedge ck) o <= (warm && vld[rs_]) ? ((WSEL != 0) ? rd[rs_*W +: W] : bank[rs_]) : {W{1'b0}};
`endif
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "ot_qfd_land: D must be a power of two >= 2");
`endif
endmodule
`default_nettype wire

// LANDFIX-SQ (2026-10-18, coordinator 0gh: no plain relays left on the Qwen compute die): FORWARDED RESET LANES.
// A reset lane (OT_SPLIT_FWD_LANES_RST=1) carries a reset LEVEL from its source (reset synchroniser / block reset output
// / reset bump) to one block reset pin.  It cannot use the data landing: the ring's read epoch is the receiver's released
// reset, which is the very level the lane carries, and the hop-0 gate (opened by the source's released reset) would hold
// an asserting reset back.  Form: hop 0 = one register on the SOURCE root (no gate), ck_o = ~ck; stations = one register
// on the lane clock, ck_o = ~ckf (half-cycle hops, as ot_qfd_lane_st); landing = the level re-registered on the
// RECEIVING block's root (one STA-timed edge, the mesochronous lane -> root hop the data landings time too).  The level is
// carried like the plain reset relay chains before it (registers without reset, ot_qwen_rst_rep class): the reset tree's
// equal-depth release (fixed edges per lane, n/2 + 1 cycles) keeps the release on a fixed block-root edge.
module ot_qfd_rlane_st #(parameter integer W = 1) (
    input  wire         cap,         // hop 0: source block root;  station: the lane's forwarded clock (previous ck_o)
    input  wire [W-1:0] a,
    output reg  [W-1:0] b,
    output wire         ck_o
);
    always @(posedge cap) b <= a;
`ifdef OT_QFD_LANE_MUT_FULL
    wire ckn, ckp;
    ot_qfd_ckinv u_ck0 (.a(cap), .y(ckn));
    ot_qfd_ckinv u_ck1 (.a(ckn), .y(ckp));
    assign ck_o = ckp;
`else
    ot_qfd_ckinv u_ck0 (.a(cap), .y(ck_o));
`endif
endmodule

// reset-release landing: the lane's reset level re-registered on the receiving block's root
module ot_qfd_rlane_land #(parameter integer W = 1) (
    input  wire         ck,          // receiving block root
    input  wire [W-1:0] a,
    output reg  [W-1:0] b
);
    always @(posedge ck) b <= a;
endmodule
