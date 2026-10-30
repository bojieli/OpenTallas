// ---------------------------------------------------------------------------------------------------------------------
// HBM-NEXT FUSED csum TREE + HUB (LEAD-HBM/LH-P3UNITS/FUSHUB, 2026-10-19; next-release P = 3 die, case f4c_t9p3).
//
// WHY.  ot_hnx_fused_top (ot_hnx_fused_eng.sv) takes all 32 lanes' chunk sums on ONE edge into a 1,024-b register and a
// 5-level pairwise tree, with RL = 4 relays per lane.  On the die the 32 lanes sit beside their VM bank pairs in 4
// quadrants (worst lane -> hub 14.5 mm); a 32 x 441 b star into one hub is not legal.  SAFE-DESIGN review (FUSED README):
// item 2/7 (single-edge star over mm) and item 5 (scb = 48 x 256 b runtime-indexed flop array).  This file replaces the
// top by a NEIGHBOUR-HOP TREE that follows the DIE graph (f4c_t9p3 plan_p4.fused_graph):
//   per quadrant q (lanes lid = 8 q + i, i = the bank index of its bank pair):
//     level 1  n1[g] at lane 2g      : a = lane 2g (abutted), b = lane 2g + 1 (stacked pair, 668 um)
//     level 2  n2L at group 0        : a = n1[0] (local), b = n1[1] (g1 -> g0, neighbour column)
//              n2R at group 3        : a = n1[2] (g2 -> g3), b = n1[3] (local)
//     level 3  n3  at group 3        : a = n2L (g0 -> g3), b = n2R (local)  = the quadrant node
//   hub (centre line): level 4 t4a = (Q0, Q1), t4b = (Q2, Q3); level 5 t5 = (t4a, t4b).
// Every link is a die lane: registered relay stations at <= 405 um (forwarded half-cycle hops) and, between clock
// regions (g1->g0, g2->g3, g0->g3, quadrant->hub: 16 crossings), a LANDED crossing (lanes/LANDING-CONTRACT.md: 4-slot
// ring, fixed latency, no backpressure).  The die binder inserts them; this RTL sees each link as a fixed latency.
//
// NUMERICS (DECISION LEAD-HBM/LH-P3UNITS 10-19): the golden sums chunk pairs (2c, 2c+1) level by level, left = even.
// Chunk u of a block is lane (u + ph) mod 32, ph = A's bank phase (VM word address bits [7:3]).  The fixed tree above
// IS the golden order exactly when ph = 0 (and lid = 8 q + i), so the compiler allocator bank-aligns every FUSED
// HC_PRE_NORM operand (ph = 0; image check tools/hbm_next/fused_phase_check.py) and the hub REFUSES (job fault, no lane
// activity) an HC_PRE_NORM record with ph != 0.  HC_POST has no cross-lane reduction: its ph stays free (lane-local rule
// only: A / B / O one phase).  No runtime reorder, no rotation hardware.
//
// STATIC SCHEDULE.  No credits, ready, FIFO admission or arbitration anywhere.
//   * Down (command bus + r channel): every node re-registers the parent bus into two KEPT copies (one per child,
//     2 edges a node).  Lanes are NOT padded to lockstep: lane L sees every hub command D(L) edges later, i.e. lane L's
//     whole calendar (VM accesses included) is offset by its fixed D(L) (handed to CMTP as a per-bank offset).
//   * Up: each node pads its EARLIER child (strap pad_b / pad_k, fixed per instance by the die binder) by the
//     difference of the two children's ROUND TRIPS, so both children's messages of one block meet on one edge (the
//     aligned pair is registered).  Then chunk sums are added (one registered FP32 add, ot_dsrom_qadd LA 6, a = lower
//     lanes) and scalars / fin / flt pass in one register.  Up latency a node: scalar 4 + pad, chunk LA + 3 + pad.  Sibling subtrees have equal depth, so one pad aligns chunk sums, scalars and fins.
//   * Every misalignment is a FAULT (fl bit): a chunk sum on one side only, two scalars on one edge, a chunk/scalar
//     output collision, an adder flag.
// Pad storage: up to 32 edges x 271 b = 8.7 kb -> SRAM (1R1W 128x256 data ring + 1R1W 32x64 control ring), with a
// post-reset fill mask (silicon SRAM powers up random).
//
// Bus formats.  UP (UW = 271): [270] v, [269] t (0 scalar, 1 chunk sum), [268:259] x, [258] fa (fin AND),
//   [257] fo (fin OR), [256] fl (fault OR), [255:0] d (chunk sum in [31:0]).
//   DOWN (DW = 173): [172] cv, [171:169] cop, [168:161] cx, [160:33] cd, [32] rv, [31:0] rd.
// MUT (bench negatives, rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv): 1..6 as ot_hnx_fused_top (lanes / heap); 7 the hub accepts ph != 0
//   for HC_PRE_NORM (run with ph != 0 vectors: the fixed tree is NOT the golden order -> mismatches); 8 lanes 2 and 4 of quadrant 0
//   swap tree positions (wrong tree order, timing still aligned -> mismatches); 9 quadrant 0's n2L pad one edge short
//   (misaligned chunk sums -> FAULT).
// ---------------------------------------------------------------------------------------------------------------------

// q = d delayed by k edges (k strap 0 .. 32).  k >= 2: SRAM rings (write slot wp, read slot wp - k + 1, registered read:
// the slot written at edge e is in q after edge e + k - 1 + 1 = the shift line's); k = 1: one register; k = 0: a wire.
module ot_hnx_fused_pad #(parameter integer WC = 15) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    k,
    input  wire [WC-1:0] dc,
    input  wire [255:0]  dd,
    output wire [WC-1:0] qc,
    output wire [255:0]  qd
);
    reg [4:0] wp; reg [5:0] fill; reg ok_q;
    wire [4:0] ra = 5'(wp - 5'(k) + 5'd1);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= '0; fill <= '0; ok_q <= 1'b0; end
        else begin
            wp <= wp + 5'd1;
            if (fill != 6'd63) fill <= fill + 6'd1;
            ok_q <= ({1'b0, fill} + 7'd1 >= {1'b0, k});                  // the slot read at this edge was written after reset
        end
    wire [255:0] rdd; wire [63:0] rdc;
    ot_sram_1r1w_128x256_m1_r2c2 u_d (.clk(clk), .r_ce_in(1'b1), .r_addr_in({2'b00, ra}), .rd_out(rdd),
        .w_ce_in(1'b1), .w_addr_in({2'b00, wp}), .wd_in(dd), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w2c_32x64_m1 u_c (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(rdc),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in({{(64 - WC){1'b0}}, dc}), .w_mask_in({64{1'b1}}));
    reg [WC-1:0] c1; reg [255:0] d1;
    always @(posedge clk or negedge rst_n) if (!rst_n) c1 <= '0; else c1 <= dc;
    always @(posedge clk) d1 <= dd;
    assign qc = (k == 6'd0) ? dc : (k == 6'd1) ? c1 : (ok_q ? rdc[WC-1:0] : {WC{1'b0}});
    assign qd = (k == 6'd0) ? dd : (k == 6'd1) ? d1 : rdd;
endmodule
