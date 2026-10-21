`timescale 1ns/1ps
// QW-COLLIO3 10-21: R collective face with the codec PHY pins in their own clock region (codec0p = second entry of
// the codec0 die clock), landed to the codec core region (codec0) by mesochronous rings (ot_coll_phy_land.sv).
// Stamped from qfd_coll_face_s1_pl (same kit form); profile as qfd_coll_face_r_safe. Face latency 53 + 1 + 2*PLK.
module qfd_coll_face_r_pl #(parameter integer PLD=2, PLK=1)(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[513:0]tx_data,
 output wire rx_valid,output wire[513:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[564:0]phy_rx,
 output wire phy_tx_valid,output wire[564:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_static_face #(.FW(514),.PHY(20),.L(53+1+2*PLK),.R(5),.PEER_R(5),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule
