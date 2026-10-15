`timescale 1ns/1ps
// Protocol-compatible normal-mode successor. Compiler beat period4 and three
// records/group produce source issues4,4,8cycles. ZeroPHYflight component
// source issue->gather11cycles; actual relays/flight require static alignment.
module s81_static_fmt1_rank_dynamic(
 input wire [1:0] rank,input wire clk,rst_n,issue_slot,src_valid,input wire[511:0]src_data,
 input wire[31:0]tag,input wire[15:0]seq,input wire last,input wire[3:0]rankmask,
 input wire commit_slot,input wire[31:0]commit_tag,input wire[15:0]commit_seq,
 input wire commit_last,input wire[3:0]commit_rankmask,input wire[59:0]commit_rows,
 input wire tx_beat_slot,input wire[1:0]tx_phase,input wire tx_frame_slot,
 input wire rx_beat_slot,input wire[1:0]rx_phase,input wire rx_frame_slot,
 output wire[2:0]phy_tx_valid,output wire[1535:0]phy_tx_data,
 input wire[2:0]phy_rx_valid,input wire[1535:0]phy_rx_data,
 output wire[3:0]vm_we,output wire[59:0]vm_rows,output wire[2047:0]vm_data,
 output wire [31:0] gather_tag,output wire [15:0] gather_seq,output wire gather_last,
 output wire fault
);
 s81_static_fmt1_rank_dynamic_clocked impl(.*,.clk_core(clk),.clk_lane({3{clk}}));
endmodule
