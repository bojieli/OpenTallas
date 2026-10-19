`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_host_cp_rxs (H-D4G5/HOSTEP 2026-10-18, coordinator 0gd): the d4g host control-plane tile on the STATIC link
// endpoint.  Successor of ot_hbm_host_cp_rx (CLOSED hdie_host_cprx_r1) for the endpoint swap
//     host_N (ot_pdie_ucie) <-> host_phy (ot_hbm_host_phy_adapt) <-> host_cp_ep (ot_hbm_lk_ep) + host_cp_ep_face
//     (hfd_lk_ep_face) <-> host_cp_rx           [credit loop t_cr / r_cr / pop across three tiles; lk_ep never closed]
//  -> host_N (ot_pdie_ucie) <-> host_ep (hfd_ep_static, CLOSED + native PASS, the COLL SerDes endpoint) <-> host_cp_rxs
// sd_tx / sd_rx / sd_st (512 b) run straight between host_N and hfd_ep_static (the same lane format as the COLL links;
// ot_hbm_host_phy_adapt and its 487 <-> 512 framing are redundant and retire).  This tile holds:
//   u_seq   ot_hbm_host_link_seq       slot-calendar TX reads, one-frame RX pingpong drain, session start-up
//   u_link  ot_hbm_host_link_capture   sequence / CRC-32 / 64-deep publication store / epoch abort (COLL link, wrapping)
//   u_land  ot_hbm_host_landing256     (unchanged, PINREG=1) the 256-deep request landing FIFO, 2 real 256x256 SRAMs
//   u_pkt   ot_hbm_host_packet_nc      the static packet controller without the TX credit (RXREG=0 fold as cp_rx)
// Session strap: session[7:0] (die strap pads, = the epoch both link ends agree on) -> pin flop -> link epoch.
// Faults out (sticky): land_fault (landing overflow / nonzero header), protocol_fault (packet), link_fault (link epoch
// abort: CRC / sequence / epoch / slot / ownership), seq_fault (TX store overflow).  The endpoint's own fault leaves the
// endpoint tile directly.
// Reset: rst_n -> ot_rst_relay (2 sync + 1 tree = the endpoint's own 2 + 1, so u_seq's beat mirror starts on the edge the
// endpoint's TX gearbox does; both tiles take rst_n from the same reset-tree level).  The landing / packet are released
// by u_seq.client_rst_n (after the link epoch is active) through their own relays.
// Fixed latencies (die-relay stages on the frame edges add to TXLAT / RXLAT): client word -> TX publication 1 edge,
// rd_v -> tx_pin 7 edges; ep rx_pin -> landing write 3 + 1 edges.  Configuration path only (no token schedule).
// Every input lands in a pin flop (link capture all-input capture, seq pin flops, landing / packet pin flops, session);
// every output is a flop Q.
// Rates (host obligation, configuration path): the host sends <= 1 request per 16 edges; the die answers <= 1 per
// TXGAP = 12 (+1 slot slip) edges, so the response store never fills (one response per request + rare status words); both
// spacings exceed the one-frame pingpong recycle of 8 receiver edges.
// MUT (bench only): 1..3 = ot_hbm_host_link_seq MUT, 4 = rx word bit 40 flipped into the landing, 5 = saturating link
// counters (COLL behaviour).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_host_cp_rxs #(parameter integer TXLAT=9, parameter integer RXLAT=6, parameter integer TXGAP=12,
 parameter integer MUT=0
)(
 input wire clk,rst_n,
 input wire [7:0] session,
 // static link endpoint face (hfd_ep_static COLL face)
 output wire ep_tx_v,output wire [611:0] ep_tx_frame,
 output wire ep_rx_arm_v,ep_rx_arm_bank,output wire [6:0] ep_rx_block_words,
 output wire ep_rx_release_v,ep_rx_release_bank,
 output wire ep_rx_slot_v,ep_rx_slot_bank,output wire [5:0] ep_rx_slot_index,
 input wire ep_rx_pin_v,input wire [611:0] ep_rx_pin_flit,
 input wire [1:0] ep_rx_block_ready,input wire ep_phy_up,
 // AXI-lite master toward ot_hbm_host_static_ingress
 output wire s_awvalid,input wire s_awready,output wire [11:0] s_awaddr,
 output wire s_wvalid,input wire s_wready,output wire [31:0] s_wdata,output wire [3:0] s_wstrb,
 input wire s_bvalid,input wire [1:0] s_bresp,output wire s_bready,
 output wire s_arvalid,input wire s_arready,output wire [11:0] s_araddr,
 input wire s_rvalid,output wire s_rready,input wire [31:0] s_rdata,
 // die status in (ot_hbm_status_join), faults out
 input wire irq,fault,
 output wire land_fault,protocol_fault,output reg link_fault,output wire seq_fault
);
 wire [0:0] rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg [7:0] ses_q;
 always @(posedge clk)ses_q<=session;
 // ---------------- sequencer + link
 wire crst_n,eb,wr_v,rd_v,xv,lup,rx_v,abort;
 wire [15:0] wr_seq,rd_seq,xseq;wire [544:0] wr_flit,rx_flit;wire [10:0] cause_unused;
 wire f_send;wire [544:0] f_flit;
 ot_hbm_host_link_seq #(.TXLAT(TXLAT),.RXLAT(RXLAT),.TXGAP(TXGAP),.OPENER(0),.MUT((MUT>=1&&MUT<=3)?MUT:0)) u_seq(
  .clk(clk),.rst_n(rr[0]),.c_tx_v(f_send),.c_tx_flit(f_flit),.client_rst_n(crst_n),
  .lc_epoch_begin(eb),.lc_wr_v(wr_v),.lc_wr_seq(wr_seq),.lc_wr_flit(wr_flit),.lc_rd_v(rd_v),.lc_rd_seq(rd_seq),
  .lc_rx_expect_v(xv),.lc_rx_expect_seq(xseq),.lc_phy_up(lup),.lc_rx_v(rx_v),
  .ep_arm_v(ep_rx_arm_v),.ep_arm_bank(ep_rx_arm_bank),.ep_block_words(ep_rx_block_words),
  .ep_release_v(ep_rx_release_v),.ep_release_bank(ep_rx_release_bank),
  .ep_slot_v(ep_rx_slot_v),.ep_slot_bank(ep_rx_slot_bank),.ep_slot_index(ep_rx_slot_index),
  .ep_block_ready(ep_rx_block_ready),.ep_phy_up(ep_phy_up),.seq_fault(seq_fault));
 ot_hbm_host_link_capture #(.MUT(MUT==5?1:0)) u_link(
  .clk(clk),.rst_n(rr[0]),.epoch_begin(eb),.epoch(ses_q),
  .wr_v(wr_v),.wr_observed_v(wr_v),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),
  .rx_expect_v(xv),.rx_expect_seq(xseq),.phy_up(lup),.tx_pin_v(ep_tx_v),.tx_pin_flit(ep_tx_frame),
  .rx_pin_v(ep_rx_pin_v),.rx_pin_flit(ep_rx_pin_flit),.rx_v(rx_v),.rx_flit(rx_flit),
  .epoch_abort(abort),.fault_cause(cause_unused));
 always @(posedge clk or negedge rr[0])if(!rr[0])link_fault<=0;else link_fault<=abort;
 // ---------------- landing + packet (as ot_hbm_host_cp_rx, credit-free)
 wire [0:0] lrst;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_lr(.clk(clk),.rst_n_in(crst_n),.rst_n(lrst));
 wire l_v,p_ready,pop_unused;wire [511:0] l_data;
 wire [544:0] land_in=(MUT==4)?(rx_flit^(545'd1<<40)):rx_flit;
 ot_hbm_host_landing256 #(.PINREG(1)) u_land(.clk(clk),.rst_n(lrst[0]),.in_v(rx_v),.in_data(land_in),
  .out_v(l_v),.out_data(l_data),.out_ready(p_ready),.pop(pop_unused),.fault(land_fault));
 ot_hbm_host_packet_nc #(.RXREG(0),.RRELAY(1)) u_pkt(.clk(clk),.rst_n(crst_n),
  .rx_valid(l_v),.rx_packet(l_data),.rx_ready(p_ready),
  .f_send(f_send),.f_flit(f_flit),
  .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),
  .s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
  .s_bvalid(s_bvalid),.s_bresp(s_bresp),.s_bready(s_bready),
  .s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
  .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),
  .irq(irq),.fault(fault),.protocol_fault(protocol_fault));
endmodule
`default_nettype wire
