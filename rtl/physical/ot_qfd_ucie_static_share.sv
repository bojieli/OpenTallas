`timescale 1ns/1ps
// One actual TP8 1043-bit physical FDI frame per link edge. Entire P597 or
// R565 CRC frame occupies low bits; unused bits are zero, with no truncation.
// Compiler reserves both streams against one capacity. RX chooses its type
// exclusively from the receiver's compiled calendar. No arbiter/ready/retry.
// This combinational boundary adds no storage stage; codec pins are registered.
// RXW (QC-P4 10-23, COORD R7): received FDI width.  1043 = the raw PHY frame (default).  597 = behind the SIX_FIVE
// gearbox, whose RX frame is 597 b: the 446 upper bits do not exist, so they are no port (as built they were a literal 0).
module qfd_ucie_static_share #(parameter integer RXW = 1043)(
 input wire clk,rst_n,input wire[1:0]tx_slot,tx_valid,
 input wire[596:0]p_frame,input wire[564:0]r_frame,
 input wire[1:0]rx_slot,input wire phy_rx_valid,input wire[RXW-1:0]phy_rx,
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
 // bits above the R565 / P597 frame must be zero (frame-type check); a 597-b receiver has no bits above P597
 wire rx_hi_r,rx_hi_p;
 if(RXW>597)begin:g_rx_hi assign rx_hi_r=|phy_rx[RXW-1:565];assign rx_hi_p=|phy_rx[RXW-1:597];end
 else begin:g_rx_597 assign rx_hi_r=|phy_rx[596:565];assign rx_hi_p=1'b0;end
 initial if(RXW!=1043 && RXW!=597)$error("qfd_ucie_static_share RXW must be 1043 or 597");
 always @(posedge clk or negedge rst_n)
 if(!rst_n)fault<=0;else if((tx_slot==2'b11)||(rx_slot==2'b11)||
 (tx_valid!==tx_slot)||(phy_rx_valid!==( |rx_slot))||
 (phy_rx_valid && ((rx_slot[1] && rx_hi_r)||(!rx_slot[1] && rx_hi_p))))fault<=1;
endmodule
