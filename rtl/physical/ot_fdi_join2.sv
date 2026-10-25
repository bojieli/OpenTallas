`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// TOK-QK/C 2026-10-24 (KV boot fixes C1 + C2): order-based join of the two halves of a split FDI flit (core clock).
//
// The x12 host SerDes is two x6 halves at two die positions (sys_SW = flit[521:0], sys_SE = flit[1042:522]); each half
// crosses into the core clock in its own ot_fdi_phy_cdc and travels its own lane, each half's valid IN THE SAME LANE WORD
// as its data (one delay for valid and data by construction).  The halves therefore arrive with a lane-depth difference
// plus up to one cycle of synchroniser jitter each.  The k-th A half pairs with the k-th B half (like a multi-lane PHY's
// lane deskew): each half is queued (DEPTH entries) and a whole flit leaves, from a register, when both queues hold one.
// No cycle alignment between the halves is assumed, so neither a lane-depth difference nor sync jitter can split a flit
// (the old join was a same-cycle AND of the halves' valids = C1).  Order and values preserved; DEPTH must cover
// (max lane-depth difference + 2) entries; an overflow would lose a half = a sequence gap the adapter reports.
// rst_n: the link reset (flushes with the PHY halves' FIFOs).
// ---------------------------------------------------------------------------------------------------------------------
module ot_fdi_join2 #(
    parameter integer WA = 522,
    parameter integer WB = 521,
    parameter integer DEPTH = 16
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               a_v,
    input  wire [WA-1:0]      a_d,
    input  wire               b_v,
    input  wire [WB-1:0]      b_d,
    output reg                o_v,
    output reg  [WA+WB-1:0]   o_d        // {b, a}
);
    localparam integer AW = (DEPTH <= 2) ? 1 : $clog2(DEPTH);
    reg [WA-1:0] qa [0:DEPTH-1];
    reg [WB-1:0] qb [0:DEPTH-1];
    reg [AW-1:0] awp, arp, bwp, brp;
    reg [AW:0]   an, bn;
    wire pop = (an != 0) && (bn != 0);
    always @(posedge clk) begin
        if (a_v) qa[awp] <= a_d;
        if (b_v) qb[bwp] <= b_d;
        o_d <= {qb[brp], qa[arp]};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            awp <= 0; arp <= 0; bwp <= 0; brp <= 0; an <= 0; bn <= 0; o_v <= 1'b0;
        end else begin
            o_v <= pop;
            if (a_v) awp <= (awp == AW'(DEPTH - 1)) ? {AW{1'b0}} : awp + 1'b1;
            if (b_v) bwp <= (bwp == AW'(DEPTH - 1)) ? {AW{1'b0}} : bwp + 1'b1;
            if (pop) begin
                arp <= (arp == AW'(DEPTH - 1)) ? {AW{1'b0}} : arp + 1'b1;
                brp <= (brp == AW'(DEPTH - 1)) ? {AW{1'b0}} : brp + 1'b1;
            end
            an <= an + (a_v ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            bn <= bn + (b_v ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        end
    end
`ifndef SYNTHESIS
    integer max_skew = 0;
    always @(posedge clk) if (rst_n) begin
        if ((a_v && an == DEPTH && !pop) || (b_v && bn == DEPTH && !pop))
            $error("ot_fdi_join2 %m: half-flit queue overflow (lane-depth difference > DEPTH)");
        if (an > bn && int'(an - bn) > max_skew) max_skew = int'(an - bn);
        if (bn > an && int'(bn - an) > max_skew) max_skew = int'(bn - an);
    end
`endif
endmodule
