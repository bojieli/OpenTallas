`timescale 1ns/1ps
// Die-name digital SerDes master: real eight-slice adapter, 512-entry
// local link RX buffer, four credits on each core-side boundary.
// The licensed analog PHY attaches at tx/rx_flit; these ports are its
// functional digital FDI boundary, not tied-off serial shell ports.
// Physical leaf views stand; parent clock distribution still requires qualification.
module qfd_io_serdes #(parameter integer MUT=0) (
 input wire ck0, ck1, ck2, ck3, ck4, ck5, ck6, ck7, rst_n,
 input wire c_v, input wire [1023:0] c_d, output wire c_cr,
 output wire r_v, output wire [1023:0] r_d, input wire r_cr,
 input wire tx_up, output wire tx_v, output wire [1042:0] tx_flit,
 input wire rx_v, input wire [1042:0] rx_flit, output wire fault
);
 qfd_link_adp512_split #(.MUT(MUT)) u_adapter (
 .ck({ck7,ck6,ck5,ck4,ck3,ck2,ck1,ck0}),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.c_cr(c_cr),
 .r_v(r_v),.r_d(r_d),.r_cr(r_cr),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),
 .rx_v(rx_v),.rx_flit(rx_flit),.fault(fault));
endmodule
// UCIe P and R have independent link credit domains: the collective's
// 546-bit partial and 514-bit result records cannot share an untagged FIFO.
module qfd_io_ucie #(parameter integer MUT=0) (
input wire rst_n,
input wire p_ck0, p_ck1, p_ck2, p_ck3, p_ck4, p_ck5, p_ck6, p_ck7,
input wire p_c_v,
input wire [1023:0] p_c_d,
output wire p_c_cr,
output wire p_r_v,
output wire [1023:0] p_r_d,
input wire p_r_cr,
input wire p_tx_up,
output wire p_tx_v,
output wire [1042:0] p_tx_flit,
input wire p_rx_v,
input wire [1042:0] p_rx_flit,
output wire p_fault,
input wire r_ck0, r_ck1, r_ck2, r_ck3, r_ck4, r_ck5, r_ck6, r_ck7,
input wire r_c_v,
input wire [1023:0] r_c_d,
output wire r_c_cr,
output wire r_r_v,
output wire [1023:0] r_r_d,
input wire r_r_cr,
input wire r_tx_up,
output wire r_tx_v,
output wire [1042:0] r_tx_flit,
input wire r_rx_v,
input wire [1042:0] r_rx_flit,
output wire r_fault
);
 qfd_io_serdes #(.MUT(MUT)) u_p (.rst_n(rst_n), .ck0(p_ck0), .ck1(p_ck1), .ck2(p_ck2), .ck3(p_ck3), .ck4(p_ck4), .ck5(p_ck5), .ck6(p_ck6), .ck7(p_ck7), .c_v(p_c_v), .c_d(p_c_d), .c_cr(p_c_cr), .r_v(p_r_v), .r_d(p_r_d), .r_cr(p_r_cr), .tx_up(p_tx_up), .tx_v(p_tx_v), .tx_flit(p_tx_flit), .rx_v(p_rx_v), .rx_flit(p_rx_flit), .fault(p_fault));
 qfd_io_serdes u_r (.rst_n(rst_n), .ck0(r_ck0), .ck1(r_ck1), .ck2(r_ck2), .ck3(r_ck3), .ck4(r_ck4), .ck5(r_ck5), .ck6(r_ck6), .ck7(r_ck7), .c_v(r_c_v), .c_d(r_c_d), .c_cr(r_c_cr), .r_v(r_r_v), .r_d(r_r_d), .r_cr(r_r_cr), .tx_up(r_tx_up), .tx_v(r_tx_v), .tx_flit(r_tx_flit), .rx_v(r_rx_v), .rx_flit(r_rx_flit), .fault(r_fault));
endmodule
