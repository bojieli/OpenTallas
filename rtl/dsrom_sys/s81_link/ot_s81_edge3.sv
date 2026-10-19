`timescale 1ns/1ps
`default_nettype none
// Candidate same-frequency regional seam, fully timed at every edge. This is
// NOT an asynchronous CDC. Both roots require a measured neighbouring clock
// budget. Place source_a/source_b/destination along <=405um physical hops.
// Two source flops plus one destination flop preserve the old E=2 ring's
// steady-state three-edge transport without its four-bank bus or multicycle.
module ot_s81_edge3 #(parameter integer W=1, parameter integer LATE=0) (
    input wire src_ck, dst_ck, src_rsi, dst_rsi,
    input wire [W-1:0] i,
    output wire [W-1:0] o
);
    reg src_rq, dst_rq;
    reg [W-1:0] source_a, source_b, destination, late_q;
    reg [1:0] age;
    always @(posedge src_ck) src_rq <= src_rsi;
    always @(posedge dst_ck) dst_rq <= dst_rsi;
    always @(posedge src_ck) begin
        source_a <= src_rq ? i : {W{1'b0}};
        source_b <= src_rq ? source_a : {W{1'b0}};
    end
    always @(posedge dst_ck) begin
        if (!dst_rq) age <= 0;
        else if (age != 2) age <= age + 1'b1;
        destination <= (age == 2) ? source_b : {W{1'b0}};
        late_q <= destination;
    end
    assign o = LATE ? late_q : destination;
endmodule
`default_nettype wire
