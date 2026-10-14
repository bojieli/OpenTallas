`timescale 1ns/1ps
// Simulation board-port fixture, not a production board-router implementation.
// Exact counterpart of the actual two-adapter BOOT gate. DATA/class payloads
// are exposed only after real FDI sequence/credit and CDC processing. A caller
// routes class528 words between these ports using actual reserved queue slots;
// it must never copy one port's FDI header/credit onto another physical link.
module qkd_host_board_port_fixture (
 input wire[7:0]ck_phy,input wire ck_pad,ck_rx_core,ck_tx_core,rst_n,phy_up,
 input wire phy_rx_v,input wire[1042:0]phy_rx_flit,
 output wire phy_tx_v,output wire[1042:0]phy_tx_flit,
 input wire core_tx_v,input wire[527:0]core_tx_d,output wire core_tx_cr,
 output wire core_rx_v,output wire[527:0]core_rx_d,input wire core_rx_cr,
 output wire[5:0]faults
);
 wire tx_v,tx_cr,rx_v,rx_cr,adapter_fault;
 wire[1023:0]tx_d,rx_d;wire[4:0]cdc_faults;
 qfd_link_adp512_split u_adapter(.ck(ck_phy),.rst_n(rst_n),
 .c_v(tx_v),.c_d(tx_d),.c_cr(tx_cr),.r_v(rx_v),.r_d(rx_d),.r_cr(rx_cr),
 .tx_up(phy_up),.tx_v(phy_tx_v),.tx_flit(phy_tx_flit),
 .rx_v(phy_rx_v),.rx_flit(phy_rx_flit),.fault(adapter_fault));
 qkd_host_phy_cdc5 u_phy(.ck_pad(ck_pad),.rx_wck(ck_pad),.rx_rck(ck_rx_core),
 .tx_wck(ck_tx_core),.tx_rck(ck_pad),.rst_n(rst_n),
 .phy_rx_v(rx_v),.phy_rx_d(rx_d),.phy_rx_cr(rx_cr),
 .phy_tx_v(tx_v),.phy_tx_d(tx_d),.phy_tx_cr(tx_cr),
 .core_rx_v(core_rx_v),.core_rx_d(core_rx_d),.core_rx_cr(core_rx_cr),
 .core_tx_v(core_tx_v),.core_tx_d(core_tx_d),.core_tx_cr(core_tx_cr),.faults(cdc_faults));
 assign faults={adapter_fault,cdc_faults};
endmodule
