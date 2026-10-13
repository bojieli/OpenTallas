// HBM R25GQ die relay (hbfd_rly_<W>_<in face><out face>): ONE register stage on a <= 500-um die hop.
// The die generator (tools/hbm_accel_die_fp.py) places a register stage wherever a region-clocked bus exceeds the
// reach; this is that stage as a real hard tile, one master per WIDTH CLASS (tools/hbm_die_rly_kits.py): a bus of W
// bits takes the smallest class >= W (spare bits tied low at the die top), a bus wider than the largest class takes
// several masters side by side along the flow.
// Function: r <= i on posedge ck, asynchronous active-low clear rs.  Physical contract: scalar ck / rs, M5 cap, the
// data flop is the only logic, flops at the pins, minimum output delay built at the output pin by the kit (outhold).
`default_nettype none
module ot_hbm_rly #(
    parameter int W = 136
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    reg [W-1:0] r;
    always @(posedge ck or negedge rs)
        if (!rs) r <= {W{1'b0}};
`ifdef OT_HBM_RLY_MUT
        else r <= i ^ {{(W-1){1'b0}}, 1'b1};   // bench mutant: bit 0 inverted
`else
        else r <= i;
`endif
    assign o = r;
endmodule
`default_nettype wire
