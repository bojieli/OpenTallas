`timescale 1ns/1ps
// Current one-clock parent baseline only. Owns original wrapper+slab reset
// stages (four flops) and unchanged calendar/three ROMs. Calendar7 needs
// distinct extracted seven-root cuts and is not silently substituted here.
module s81_static_calendar_root #(
 parameter ROM_FILE="", parameter integer CYCLES=1,
 parameter integer AW=(CYCLES<2 ? 1:$clog2(CYCLES))
)(
 input wire clk,rst_n_in,input wire [84:0] c_cmd,
 output reg [8:0] c_done,output wire [1:0] c_st,
 input wire datapath_fault,
 output reg read_slot,
 output reg [13:0] read_row,
 output reg issue_slot,
 output reg [31:0] tag,
 output reg [15:0] seq,
 output reg last,
 output reg [3:0] rankmask,
 output reg commit_slot,
 output reg [31:0] commit_tag,
 output reg [15:0] commit_seq,
 output reg commit_last,
 output reg [3:0] commit_rankmask,
 output reg [59:0] commit_rows,
 output reg tx_beat_slot,
 output reg [1:0] tx_phase,
 output reg tx_frame_slot,
 output reg rx_beat_slot,
 output reg [1:0] rx_phase,
 output reg rx_frame_slot,
 output reg [4:0] channel_tx_slot,
 output reg [9:0] channel_tx_kind,
 output reg [49:0] channel_tx_seq,
 output reg [4:0] channel_tx_last,
 output reg [4:0] channel_rx_slot,
 output reg [9:0] channel_rx_kind,
 output reg [49:0] channel_rx_seq,
 output reg [4:0] channel_rx_last,
 output reg [4:0] channel_tx_beat_slot,
 output reg [4:0] channel_tx_frame_slot,
 output reg [9:0] channel_tx_phase,
 output reg [4:0] channel_rx_beat_slot,
 output reg [4:0] channel_rx_frame_slot,
 output reg [9:0] channel_rx_phase,
 output reg hc_reduce_slot,
 output reg hc_write_slot,
 output reg [3:0] hc_word_index,
 output reg [15:0] hc_expect_seq,
 output reg hc_expect_last,
 output reg hc_emit_slot,
 output reg [31:0] hc_emit_tag,
 output reg commit_gather,
 output reg raw_capture_payload_slot,
 output reg raw_capture_meta_slot,
 output reg raw_rx_write_slot,
 output reg [13:0] raw_rx_payload_row,
 output reg [13:0] raw_rx_meta_row,
 output reg [7:0] raw_rx_tag,
 output reg hc_assemble_slot,
 output wire busy
,output wire rst_n_slab,rst_n_calendar
);
 reg[1:0]reset_q,rr;
 always @(posedge clk or negedge rst_n_in)
  if(!rst_n_in)reset_q<=0;else reset_q<={reset_q[0],1'b1};
 assign rst_n_slab=reset_q[1];
 always @(posedge clk or negedge rst_n_slab)
  if(!rst_n_slab)rr<=0;else rr<={rr[0],1'b1};
 assign rst_n_calendar=rr[1];
 s81_static_calendar_controller #(.ROM_FILE(ROM_FILE),.CYCLES(CYCLES),.AW(AW)) calendar(
  .clk(clk),.rst_n(rst_n_calendar),.*);
endmodule
