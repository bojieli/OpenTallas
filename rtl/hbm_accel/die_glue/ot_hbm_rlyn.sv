// HNX-DIE 10-20: RESET-FREE die relay stage (hbfd_rlyn_<W>_<dir>): ONE register stage on a <= 405-um die hop, no reset pin.
// Static-schedule rule (same as the half-cycle lane stations, tools/hbm_die_v16/relay_layer_d4f.py --land): a plain data
// relay needs no reset because its producer holds its (reset) output while the regional clock runs during reset, so the
// relay chain is flushed to the producer's reset value after <= depth edges; the consumer leaves reset on the same root
// edge as the producer (LANDING contract) and the compiler never reads a relay output before depth edges after release.
// Precondition (checked by tools/hbm_next/die/rlyn_flush_bench.sh): regional reset asserted >= depth clock edges with the
// clock running.  Removes the per-hop rs sink from the reset forest (P3 die f4c_t9p3: 31,148 relay rs POR sinks).
// Physical contract as ot_hbm_rly: scalar ck, M5 cap, the data flop is the only logic, flops at the pins.
// OT_HBM_RLYN_MUT (bench only): bit 0 inverted -> the flush/lockstep check must FAIL.
`default_nettype none
module ot_hbm_rlyn #(
    parameter int W = 136
) (
    input  wire         ck,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    reg [W-1:0] r;
    always @(posedge ck)
`ifdef OT_HBM_RLYN_MUT
        r <= i ^ {{(W-1){1'b0}}, 1'b1};
`else
        r <= i;
`endif
    assign o = r;
endmodule
`default_nettype wire
