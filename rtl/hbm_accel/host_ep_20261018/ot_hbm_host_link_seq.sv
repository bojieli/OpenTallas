`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_host_link_seq (H-D4G5/HOSTEP 2026-10-18): the host-link sequencer between the reliability layer
// (ot_hbm_host_link_capture) and the static link endpoint hfd_ep_static (CLOSED hep_static_w5f_1016-w5f-00f041029).
// It replaces the retired endpoint pair ot_hbm_lk_ep + hfd_lk_ep_face and its on-die credit loop (t_cr / r_cr / pop).
//
// TX (die -> host), static slot calendar, no credit:
//   * every client word (c_tx_v / c_tx_flit, the packet controller's response / status flit) is PUBLISHED into the link
//     store at the next write sequence (wr_v, wr_seq = wc); nothing gates the client (the store is 64 deep; a 65th
//     unread word is a sticky seq_fault, and the native ownership map faults it too).
//   * a word is READ (rd_v, rd_seq = rc -> CRC + header -> tx_pin_v 7 edges later) only on a cycle whose frame reaches the
//     endpoint's TX gearbox on a data slot: a mirror of ot_hep_tx_gbx's (ph, gc) beat counter released on the same reset
//     edge, started TXLAT steps ahead (TXLAT = rd_v -> gearbox edges = 7 link-capture + 1 endpoint pin + 1 = 9, plus die
//     relay stages on the frame edge).  A frame on beat phase 4 or the IDLE beat is the endpoint's sticky cal_fault.
//   * reads are spaced >= TXGAP edges (the far receiver drains one-frame blocks: one frame per 8 edges minimum, x2).
//   * reads start when the session is open: OPENER = 0 (die): on the first host frame verified by the link (rx_v); the
//     host opens the session only after its own receiver is locked.  OPENER = 1 (host model): OPEN_WAIT edges after
//     phy_up.  Reads also need phy_up (a TX frame with the PHY down is a link fault).
// RX (host -> die), the off-die elastic boundary (owner rule: flow control only at off-die boundaries):
//   * one-frame blocks in the endpoint's two-bank pingpong (block_words = 1): bank 0 is armed at a fixed edge after
//     reset; when the armed bank reports block_ready (pin flop), ONE edge arms the other bank and releases this one,
//     the next edge reads its slot 0, and RXLAT (= 6: endpoint pin + pingpong slot -> pin 4 + 1) edges later the link
//     checks the frame (rx_expect_v with the next expected sequence on the exact edge rx_pin_v arrives).  Host rule:
//     frames >= 8 edges apart at the die receiver (the host sends at most one per TXGAP); an earlier frame finds no
//     armed bank = the endpoint's sticky 'early' fault, never a silent drop.
//   * no ready / credit leaves toward the host; the landing FIFO (256) absorbs requests, the host bounds its outstanding
//     requests by the responses it has received (end-to-end at the off-die boundary; overflow = land_fault).
// Session: epoch_begin at a fixed edge after reset with epoch = the session strap (both ends must agree; a frame of any
// other session fails the epoch check).  A link fault (CRC / sequence / epoch / slot) is the sticky epoch_abort, as COLL's
// link: recovery is the coordinated host-link reset (new session strap); faults are never silent.
// client_rst_n releases the client (landing + packet) RST_CLIENT edges after reset, after the epoch is active.
// Every output is a flop Q; ep_block_ready / ep_phy_up land in pin flops.  c_tx_v / c_tx_flit feed the link capture's
// own pin flops (wr_v / wr_flit) unchanged, so the client's flop Q -> link pin flop is one wire.
// MUT (bench only): 1 TX calendar one step late, 2 RX expect one edge early, 3 no TX spacing (TXGAP 1).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_host_link_seq #(
 parameter integer TXLAT = 9, parameter integer RXLAT = 6, parameter integer TXGAP = 16,
 parameter integer OPENER = 0, parameter integer OPEN_WAIT = 256, parameter integer IDLE_K = 204,
 parameter integer RST_CLIENT = 8, parameter integer MUT = 0
)(
 input wire clk,rst_n,                         // rst_n: the tile's relayed reset (same release edge as the endpoint's)
 // client TX words
 input wire c_tx_v,input wire [544:0] c_tx_flit,
 output reg client_rst_n,
 // link capture control
 output reg lc_epoch_begin,
 output wire lc_wr_v,output reg [15:0] lc_wr_seq,output wire [544:0] lc_wr_flit,
 output reg lc_rd_v,output reg [15:0] lc_rd_seq,
 output reg lc_rx_expect_v,output reg [15:0] lc_rx_expect_seq,
 output wire lc_phy_up,
 input wire lc_rx_v,
 // endpoint static RX control / status
 output reg ep_arm_v,ep_arm_bank,output reg [6:0] ep_block_words,
 output reg ep_release_v,ep_release_bank,
 output reg ep_slot_v,ep_slot_bank,output reg [5:0] ep_slot_index,
 input wire [1:0] ep_block_ready,input wire ep_phy_up,
 output reg seq_fault
);
 localparam integer TL=(MUT==1)?TXLAT+1:TXLAT;
 localparam integer RL=(MUT==2)?RXLAT-1:RXLAT;
 localparam integer TG=(MUT==3)?1:TXGAP;
 localparam integer GB=13;
 // ---------------- pin flops
 reg [1:0] br_q;reg up_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin br_q<=0;up_q<=0;end else begin br_q<=ep_block_ready;up_q<=ep_phy_up;end
 assign lc_phy_up=up_q;
 // ---------------- start-up sequence (fixed edges)
 reg [4:0] t0;
 reg opened;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin t0<=0;lc_epoch_begin<=0;client_rst_n<=0;end
  else begin
   if(t0!=5'd31)t0<=t0+5'd1;
   lc_epoch_begin<=(t0==5'd0);
   if(t0==RST_CLIENT[4:0])client_rst_n<=1'b1;
  end
 // ---------------- TX: publication (one wire into the link pin flops) + store occupancy
 assign lc_wr_v=c_tx_v;
 assign lc_wr_flit=c_tx_flit;
 reg [15:0] rc;
 reg [15:0] wd[0:7];                            // write count as the link store can serve it (8 edges after the write)
 integer i;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin lc_wr_seq<=0;for(i=0;i<8;i=i+1)wd[i]<=0;seq_fault<=0;end
  else begin
   if(c_tx_v)lc_wr_seq<=lc_wr_seq+16'd1;
   wd[0]<=lc_wr_seq;for(i=1;i<8;i=i+1)wd[i]<=wd[i-1];
   if(c_tx_v && (lc_wr_seq-rc)==16'd64)seq_fault<=1'b1;
  end
 // ---------------- TX: endpoint gearbox beat mirror, TL steps ahead (= ot_hep_tx_gbx ph / gc)
 reg [2:0] ph;reg [GB-1:0] gc;
 wire idle_now=(gc==IDLE_K[GB-1:0]);
 wire slot_ok=!idle_now && ph!=3'd4;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin ph<=TL%5;gc<=TL/5;end
  else begin
   ph<=idle_now?ph:(ph==3'd4 ?3'd0:ph+3'd1);
   gc<=idle_now?{GB{1'b0}}:(ph==3'd4 ?gc+1'b1:gc);
  end
 // ---------------- TX: read on calendar slots
 reg [4:0] gap;
 reg [8:0] ow;
 wire rd_go=opened && up_q && rc!=wd[7] && gap>=TG[4:0]-5'd1 && slot_ok;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin rc<=0;gap<=5'd31;lc_rd_v<=0;lc_rd_seq<=0;opened<=0;ow<=0;end
  else begin
   lc_rd_v<=rd_go;lc_rd_seq<=rc;
   if(rd_go)begin rc<=rc+16'd1;gap<=0;end else if(gap!=5'd31)gap<=gap+5'd1;
   if(OPENER!=0)begin
    if(up_q && ow!=9'h1ff)ow<=ow+9'd1;
    if(up_q && ow>=OPEN_WAIT[8:0])opened<=1'b1;
   end else if(lc_rx_v)opened<=1'b1;
  end
 // ---------------- RX: one-frame pingpong blocks, drained on fixed edges after block_ready
 reg fb,armed,rd_pend;
 reg [RL-1:0] sd;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   fb<=0;armed<=0;rd_pend<=0;sd<=0;
   ep_arm_v<=0;ep_arm_bank<=0;ep_block_words<=7'd1;ep_release_v<=0;ep_release_bank<=0;
   ep_slot_v<=0;ep_slot_bank<=0;ep_slot_index<=0;lc_rx_expect_v<=0;lc_rx_expect_seq<=0;
  end else begin
   ep_arm_v<=0;ep_release_v<=0;ep_slot_v<=0;
   if(t0==5'd2)begin ep_arm_v<=1;ep_arm_bank<=0;armed<=1;end
   else if(armed && !rd_pend && br_q[fb])begin
    ep_arm_v<=1;ep_arm_bank<=!fb;                 // the other bank takes the next frame
    ep_release_v<=1;ep_release_bank<=fb;          // this bank drains
    rd_pend<=1;
   end else if(rd_pend)begin
    ep_slot_v<=1;ep_slot_bank<=fb;ep_slot_index<=0;
    rd_pend<=0;fb<=!fb;
   end
   sd<={sd[RL-2:0],ep_slot_v};
   lc_rx_expect_v<=sd[RL-2];
   if(lc_rx_expect_v)lc_rx_expect_seq<=lc_rx_expect_seq+16'd1;
  end
endmodule
`default_nettype wire
