`timescale 1ns/1ps
module s81_static_raw_fmt1_lane #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire tx_v,input wire[9:0]tx_seq,
 input wire tx_last,input wire[551:0]tx_payload,
 output wire rx_v,output wire rx_last,output wire[551:0]rx_payload,
 input wire[9:0]rx_expected_seq,input wire rx_expected_last,
 input wire tx_beat_slot,input wire[1:0]tx_phase,input wire tx_frame_slot,
 input wire rx_beat_slot,input wire[1:0]rx_phase,input wire rx_frame_slot,
 output wire phy_tx_valid,output wire[511:0]phy_tx_data,
 input wire phy_rx_valid,input wire[511:0]phy_rx_data,output wire fault
);
 wire tv,gv,cf,gf;wire[594:0]tf,gr;
 s81_static_raw_fmt1_codec #(.MUT(MUT)) c(.clk(clk),.rst_n(rst_n),
 .tx_v(tx_v),.tx_seq(tx_seq),.tx_last(tx_last),.tx_payload(tx_payload),
 .tx_frame_v(tv),.tx_frame(tf),.rx_frame_v(gv),.rx_frame(gr),
 .rx_expected_seq(rx_expected_seq),.rx_expected_last(rx_expected_last),
 .rx_v(rx_v),.rx_last(rx_last),.rx_payload(rx_payload),.fault(cf));
 s81_static_fmt1_gearbox b(.*,.tx_frame_v(tv),.tx_frame(tf),.rx_frame_v(gv),.rx_frame(gr),.fault(gf));
 assign fault=cf|gf;
endmodule
