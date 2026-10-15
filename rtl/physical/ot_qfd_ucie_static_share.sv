`timescale 1ns/1ps
// One actual TP8 1043-bit physical FDI frame per link edge. Entire P597 or
// R565 CRC frame occupies low bits; unused bits are zero, with no truncation.
// Compiler reserves both streams against one capacity. RX chooses its type
// exclusively from the receiver's compiled calendar. No arbiter/ready/retry.
// This combinational boundary adds no storage stage; codec pins are registered.
module qfd_ucie_static_share(
 input wire clk,rst_n,input wire[1:0]tx_slot,tx_valid,
 input wire[596:0]p_frame,input wire[564:0]r_frame,
 input wire[1:0]rx_slot,input wire phy_rx_valid,input wire[1042:0]phy_rx,
 output wire phy_tx_valid,output wire[1042:0]phy_tx,
 output wire[1:0]rx_valid,output wire[1161:0]rx_frames,output reg fault);
 assign phy_tx_valid=|tx_slot;
`ifdef OT_UCIE_SHARE_MUT_VALID_SELECT
 wire select_r=tx_valid[1];
`else
 wire select_r=tx_slot[1];
`endif
 assign phy_tx=select_r?{478'b0,r_frame}:{446'b0,p_frame};
`ifdef OT_UCIE_SHARE_MUT_RX_TYPE
 assign rx_frames={phy_rx[596:32],phy_rx[596:0]};
`else
 assign rx_frames={phy_rx[564:0],phy_rx[596:0]};
`endif
 assign rx_valid=rx_slot & {2{phy_rx_valid}};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)fault<=0;else if((tx_slot==2'b11)||(rx_slot==2'b11)||
 (tx_valid!==tx_slot)||(phy_rx_valid!==( |rx_slot))||
 (phy_rx_valid && ((rx_slot[1] && |phy_rx[1042:565])||(!rx_slot[1] && |phy_rx[1042:597]))))fault<=1;
endmodule
