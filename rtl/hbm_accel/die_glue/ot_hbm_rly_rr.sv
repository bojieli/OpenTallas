// HBM-RSTROW 2026-10-19 (coordinator 0jp, Proposal A: reset carried along each relay row): hbfd_rly_<W>_<flow>_rr = the
// SAME register stage as hbfd_rly_<W>_<flow> (ot_hbm_rly instantiated unchanged: r <= i on posedge ck, asynchronous
// active-low clear from rs, registered reset relay at > 256 b or RS_RELAY=1 -> stage release 3 edges after rs) plus ONE
// row-reset flop:
//   rso <= 1 on posedge ck, cleared asynchronously by rs  =>  assert immediate, release exactly 1 clock edge after rs.
// rso drives the rs pin of the NEXT relay(s) of the same row (the data successor(s) of o, same region clock), so the
// release walks the row in lockstep with the data: the row head is fed by a regional reset-forest leaf, the station at
// data depth k from the head releases its rso at head + k + 1.  Semantics (tools/hbm_die_v16/reset_forest_layer.py
// --relay-rows): a station at depth k receives producer data no earlier than D + 1 + k (D = producer block release age),
// so the row is exact when head + k + S <= D + 1 + k for every station (S = 0 or 3 stage release lag), i.e. the head is
// fed at age <= D - 2.  Earlier releases only pass the producer's reset-state (idle) outputs.
// OT_HBM_RLY_RR_MUT_COMB (bench only): rso = rs (no row-reset flop: a combinational daisy chain) -> release-age check FAILS.
// OT_HBM_RLY_RR_MUT_2   (bench only): two row-reset flops (release 2 edges after rs) -> release-age check FAILS.
`default_nettype none
module ot_hbm_rly_rr #(
    parameter int W = 136,
    parameter int RS_RELAY = 0
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o,
    output wire         rso
);
    ot_hbm_rly #(.W(W), .RS_RELAY(RS_RELAY)) u_stage (.ck(ck), .rs(rs), .i(i), .o(o));
`ifdef OT_HBM_RLY_RR_MUT_COMB
    assign rso = rs;
`else
    (* keep = "true", dont_touch = "true" *) reg rq;
    always @(posedge ck or negedge rs)
        if (!rs) rq <= 1'b0; else rq <= 1'b1;
`ifdef OT_HBM_RLY_RR_MUT_2
    (* keep = "true", dont_touch = "true" *) reg rq2;
    always @(posedge ck or negedge rs)
        if (!rs) rq2 <= 1'b0; else rq2 <= rq;
    assign rso = rq2;
`else
    assign rso = rq;
`endif
`endif
endmodule
`default_nettype wire
