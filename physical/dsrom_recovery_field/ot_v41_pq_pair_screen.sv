`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_pq_pair_screen: physical-screen top of the PER-PAIR hardware that DS-ROM recovery lever "field" (PQ, 2026-
// 10-04) adds: the pair's configuration loader with the pending load (ot_v41_pair_pq_ld) and the element's banked
// output tags / op parity / bank guard (ot_v41_elem_pq_tags), wired exactly as in ot_v41_pair_pq_w17w10 and
// ot_v41_rom_elem_pq_w10 (FAST: go and go_tag registered at the element boundary, configuration not).  The element
// signals they meet are registers in context (walker state, the segment tree's output tag, the partial's output
// registers o_row / o_seg / o_n / o_v), so they are registers here too and every timed path is register to register
// as in the pair.  Screen only: the configuration ROM is an input port.
// ---------------------------------------------------------------------------
module ot_v41_pq_pair_screen #(
    parameter integer NSEG = 8,
    parameter integer PHW = 6,
    parameter integer PQ = 1,
    parameter integer NB = 2,
    parameter integer MTP = 1,
    parameter integer TRW = $clog2(NSEG) + 1,
    parameter integer AW = $clog2((3 * NSEG + 1) << PHW)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              cfg_go,
    input  wire [PHW-1:0]    cfg_ph,
    input  wire [2:0]        cfg_np,
    input  wire              go,
    input  wire [1:0]        go_tag,
    output wire [AW-1:0]     cm_a,
    input  wire [47:0]       cm_q,
    input  wire              i_walk_busy,
    input  wire              i_walking,
    input  wire [NB-1:0]     i_t_v,
    input  wire [NB*TRW-1:0] i_t_tree,
    input  wire [NB*3-1:0]   i_t_pos,
    output reg  [NB-1:0]     o_v,
    output reg  [NB*16-1:0]  o_row,
    output reg  [NB*5-1:0]   o_seg,
    output reg  [NB*5-1:0]   o_n,
    output reg  [47:0]       o_cfg,
    output reg               o_go_e,
    output reg               o_tp,
    output reg               o_swap,
    output reg  [339:0]      o_lv,
    output wire              fault
);
    // element-side registers (context)
    reg walk_busy, walking;
    reg [NB-1:0] t_v;
    reg [NB*TRW-1:0] t_tree;
    reg [NB*3-1:0] t_pos;
    always @(posedge clk) begin
        walk_busy <= i_walk_busy; walking <= i_walking; t_v <= i_t_v; t_tree <= i_t_tree; t_pos <= i_t_pos;
    end
    wire        c_v, go_p, ld_busy, f_ld, f_tg, bank_free, sh_free, swap, tp;
    wire [4:0]  c_a;
    wire [47:0] c_d;
    ot_v41_pair_pq_ld #(.NSEG(NSEG), .PHW(PHW), .PQ(PQ)) u_ld (.clk(clk), .rst_n(rst_n), .cfg_go(cfg_go),
        .cfg_ph(cfg_ph), .cfg_np(cfg_np), .go(go), .e_sh_free(sh_free), .e_bank_free(bank_free), .cm_a(cm_a),
        .cm_q(cm_q), .c_v(c_v), .c_a(c_a), .c_d(c_d), .go_e(go_p), .ld_busy(ld_busy), .fault(f_ld));
    // the element's FAST input registers for go / go_tag
    reg r_go;
    reg [1:0] r_tag;
    always @(posedge clk or negedge rst_n) if (!rst_n) r_go <= 1'b0; else r_go <= go_p;
    always @(posedge clk) r_tag <= go_tag;
    wire [NB-1:0] q_idle;
    wire [NB*16-1:0] q_row;
    wire [NB*5-1:0] q_idx, q_n;
    ot_v41_elem_pq_tags #(.NSEG(NSEG), .NB(NB), .MTP(MTP), .PQ(PQ)) u_tg (.clk(clk), .rst_n(rst_n), .cfg_v(c_v),
        .cfg_a(c_a), .cfg_d(c_d[25:0]), .go_e(r_go), .go_tag(r_tag), .walk_busy(walk_busy), .walking(walking),
        .tp(tp), .bank_free(bank_free), .sh_free(sh_free), .swap(swap), .fault(f_tg), .t_tree(t_tree), .t_pos(t_pos), .q_idle(q_idle),
        .q_row(q_row), .q_idx(q_idx), .q_n(q_n));
    // the element's walker-side configuration: shadow (written by the load) and live (copied on swap), ~340 bits as
    // in ot_v41_rom_elem_pq_w10 (8 segments x 17 + 8 classes x 22 + 20): the swap's fan-out
    reg [339:0] sh, lv;
    always @(posedge clk) begin
        if (c_v) sh <= {sh[339-43:0], c_d[42:0]};
        if (swap) lv <= sh;
    end
    integer m;
    always @(posedge clk) begin
        for (m = 0; m < NB; m = m + 1) o_v[m] <= t_v[m] && !q_idle[m];
        o_lv <= lv;
        o_row <= q_row; o_seg <= q_idx; o_n <= q_n; o_cfg <= c_d; o_go_e <= r_go; o_tp <= tp; o_swap <= swap;
    end
    assign fault = f_ld | f_tg;
endmodule
