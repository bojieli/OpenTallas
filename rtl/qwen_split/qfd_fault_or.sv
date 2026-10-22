// qfd_fault_or -- one node of the Qwen compute die fault-observability OR tree (Q.BIND.1, lane QW-GRT5 10-20).
//
// Purpose: every runtime fault / abort output of the die (inventory tools/qwen_split/fault_inventory.py: on dv2f20g4g
// 425 instance ports / 498 bits over 64 clock roots, e.g. landing ring faults, collective fault_code, D2D aborts) must
// reach STATUS. Each region gets leaf nodes beside its fault sources; region roots chain toward sys_face through
// landed crossings (ot_qfd_land), so no wire crosses a region clock unlanded and no wire is longer than the 405 um
// planning reach (tools/qwen_split/fault_or_plan.py plans the geometry and fails closed on any violation).
//
// Function: o = sticky OR of every bit of f seen since reset release. A fault is a monotonic level here: once set it
// stays until the region reset, so a landed crossing (fixed latency, no handshake) carries it exactly and the static
// schedule never depends on it (observation only; it never stalls or selects a cycle).
//
// Safe-design checklist (owner 10-19):
//  1 pins   : every input bit is registered at the face (fq); output o is a flop. Reset lands in 2 registered stages
//             (rl) from the regional reset leaf rs (active low, async assert, release on ck -- as ot_qfd_land.rs).
//  2 reach  : node is small (N <= 16 flops + 3); the planner keeps every source->node and node->node wire <= 405 um.
//  3 fanout : rl[1] drives N+2 flops (<= 18 <= 32); no other net fans out above 1.
//  4 depth  : one N-input OR (N <= 16: 4 levels of OR2) + one OR2 per stage.
//  5 storage: N + 4 flops, no arrays.
//  7 clock  : single regional clock ck; crossings are made outside by landings, never inside the node.
//  8 latency: f -> o = 3 ck edges (fq, s, o); the planner prices the full source->STATUS bound per path.
module qfd_fault_or #(
    parameter int N = 16
) (
    input  wire         ck,
    input  wire         rs,   // regional reset leaf, active low (async assert, release on ck)
    input  wire [N-1:0] f,    // fault bits: any 1 = fault
    output reg          o     // sticky registered OR
);
    initial begin
        if (N < 1 || N > 16) $error("qfd_fault_or: N=%0d outside 1..16 (fanin cap)", N);
    end

    reg [1:0] rl;              // 2-stage reset landing at the face
    always @(posedge ck or negedge rs)
        if (!rs) rl <= 2'b00;
        else     rl <= {rl[0], 1'b1};

    reg [N-1:0] fq;            // input pin registers
    reg         s;             // sticky
    always @(posedge ck or negedge rl[1])
        if (!rl[1]) begin
            fq <= {N{1'b0}};
            s  <= 1'b0;
            o  <= 1'b0;
        end else begin
            fq <= f;
`ifdef QFD_FAULT_OR_MUT_NOSTICKY
            s  <= (|fq);           // bench mutant: drops the sticky hold
`else
            s  <= s | (|fq);
`endif
            o  <= s;
        end
endmodule
