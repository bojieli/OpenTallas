// QC-A0-KITS-13 10-29 (COORD ruling d, B-hop): one clock-gate copy per A0 clock-entry cluster, its enable relayed
// through K registered hops on the UNGATED clock -- the same hop count budget as the data it gates.
//   en (tile enable, 1-cycle lead) -> h[0] -> ... -> h[K-1] -> ICG ENA (latched on the low phase) -> gck
// A cluster whose first register is s gated stages after the ungated input faces (measured, README §3) is safe with
// K <= s - 1: its first needed gated edge comes s cycles after the face capture, the relayed enable opens it K + 1
// cycles after.  Turn-off is delayed by K too (only adds clock edges).  The hops are set to 1 in reset, so every gate is
// open during reset exactly like the tile-root form (en = 1 while !rst_n).
// keep_hierarchy: each cluster keeps its own hop chain (no merge of the identical chains), so the placer puts each chain
// and its gate at its cluster (the enable then crosses the tile in <= 405-um registered hops, METHODOLOGY 12.13).
// xk (simulation only): one extra hop, the bench mutant that must FAIL when K + 1 > s - 1.
(* keep_hierarchy *)
module ot_a0_icg_hop #(
    parameter integer K = 0
) (
    input  wire ck,
    input  wire rst_n,
    input  wire en,
    input  wire xk,
    output wire gck
);
    wire e;
    generate if (K == 0) begin : g_k0
        wire e0 = en;
`ifdef SYNTHESIS
        assign e = e0;
`else
        reg x1;
        always @(posedge ck or negedge rst_n) if (!rst_n) x1 <= 1'b1; else x1 <= e0;
        assign e = xk ? x1 : e0;
`endif
    end else begin : g_kn
        reg [K-1:0] h;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) h <= {K{1'b1}};
            else h <= (h << 1) | K'(en);
`ifdef SYNTHESIS
        assign e = h[K-1];
`else
        reg x1;
        always @(posedge ck or negedge rst_n) if (!rst_n) x1 <= 1'b1; else x1 <= h[K-1];
        assign e = xk ? x1 : h[K-1];
`endif
    end endgenerate
`ifdef SYNTHESIS
    ICGx8DC_ASAP7_75t_R u_icg (.CLK(ck), .ENA(e), .SE(1'b0), .GCLK(gck));
`else
    reg en_l;
    /* verilator lint_off COMBDLY */
    always_latch if (!ck) en_l = e;      // ICG cell function: latch transparent while ck is low, AND with ck
    /* verilator lint_on COMBDLY */
    assign gck = ck & en_l;
`endif
endmodule
