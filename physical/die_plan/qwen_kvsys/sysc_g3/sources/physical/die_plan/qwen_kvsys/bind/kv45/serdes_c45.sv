`timescale 1ns/1ps
`default_nettype none
// Native C2: exactly one Gray-pointer FIFO crossing per direction at each PHY half.
module ot_qfd_serdes_112g_x6_phy_c45 #(parameter W=522) (
 input wire clk, clk_phy, rst_n, tx_v,
 input wire [W-1:0] tx_flit,
 output wire tx_up, rx_v,
 output wire [W-1:0] rx_flit
);
 wire p_rst_n, p_tx_v, p_rx_v, p_tx_up;
 wire [W-1:0] p_tx_d, p_rx_d;
 ot_fdi_phy_cdc #(.W(W), .DEPTH(8)) u_fdi_cdc (
  .clk(clk), .link_rst_n(rst_n), .c_tx_v(tx_v), .c_tx_d(tx_flit),
  .c_rx_v(rx_v), .c_rx_d(rx_flit), .c_tx_up(tx_up), .clk_phy(clk_phy),
  .p_rst_n(p_rst_n), .p_tx_v(p_tx_v), .p_tx_d(p_tx_d),
  .p_rx_v(p_rx_v), .p_rx_d(p_rx_d), .p_tx_up(p_tx_up));
 ot_qfd_serdes_112g_x6_phy #(.W(W)) u_phy (
  .clk(clk_phy), .rst_n(p_rst_n), .tx_v(p_tx_v), .tx_flit(p_tx_d),
  .tx_up(p_tx_up), .rx_v(p_rx_v), .rx_flit(p_rx_d));
endmodule
module ot_qfd_serdes_112g_x12_phy_s2_c45 (
 input wire clk, clk_phy, rst_n, tx_v,
 input wire [1042:0] tx_flit,
 output wire tx_up, rx_v_w, rx_v_e,
 output wire [1042:0] rx_flit
);
 wire up_w, up_e;
 ot_qfd_serdes_112g_x6_phy_c45 #(.W(522)) u_W (
  .clk(clk), .clk_phy(clk_phy), .rst_n(rst_n), .tx_v(tx_v), .tx_flit(tx_flit[521:0]),
  .tx_up(up_w), .rx_v(rx_v_w), .rx_flit(rx_flit[521:0]));
 ot_qfd_serdes_112g_x6_phy_c45 #(.W(521)) u_E (
  .clk(clk), .clk_phy(clk_phy), .rst_n(rst_n), .tx_v(tx_v), .tx_flit(tx_flit[1042:522]),
  .tx_up(up_e), .rx_v(rx_v_e), .rx_flit(rx_flit[1042:522]));
 assign tx_up = up_w & up_e;
endmodule
module ot_qfd_serdes_112g_x12_phy_c45 (
 input wire clk, clk_phy, rst_n, tx_v,
 input wire [1042:0] tx_flit,
 output wire tx_up, rx_v_w, rx_v_e,
 output wire [1042:0] rx_flit
);
 ot_qfd_serdes_112g_x12_phy_s2_c45 u_sub (.*);
endmodule
// The reconstructed PHY-to-host data path has four core relay stages. Carry
// each half-valid through exactly the same age before the planner replaces it.
module qkd_rlys_kv45_valid4 (input wire ck, input wire [1:0] a, output wire [1:0] b);
 reg [1:0] q0, q1, q2, q3;
 always @(posedge ck) begin q0<=a; q1<=q0; q2<=q1; q3<=q2; end
 assign b=q3;
endmodule
`default_nettype wire
