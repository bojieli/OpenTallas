`timescale 1ns/1ps
// ot_pdie_serdes_col_flat (S81-SERDES 10-19, S81.STA.OWN.7): the WIRES-ONLY flat SerDes column parent (child instances
// and wires only) from which tools/landed_parent/lp.py generates the landed column ot_pdie_serdes_col_lp
// (spec tools/landed_parent/specs/ot_pdie_serdes_col.json; kit physical/ref_tile/s81lk_serdes_col_lp).
// Function = ot_pdie_serdes_col (same pads, same FEC frame, same rate matcher), all glue moved into children:
//   TX (core clk family):  tx face reg u_txf -> live flag u_live_t + FEC encoder u_enc -> relay rows u_txr0/u_txr1 ->
//                          analog PMA TX u_ptx (pads S face)
//   RX (pma_rck family):   analog PMA RX u_prx -> u_syn (+ live flag u_live_r) -> u_dly / u_chn -> u_out -> rate matcher
//   CDC (COORDINATOR LEAD-S81 10-19 11:53: pma_rck is NOT the core PLL): the ONLY rck -> clk crossings are the closed
//                          gray-FIFO rate matcher u_rm (elastic: deletes IDLE beats, off-die boundary) and the 2-flop
//                          status synchroniser u_sts; both are lp.py CDC children (child_pin_regions).
// Clock ports clk / pma_rck are replaced by lp.py with one port per region (ck_tx, ck_ptx on clk; ck_syn, ck_dly,
// ck_chn, ck_out on pma_rck).  rst is landed by the lp regional reset runs (2+ registered stages per region).
module ot_pdie_serdes_col_flat (
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
    wire [511:0] tx_f; wire t_live, e_v, e_flt; wire [543:0] e_d; wire [544:0] r0_q, r1_q;
    ot_pl_pad #(.W(512), .N(1)) u_txf (.ck(clk), .d(tx), .q(tx_f));
    ot_s81_col_live u_live_t (.clk(clk), .rst_n(rst), .q(t_live));
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(rst), .tx_v(t_live), .tx_d(tx_f), .p_v(e_v), .p_d(e_d), .fault(e_flt));
    ot_pl_pad #(.W(545), .N(1)) u_txr0 (.ck(clk), .d({e_v, e_d}), .q(r0_q));
    ot_pl_pad #(.W(545), .N(1)) u_txr1 (.ck(clk), .d(r0_q), .q(r1_q));
    ot_s81_pma_txm u_ptx (.ck(clk), .d_v(r1_q[544]), .d(r1_q[543:0]), .pma_tx(pma_tx), .pma_tck(pma_tck));
    // ---- receive (KP4 decoder tiles as direct children)
    wire [543:0] r_d, x_q, d_q, cw; wire r_live;
    wire [3:0] k_v; wire [309:0] k_lo; wire [4:0] k_L, o_ne; wire k_any, o_unc, fs, lock; wire [7:0] apply;
    wire q_v, q_first, q_unc; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq;
    wire [31:0] n_relock, n_corr, n_unc;
    ot_s81_pma_rxm u_prx (.pma_rck(pma_rck), .pma_rx(pma_rx), .q(r_d));
    ot_s81_col_live u_live_r (.clk(pma_rck), .rst_n(rst), .q(r_live));
    ot_s81_kp4_dsyn u_syn (.clk(pma_rck), .rst_n(rst), .p_v(r_live), .p_d(r_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_relock));
    ot_s81_kp4_ddly u_dly (.clk(pma_rck), .rst_n(rst), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dchn u_chn (.clk(pma_rck), .rst_n(rst), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
    ot_s81_kp4_dout u_out (.clk(pma_rck), .rst_n(rst), .d_q(d_q), .cw(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne),
        .fs(fs), .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
    // ---- CDC children (rck -> clk)
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(pma_rck), .wrst_n(rst), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rst), .r_d(rx),
        .fault(rm_flt));
    ot_s81_col_sts u_sts (.ck_r(pma_rck), .rst_r_n(rst), .lock(lock), .q_v(q_v), .q_first(q_first), .q_unc(q_unc),
        .ck_t(clk), .rst_t_n(rst), .rm_flt(rm_flt), .e_flt(e_flt), .st(st));
endmodule
