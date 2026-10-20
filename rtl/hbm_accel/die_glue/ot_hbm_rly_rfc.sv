// L2H-RSTFB 2026-10-19 (HBM d4g H.RST.FB, structurally safe successor of LH-RSTHOP ot_hbm_rly_rfhop): a reset-forest
// CARRIER STAGE co-located inside a placed lane relay station.  GEN2c/GEN2d lane relays (~56k stations) fill every
// channel, so separate reset tiles (hbfd_rrl_* / hbfd_rrl_c*) find too few legal homes; the station that already sits in
// the channel carries the forest stage instead: hbfd_rly_<W>_<flow>_rfc / _rrfc = the UNCHANGED station (ot_hbm_rly /
// ot_hbm_rly_rr, data path and row reset rs/rso untouched) + this stage on the station's own regional clock ck.
//
// SAFE-DESIGN item 1 (reset lands in 2 registered stages at the face), same discipline as hbfd_rrl_c 5ab727c0f:
//   land[1:0] : the 2-stage landing; rfi is the asynchronous clear of THESE TWO FLOPS ONLY (reset_landing <= 2 sinks).
//   q         : the carrier output flop, cleared SYNCHRONOUSLY while land[1] is low, set when land[1] is high.
//   rfo       = land[1] & q   (q is flop-driven; the AND only lets the assertion through at once).
// Semantics (exact, ideal common-phase edge model):
//   assertion : rfi low  =>  land[1] low at once  =>  rfo low at once (immediate, no clock needed).
//   release   : rfi rises before edge e0  =>  land[0]=1 @e0, land[1]=1 @e1, q=1 @e2  =>  rfo high after the 3rd edge.
//               FIXED RELEASE AGE = 3 EDGES per hosted carrier stage (the planner charges 3, not 1, per hosted hop).
//   A chain of N hosted stages releases its k-th output (k = 1..N) exactly 3k edges after the head rfi.
// rfi/rfo are independent of the station's data stage and of rs/rso: no data, timing or schedule change.
// Bench-only mutants (rtl/hbm_accel/die_glue/test/bench_rly_rfc.sh):
//   OT_HBM_RLY_RFC_MUT_1LAND : one landing flop (age 2)                       -> release-age check FAILS
//   OT_HBM_RLY_RFC_MUT_COMB  : rfo = rfi (combinational daisy chain, age 0)   -> release-age check FAILS
//   OT_HBM_RLY_RFC_MUT_NOGATE: rfo = q (assertion waits for a clock edge)      -> immediate-assertion check FAILS
`default_nettype none
module ot_hbm_rly_rfc (
    input  wire ck,
    input  wire rfi,
    output wire rfo
);
`ifdef OT_HBM_RLY_RFC_MUT_COMB
    assign rfo = rfi;
`else
    (* async_reg = "true", keep = "true", dont_touch = "true" *) reg [1:0] land;
    (* keep = "true", dont_touch = "true" *) reg q;
    always @(posedge ck or negedge rfi)
        if (!rfi) land <= 2'b00;
`ifdef OT_HBM_RLY_RFC_MUT_1LAND
        else land <= 2'b11;
`else
        else land <= {land[0], 1'b1};
`endif
    always @(posedge ck)
        if (!land[1]) q <= 1'b0; else q <= 1'b1;
`ifdef OT_HBM_RLY_RFC_MUT_NOGATE
    assign rfo = q;
`else
    assign rfo = land[1] & q;
`endif
`endif
endmodule
`default_nettype wire
