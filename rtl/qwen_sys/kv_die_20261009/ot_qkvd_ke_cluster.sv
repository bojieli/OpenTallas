`timescale 1ns/1ps
// q13-kvleaves 2026-10-13: the KV end of the die link as a THIN cluster (ot_qkvd_kv_end SPL=1): hard children only
// (ot_qkvd_ke_tiles.sv + the pin-registered link buffers ot_qkvd_sbufp / ot_qkvd_fbuf8p), no register and no logic of
// its own (three tied strap buses).  Every seam is flop -> wire -> flop except the TX head mux in ot_qkvd_ke_tm (buffer dout flop ->
// wire -> 2 gate levels -> tf0) and the per-slice head-capture enable in ot_qkvd_ke_ro.  See ot_qkvd_ke_tiles.sv.
// Buffers: TX class 4 / 5 (UCX deep) sbufp, class 6 fbuf8p; RX class 0 fbuf8p, 1 sbufp, 2 fbuf8p, 3 sbufp.
module ot_qkvd_ke_cluster #(
    parameter integer QD = 48,
    parameter integer UCX = 48,
    parameter integer FCR_RES = 32,
    parameter integer MUT = 0                  // bench only: 1 = one extra link credit on TX class 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [2:0]      t_v,
    input  wire [3*528-1:0] t_d,
    output wire [2:0]      t_cr,
    output wire [3:0]      r_v,
    output wire [4*528-1:0] r_d,
    input  wire [3:0]      r_cr,
    input  wire            tx_up,
    output wire            tx_v,
    output wire [547:0]    tx_flit,
    input  wire            rx_v,
    input  wire [547:0]    rx_flit,
    output wire            fault,
    output wire [4:0]      fault_cause
);
    localparam integer W = 528;
    wire        rsw, rs_s, rs_n, rs_ta, rs_tb;
    wire [2:0]  civ, pp_t, gq, gq2, psh_t;
    wire [3:0]  crq, pp_r, rqq, psh_r;
    wire        rqv, upq, tv0;
    wire [19:0] rqh, tf0h;
    wire [5:0]  flt;
    wire [3*W-1:0] ce_d, ib_head;
    wire [4*W-1:0] re_w, rb_head;
    wire [2:0]  ib_empty;
    wire [3:0]  rb_empty;
    wire [7:0]  cfg_ucx  = 8'(UCX);
    wire [7:0]  cfg_qd   = 8'(QD);
    wire [7:0]  cfg_fcr0 = 8'(FCR_RES + (MUT == 1 ? 1 : 0));

    ot_qkvd_ke_wf u_wf (.clk(clk), .rst_n(rst_n), .rsw(rsw), .flt_i(flt), .fault(fault), .fault_cause(fault_cause));
    ot_qkvd_ke_ctl u_ctl (.clk(clk), .rst_n(rsw), .cfg_ucx(cfg_ucx), .cfg_qd(cfg_qd), .cfg_fcr0(cfg_fcr0),
        .civ(civ), .rqv(rqv), .rqh(rqh), .crq(crq), .upq(upq), .pp_t(pp_t), .pp_r(pp_r), .gq_o(gq), .gq2_o(gq2),
        .rqq_o(rqq), .tf0h(tf0h), .tv0(tv0), .flt(flt), .rs_s(rs_s), .rs_n(rs_n), .rs_ta(rs_ta), .rs_tb(rs_tb));
    // ---- die TX face lanes and TX buffers ----
    ot_qkvd_ke_ti u_ti0 (.clk(clk), .rst_n(rs_s), .t_v(t_v[0]), .t_d(t_d[W*0 +: W]), .t_cr(t_cr[0]), .tcr_i(gq2[0]),
        .civ(civ[0]), .psh(psh_t[0]), .ce_d(ce_d[W*0 +: W]));
    ot_qkvd_ke_ti u_ti1 (.clk(clk), .rst_n(rs_s), .t_v(t_v[1]), .t_d(t_d[W*1 +: W]), .t_cr(t_cr[1]), .tcr_i(gq2[1]),
        .civ(civ[1]), .psh(psh_t[1]), .ce_d(ce_d[W*1 +: W]));
    ot_qkvd_ke_ti u_ti2 (.clk(clk), .rst_n(rs_s), .t_v(t_v[2]), .t_d(t_d[W*2 +: W]), .t_cr(t_cr[2]), .tcr_i(gq2[2]),
        .civ(civ[2]), .psh(psh_t[2]), .ce_d(ce_d[W*2 +: W]));
    ot_qkvd_sbufp  u_tb0 (.clk(clk), .rst_n(rs_ta), .push(psh_t[0]), .din(ce_d[W*0 +: W]), .pop(pp_t[0]),
        .dout(ib_head[W*0 +: W]), .empty(ib_empty[0]));
    ot_qkvd_sbufp  u_tb1 (.clk(clk), .rst_n(rs_ta), .push(psh_t[1]), .din(ce_d[W*1 +: W]), .pop(pp_t[1]),
        .dout(ib_head[W*1 +: W]), .empty(ib_empty[1]));
    ot_qkvd_fbuf8p u_tb2 (.clk(clk), .rst_n(rs_ta), .push(psh_t[2]), .din(ce_d[W*2 +: W]), .pop(pp_t[2]),
        .dout(ib_head[W*2 +: W]), .empty(ib_empty[2]));
    wire [W-1:0] tw;
    ot_qkvd_ke_tm u_tm (.clk(clk), .rst_n(rs_n), .gq_i(gq), .h0(ib_head[W*0 +: W]), .h1(ib_head[W*1 +: W]),
        .h2(ib_head[W*2 +: W]), .tw(tw));
    ot_qkvd_ke_tf u_tf (.clk(clk), .rst_n(rs_n), .tx_up(tx_up), .tx_v(tx_v), .tx_flit(tx_flit), .upq(upq), .tf0h(tf0h),
        .tv0_i(tv0), .tw(tw));
    // ---- FDI RX capture, RX buffers and die RX face lanes ----
    ot_qkvd_ke_rq u_rq (.clk(clk), .rst_n(rs_n), .rx_v(rx_v), .rx_flit(rx_flit), .rqv(rqv), .rqh(rqh), .psh(psh_r),
        .w0(re_w[W*0 +: W]), .w1(re_w[W*1 +: W]), .w2(re_w[W*2 +: W]), .w3(re_w[W*3 +: W]));
    ot_qkvd_fbuf8p u_rb0 (.clk(clk), .rst_n(rs_tb), .push(psh_r[0]), .din(re_w[W*0 +: W]), .pop(pp_r[0]),
        .dout(rb_head[W*0 +: W]), .empty(rb_empty[0]));
    ot_qkvd_sbufp  u_rb1 (.clk(clk), .rst_n(rs_tb), .push(psh_r[1]), .din(re_w[W*1 +: W]), .pop(pp_r[1]),
        .dout(rb_head[W*1 +: W]), .empty(rb_empty[1]));
    ot_qkvd_fbuf8p u_rb2 (.clk(clk), .rst_n(rs_tb), .push(psh_r[2]), .din(re_w[W*2 +: W]), .pop(pp_r[2]),
        .dout(rb_head[W*2 +: W]), .empty(rb_empty[2]));
    ot_qkvd_sbufp  u_rb3 (.clk(clk), .rst_n(rs_tb), .push(psh_r[3]), .din(re_w[W*3 +: W]), .pop(pp_r[3]),
        .dout(rb_head[W*3 +: W]), .empty(rb_empty[3]));
    ot_qkvd_ke_ro u_ro0 (.clk(clk), .rst_n(rs_s), .en_i(rqq[0]), .head(rb_head[W*0 +: W]), .r_cr(r_cr[0]), .r_v(r_v[0]),
        .r_d(r_d[W*0 +: W]), .crq(crq[0]));
    ot_qkvd_ke_ro u_ro1 (.clk(clk), .rst_n(rs_s), .en_i(rqq[1]), .head(rb_head[W*1 +: W]), .r_cr(r_cr[1]), .r_v(r_v[1]),
        .r_d(r_d[W*1 +: W]), .crq(crq[1]));
    ot_qkvd_ke_ro u_ro2 (.clk(clk), .rst_n(rs_s), .en_i(rqq[2]), .head(rb_head[W*2 +: W]), .r_cr(r_cr[2]), .r_v(r_v[2]),
        .r_d(r_d[W*2 +: W]), .crq(crq[2]));
    ot_qkvd_ke_ro u_ro3 (.clk(clk), .rst_n(rs_s), .en_i(rqq[3]), .head(rb_head[W*3 +: W]), .r_cr(r_cr[3]), .r_v(r_v[3]),
        .r_d(r_d[W*3 +: W]), .crq(crq[3]));
`ifndef SYNTHESIS
    // every cycle: each control shadow's empty equals its buffer tile's empty (as ot_qkvd_d2d PQ)
    always @(posedge clk) if (u_ctl.rs && ({u_ctl.sh_e_r, u_ctl.sh_e_t} !== {rb_empty, ib_empty})) begin
        $display("ERROR ot_qkvd_ke_cluster: shadow empties %b != buffer empties %b at %0t", {u_ctl.sh_e_r, u_ctl.sh_e_t},
                 {rb_empty, ib_empty}, $time);
        $fatal(1);
    end
    initial if (UCX <= 8 || UCX > 64) begin $display("ERROR ot_qkvd_ke_cluster: UCX %0d outside the sbufp range", UCX); $fatal(1); end
`endif
endmodule
