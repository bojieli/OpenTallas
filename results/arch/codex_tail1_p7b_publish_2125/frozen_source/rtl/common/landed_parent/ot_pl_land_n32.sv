`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-CAPC4 (2026-10-20): opt-in NATIVE32-safe landing ring writer (lp.py spec "landing_writer": "n32").
// Same ports, slot layout, K / reset ages and read contract as ot_pl_land_chunk_w (ot_pl_land.sv, unchanged), so the
// unchanged ot_pl_land_chunk_r reads it.  Why: the mandatory pre-gate mapped native census (limit 32 loads incl. resets)
// FAILS ot_pl_land_local_w for any chunk >= 3 bits: its slot write enable is (rq && write_oh[s]), and Yosys/ABC fans the
// local rq flop out to every slot data / epoch mux (s81sl_capc5 gate 10-20 02:36: rq 120 loads at CHUNK_BITS 24).
// Here the slot data enable is a kept one-hot selector copy alone, one copy (ot_pl_land_n32_oh, own hierarchy) per 12 data
// bits (gate 02:42: one 24-bit write_oh drove 50 loads); rq only resets the copies and valid.
// Equivalence: while rq is low the reader sees vld = 0 (valid is reset) and stays cold (its own rq/warm), so a data slot
// written during reset is never read before it is rewritten after release: the read output o is identical edge for edge.
// The write epoch tags exist only for simulation (assertion inputs of ot_pl_land_local_r); synthesis drives epo 0.
// ---------------------------------------------------------------------------------------------------------------------
// one kept copy of the one-hot slot selector (distinct ID per copy: separate hierarchies, never merged back by Yosys)
(* keep_hierarchy = "yes" *)
module ot_pl_land_n32_oh #(parameter integer D = 4, ID = 0) (
    input wire ck, rq,
    output wire [D-1:0] oh
);
    (* keep *) reg [D-1:0] r;
    always @(posedge ck)
        if (!rq) r <= {{(D-1){1'b0}},1'b1};
        else     r <= {r[D-2:0], r[D-1]};
    assign oh = r;
endmodule

module ot_pl_land_n32_local_w #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer GB = 12                                  // data bits per kept selector copy (~2 GB + 2 loads)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);
    localparam integer NC = (W + GB - 1) / GB;
    reg rq;
    reg [D-1:0] valid;
    wire [NC*D-1:0] oh;                                        // copy g = oh[g*D +: D]
    always @(posedge ck) rq <= rsi;
    genvar s, g;
    generate for (g = 0; g < NC; g = g + 1) begin : g_oh
        ot_pl_land_n32_oh #(.D(D), .ID(g)) u_oh (.ck(ck), .rq(rq), .oh(oh[g*D +: D]));
    end endgenerate
    always @(posedge ck)
        if (!rq) valid <= 0;
        else     valid <= valid | oh[D-1:0];
    generate for (s=0;s<D;s=s+1) begin:g_slot
        for (g = 0; g < NC; g = g + 1) begin : g_grp
            localparam integer LO = g * GB;
            localparam integer GW = (W - LO < GB) ? W - LO : GB;
            reg [GW-1:0] dq;
            always @(posedge ck) if (oh[g*D + s]) dq <= i[LO +: GW];
            assign bank[s*W + LO +: GW] = dq;
        end
    end endgenerate
    assign vld = valid;
`ifndef SYNTHESIS
    reg [AW:0] wc;
    reg [AW:0] epoch [0:D-1];
    always @(posedge ck) if (!rq) wc <= 0; else wc <= wc + 1'b1;
    generate for (s=0;s<D;s=s+1) begin:g_ep
        always @(posedge ck) if (rq && oh[s]) epoch[s] <= wc;
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
`else
    assign epo = {(D*(AW+1)){1'b0}};
`endif
endmodule

module ot_pl_land_n32_chunk_w #(
    parameter integer W = 514, D = 4, CHUNK_BITS = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld
);
    genvar c, s;
    generate for (c = 0; c < (W + CHUNK_BITS - 1) / CHUNK_BITS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        wire [D*CW-1:0] cb;
        wire [D*(AW+1)-1:0] ce;
        wire [D-1:0] cv;
        (* keep_hierarchy = "yes" *) ot_pl_land_n32_local_w #(.W(CW), .D(D)) u_local (
            .ck(ck), .rsi(rsi), .i(i[c*CHUNK_BITS +: CW]), .bank(cb), .epo(ce), .vld(cv));
        for (s = 0; s < D; s = s + 1) begin : g_slot
            assign bank[s*W + c*CHUNK_BITS +: CW] = cb[s*CW +: CW];
        end
        assign vld[c*D +: D] = cv;
        if (c == 0) begin : g_tags
            assign epo = ce;
        end
    end endgenerate
`ifndef SYNTHESIS
    initial if (CHUNK_BITS < 1 || CHUNK_BITS > 24) $fatal(1, "ot_pl_land_n32_chunk_w: CHUNK_BITS must be 1..24");
`endif
endmodule
// Opt-in vector-reset form: identical per-chunk reset ages to ot_pl_land_split_w.
module ot_pl_land_n32_split_w #(
    parameter integer W = 1088, D = 4, CHUNK_BITS = 24, RG = 32,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer NC = (W + CHUNK_BITS - 1) / CHUNK_BITS
) (
    input wire ck,
    input wire [(NC + RG - 1) / RG - 1:0] rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D*NC-1:0] vld
);
    genvar c, s;
    generate for (c = 0; c < NC; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        wire [D*CW-1:0] cb;
        wire [D*(AW+1)-1:0] ce;
        wire [D-1:0] cv;
        (* keep_hierarchy = "yes" *) ot_pl_land_n32_local_w #(.W(CW), .D(D)) u_local (
            .ck(ck), .rsi(rsi[c / RG]), .i(i[c*CHUNK_BITS +: CW]), .bank(cb), .epo(ce), .vld(cv));
        for (s = 0; s < D; s = s + 1) begin : g_slot
            assign bank[s*W + c*CHUNK_BITS +: CW] = cb[s*CW +: CW];
        end
        assign vld[c*D +: D] = cv;
        if (c == 0) begin : g_tags
            assign epo = ce;
        end
    end endgenerate
`ifndef SYNTHESIS
    initial if (CHUNK_BITS < 1 || CHUNK_BITS > 24 || RG < 1 || RG > 32)
        $fatal(1, "ot_pl_land_n32_split_w: CHUNK_BITS must be 1..24, RG 1..32");
`endif
endmodule

`default_nettype wire
