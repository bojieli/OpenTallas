// Q-RSTGEN7 10-19 test excerpt (NOT a die): the clock + reset connections of the reset-tree last hops and their sinks in
// the dv2f15r GEN netlist ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/dv2f15r/chain/case_r22k/die.v
// (src 5a789562d), other pins dropped.  dv2f15codex die STA TT (same classes): rstt_rst_d2d__fo1__r3_12 -> d2d_rom/rst_n
// -100.7 ps (stream -> stream__early), rstt_rst_io_0 -> io_ucie/rst_n -220.9 ps (stream -> ucie).
module qfd_die_rstgen7_excerpt ();
  ot_qfd_ucie_x64_phy io_ucie (.clk(n_clk_ucie), .rst_n(n_rst_io__t111));
  ot_qfd_serdes_112g_x12_phy_s597 io_serdes (.clk(n_clk_serdes0), .rst_n(n_rst_io__t94));
  qfd_d2d_static d2d_rom (.por_n(n_rst_d2d__r4), .phy_rst_n(n_lnk_phy_rst), .fwd_link_rst_n(n_lnk_fwd_lrst__r4), .ck(n_clk_d2d), .rst_n(n_rst_d2d__fo1__r3__t5));
  ot_qfd_serdes_112g_x12_phy_s597 io_serdes_1 (.clk(n_clk_serdes1), .rst_n(n_rst_io__t194));
  ot_qfd_serdes_112g_x12_phy_s597 io_serdes_2 (.clk(n_clk_serdes2), .rst_n(n_rst_io__t220));
  qfd_sys_face sys_face (.ck(n_clk_d2d), .rst_n(n_rst_d2d__fo2__r4__t24));
  qfd_landh_548_WS_95x60 rly_lnk_rx_payload__fo1_2 (.ck(n_clk_d2d), .rs(n_rst_d2d__fo2__r4__t24));
  qfd_landh_32_SW_65x30 rly_sf_cfg_data_2 (.ck(n_clk_d2d), .rs(n_rst_d2d__fo1__r3__t5));
  qfd_rlyh0_1_SN_65x30 rly_sf_cal_seg_0 (.ck(n_clk_d2d), .en(n_rst_d2d__fo2__r4__t24));
  qfd_rst_rep rstt_rst_d2d__fo1__r3_12 (.clk(n_clk_d2d), .d(n_rst_d2d__fo1__r3__t4), .q0(n_rst_d2d__fo1__r3__t5));
  qfd_rst_rep rstt_rst_d2d__fo2__r4_9 (.clk(n_clk_d2d), .d(n_rst_d2d__fo2__r4__t23), .q0(n_rst_d2d__fo2__r4__t24));
  qfd_rst_rep rstt_rst_io_0 (.clk(n_clk_coll), .d(n_rst_io__t110), .q0(n_rst_io__t111));
  qfd_rst_rep rstt_rst_io_1 (.clk(n_clk_coll), .d(n_rst_io__t219), .q0(n_rst_io__t220));
  qfd_rst_rep rstt_rst_io_2 (.clk(n_clk_coll), .d(n_rst_io__t193), .q0(n_rst_io__t194));
  qfd_rst_rep rstt_rst_io_3 (.clk(n_clk_coll), .d(n_rst_io__t93), .q0(n_rst_io__t94));
endmodule
