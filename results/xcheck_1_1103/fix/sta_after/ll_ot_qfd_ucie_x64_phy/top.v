module top(input clk);
  wire w_rst_n;
  wire q_rst_n; DFFHQNx1_ASAP7_75t_R l_rst_n (.CLK(clk), .D(1'b0), .QN(q_rst_n)); DLLx1_ASAP7_75t_R ll_rst_n (.CLK(clk), .D(q_rst_n), .Q(w_rst_n));
  wire w_tx_up;
  DFFHQNx1_ASAP7_75t_R c_tx_up (.CLK(clk), .D(w_tx_up), .QN());
  wire w_tx_v;
  wire q_tx_v; DFFHQNx1_ASAP7_75t_R l_tx_v (.CLK(clk), .D(1'b0), .QN(q_tx_v)); DLLx1_ASAP7_75t_R ll_tx_v (.CLK(clk), .D(q_tx_v), .Q(w_tx_v));
  wire [1042:0] w_tx_flit;
  wire q_tx_flit; DFFHQNx1_ASAP7_75t_R l_tx_flit (.CLK(clk), .D(1'b0), .QN(q_tx_flit)); DLLx1_ASAP7_75t_R ll_tx_flit (.CLK(clk), .D(q_tx_flit), .Q(w_tx_flit[0]));
  wire w_rx_v;
  DFFHQNx1_ASAP7_75t_R c_rx_v (.CLK(clk), .D(w_rx_v), .QN());
  wire [1042:0] w_rx_flit;
  DFFHQNx1_ASAP7_75t_R c_rx_flit (.CLK(clk), .D(w_rx_flit[0]), .QN());
  ot_qfd_ucie_x64_phy u_phy (.clk(clk), .rst_n(w_rst_n), .tx_up(w_tx_up), .tx_v(w_tx_v), .tx_flit(w_tx_flit), .rx_v(w_rx_v), .rx_flit(w_rx_flit));
endmodule
