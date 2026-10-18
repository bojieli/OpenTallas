`timescale 1ns/1ps
`default_nettype none
// HBM-FAULT 2026-10-17: regional fault-aggregation leaf (coordinator 0da+ (b): every fault output of the die must be
// observable at the host status join). One small pin-registered tile per region; leaves chain / tree to their region
// root, region roots feed ot_hbm_status_join_fa, which holds the fault (sticky) until the host clears it. No star hub:
// every leaf reads only the fault pins of its neighbours (its region's blocks and its child leaves); every hop is
// registered (the die relay planner adds registered stations on hops longer than the reach; their count is fixed per
// die revision, so every source has one fixed latency to the join).
//
//  in[N-1:0]: fault / retry / status bits (pulse or level) of the region's blocks and the fault outputs of child
//  leaves. Every bit lands in a pin flop; SYNC_MASK bits (sticky fault levels from another clock domain: the serial
//  SU slices / cores) take a second synchroniser flop. fault = OR of the registered bits, a flop Q.
//  A pulse is never lost: it travels as a registered pulse up the tree and is held at the join.
//  Fixed latency (edges): bit -> fault 2; SYNC bit -> fault 3.
// The fault path never gates or reschedules execution; it only reaches the host status.
// MUT (bench only): 1 drops in[N-1], 2 output not registered (one edge early), 3 SYNC_MASK ignored.
module ot_hbm_fault_leaf #(
    parameter integer N = 1,
    parameter [63:0] SYNC_MASK = 64'd0,
    parameter integer MUT = 0
)(
    input  wire clk, rst_n,
    input  wire [N-1:0] in,
    output wire fault
);
    wire [N-1:0] smask = (MUT == 3) ? {N{1'b0}} : SYNC_MASK[N-1:0];
    wire [N-1:0] keep  = (MUT == 1) ? ({N{1'b1}} >> 1) : {N{1'b1}};
    reg [N-1:0] p1, p2;
    reg f;
    wire any = |(((p1 & ~smask) | (p2 & smask)) & keep);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin p1 <= {N{1'b0}}; p2 <= {N{1'b0}}; f <= 1'b0; end
        else begin p1 <= in; p2 <= p1; f <= any; end
    assign fault = (MUT == 2) ? any : f;
endmodule
`default_nettype wire
