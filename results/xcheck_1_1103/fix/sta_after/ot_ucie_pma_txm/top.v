module top(input clk);
  wire [512:0] w_d;
  DFFHQNx1_ASAP7_75t_R l_d (.CLK(clk), .D(1'b0), .QN(w_d[0]));
  wire [512:0] w_pma_tx;
  DFFHQNx1_ASAP7_75t_R c_pma_tx (.CLK(clk), .D(w_pma_tx[0]), .QN());
  wire w_pma_tck;
  DFFHQNx1_ASAP7_75t_R c_pma_tck (.CLK(clk), .D(w_pma_tck), .QN());
  ot_ucie_pma_txm u_phy (.ck(clk), .d(w_d), .pma_tx(w_pma_tx), .pma_tck(w_pma_tck));
endmodule
