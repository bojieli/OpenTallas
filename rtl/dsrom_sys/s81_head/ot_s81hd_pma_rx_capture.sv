`timescale 1ns/1ps
`default_nettype none
// HEAD F1 port capture: the existing LAT full-width RX banks, with an
// optional falling-edge first bank. No reset is added: as for ot_s81_pma_bm,
// inactive words are zero and startup state is flushed by incoming words.
// FIRST_FALL=0 is bit/edge-identical to ot_s81_pma_bm. FIRST_FALL=1 keeps
// banks1..LAT-1 rising; its source-labelled FEC-input age must be repriced.
module ot_s81hd_pma_rx_capture #(
    parameter integer W = 544,
    parameter integer LAT = 4,
    parameter bit FIRST_FALL = 0
) (
    input wire clk,
    input wire d_v,
    input wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] l [0:LAT-1];
    generate if (FIRST_FALL) begin : g_first_fall
`ifdef OT_HEAD_RXCAP_MUT_RISE
        always @(posedge clk) l[0] <= d_v ? d : {W{1'b0}};
`else
        always @(negedge clk) l[0] <= d_v ? d : {W{1'b0}};
`endif
    end else begin : g_first_rise
        always @(posedge clk) l[0] <= d_v ? d : {W{1'b0}};
    end endgenerate
    generate for (genvar s = 1; s < LAT; s = s + 1) begin : g_tail
`ifdef OT_HEAD_RXCAP_MUT_TAIL_FALL
        if (FIRST_FALL && s == 1) begin
            always @(negedge clk) l[s] <= l[s-1];
        end else begin
            always @(posedge clk) l[s] <= l[s-1];
        end
`else
        always @(posedge clk) l[s] <= l[s-1];
`endif
    end endgenerate
`ifdef OT_HEAD_RXCAP_MUT_TOPBIT
    assign q = l[LAT-1] ^ (FIRST_FALL ? ({{(W-1){1'b0}},1'b1} << (W-1)) : {W{1'b0}});
`else
    assign q = l[LAT-1];
`endif
`ifndef SYNTHESIS
    initial if (W < 1 || LAT < 2) $fatal(1,"HEAD RX capture requires W>=1 and LAT>=2");
`endif
endmodule
`default_nettype wire
