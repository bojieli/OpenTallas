`timescale 1ns/1ps
// STW-S81-OWN7 10-21 flat8s = flat8 with the SHORT TX lane: the encoder is placed on the PMA TX digital face and drives it
// directly (relay rows u_txr0 / u_txr1 removed; they existed only to carry the encoder output 1.3 mm from the N face to the
// PMA).  TX latency -2 edges vs flat7/flat8 (and the landed column loses the two TX landings, -6 edges).  Otherwise = flat8
// (landed status halves u_sts_r / u_sts_t, PMA RX ot_s81_pma_rxn).  Source of the lp8b landed column (FALLBACK).
module ot_pdie_serdes_col_flat8s (
    input  wire          clk,
    input  wire          pma_rck,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    output wire [543:0]  pma_tx,
    output wire          pma_tck,
    input  wire [543:0]  pma_rx
);
    // ---- transmit
    // short TX (flat8s): the encoder sits on the PMA TX digital face; its registered p_v / p_d pins feed the PMA TX input
    // registers directly (one region, one single-cycle hop <= ~250 um): no relay rows u_txr0 / u_txr1, no TX landings.
    wire t_live, e_v, e_flt; wire [543:0] e_d;
    ot_s81_col_live u_live_t (.clk(clk), .rst_n(rst), .q(t_live));
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(rst), .tx_v(t_live), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt));
    ot_s81_pma_txm u_ptx (.ck(clk), .d_v(e_v), .d(e_d), .pma_tx(pma_tx), .pma_tck(pma_tck));
    // ---- receive (KP4 decoder tiles as direct children)
    wire [543:0] r_d, x_q, d_q, cw; wire r_live;
    wire [3:0] k_v; wire [309:0] k_lo; wire [4:0] k_L, o_ne; wire k_any, o_unc, fs, lock; wire [7:0] apply;
    wire q_v, q_first, q_unc; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq;
    wire [31:0] n_relock, n_corr, n_unc;
    ot_s81_pma_rxn u_prx (.pma_rck(pma_rck), .pma_rx(pma_rx), .q(r_d));
    ot_s81_col_live u_live_r (.clk(pma_rck), .rst_n(rst), .q(r_live));
    ot_s81_kp4_dsyn u_syn (.clk(pma_rck), .rst_n(rst), .p_v(r_live), .p_d(r_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
    ot_s81_kp4_ddly u_dly (.clk(pma_rck), .rst_n(rst), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dchn u_chn (.clk(pma_rck), .rst_n(rst), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
    ot_s81_kp4_dout u_out (.clk(pma_rck), .rst_n(rst), .d_q(d_q), .cw(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne),
        .fs(fs), .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
    // ---- CDC child (rck -> clk): the rate matcher only
    wire rm_flt, m_wce, m_rce; wire [3:0] m_waddr, m_raddr; wire [545:0] m_wd, m_wmask, m_rd;
    ot_s81_rate_match_sr u_rm (.wclk(pma_rck), .wrst_n(rst), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rst), .r_d(rx),
        .fault(rm_flt), .m_wce(m_wce), .m_waddr(m_waddr), .m_wd(m_wd), .m_wmask(m_wmask), .m_rce(m_rce), .m_raddr(m_raddr),
        .m_rd(m_rd));
    ot_sram_1r1w2c_16x546_m1 u_rmm (.wclk(pma_rck), .rclk(clk), .r_ce_in(m_rce), .r_addr_in(m_raddr), .rd_out(m_rd),
        .w_ce_in(m_wce), .w_addr_in(m_waddr), .wd_in(m_wd), .w_mask_in(m_wmask));
    // ---- status: two halves, the lock_r / unc_r crossing is LANDED by lp.py (STW-S81-OWN7 10-21)
    wire s_lock_r, s_unc_r;
    ot_s81_col_sts_r u_sts_r (.ck_r(pma_rck), .rst_r_n(rst), .lock(lock), .q_v(q_v), .q_first(q_first), .q_unc(q_unc),
        .lock_r(s_lock_r), .unc_r(s_unc_r));
    // encoder fault relay (flat8s): the encoder now sits ~1 mm below the output region, so its sticky fault flag takes one
    // 1-bit relay row u_efr (own small region at mid-column: two landed hops <= ~500 um instead of one ~1 mm hop); +1 edge
    // on the fault flag only.
    wire e_flt_r;
    ot_pl_pad #(.W(1), .N(1)) u_efr (.ck(clk), .d(e_flt), .q(e_flt_r));
    ot_s81_col_sts_t u_sts_t (.ck_t(clk), .rst_t_n(rst), .lock_r(s_lock_r), .unc_r(s_unc_r), .rm_flt(rm_flt), .e_flt(e_flt_r),
        .st(st));
endmodule
