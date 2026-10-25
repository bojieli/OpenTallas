`timescale 1ns/1ps
`default_nettype none
// ot_dp_rsync: a reset spine landing (asbuilt.reset_spines): W active-low resets, each asserted asynchronously and
// released after S (>= 2) clocks of the receiving partition.
module ot_dp_rsync #(parameter integer W = 1, parameter integer S = 2) (
    input  wire         clk,
    input  wire [W-1:0] a,
    output wire [W-1:0] q
);
    genvar g;
    generate for (g = 0; g < W; g = g + 1) begin : b
        reg [S-1:0] r;
        always @(posedge clk or negedge a[g])
            if (!a[g]) r <= {S{1'b0}}; else r <= {r[S-2:0], 1'b1};
        assign q[g] = r[S-1];
    end endgenerate
endmodule
// ot_dp_or: N-input OR of a re-emitted fault tree (an as-built reducer chain, removed and rebuilt per sink partition).
module ot_dp_or #(parameter integer N = 1) (
    input  wire [N-1:0] a,
    output wire         y
);
    assign y = |a;
endmodule
// ot_dp_and: N-input AND of a re-emitted AND join (an as-built AND reducer, e.g. link-up, rebuilt per sink partition).
module ot_dp_and #(parameter integer N = 1) (
    input  wire [N-1:0] a,
    output wire         y
);
    assign y = &a;
endmodule
// ot_dp_dly: D reset-less register stages (D >= 1): the as-built transport stages of an INTRA-partition path, kept.
module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
    end
    assign q = r[D-1];
endmodule
`default_nettype wire
