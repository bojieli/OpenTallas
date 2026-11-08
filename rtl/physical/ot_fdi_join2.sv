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
    parameter integer DEPTH = 16,
    // DIE-KV-93 11-08 (FDI join_rf TT -16.52 after its one ECO: arp[2] -> 12 BUFx2 fan-out levels -> o_d[262], the 4-bit
    // read pointers select 16 x 522 / 16 x 521 bits): RP_COPIES identical copies of arp / brp, each one selecting a
    // contiguous slice of its queue's read word (register replication of a high-fan-out select).  Same pointer value in
    // every copy every edge (same reset, same update), so o_d / o_v are identical every edge (bench).  1 = unchanged.
    parameter integer RP_COPIES = 1,
    // DIE-KV-93 11-08 (COORD 10:0x; RP_COPIES place WNS -180 ps is WRITE side: a_v -> AND4 entry decode -> 15 BUFx2
    // fan-out levels -> 522 enable muxes): WR_COPIES > 0 registers the one-hot entry write enables (from a_v and awp) in
    // WR_COPIES keep-copies, each copy writing one contiguous slice of a per-entry row from a registered copy of a_d.
    // Costs ONE input cycle (pin-cycle lever): a half is written, counted and poppable one edge later, so o_v / o_d are
    // the WR_COPIES = 0 stream delayed by exactly one edge (bench).  0 = unchanged.
    parameter integer WR_COPIES = 0
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
    wire [WA-1:0] qa_r [0:DEPTH-1];
    wire [WB-1:0] qb_r [0:DEPTH-1];
    wire a_wv, b_wv;                                   // valid as counted (WR_COPIES > 0: one edge after a_v / b_v)
    generate if (RP_COPIES > 1) begin : g_rpc
        localparam integer SA = (WA + RP_COPIES - 1) / RP_COPIES, SB = (WB + RP_COPIES - 1) / RP_COPIES;
        (* keep = "true" *) reg [AW-1:0] arp_c [0:RP_COPIES-1];
        (* keep = "true" *) reg [AW-1:0] brp_c [0:RP_COPIES-1];
        genvar c;
        for (c = 0; c < RP_COPIES; c = c + 1) begin : g_c
            localparam integer A0 = (c * SA < WA) ? c * SA : WA, A1 = ((c + 1) * SA < WA) ? (c + 1) * SA : WA;
            localparam integer B0 = (c * SB < WB) ? c * SB : WB, B1 = ((c + 1) * SB < WB) ? (c + 1) * SB : WB;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin arp_c[c] <= {AW{1'b0}}; brp_c[c] <= {AW{1'b0}}; end
                else if (pop) begin
                    arp_c[c] <= (arp_c[c] == AW'(DEPTH - 1)) ? {AW{1'b0}} : arp_c[c] + 1'b1;
                    brp_c[c] <= (brp_c[c] == AW'(DEPTH - 1)) ? {AW{1'b0}} : brp_c[c] + 1'b1;
                end
            if (A1 > A0) begin : g_a
                always @(posedge clk) o_d[A1-1:A0] <= qa_r[arp_c[c]][A1-1:A0];
            end
            if (B1 > B0) begin : g_b
                always @(posedge clk) o_d[WA+B1-1:WA+B0] <= qb_r[brp_c[c]][B1-1:B0];
            end
        end
    end else begin : g_rp1
        always @(posedge clk) o_d <= {qb_r[brp], qa_r[arp]};
    end endgenerate
    generate if (WR_COPIES > 0) begin : g_wrc
        localparam integer SA = (WA + WR_COPIES - 1) / WR_COPIES, SB = (WB + WR_COPIES - 1) / WR_COPIES;
        (* keep = "true" *) reg [DEPTH-1:0] wa_c [0:WR_COPIES-1];
        (* keep = "true" *) reg [DEPTH-1:0] wb_c [0:WR_COPIES-1];
        reg [WA-1:0] a_d_r;
        reg [WB-1:0] b_d_r;
        reg a_v_r, b_v_r;
        always @(posedge clk) begin a_d_r <= a_d; b_d_r <= b_d; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin a_v_r <= 1'b0; b_v_r <= 1'b0; end
            else begin a_v_r <= a_v; b_v_r <= b_v; end
        assign a_wv = a_v_r;
        assign b_wv = b_v_r;
        genvar c, e;
        for (c = 0; c < WR_COPIES; c = c + 1) begin : g_c
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin wa_c[c] <= {DEPTH{1'b0}}; wb_c[c] <= {DEPTH{1'b0}}; end
                else begin
                    wa_c[c] <= a_v ? ({{(DEPTH-1){1'b0}}, 1'b1} << awp) : {DEPTH{1'b0}};
                    wb_c[c] <= b_v ? ({{(DEPTH-1){1'b0}}, 1'b1} << bwp) : {DEPTH{1'b0}};
                end
        end
        for (e = 0; e < DEPTH; e = e + 1) begin : g_e
            reg [WA-1:0] ra;
            reg [WB-1:0] rb;
            for (c = 0; c < WR_COPIES; c = c + 1) begin : g_c
                localparam integer A0 = (c * SA < WA) ? c * SA : WA, A1 = ((c + 1) * SA < WA) ? (c + 1) * SA : WA;
                localparam integer B0 = (c * SB < WB) ? c * SB : WB, B1 = ((c + 1) * SB < WB) ? (c + 1) * SB : WB;
                if (A1 > A0) begin : g_a
                    always @(posedge clk) if (wa_c[c][e]) ra[A1-1:A0] <= a_d_r[A1-1:A0];
                end
                if (B1 > B0) begin : g_b
                    always @(posedge clk) if (wb_c[c][e]) rb[B1-1:B0] <= b_d_r[B1-1:B0];
                end
            end
            assign qa_r[e] = ra;
            assign qb_r[e] = rb;
        end
    end else begin : g_wr1
        always @(posedge clk) begin
            if (a_v) qa[awp] <= a_d;
            if (b_v) qb[bwp] <= b_d;
        end
        assign a_wv = a_v;
        assign b_wv = b_v;
        genvar e;
        for (e = 0; e < DEPTH; e = e + 1) begin : g_e
            assign qa_r[e] = qa[e];
            assign qb_r[e] = qb[e];
        end
    end endgenerate
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
            an <= an + (a_wv ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            bn <= bn + (b_wv ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        end
    end
`ifndef SYNTHESIS
    integer max_skew = 0;
    always @(posedge clk) if (rst_n) begin
        if ((a_wv && an == DEPTH && !pop) || (b_wv && bn == DEPTH && !pop))
            $error("ot_fdi_join2 %m: half-flit queue overflow (lane-depth difference > DEPTH)");
        if (an > bn && int'(an - bn) > max_skew) max_skew = int'(an - bn);
        if (bn > an && int'(bn - an) > max_skew) max_skew = int'(bn - an);
    end
`endif
endmodule
