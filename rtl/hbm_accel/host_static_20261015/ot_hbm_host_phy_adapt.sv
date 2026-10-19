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
// Fixed added latency: +2 edges TX (endpoint -> PHY), +2 edges RX (PHY -> endpoint), +2 session; the link is elastic
// (endpoint CRC/replay/credits), so no compile schedule depends on it.
// PIN STAGES (HBM-NATIVE 10-17, after the routed native pin audit of hdie_host_phy_r1-r1-dcfed59ab: phy_tx launch up to
// 255.2 ps > 220 on 12 pins): the r1 RTL had ONE flop per bit between two faces (ep_tx S -> phy_tx N, phy_rx W -> ep_rx E,
// session_pad S -> session E), a feedthrough register that is both the input capture and the output launch flop, so it
// can sit at only one of its two pins (the routed phy_tx[460] flop sits at y 3.2 beside ep_tx[460], 87 um + 45 um of wire
// from its N pin). Each feedthrough is now TWO flops: a capture flop at the input pin and a launch flop at the output pin
// (the kit's io_flop_at_pins anchors each at its own face), the face-to-face wire is a full reg->reg cycle. +1 edge on
// TX, RX and session vs r1 (r1 was +1 each way); the reserved-lane / status checks (pad_q, st_q -> pad_fault, phy_fault)
// are pin captures + launch flops already and keep r1 timing. Elastic link: no compile-schedule change. Bench
// tb_host_phy_pin_stage: phy_tx/ep_rx/session == r1 one edge later, pad_fault/phy_fault == r1, every edge.
module ot_hbm_host_phy_adapt #(parameter integer LW=487, parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire [LW-1:0] ep_tx,output reg [511:0] phy_tx,
 input wire [511:0] phy_rx,input wire [1:0] phy_st,output reg [LW-1:0] ep_rx,
 input wire [23:0] session_pad,output reg [23:0] session,
 output reg pad_fault,phy_fault
);
 reg [511-LW:0] pad_q;reg [1:0] st_q;
 reg [LW-1:0] tx_c,rx_c;reg [23:0] ses_c;          // input-pin capture stages (ep_tx S, phy_rx W, session_pad S)
 always @(posedge clk)begin
  tx_c<=ep_tx;rx_c<=phy_rx[LW-1:0];ses_c<=session_pad;
`ifdef OT_HOST_PHY_STAGE_MUT
  phy_tx<={{(512-LW){1'b0}},ep_tx};                 // mutant: TX stage bypassed (r1 timing)
`else
  phy_tx<={{(512-LW){1'b0}},tx_c};                  // output-pin launch stages (phy_tx N, ep_rx E, session E)
`endif
  ep_rx<=rx_c^((MUT==1)?{{(LW-1){1'b0}},1'b1}:{LW{1'b0}});
  session<=ses_c;
  pad_q<=phy_rx[511:LW];                            // reserved-lane check: capture flops at the W pins (unchanged)
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
