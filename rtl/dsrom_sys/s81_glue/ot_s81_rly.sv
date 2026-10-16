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
    assign o = r;
endmodule
`default_nettype wire
