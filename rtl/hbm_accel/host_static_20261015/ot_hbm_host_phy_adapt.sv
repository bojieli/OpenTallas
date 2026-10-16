`timescale 1ns/1ps
`default_nettype none
// Host link PHY adapter leaf (H-NETLIST cp2, 2026-10-15): the glue hfd_host_native kept in its
// composition, now a real pin-registered tile between the endpoint core and the host UCIe macro.
//  * TX: the 487-b endpoint word is framed into the 512-b UCIe digital beat; beat bits [511:487] are the
//    link's reserved lanes, transmitted as zero by this framer (the far receiver checks them).
//  * RX: the 512-b UCIe beat is split to the endpoint word; reserved lanes are checked once the PHY
//    reports a live link (st[1]) -> pad_fault (sticky). st[0] (rate-match fault) -> phy_fault.
//  * session: the host link session id arrives on die strap pads session_pad[23:0] (off-die sideband,
//    it changes only under the coordinated reset; both link ends must agree before any configuration
//    can cross the link, so no on-die configuration source can provide it) -> pin flop -> endpoint face.
// Fixed added latency: +1 edge TX (endpoint -> PHY), +1 edge RX (PHY -> endpoint); the link is elastic
// (endpoint CRC/replay/credits), so no schedule depends on it.
module ot_hbm_host_phy_adapt #(parameter integer LW=487, parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire [LW-1:0] ep_tx,output reg [511:0] phy_tx,
 input wire [511:0] phy_rx,input wire [1:0] phy_st,output reg [LW-1:0] ep_rx,
 input wire [23:0] session_pad,output reg [23:0] session,
 output reg pad_fault,phy_fault
);
 reg [511-LW:0] pad_q;reg [1:0] st_q;
 always @(posedge clk)begin
  phy_tx<={{(512-LW){1'b0}},ep_tx};
  pad_q<=phy_rx[511:LW];ep_rx<=phy_rx[LW-1:0]^((MUT==1)?{{(LW-1){1'b0}},1'b1}:{LW{1'b0}});
  session<=session_pad;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin st_q<=0;pad_fault<=0;phy_fault<=0;end
  else begin
   st_q<=phy_st;
   if(st_q[1] && pad_q!=0 && MUT!=2)pad_fault<=1;
   phy_fault<=st_q[0];
  end
endmodule
`default_nettype wire
