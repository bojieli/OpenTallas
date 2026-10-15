`timescale 1ns/1ps
// Protocol-compatible normal-mode successor. Compiler beat period4 and three
// records/group produce source issues4,4,8cycles. ZeroPHYflight component
// source issue->gather11cycles; actual relays/flight require static alignment.
module s81_static_fmt1_rank #(parameter integer RANK=0)(
 input wire clk,rst_n,issue_slot,src_valid,input wire[511:0]src_data,
 input wire[31:0]tag,input wire[15:0]seq,input wire last,input wire[3:0]rankmask,
 input wire commit_slot,input wire[31:0]commit_tag,input wire[15:0]commit_seq,
 input wire commit_last,input wire[3:0]commit_rankmask,input wire[59:0]commit_rows,
 input wire tx_beat_slot,input wire[1:0]tx_phase,input wire tx_frame_slot,
 input wire rx_beat_slot,input wire[1:0]rx_phase,input wire rx_frame_slot,
 output wire[2:0]phy_tx_valid,output wire[1535:0]phy_tx_data,
 input wire[2:0]phy_rx_valid,input wire[1535:0]phy_rx_data,
 output wire[3:0]vm_we,output wire[59:0]vm_rows,output wire[2047:0]vm_data,
 output wire fault
);
 wire txv,ef;wire[568:0]txf;wire[3:0]rv;wire[2275:0]rf;wire[2:0]lf;
 s81_static_fmt1_core #(.RANK(RANK)) core(.*,.tx_valid(txv),.tx_frame(txf),.remote_v(rv),.remote_frame(rf),.fault(ef));
 assign rv[RANK]=1'b0;assign rf[RANK*569+:569]=569'b0;
 genvar g;
 generate for(g=0;g<3;g=g+1)begin:L
  localparam integer PEER=g<RANK ? g:g+1;
  s81_static_fmt1_lane #(.PEER(PEER)) lane(.clk(clk),.rst_n(rst_n),.tx_v(txv),.tx_record(txf),
   .rx_v(rv[PEER]),.rx_record(rf[PEER*569+:569]),
   .tx_beat_slot(tx_beat_slot),.tx_phase(tx_phase),.tx_frame_slot(tx_frame_slot),
   .rx_beat_slot(rx_beat_slot),.rx_phase(rx_phase),.rx_frame_slot(rx_frame_slot),
   .phy_tx_valid(phy_tx_valid[g]),.phy_tx_data(phy_tx_data[g*512+:512]),
   .phy_rx_valid(phy_rx_valid[g]),.phy_rx_data(phy_rx_data[g*512+:512]),.fault(lf[g]));
 end endgenerate
 assign fault=ef || |lf;
endmodule
