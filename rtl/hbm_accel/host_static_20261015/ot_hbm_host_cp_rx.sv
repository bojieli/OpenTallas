`timescale 1ns/1ps
`default_nettype none
// HBM die d4f host control-plane receive tile: the host landing FIFO folded with the static host packet controller
// (HBMA-HOST2 2026-10-17, coordinator 0dc+ (b)). Replaces the separate host_cp_landing + host_cp_packet tiles and the
// 512-bit landing -> packet bus between them (out_v/out_data/out_ready become internal wires).
//  * ot_hbm_host_landing256 PINREG=1 is unchanged (2 real 256x256 SRAMs, pin-registered endpoint face).
//  * ot_hbm_host_packet_static RXREG=0 takes rx_packet straight from the landing's out_data flop Q (held through the
//    consume edge, which is the packet's rx_take edge), so the packet's 512-b rx pin flop stage is gone; RRELAY=1 gives
//    it its own regional reset relay (5 regions). The landing gets a 1-region relay with the same 2+1 stages, so both
//    release on the same edge.
// Cycle-exact with the separate pair (landing PINREG=1 + packet RXREG=1) when that pair's rst_n is the same relayed
// reset: tb_hbm_host_cp_rx_lockstep compares every output every edge. Reset release: +3 edges (configuration only;
// the host link is elastic). Every remaining tile pin is a flop Q / lands in a pin flop as in the two masters.
// Pins: endpoint face (E) in_v/in_data/pop + f_send/f_flit/t_cr; ingress AXI-lite master + status (S).
module ot_hbm_host_cp_rx #(parameter integer TXC=32, parameter integer RRELAY=1,
 parameter integer MUT=0   // bench: 1 rx word bit 40 flipped inside the fold, 2 packet without its reset relay
)(
 input wire clk,rst_n,
 // endpoint face: host link rx into the landing FIFO, credit return, tx flits, tx credit
 input wire in_v,input wire [544:0] in_data,output wire pop,
 output wire f_send,output wire [544:0] f_flit,input wire t_cr,
 // AXI-lite master toward ot_hbm_host_static_ingress
 output wire s_awvalid,input wire s_awready,output wire [11:0] s_awaddr,
 output wire s_wvalid,input wire s_wready,output wire [31:0] s_wdata,output wire [3:0] s_wstrb,
 input wire s_bvalid,input wire [1:0] s_bresp,output wire s_bready,
 output wire s_arvalid,input wire s_arready,output wire [11:0] s_araddr,
 input wire s_rvalid,output wire s_rready,input wire [31:0] s_rdata,
 // die status in (ot_hbm_status_join), faults out
 input wire irq,fault,
 output wire land_fault,protocol_fault
);
 wire [0:0] lrst;
 generate if(RRELAY!=0)begin:g_lr
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_lr(.clk(clk),.rst_n_in(rst_n),.rst_n(lrst));
 end else begin:g_lr0
  assign lrst=rst_n;
 end endgenerate
 wire l_v,p_ready;wire [511:0] l_data;
 ot_hbm_host_landing256 #(.PINREG(1)) u_land(.clk(clk),.rst_n(lrst[0]),.in_v(in_v),.in_data(in_data),
  .out_v(l_v),.out_data(l_data),.out_ready(p_ready),.pop(pop),.fault(land_fault));
 wire [511:0] rx_word=(MUT==1)?(l_data^(512'd1<<40)):l_data;
 ot_hbm_host_packet_static #(.TXC(TXC),.RXREG(0),.RRELAY((MUT==2)?0:RRELAY)) u_pkt(.clk(clk),.rst_n(rst_n),
  .rx_valid(l_v),.rx_packet(rx_word),.rx_ready(p_ready),
  .f_send(f_send),.f_flit(f_flit),.t_cr(t_cr),
  .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),
  .s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
  .s_bvalid(s_bvalid),.s_bresp(s_bresp),.s_bready(s_bready),
  .s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
  .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),
  .irq(irq),.fault(fault),.protocol_fault(protocol_fault));
endmodule
`default_nettype wire
