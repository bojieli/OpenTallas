`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// EDGE INDEX SCORER, hub side: the exact global top-K of the four per-stack
// candidate lists, in ascending position order.
//
//   ot_dsrom_edge_merge4  four stack lists (each ascending, <= K) -> one list in
//                         ascending GLOBAL position, WM elements per cycle;
//   pack                  WM-lane beats -> W-lane lines (dense);
//   ot_hdc_tselect        the qualified threshold selector (unchanged): the K
//                         largest, ties to the lower position, emitted in
//                         arrival order = ascending position.
// The stacks interleave positions in 16-key chunks, so their lists cannot be
// concatenated; the merge restores the position order the selector's tie rule
// and the attention's row order need (golden: sorted(topk_lowest_index(...))).
//
// The selector's line memory (<= 4K/W lines) is one 1R1W memory; its reads are
// issued one cycle early from the selector's sequential pass address
// ((re ? raddr + 1 : 0), asserted in simulation) and registered after the
// macro, so the macro's clk->q is a full cycle off the selector's logic.
// ---------------------------------------------------------------------------
module ot_dsrom_edge_hub #(
    parameter integer WM    = 16,     // link lanes = merge lanes
    parameter integer W     = 64,     // selector lanes
    parameter integer VW    = 16,
    parameter integer IW    = 20,
    parameter integer K     = 512,
    parameter integer MACRO = 0,
    parameter integer CONTIGUOUS = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               start,          // new query: clears the merge
    input  wire [3:0]         i_valid,
    output wire [3:0]         i_ready,
    input  wire [3:0]         i_last,
    input  wire [4*WM-1:0]    i_lv,
    input  wire [4*WM*VW-1:0] i_val,
    input  wire [4*WM*IW-1:0] i_idx,
    output wire               o_valid,        // selected, ascending position, W lanes packed
    output wire               o_last,
    output wire [W-1:0]       o_lv,
    output wire [W*VW-1:0]    o_val,
    output wire [W*IW-1:0]    o_idx,
    output wire               busy
);
    localparam integer EW  = 1 + VW + IW;
    localparam integer QN  = W / WM;
    localparam integer TAW = $clog2((4 * K + W - 1) / W);
    localparam integer KW  = $clog2(K + 1);
    localparam [KW-1:0] KK = K;

    wire              m_v, m_l;
    wire              m_r;
    wire [WM-1:0]     m_lv;
    wire [WM*IW-1:0]  m_idx;
    wire [WM*VW-1:0]  m_val;
    generate if (CONTIGUOUS != 0) begin : g_concat
        // Lists are disjoint contiguous ranges, already position ordered.
        // Consume the empty terminal beat too; only stack 3 ends the union.
        reg [2:0] side;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) side <= 0;
            else if (start) side <= 0;
            else if (m_v && m_r && i_last[side[1:0]]) side <= side + 1'b1;
        end
        assign m_v = side < 4 && i_valid[side[1:0]];
        assign m_l = side == 3 && i_last[side[1:0]];
        assign m_lv = i_lv[WM*side[1:0] +: WM];
        assign m_idx = i_idx[WM*IW*side[1:0] +: WM*IW];
        assign m_val = i_val[WM*VW*side[1:0] +: WM*VW];
        assign i_ready = side < 4 ? (4'b0001 << side[1:0]) & {4{m_r}} : 4'b0;
    end else begin : g_roundrobin
        ot_dsrom_edge_merge4 #(.W(WM), .IW(IW), .PW(VW)) u_merge (
            .clk(clk), .rst_n(rst_n), .start(start),
            .i_valid(i_valid), .i_ready(i_ready), .i_last(i_last), .i_lv(i_lv), .i_idx(i_idx), .i_pay(i_val),
            .o_valid(m_v), .o_ready(m_r), .o_last(m_l), .o_lv(m_lv), .o_idx(m_idx), .o_pay(m_val));
    end endgenerate

    // -- pack WM-lane beats into W-lane lines ----------------------------------------------------
    reg              p_v, p_l;
    reg  [W-1:0]     p_lv;
    reg  [W*VW-1:0]  p_val;
    reg  [W*IW-1:0]  p_idx;
    reg  [$clog2(QN+1)-1:0] pq;
    wire             t_in_ready;
    wire             p_take = p_v && t_in_ready;
    assign m_r = !p_v || p_take;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin p_v <= 1'b0; p_l <= 1'b0; pq <= 0; p_lv <= 0; end
        else if (start) begin p_v <= 1'b0; p_l <= 1'b0; pq <= 0; p_lv <= 0; end
        else begin
            if (p_take) begin p_v <= 1'b0; p_lv <= 0; end
            if (m_v && m_r) begin
                p_lv[WM*pq +: WM]       <= m_lv;
                p_val[WM*VW*pq +: WM*VW] <= m_val;
                p_idx[WM*IW*pq +: WM*IW] <= m_idx;
                if (pq == QN - 1 || m_l) begin p_v <= 1'b1; p_l <= m_l; pq <= 0; end
                else pq <= pq + 1'b1;
                if (pq == 0) begin
                    // a new line: clear the lanes above this beat
                    p_lv[W-1:WM] <= 0;
                end
            end
        end
    end

    // -- selector + its line memory ------------------------------------------------------------
    wire              t_out_valid, t_out_last, t_busy, t_we, t_re;
    wire [W-1:0]      t_out_lv, t_out_ninf;
    wire [TAW-1:0]    t_wa, t_ra;
    wire [W*EW-1:0]   t_wd;
    reg  [W*EW-1:0]   t_rd;
    wire [W*EW-1:0]   r_q;
    wire [TAW:0]      pred = t_re ? {1'b0, t_ra} + 1'b1 : {(TAW+1){1'b0}};
    reg               rq1;
    ot_dsrom_edge_ram #(.AW(TAW), .DW(W*EW), .MACRO(MACRO)) u_lmem (
        .clk(clk), .re(1'b1), .raddr(pred[TAW-1:0]), .rdata(r_q),
        .we(t_we), .waddr(t_wa), .wdata(t_wd));
    always @(posedge clk) t_rd <= r_q;
    ot_hdc_tselect #(.W(W), .VW(VW), .IW(IW), .K(K), .AW(TAW)) u_tsel (
        .clk(clk), .rst_n(rst_n), .in_valid(p_v), .in_ready(t_in_ready), .in_last(p_l),
        .in_lv(p_lv), .in_val(p_val), .in_idx(p_idx), .in_k(KK),
        .out_valid(t_out_valid), .out_last(t_out_last), .out_lv(t_out_lv), .out_val(o_val),
        .out_idx(o_idx), .out_ninf(t_out_ninf),
        .mem_we(t_we), .mem_waddr(t_wa), .mem_wdata(t_wd), .mem_re(t_re),
        .mem_raddr(t_ra), .mem_rdata(t_rd), .busy(t_busy));
    assign o_valid = t_out_valid;
    assign o_last  = t_out_last;
    assign o_lv    = t_out_lv;
    assign busy    = t_busy || p_v || m_v || (|i_valid);

`ifndef SYNTHESIS
    reg [TAW-1:0] pq_a;
    reg           pq_v;
    always @(posedge clk) begin
        pq_v <= rst_n;
        pq_a <= pred[TAW-1:0];
        if (rst_n && t_re && !(pq_v && pq_a == t_ra))
            $fatal(1, "edge hub: selector read %0d not predicted", t_ra);
        if (rst_n && t_we && t_re && t_wa == t_ra)
            $fatal(1, "edge hub: line memory read/write collision");
    end
`endif
endmodule
