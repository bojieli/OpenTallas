// LH-RSTHOP 2026-10-19 (HBM d4g H.RST, structural fallback; coordinator 0jp A "relay rows carry the reset"): a reset-forest
// reach hop CO-LOCATED inside a lane relay station.  GEN2c case_a places 56.6k lane relay tiles in every channel, so the
// separate 32.4 um hbfd_rrl_hop tiles of tools/hbm_die_v16/reset_forest_layer.py found no legal home within the 405 um
// reach (forest_codex9d5a2c350 / ofly: 'no legal reset relay within routed reach').  The station that already sits in the
// channel carries the hop instead: hbfd_rly_<W>_<flow>_rf / _rrf = the UNCHANGED station (ot_hbm_rly / ot_hbm_rly_rr) plus
// ONE forest reset flop with exactly hbfd_rrl_hop semantics:
//   rfo <= 1 on posedge ck, cleared asynchronously by rfi  =>  assert immediate, release exactly 1 clock edge after rfi.
// ck is the station's own regional clock (the planner only hosts a hop on a station of the forest's clock domain).
// rfi/rfo are independent of the station's data stage and of rs/rso (the row reset): no data, timing or schedule change.
// OT_HBM_RLY_RF_MUT_COMB (bench only): rfo = rfi (no flop: combinational daisy chain) -> release-age check FAILS.
`default_nettype none
module ot_hbm_rly_rfhop (
    input  wire ck,
    input  wire rfi,
    output wire rfo
);
`ifdef OT_HBM_RLY_RF_MUT_COMB
    assign rfo = rfi;
`else
    (* keep = "true", dont_touch = "true" *) reg fq;
    always @(posedge ck or negedge rfi)
        if (!rfi) fq <= 1'b0; else fq <= 1'b1;
    assign rfo = fq;
`endif
endmodule
`default_nettype wire
