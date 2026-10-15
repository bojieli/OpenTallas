// S81 die relay (dsfd_rly_<W>_<in face><out face>): ONE register stage on a <= 500-um die seam.
// Function is the die netlist's relay: r <= i on posedge ck, asynchronous active-low clear rs.
// Physical contract (results/arch/hier_contract_1011/s81.json, relay masters): scalar ck / rs, M5 cap, the data
// flop is the only logic; the minimum output delay (FF clock->o at the pin minus clock insertion, >= the abutted
// receiver's hold + 50 ps die hold uncertainty) is built at the output pin by the kit (ref_tile "outhold").
`default_nettype none
module ot_s81_rly #(
    parameter int W = 63
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    reg [W-1:0] r;
    always @(posedge ck or negedge rs)
        if (!rs) r <= {W{1'b0}};
`ifdef OT_S81_RLY_MUT
        else r <= i ^ {{(W-1){1'b0}}, 1'b1};   // bench mutant: bit 0 inverted
`else
        else r <= i;
`endif
    assign o = r;
endmodule
`default_nettype wire
