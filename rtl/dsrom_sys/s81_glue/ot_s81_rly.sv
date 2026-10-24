// S81 die relay (dsfd_rly_<W>_<in face><out face>): ONE register stage on a <= 500-um die seam.
// Function is the die netlist's relay: r <= i on posedge ck, asynchronous active-low clear rs.
// Physical contract (results/arch/hier_contract_1011/s81.json, relay masters): scalar ck / rs, M5 cap, the data
// flop is the only logic; the minimum output delay (FF clock->o at the pin minus clock insertion, >= the abutted
// receiver's hold + 50 ps die hold uncertainty) is built at the output pin by the kit (ref_tile "outhold").
// RSREG = 1 (S-NET+FILL r4, 2026-10-15, native audit: rs fanned out to every data flop -> rs capture 195-294 ps > 190):
// rs drives ONE reset pin register rq (asynchronous assert, release one ck edge later); the data flops clear from rq.
// Initialization mode only (the die reset release calendar), no data edge.  RSREG = 0 is the original relay.
`default_nettype none
module ot_s81_rly #(
    parameter int W = 63,
    parameter int RSREG = 0
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
`ifdef OT_S81_RLY_RSSLICE
    // S81-TILES-A 10-20 (FRAME5 rf2, opt-in, default OFF): the frame native census (h10 rffwd gate, 203 violations, all
    // RESETN) found the single reset pin register rq clearing W data flops (536/283/266/63/38 loads) and, for RSREG = 0
    // relays wider than 32, the forest leaf clearing W flops directly (54/63/66).  Sliced form: NS = ceil(W/32) kept rq
    // copies (rs -> NS <= 32 loads), copy s clears data bits [32s, 32s+31] only (<= 32 loads).  RSREG != 0: cycle-identical
    // to the single rq (same asynchronous assert, same one-edge-later release).  RSREG = 0 with W > 32 takes the same
    // sliced rq (release one ck edge later; initialization only -- requalified by the frame benches).  W <= 32 with
    // RSREG = 0 is unchanged (rs direct).
    localparam int NS = (W + 31) / 32;
    reg [W-1:0] r;
    wire [NS-1:0] rsv;
    generate if (RSREG != 0 || W > 32) begin : g_rsslice
        for (genvar s = 0; s < NS; s = s + 1) begin : g_s
            wire q;
            (* keep_hierarchy = "yes" *) ot_s81_rly_rq #(.ID(s)) u_rq (.ck(ck), .rs(rs), .q(q));
`ifdef OT_S81_RLY_RSMUT
            assign rsv[s] = rs;             // bench mutant: reset pin registers bypassed
`else
            assign rsv[s] = q;
`endif
        end
    end else begin : g_rs
        assign rsv = {NS{rs}};
    end endgenerate
    generate for (genvar s = 0; s < NS; s = s + 1) begin : g_d
        localparam int LO = 32 * s;
        localparam int SW = (W - LO < 32) ? (W - LO) : 32;
        always @(posedge ck or negedge rsv[s])
            if (!rsv[s]) r[LO +: SW] <= {SW{1'b0}};
`ifdef OT_S81_RLY_MUT
            else r[LO +: SW] <= i[LO +: SW] ^ ((s == 0) ? {{(SW-1){1'b0}}, 1'b1} : {SW{1'b0}});   // bench mutant: bit 0 inverted
`else
            else r[LO +: SW] <= i[LO +: SW];
`endif
    end endgenerate
`else
    reg [W-1:0] r;
    wire rsi;
    generate if (RSREG != 0) begin : g_rsreg
        reg rq;
        always @(posedge ck or negedge rs)
            if (!rs) rq <= 1'b0;
            else rq <= 1'b1;
`ifdef OT_S81_RLY_RSMUT
        assign rsi = rs;                    // bench mutant: reset pin register bypassed
`else
        assign rsi = rq;
`endif
    end else begin : g_rs
        assign rsi = rs;
    end endgenerate
    always @(posedge ck or negedge rsi)
        if (!rsi) r <= {W{1'b0}};
`ifdef OT_S81_RLY_MUT
        else r <= i ^ {{(W-1){1'b0}}, 1'b1};   // bench mutant: bit 0 inverted
`else
        else r <= i;
`endif
`endif
    assign o = r;
endmodule

// ot_s81_rly_k (S81-P9-RTL 10-23): ot_s81_rly (non-sliced form, cycle-identical for every RSREG) whose flops are KEPT.
// R3-INTERNAL far-qbank twins (frame_band_plan.py (g)) copy a relay with identical D/ck/rs; Yosys opt_merge folded the
// twin back into its original (col_h10_r1__t1 kit synth).  (* keep *) on the flop processes marks the $dff cells; a kept
// cell is still merged with an unkept identical one, so the original and every twin use this module.  ID only names the copy.
module ot_s81_rly_k #(
    parameter int W = 63,
    parameter int RSREG = 0,
    parameter int ID = 0
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    reg [W-1:0] r;
    wire rsi;
    generate if (RSREG != 0) begin : g_rsreg
        reg rq;
        (* keep *) always @(posedge ck or negedge rs)
            if (!rs) rq <= 1'b0;
            else rq <= 1'b1;
`ifdef OT_S81_RLY_RSMUT
        assign rsi = rs;                    // bench mutant: reset pin register bypassed
`else
        assign rsi = rq;
`endif
    end else begin : g_rs
        assign rsi = rs;
    end endgenerate
    (* keep *) always @(posedge ck or negedge rsi)
        if (!rsi) r <= {W{1'b0}};
`ifdef OT_S81_RLY_MUT
        else r <= i ^ {{(W-1){1'b0}}, 1'b1};   // bench mutant: bit 0 inverted
`else
        else r <= i;
`endif
    assign o = r;
endmodule

`ifdef OT_S81_RLY_RSSLICE
// One kept reset pin register copy of the sliced ot_s81_rly (distinct ID per copy so synthesis never merges copies).
module ot_s81_rly_rq #(
    parameter int ID = 0
) (
    input  wire ck,
    input  wire rs,
    output wire q
);
    (* keep *) reg rq;
    always @(posedge ck or negedge rs)
        if (!rs) rq <= 1'b0;
        else rq <= 1'b1;
    assign q = rq;
endmodule
`endif
`default_nettype wire
