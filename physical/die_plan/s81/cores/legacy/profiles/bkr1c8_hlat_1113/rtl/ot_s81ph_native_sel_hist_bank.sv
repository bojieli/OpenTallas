`timescale 1ns/1ps
// TOPK5 independent32-bin arithmetic leaf. Not wired into release quarter.
// Harden each leaf before composing; see results/arch/s81_topk5_1020/partition_model.json.


// Same fixed popcount helper as golden; independent namespace avoids importing
// unrelated unclosed selector-library changes into this standalone hard bank.
module ot_s81ph_hist32_popc #(
    parameter integer N  = 16,
    parameter integer OW = 5
) (
    input  wire [N-1:0]  x,
    output wire [OW-1:0] y
);
    localparam integer NP = (N > 1) ? (1 << $clog2(N)) : 2;
    /* verilator lint_off UNOPTFLAT */
    wire [2*NP*OW-1:0] t;
    /* verilator lint_on UNOPTFLAT */
    genvar n;
    generate
        for (n = 0; n < NP; n = n + 1) begin : g_leaf
            if (n < N) begin : g_x
                assign t[OW*(NP+n) +: OW] = {{(OW-1){1'b0}}, x[n]};
            end else begin : g_0
                assign t[OW*(NP+n) +: OW] = {OW{1'b0}};
            end
        end
        for (n = 1; n < NP; n = n + 1) begin : g_node
            assign t[OW*n +: OW] = t[OW*(2*n) +: OW] + t[OW*(2*n+1) +: OW];
        end
    endgenerate
    assign t[OW-1:0] = {OW{1'b0}};
    assign y = t[OW +: OW];
endmodule
