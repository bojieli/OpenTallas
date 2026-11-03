module top(input clk);
  wire [511:0] w_tx;
  DFFHQNx1_ASAP7_75t_R l_tx (.CLK(clk), .D(1'b0), .QN(w_tx[0]));
  wire [511:0] w_rx;
  DFFHQNx1_ASAP7_75t_R c_rx (.CLK(clk), .D(w_rx[0]), .QN());
  ot_pdie_serdes u_phy (.clk(clk), .tx(w_tx), .rx(w_rx));
endmodule
