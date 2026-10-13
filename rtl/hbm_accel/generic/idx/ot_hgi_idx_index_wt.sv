`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX frame adapter, WIDE-LANE form, TILED (el1013-idx-tiles 2026-10-13; ot_hgi_idx_unit IXW = 2).
// Same ports, parameters and transaction-level contract as ot_hgi_idx_index_w (the flat conservative line, untouched);
// this wrapper holds nothing but six hard-leaf instances of five masters and wires (no parent logic, no parent route):
//   u_lane0 / u_lane1  ot_hgi_idxw_lane   read lanes 0..3 / 4..7 (one master, no differing parameter)
//   u_qcore            ot_hgi_idxw_qcore  frame FSM, chunk walk, group-order merge, weights, query ring, fs / qb
//   u_keep             ot_hgi_idxw_keep   6-stage exact ordinal divide, K-result FIFO, keep bitmap, kin
//   u_beat             ot_hgi_idxw_beat   to / co beat FIFOs and compaction
//   u_wr               ot_hgi_idxw_wr     sector packers, lane arbiter, wwq
// SPEC: results/arch/hbm_b2_idx_ixw1_1013/SPEC.md "Tiled redesign".  Every leaf port is registered on both sides; the
// seams S1..S4 carry finite credits / reservations (no combinational ready, no stall across a leaf).
// MUT: 1 / 2 inherited (head weight of the next head, R from the next lane); bench-only 11 one divider stage wrong,
// 12 one regional pointer copy off by one, 13 one credit returned twice.  DL = landing depth inside the lane leaf.
module ot_hgi_idx_index_wt #(
    parameter integer MUT = 0,
    parameter integer DL  = 4,
    parameter integer LQ  = 8,
    parameter integer NL  = 8       // fixed 8 (two 4-lane leaves)
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
    wire [18:0] dsc0, dsc1; wire pop0, pop1, obv0, obv1, rdy0, rdy1; wire [1023:0] ob0, ob1;
    wire [1023:0] kc_d; wire kc_ci, kc_cv, kc_last; wire [1:0] kc_slot; wire [2:0] kc_cnt; wire [12:0] kc_shi;
    wire kstart, k_keep_en, kcr, kin_sent; wire [6:0] k_rank; wire [17:0] k_c_base; wire [11:0] k_c_n;
    wire bstart, b_cand_en, b_idle, b_bad;
    wire wstart, wflush, wabort, w_has_r, w_done; wire [17:0] w_o_base, w_r_base, w_d_base, w_dv_base;
    wire t2_v, t2_cr, d1_v, d1_cr; wire [3:0] t2_n, d1_n; wire [255:0] t2_o, t2_r; wire [63:0] d1_i, d1_x;
    ot_hgi_idxw_lane #(.MUT(MUT), .DL(DL), .LQ(LQ)) u_lane0 (.clk(clk), .rst_n(rst_n), .wrr_i(wrr[4*257-1:0]),
        .wrq_o(wrq[4*16-1:0]), .wrq_cr_i(wrq_cr[3:0]), .gnt_i(rg_gnt), .dsc_i(dsc0), .pop_i(pop0), .ob_o(ob0),
        .ob_v_o(obv0), .rdy_o(rdy0));
    ot_hgi_idxw_lane #(.MUT(MUT), .DL(DL), .LQ(LQ)) u_lane1 (.clk(clk), .rst_n(rst_n), .wrr_i(wrr[8*257-1:4*257]),
        .wrq_o(wrq[8*16-1:4*16]), .wrq_cr_i(wrq_cr[7:4]), .gnt_i(rg_gnt), .dsc_i(dsc1), .pop_i(pop1), .ob_o(ob1),
        .ob_v_o(obv1), .rdy_o(rdy1));
    ot_hgi_idxw_qcore #(.MUT(MUT)) u_qcore (.clk(clk), .rst_n(rst_n), .go_i(go_i), .k_i(k_i), .cand_en_i(cand_en_i),
        .keep_en_i(keep_en_i), .n_i(n_i), .rank_i(rank_i), .pos_i(pos_i), .a_base_i(a_base_i), .b_base_i(b_base_i),
        .c_base_i(c_base_i), .o_base_i(o_base_i), .r_base_i(r_base_i), .d_base_i(d_base_i), .d_stride_i(d_stride_i),
        .c_stride_i(c_stride_i), .c_n_i(c_n_i), .has_r_i(has_r_i), .done_o(done), .fault_o(fault), .rg_req_o(rg_req),
        .fs_o(fs), .qb_o(qb), .qbr_i(qbr), .ev_i(ev),
        .dsc0_o(dsc0), .dsc1_o(dsc1), .pop0_o(pop0), .pop1_o(pop1), .ob0_i(ob0), .ob1_i(ob1), .ob0_v_i(obv0),
        .ob1_v_i(obv1), .rdy0_i(rdy0), .rdy1_i(rdy1),
        .kc_d_o(kc_d), .kc_ci_o(kc_ci), .kc_cv_o(kc_cv), .kc_last_o(kc_last), .kc_slot_o(kc_slot), .kc_cnt_o(kc_cnt),
        .kc_shi_o(kc_shi), .kstart_o(kstart), .keep_en_o(k_keep_en), .rank_o(k_rank), .c_base_o(k_c_base), .c_n_o(k_c_n),
        .kcr_i(kcr), .kin_sent_i(kin_sent),
        .bstart_o(bstart), .cand_en_o(b_cand_en), .b_idle_i(b_idle), .b_bad_i(b_bad),
        .wstart_o(wstart), .flush_o(wflush), .wabort_o(wabort), .has_r_o(w_has_r), .o_base_o(w_o_base),
        .r_base_o(w_r_base), .d_base_o(w_d_base), .dv_base_o(w_dv_base), .w_done_i(w_done));
    ot_hgi_idxw_keep #(.MUT(MUT)) u_keep (.clk(clk), .rst_n(rst_n), .kc_d_i(kc_d), .kc_ci_i(kc_ci), .kc_cv_i(kc_cv),
        .kc_last_i(kc_last), .kc_slot_i(kc_slot), .kc_cnt_i(kc_cnt), .kc_shi_i(kc_shi), .kstart_i(kstart),
        .keep_en_i(k_keep_en), .rank_i(k_rank), .c_base_i(k_c_base), .c_n_i(k_c_n), .kcr_o(kcr), .kin_sent_o(kin_sent),
        .kin_o(kin));
    ot_hgi_idxw_beat #(.MUT(MUT)) u_beat (.clk(clk), .rst_n(rst_n), .to_i(to), .toc_o(toc), .co_i(co), .coc_o(coc),
        .bstart_i(bstart), .cand_en_i(b_cand_en), .b_idle_o(b_idle), .b_bad_o(b_bad),
        .t2_v_o(t2_v), .t2_n_o(t2_n), .t2_o_o(t2_o), .t2_r_o(t2_r), .t2_cr_i(t2_cr),
        .d1_v_o(d1_v), .d1_n_o(d1_n), .d1_i_o(d1_i), .d1_x_o(d1_x), .d1_cr_i(d1_cr));
    ot_hgi_idxw_wr #(.LQ(LQ)) u_wr (.clk(clk), .rst_n(rst_n), .wwq_o(wwq), .wwq_cr_i(wwq_cr), .wwq_done_i(wwq_done),
        .wg_req_o(wg_req), .wg_gnt_i(wg_gnt), .t2_v_i(t2_v), .t2_n_i(t2_n), .t2_o_i(t2_o), .t2_r_i(t2_r), .t2_cr_o(t2_cr),
        .d1_v_i(d1_v), .d1_n_i(d1_n), .d1_i_i(d1_i), .d1_x_i(d1_x), .d1_cr_o(d1_cr),
        .wstart_i(wstart), .flush_i(wflush), .wabort_i(wabort), .has_r_i(w_has_r), .o_base_i(w_o_base),
        .r_base_i(w_r_base), .d_base_i(w_d_base), .dv_base_i(w_dv_base), .w_done_o(w_done));
endmodule
`default_nettype wire
