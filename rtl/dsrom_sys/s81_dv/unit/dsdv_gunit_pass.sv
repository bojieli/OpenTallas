`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_pass -- the registered feedthrough every G-unit leaf uses for the buses it only
// carries (the column-3 V rung both ways, the cw configuration stream, the CTL rows, the sid strap): an input flop at
// the entry face and an output flop at the exit face (N = 2 edges per leaf, one 673-um leaf height between them,
// repeated; measured reach 600-750 um).  Bit 0 (the V valid / header bit, or a valid) is reset so a leaf leaves reset
// idle; the rest is data (no reset on the datapath).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_pass #(
    parameter integer W = 276,
    parameter integer N = 2
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [N-1:0] v;                                      // bit 0 of each stage (reset)
    reg [W-1:1] s [0:N-1];                              // the rest (data, no reset)
    integer k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) v <= {N{1'b0}};
        else begin v[0] <= d[0]; for (k = 1; k < N; k = k + 1) v[k] <= v[k - 1]; end
    always @(posedge clk) begin
        s[0] <= d[W-1:1];
        for (k = 1; k < N; k = k + 1) s[k] <= s[k - 1];
    end
    assign q = {s[N - 1], v[N - 1]};
endmodule
