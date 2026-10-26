// Qwen KV/system die relay STANDARDS (Q-KVSYS-RLY 2026-10-16; owner rule 19:50 PT 10-15 "fewer distinct tiles").
// The KV die's 21 generated per-width relay masters qkd_rly_<W> (tools/qwen_kv_die/kv_relays.py, 8,276 instances in
// kvs11-v143c) are replaced by FOUR hardened width classes, replicated: qkd_rlys_1 / _36 / _296 / _528.  A die relay
// stage of W bits = the replicas tools/qwen_kv_die/kv_rly_std.py picks (spare INPUT bits tied low as DECLARED pads,
// die_port_bind PADS; spare outputs open); a reverse bit of a mixed relay rides its own qkd_rlys_1 (b -> a).
// Function: exactly the qkd_rly_* contract -- ONE register a bit on the core clock ck, no reset (flush rule: the KV
// die's reset sequencer releases rso_* >= 128 core cycles after the clock runs), no logic between pin and flop.
// Latency: 1 core cycle per relay stage, already counted by the die plan (kv_die.py relay_stages).  The flop IS the
// pin register of both pins (a -> flop -> b), so the tile has no further pin registers (spec pin_regs opt-out).
`default_nettype none
module ot_qkd_rlys #(
    parameter int W = 36
) (
    input  wire         ck,
    input  wire [W-1:0] a,
    output wire [W-1:0] b
);
    reg [W-1:0] r;
    always @(posedge ck)
`ifdef OT_QKD_RLYS_MUT
        r <= a ^ {{(W-1){1'b0}}, 1'b1};          // bench mutant: bit 0 inverted
`else
        r <= a;
`endif
    assign b = r;
endmodule

module qkd_rlys_1   (input wire ck, input wire [0:0]   a, output wire [0:0]   b); ot_qkd_rlys #(.W(1))   u (.ck(ck), .a(a), .b(b)); endmodule
module qkd_rlys_36  (input wire ck, input wire [35:0]  a, output wire [35:0]  b); ot_qkd_rlys #(.W(36))  u (.ck(ck), .a(a), .b(b)); endmodule
module qkd_rlys_296 (input wire ck, input wire [295:0] a, output wire [295:0] b); ot_qkd_rlys #(.W(296)) u (.ck(ck), .a(a), .b(b)); endmodule
module qkd_rlys_528 (input wire ck, input wire [527:0] a, output wire [527:0] b); ot_qkd_rlys #(.W(528)) u (.ck(ck), .a(a), .b(b)); endmodule
`default_nettype wire
