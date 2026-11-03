module top(input clk);
  wire [512:0] w_pma_rx;
  DFFHQNx1_ASAP7_75t_R l_pma_rx (.CLK(clk), .D(1'b0), .QN(w_pma_rx[0]));
  wire [512:0] w_q;
  DFFHQNx1_ASAP7_75t_R c_q (.CLK(clk), .D(w_q[0]), .QN());
  ot_ucie_pma_rxm u_phy (.pma_rck(clk), .pma_rx(w_pma_rx), .q(w_q));
endmodule
