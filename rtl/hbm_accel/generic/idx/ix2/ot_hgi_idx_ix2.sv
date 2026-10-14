`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX frame adapter ix2 (hbm-redesign-idx 2026-10-13; ot_hgi_idx_unit IXW = 3): a from-scratch regional
// form of ot_hgi_idx_index_w with the SAME ports, lane client format, selector ports and MUT 1 / MUT 2 (reference and
// golden: ot_hgi_idx_index[_w], tools/hgi_sim/machine.py u_idx_index).  This module is wires only; the leaves are
//   u_ln[0..7] ot_hgi_idx_ix2_lane  read lanes (physical tiles: lanes 0-3 / 4-7), static per-lane B -> C -> A walk
//   u_kp[0..1] ot_hgi_idx_ix2_kp    keep walk a lane quad: divider-free block -> (owner, ordinal)
//   u_qa       ot_hgi_idx_ix2_qa    head weights and query blocks
//   u_pk       ot_hgi_idx_ix2_pk    top-k / candidate beat FIFOs and compaction
//   u_wp       ot_hgi_idx_ix2_wp    sector packers and write lanes
//   u_kc       ot_hgi_idx_ix2_kc    ONE leaf: frame control ct (operand check, FSM, fs, done / fault) + keep bitmaps ks
// Differences to the reference contract: keep_en faults unless C.stride is a multiple of 64 words (reference: 32);
// NL must be 8; DL is unused (the landing FIFOs are 4 deep and need no reservation).  MUT 3 = keep divide mutant.
module ot_hgi_idx_ix2 #(
    parameter integer MUT = 0,
    parameter integer DL  = 4,
    parameter integer LQ  = 10,
    parameter integer NL  = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go_i,
    input  wire [11:0]   k_i,
    input  wire          cand_en_i, keep_en_i,
    input  wire [31:0]   n_i,
    input  wire [6:0]    rank_i,
    input  wire [19:0]   pos_i,
    input  wire [17:0]   a_base_i, b_base_i, c_base_i, o_base_i, r_base_i, d_base_i,
    input  wire [17:0]   d_stride_i,
    input  wire [17:0]   c_stride_i,
    input  wire [11:0]   c_n_i,
    input  wire          has_r_i,
    output wire          done,
    output wire          fault,
    output wire [NL*16-1:0]  wrq,
    input  wire [NL-1:0]     wrq_cr,
    input  wire [NL*257-1:0] wrr,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire [NL*280-1:0] wwq,
    input  wire [NL-1:0]     wwq_cr,
    input  wire [NL-1:0]     wwq_done,
    output wire              wg_req,
    input  wire              wg_gnt,
    output wire [89:0]   fs,
    output wire [1047:0] qb,
    input  wire          qbr,
    output wire [344:0]  kin,
    input  wire [611:0]  to,
    output wire          toc,
    input  wire [71:0]   co,
    output wire          coc,
    input  wire [1:0]    ev
);
    wire start, run, flush, qa_done, qa_bad, pk_done, pk_bad, wp_idle, kin_sent;
    wire [7:0] ln_idle, c_done, b_v, a_v, a_cr, c_v, c_cr; wire [2047:0] ab_d; wire [831:0] c_h; wire [63:0] c_f;
    wire [1:0] ks_v; wire [21:0] ks_ord;
    wire t_v, t_cr, d_v, d_cr; wire [3:0] t_n; wire [159:0] t_o; wire [135:0] t_r; wire [1:0] d_n; wire [65:0] d_p;
    genvar g;
    generate
        if (NL != 8) begin : g_nl  ot_hgi_idx_ix2_needs_NL_8 u_bad (); end
        for (g = 0; g < 8; g = g + 1) begin : g_ln
            ot_hgi_idx_ix2_lane #(.LQ(LQ)) u_ln (.clk(clk), .rst_n(rst_n), .lid(3'(g)), .start(start), .run(run),
                .keep_en_i(keep_en_i), .rank_i(rank_i), .a_base_i(a_base_i), .b_base_i(b_base_i), .c_base_i(c_base_i),
                .c_stride_i(c_stride_i), .c_n_i(c_n_i), .wrq(wrq[g*16 +: 16]), .wrq_cr(wrq_cr[g]), .wrr(wrr[g*257 +: 257]),
                .rg_gnt(rg_gnt), .ab_d(ab_d[g*256 +: 256]), .b_v(b_v[g]), .a_v(a_v[g]), .a_cr(a_cr[g]),
                .c_v(c_v[g]), .c_h(c_h[g*104 +: 104]), .c_f(c_f[g*8 +: 8]), .c_cr(c_cr[g]), .c_done(c_done[g]),
                .idle(ln_idle[g]));
        end
        for (g = 0; g < 2; g = g + 1) begin : g_kp
            ot_hgi_idx_ix2_kp #(.MUT(MUT)) u_kp (.clk(clk), .rst_n(rst_n), .start(start), .rank_i(rank_i),
                .c_v(c_v[g*4 +: 4]), .c_h(c_h[g*416 +: 416]), .c_f(c_f[g*32 +: 32]), .c_cr(c_cr[g*4 +: 4]),
                .ks_v(ks_v[g]), .ks_ord(ks_ord[g*11 +: 11]));
        end
    endgenerate
    ot_hgi_idx_ix2_qa #(.MUT(MUT)) u_qa (.clk(clk), .rst_n(rst_n), .start(start), .run(run), .keep_en_i(keep_en_i),
        .a_base_i(a_base_i), .b_base_i(b_base_i), .ab_d(ab_d), .b_v(b_v), .a_v(a_v), .a_cr(a_cr),
        .kin_sent(kin_sent), .qbr(qbr), .qb(qb), .qa_done(qa_done), .qa_bad(qa_bad));
    ot_hgi_idx_ix2_pk #(.MUT(MUT)) u_pk (.clk(clk), .rst_n(rst_n), .start(start), .run(run), .cand_en_i(cand_en_i),
        .to(to), .toc(toc), .co(co), .coc(coc), .t_v(t_v), .t_n(t_n), .t_o(t_o), .t_r(t_r), .t_cr(t_cr),
        .d_v(d_v), .d_n(d_n), .d_p(d_p), .d_cr(d_cr), .pk_done(pk_done), .pk_bad(pk_bad));
    ot_hgi_idx_ix2_wp #(.LQ(LQ)) u_wp (.clk(clk), .rst_n(rst_n), .start(start), .run(run), .flush(flush), .has_r_i(has_r_i),
        .o_base_i(o_base_i), .r_base_i(r_base_i), .d_base_i(d_base_i), .d_stride_i(d_stride_i),
        .t_v(t_v), .t_n(t_n), .t_o(t_o), .t_r(t_r), .t_cr(t_cr), .d_v(d_v), .d_n(d_n), .d_p(d_p), .d_cr(d_cr),
        .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .wg_req(wg_req), .wg_gnt(wg_gnt), .wp_idle(wp_idle));
    ot_hgi_idx_ix2_kc u_kc (.clk(clk), .rst_n(rst_n), .go_i(go_i), .k_i(k_i), .cand_en_i(cand_en_i), .keep_en_i(keep_en_i),
        .n_i(n_i), .rank_i(rank_i), .pos_i(pos_i), .a_lo_i(a_base_i[2:0]), .cs_lo_i(c_stride_i[5:0]), .ev(ev),
        .ln_idle(ln_idle), .qa_done(qa_done), .qa_bad(qa_bad), .pk_done(pk_done), .pk_bad(pk_bad), .wp_idle(wp_idle),
        .start(start), .run(run), .flush(flush), .fs(fs), .rg_req(rg_req), .done(done), .fault(fault),
        .ks_v(ks_v), .ks_ord(ks_ord), .c_done(c_done), .kin(kin), .kin_sent(kin_sent));
endmodule
`default_nettype wire
