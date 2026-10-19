`timescale 1ns/1ps
// q3h shared relay station (Q-DIEPLAN3-CB, 2026-10-16).  One registered stage of W bits that drives N children (N 1..4):
// the down (broadcast) word or the up (partial-sum) word of the q3h hierarchical relay tree.  Exact by construction:
// q is d one edge later, for every bit; no reset on data (the static schedule never reads a word before its producer
// wrote it; go / valid bits are plain data here, as in ot_qfd_xcst b_q).  One register bank: every child sees the same
// flop outputs (the station is placed at the fork point of its children; each hop <= 373 um pin to pin).
module qfd_q3h_stn #(
    parameter integer W = 516,
    parameter integer N = 1
) (
    input  wire           ck,
    input  wire [W-1:0]   d,
    output wire [N*W-1:0] q
);
    initial if (N < 1 || N > 4) $fatal(1, "qfd_q3h_stn: N must be 1..4 (got %0d)", N);
    (* keep *) reg [W-1:0] q_r;
    always @(posedge ck) q_r <= d;
    assign q = {N{q_r}};
endmodule

// D back-to-back stations of W bits (a relay run along one route; each stage is its own instance so the cluster
// kit binds every stage to its planned (x, y) slot).  D = 0 is a wire (a direct pin-to-pin hop).
module qfd_q3h_run #(
    parameter integer W = 514,
    parameter integer D = 1
) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    genvar i;
    generate if (D == 0) begin : g_wire
        assign q = d;
    end else begin : g_run
        wire [W-1:0] s [0:D];
        assign s[0] = d;
        for (i = 0; i < D; i = i + 1) begin : g_s
            qfd_q3h_stn #(.W(W), .N(1)) u_s (.ck(ck), .d(s[i]), .q(s[i+1]));
        end
        assign q = s[D];
    end endgenerate
endmodule
