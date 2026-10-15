`timescale 1ns/1ps
// Five real scheduled pass-through lanes, physical 3..7.
// Independent delivered clock entry per lane plus adapter; compiler must price
// their measured phases/insertion. No independent asynchronous clock crossing. The compiler provides
// every calendar edge; no runtime demand arbitration. adapter + CRC2 + GBX1
// TX edges and GBX1 + CRC2 + adapter1 RX edges are all charged separately.
// tx_seq is sampled one edge after adapter TX slot. RX expected metadata is
// sampled one edge after the gearbox frame-completion edge. rx_slot is sampled
// three edges after gearbox completion. PHY flight/relays remain extra.
module s81_static_fmt1_channels_clocked #(parameter integer MUT=0)(
 input wire clk_adapter, input wire[4:0]clk_lane, input wire rst_n,
 input wire[4:0]tx_slot,rx_slot,input wire[9:0]tx_kind,rx_kind,
 input wire vm_tx_last,vm_tx_valid,input wire[2:0]vm_tx_channel,
 input wire[551:0]vm_tx_payload,input wire[513:0]wfc_tx,
 input wire host_tx_valid,input wire[10:0]host_status,input wire[64:0]host_completion,
 output wire vm_rx_last,vm_rx_valid,output wire[2:0]vm_rx_channel,
 output wire[551:0]vm_rx_payload,output wire[513:0]wfc_rx,output wire[515:0]host_rx,
 input wire[49:0]tx_seq,rx_expected_seq,input wire[4:0]rx_expected_last,
 input wire[4:0]tx_beat_slot,tx_frame_slot,rx_beat_slot,rx_frame_slot,
 input wire[9:0]tx_phase,rx_phase,
 output wire[4:0]phy_tx_valid,output wire[2559:0]phy_tx_data,
 input wire[4:0]phy_rx_valid,input wire[2559:0]phy_rx_data,
 output wire fault
);
 wire[4:0]lane_tx_valid,lane_tx_last,lane_rx_valid,lane_rx_last,lf;
 wire[2759:0]lane_tx_payload,lane_rx_payload;wire af;
 dsfd_coll_static_channels a(.*,.clk(clk_adapter),.fault(af));
 genvar c;
 generate for(c=0;c<5;c=c+1)begin:g_lane
 s81_static_raw_fmt1_lane #(.MUT(MUT)) l(.clk(clk_lane[c]),.rst_n(rst_n),
 .tx_v(lane_tx_valid[c]),.tx_seq(tx_seq[c*10+:10]),.tx_last(lane_tx_last[c]),.tx_payload(lane_tx_payload[c*552+:552]),
 .rx_v(lane_rx_valid[c]),.rx_last(lane_rx_last[c]),.rx_payload(lane_rx_payload[c*552+:552]),
 .rx_expected_seq(rx_expected_seq[c*10+:10]),.rx_expected_last(rx_expected_last[c]),
 .tx_beat_slot(tx_beat_slot[c]),.tx_phase(tx_phase[c*2+:2]),.tx_frame_slot(tx_frame_slot[c]),
 .rx_beat_slot(rx_beat_slot[c]),.rx_phase(rx_phase[c*2+:2]),.rx_frame_slot(rx_frame_slot[c]),
 .phy_tx_valid(phy_tx_valid[c]),.phy_tx_data(phy_tx_data[c*512+:512]),
 .phy_rx_valid(phy_rx_valid[c]),.phy_rx_data(phy_rx_data[c*512+:512]),.fault(lf[c]));
 end endgenerate
 assign fault=af|(|lf);
endmodule
