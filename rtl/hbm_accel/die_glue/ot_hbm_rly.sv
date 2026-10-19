// HBM R25GQ die relay (hbfd_rly_<W>_<in face><out face>): ONE register stage on a <= 500-um die hop.
// The die generator (tools/hbm_accel_die_fp.py) places a register stage wherever a region-clocked bus exceeds the
// reach; this is that stage as a real hard tile, one master per WIDTH CLASS (tools/hbm_die_rly_kits.py): a bus of W
// bits takes the smallest class >= W (spare bits tied low at the die top), a bus wider than the largest class takes
// several masters side by side along the flow.
// Function: r <= i on posedge ck, asynchronous active-low clear rs.  Physical contract: scalar ck / rs, M5 cap, the
// data flop is the only logic, flops at the pins, minimum output delay built at the output pin by the kit (outhold).
// RS_RELAY (NATIVE-FIX3 2026-10-18, default 0 = unchanged): 1 puts the registered reset relay (rtl/lib/ot_rst_relay.sv)
// on rs at ANY width, so the rs pin drives 3 relay flops beside its face instead of the async clear of all W stage
// flops (hbfd_rly_136 NS/SN routed native capture 194-211 ps on rs, NATIVE-3).  Cost: the stage release is 3 clock
// edges later than rs (the > 256 b classes already behave this way); assert stays asynchronous and immediate.
// OT_HBM_RLY_MUT_NORR (bench only): the relay is bypassed (rn = rs), the release-latency check must FAIL.
`default_nettype none
module ot_hbm_rly #(
    parameter int W = 136,
    parameter int RS_RELAY = 0
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    // reset: a class of <= 256 b clears its flops straight from rs; a wider class goes through the registered reset
    // relay, one copy per 256 b (assert asynchronous and immediate, release 3 clock edges later: rtl/lib/ot_rst_relay.sv)
    localparam int G = (W + 255) / 256;
    wire [G-1:0] rn;
    generate
        if (W > 256 || RS_RELAY != 0) begin : g_rr
`ifdef OT_HBM_RLY_MUT_NORR
            assign rn = {G{rs}};   // bench mutant: reset relay bypassed
`else
            ot_rst_relay #(.REGIONS(G), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(ck), .rst_n_in(rs), .rst_n(rn));
`endif
        end else begin : g_nr
            assign rn = rs;
        end
    endgenerate
    reg [W-1:0] r;
    genvar g;
    generate
        for (g = 0; g < G; g = g + 1) begin : g_grp
            localparam int LO = g * 256;
            localparam int N  = (W - LO > 256) ? 256 : W - LO;
            always @(posedge ck or negedge rn[g])
                if (!rn[g]) r[LO +: N] <= {N{1'b0}};
`ifdef OT_HBM_RLY_MUT
                else r[LO +: N] <= (g == 0) ? i[LO +: N] ^ {{(N-1){1'b0}}, 1'b1} : i[LO +: N];   // bench mutant: bit 0 inverted
`else
                else r[LO +: N] <= i[LO +: N];
`endif
        end
    endgenerate
    assign o = r;
endmodule
`default_nettype wire
