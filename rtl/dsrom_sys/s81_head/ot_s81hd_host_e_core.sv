`timescale 1ns/1ps
`default_nettype none
// DH55-HSPLIT: hd_host_e = lane1 only; see ot_s81hd_host_w_core.sv for the seam contract (l1_rx E->W, l1_tx W->E).
module ot_s81hd_host_e_core #(
 parameter[1:0]CH_B=2'b11
)(
 input wire ck,rst_n,
 input wire[513:0]coll_i1,
 output wire[511:0]coll_o1,
 output wire[557:0]l1_rx_o,
 input wire[553:0]l1_tx_i
);
 wire rx_v;wire[552:0]rx_d;wire[3:0]flt;
 ot_s81hd_mesh_lane u_lane1(.ck(ck),.rst_n(rst_n),.chb(CH_B[1]),
  .rx(coll_i1),.tx(coll_o1),.tx_v(l1_tx_i[553]),.tx_d(l1_tx_i[552:0]),
  .rx_v(rx_v),.rx_d(rx_d),.flt(flt));
 assign l1_rx_o={flt,rx_v,rx_d};
endmodule
`default_nettype wire
