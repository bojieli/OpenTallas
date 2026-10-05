// Experimental companion: PQ default off; no adoption or clock claim beyond its own screen.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_elem_pq_tags: the PQ additions of ot_v41_rom_elem_pq_w10 (DS-ROM recovery lever "field", 2026-10-04) in
// one module, so they are screened physically on their own:
//
//   * the output-tag configuration fields (segment row per macro, segment index, segments in row), banked when
//     PQ = 1: a configuration load writes bank `wbank` (the next op's), the partial at the segment-tree exit reads
//     the bank of its own op (its tree parity with the position parity removed);
//   * the op bank / segment-tree parity `tp` (= the running op's bank) and each bank's 2-bit op tag, which replaces
//     row bits [15:14] of every partial (real rows are < 2^14; bit 15 of a configured row still marks an idle half);
//   * the bank guard: a bank is live from its op's go until DRAIN cycles after its walkers stop; `bank_free` says
//     the next load may write `wbank`; writing a live bank or a go while walking is a fault;
//   * the configuration SHADOW control: a load fills the element's shadow of the walker-side fields (it may run
//     while the current op walks); when the shadow is full and the walkers are idle it is copied into the live
//     fields (`swap`), and a go is accepted SETTLE cycles later (the element's registered sub-block facts re-derive);
//     a load into a full shadow, or a go before the copy has settled, is a fault.
//
// PQ = 0: one bank, tp = 0, rows unchanged -- the ot_v41_rom_elem_w10 behaviour.
// ---------------------------------------------------------------------------
module ot_v41_elem_pq_tags #(
    parameter integer NSEG = 8,
    parameter integer NB = 2,
    parameter integer MTP = 1,
    parameter integer PQ = 0,
    parameter integer DRAIN = 127,
    parameter integer SETTLE = 5,
    // derived
    parameter integer SW = $clog2(NSEG),
    parameter integer TRW = SW + (MTP != 0 ? 1 : 0)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              cfg_v,
    input  wire [4:0]        cfg_a,
    input  wire [25:0]       cfg_d,
    input  wire              go_e,
    input  wire [1:0]        go_tag,
    input  wire              walk_busy,
    input  wire              walking,
    output reg               tp,
    output wire              bank_free,
    output wire              sh_free,
    output wire              swap,
    output reg               fault,
    input  wire [NB*TRW-1:0] t_tree,
    input  wire [NB*3-1:0]   t_pos,
    output wire [NB-1:0]     q_idle,
    output wire [NB*16-1:0]  q_row,
    output wire [NB*5-1:0]   q_idx,
    output wire [NB*5-1:0]   q_n
);
    localparam integer NBK = PQ != 0 ? 2 : 1;
    localparam integer RW = $clog2(NB * NSEG);
    reg [15:0] s_row [0:NBK*NB*NSEG-1];   // [bank][macro * NSEG + segment]
    reg [4:0]  s_idx [0:NBK*NSEG-1];
    reg [4:0]  s_n   [0:NBK*NSEG-1];
    reg        wbank;
    reg [1:0]  otag [0:1];
    wire       wb = wbank & (PQ != 0);
    always @(posedge clk) if (cfg_v) begin
        if ({27'd0, cfg_a} < NSEG) begin
            s_row[{wb, RW'(cfg_a[SW-1:0])}] <= cfg_d[15:0];
            s_idx[{wb, cfg_a[SW-1:0]}] <= cfg_d[20:16];
            s_n[{wb, cfg_a[SW-1:0]}]   <= cfg_d[25:21];
        end else if ({27'd0, cfg_a} > 2 * NSEG) begin   // 2NSEG+1+s: the row of segment s on the second macro
            s_row[{wb, RW'(NSEG + cfg_a[SW-1:0] - 1)}] <= cfg_d[15:0];
        end
    end
    genvar mb;
    generate for (mb = 0; mb < NB; mb = mb + 1) begin : g_q
        wire [TRW-1:0] tt = t_tree[TRW*mb +: TRW];
        wire [SW-1:0]  ts = tt[SW-1:0];
        wire           bk = (PQ != 0) && ((MTP != 0) ? (tt[TRW-1] ^ t_pos[3*mb]) : 1'b0);
        wire [15:0]    r = s_row[{bk, RW'(mb * NSEG) + RW'(ts)}];
        assign q_idle[mb] = r[15];
        assign q_row[16*mb +: 16] = (PQ != 0) ? {otag[bk], r[13:0]} : r;
        assign q_idx[5*mb +: 5] = s_idx[{bk, ts}];
        assign q_n[5*mb +: 5] = s_n[{bk, ts}];
    end endgenerate
    reg [7:0] gcnt [0:1];
    // a go starting this cycle switches the load bank to ~wbank (and makes wbank live): judge the bank the load
    // will actually write
    wire      nbank = go_e ? ~wbank : wbank;
    assign bank_free = (PQ == 0) || gcnt[nbank] == 8'd0;
    reg       sh_full;
    reg [2:0] settle;
    localparam integer CW = 3 * NSEG + 1;
    assign sh_free = (PQ == 0) || !sh_full;
    assign swap = (PQ != 0) && sh_full && !walking && !go_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wbank <= 1'b0; tp <= 1'b0; gcnt[0] <= 8'd0; gcnt[1] <= 8'd0; fault <= 1'b0; sh_full <= 1'b0; settle <= 3'd0;
            otag[0] <= 2'd0; otag[1] <= 2'd0;
        end else if (PQ != 0) begin
            if (go_e) begin
                tp <= wbank; wbank <= ~wbank; otag[wbank] <= go_tag;
            end
            gcnt[0] <= ((go_e && !wbank) || (walk_busy && !tp)) ? DRAIN[7:0] : (gcnt[0] != 8'd0 ? gcnt[0] - 8'd1 : 8'd0);
            gcnt[1] <= ((go_e && wbank) || (walk_busy && tp)) ? DRAIN[7:0] : (gcnt[1] != 8'd0 ? gcnt[1] - 8'd1 : 8'd0);
            if (cfg_v && gcnt[wbank] != 8'd0) fault <= 1'b1;
            if (cfg_v && sh_full) fault <= 1'b1;
            if (go_e && (walking || sh_full || settle != 3'd0)) fault <= 1'b1;
            if (cfg_v && {27'd0, cfg_a} == CW - 1) sh_full <= 1'b1;          // the last word of a load
            else if (swap) sh_full <= 1'b0;
            settle <= swap ? 3'(SETTLE) : (settle != 3'd0 ? settle - 3'd1 : 3'd0);
        end
    end
endmodule
