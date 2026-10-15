`timescale 1ns/1ps
// Hardened lane root, actual CRC pipeline and static FMT1 gearbox; no macros.
module s81_static_fmt1_lane #(parameter integer PEER=0)(
 input wire clk,rst_n,input wire tx_v,input wire[568:0]tx_record,
 output wire rx_v,output wire[568:0]rx_record,
 input wire tx_beat_slot,input wire[1:0]tx_phase,input wire tx_frame_slot,
 input wire rx_beat_slot,input wire[1:0]rx_phase,input wire rx_frame_slot,
 output wire phy_tx_valid,output wire[511:0]phy_tx_data,
 input wire phy_rx_valid,input wire[511:0]phy_rx_data,
 output wire fault
);
 wire tv,gv,cf,gf;wire[594:0]tf,gr;
 s81_static_fmt1_codec #(.PEER(PEER)) c(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_record(tx_record),
  .tx_frame_v(tv),.tx_frame(tf),.rx_frame_v(gv),.rx_frame(gr),.rx_v(rx_v),.rx_record(rx_record),.fault(cf));
 s81_static_fmt1_gearbox b(.*,.tx_frame_v(tv),.tx_frame(tf),.rx_frame_v(gv),.rx_frame(gr),.fault(gf));
 assign fault=cf || gf;
endmodule
